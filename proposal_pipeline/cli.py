"""제안서 생성 CLI (v2).

사용법:
  # 참조 데이터로 테스트 (Gamma 없이 고정 페이지만)
  proposal-generate --customer "삼성전자" --title "AI 교육" \\
      --modules process-structuring,rag-agent --sample

  # PBL + 사례 포함
  proposal-generate --customer "현대자동차" --title "AI 교육" \\
      --modules prompt-rubric --sample \\
      --pbl part_pbl_로드맵,part_pbl_마일스톤 \\
      --cases part_사례_르노코리아,part_사례_현대차

  # LLM 생성 커리큘럼 JSON 사용
  proposal-generate --customer "LG전자" --title "AI 교육" \\
      --curriculum-json curriculum.json

  # Gamma 설득 파트 포함
  proposal-generate --customer "삼성전자" --title "AI 교육" \\
      --modules process-structuring --sample --with-gamma
"""

import argparse
import json
import logging
import math
import sys
from datetime import date
from pathlib import Path

from .config import GAMMA_API_KEY, GAMMA_BASE_URL
from .curriculum.models import CurriculumModule, DesignBackground, FlowStep, PersuasionSlide, TablePage, TopicRow
from .gamma.client import GammaHttpClient
from .pipeline.models import PipelineConfig, build_config
from .pipeline.pipeline import DefaultProposalPipeline
from .pptx_merger.merger import PptxZipMerger
from .pptx_replacer.replacer import PptxFileReplacer
from ._resources import get_template_dir, get_data_dir, set_template_dir

DEFAULT_GAMMA_PROMPT = """\
고객사: {{고객명}}
산업: {{산업}}
교육 목표: {{목표}}
현재 페인포인트: {{페인포인트}}
선택 교육 과정: {{모듈_요약}}

위 정보를 바탕으로 AI 교육 제안서의 핵심 설득 파트를 생성해주세요:
1. 고객사의 현재 AI 도입 Gap 분석
2. 교육 솔루션 제안 (선택된 과정 기반)
3. 핵심 프레임워크 2-3개
4. 전체 교육 로드맵
5. 기대 가치 및 ROI"""


def load_modules_from_reference(
    ref_path: Path, module_ids: list[str]
) -> list[CurriculumModule]:
    """참조 JSON에서 CurriculumModule 객체 생성 (테스트/샘플 용도)."""
    with open(ref_path, encoding="utf-8") as f:
        ref = json.load(f)

    modules = []
    for mid in module_ids:
        if mid not in ref:
            available = ", ".join(ref.keys())
            raise ValueError(f"알 수 없는 모듈: {mid} (가능: {available})")

        data = ref[mid]
        topics = [TopicRow(**t) for t in data["topics"]]

        # table_pages 수에 따라 topics 분할
        n_pages = data.get("table_pages", 1)
        rows_per_page = math.ceil(len(topics) / n_pages)

        table_pages = []
        for i in range(n_pages):
            start = i * rows_per_page
            end = min(start + rows_per_page, len(topics))
            label = f"{i + 1}차" if n_pages > 1 else ""
            table_pages.append(TablePage(label=label, rows=topics[start:end]))

        modules.append(CurriculumModule(
            id=mid,
            name=data["name"],
            total_hours=data["total_hours"],
            table_pages=table_pages,
        ))

    return modules


def load_modules_from_json(json_path: Path) -> list[CurriculumModule]:
    """LLM 생성 커리큘럼 JSON에서 CurriculumModule 객체 생성."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    modules = []
    for item in data:
        table_pages = []
        for tp in item.get("table_pages", []):
            rows = [TopicRow(**r) for r in tp["rows"]]
            table_pages.append(TablePage(label=tp.get("label", ""), rows=rows))

        # 설계배경
        design_bg = None
        if "design_bg" in item:
            db = item["design_bg"]
            steps = [FlowStep(**s) for s in db.get("steps", [])]
            design_bg = DesignBackground(purpose=db["purpose"], steps=steps)

        modules.append(CurriculumModule(
            id=item["id"],
            name=item["name"],
            total_hours=item["total_hours"],
            table_pages=table_pages,
            design_bg=design_bg,
            consultant_context=item.get("consultant_context", ""),
        ))

    return modules


def load_persuasion_from_json(json_path: Path) -> list[PersuasionSlide]:
    """JSON 파일에서 설득 파트 슬라이드 목록을 로드한다.

    JSON 형식:
      { "persuasion_slides": [
          { "visual_type": "gap_analysis", "title": "...", "subtitle": "...", "data": {...} },
          ...
        ],
        ... (modules 데이터)
      }

    또는 배열 형식에서 첫 번째 객체의 persuasion_slides 필드를 읽는다.
    """
    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)

    # 배열이면 첫 번째 항목에서 추출 (또는 최상위 dict)
    if isinstance(raw, list):
        # 배열 안에 persuasion_slides를 가진 항목 탐색
        ps_list = []
        for item in raw:
            if "persuasion_slides" in item:
                ps_list = item["persuasion_slides"]
                break
        if not ps_list:
            return []
    elif isinstance(raw, dict):
        ps_list = raw.get("persuasion_slides", [])
    else:
        return []

    return [
        PersuasionSlide(
            visual_type=ps["visual_type"],
            title=ps["title"],
            subtitle=ps["subtitle"],
            data=ps.get("data", {}),
        )
        for ps in ps_list
    ]


def main():
    parser = argparse.ArgumentParser(description="제안서 생성 CLI (v2)")

    # 고객 변수
    parser.add_argument("--customer", required=True, help="고객사명")
    parser.add_argument("--title", default="AI 교육 제안서", help="교육 제목")
    parser.add_argument("--date", default=str(date.today()), help="제안 날짜")

    # 모듈 선택
    parser.add_argument(
        "--modules", default=None,
        help="모듈 ID (쉼표 구분). 예: process-structuring,rag-agent",
    )
    parser.add_argument(
        "--curriculum-json", default=None,
        help="LLM 생성 커리큘럼 JSON 파일 경로",
    )
    parser.add_argument(
        "--sample", action="store_true",
        help="참조 데이터(data/curriculum_reference.json)로 테스트",
    )

    # PBL / 사례
    parser.add_argument(
        "--pbl", default=None,
        help="PBL 파트 (쉼표 구분). 예: part_pbl_로드맵,part_pbl_마일스톤",
    )
    parser.add_argument(
        "--cases", default=None,
        help="사례 파트 (쉼표 구분). 예: part_사례_르노코리아,part_사례_현대차",
    )
    parser.add_argument("--pbl-name", default="PBL 멘토링", help="PBL 구간 표지 과정명")

    # Gamma
    parser.add_argument("--with-gamma", action="store_true", help="Gamma 설득 파트 포함")
    parser.add_argument("--gamma-theme", default="jdvmtofxo715647", help="Gamma 테마 ID")
    parser.add_argument("--industry", default="", help="산업 (Gamma 프롬프트용)")
    parser.add_argument("--goal", default="", help="교육 목표 (Gamma 프롬프트용)")
    parser.add_argument("--pain", default="", help="페인포인트 (Gamma 프롬프트용)")

    # 출력
    parser.add_argument("--output-dir", default=None, help="출력 디렉토리")
    parser.add_argument("--template-dir", default=None, help="템플릿 디렉토리 (parts 폴더)")
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 로그")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # ── 템플릿 디렉토리 설정 ──
    if args.template_dir:
        set_template_dir(Path(args.template_dir).parent)
        tpl_dir = Path(args.template_dir)
    else:
        tpl_dir = get_template_dir("parts")

    reference_json = get_data_dir() / "curriculum_reference.json"
    out_dir = Path(args.output_dir) if args.output_dir else Path("output")

    # ── 모듈 로드 ──
    if args.curriculum_json:
        json_path = Path(args.curriculum_json)
        modules = load_modules_from_json(json_path)
        persuasion_slides = load_persuasion_from_json(json_path)
    elif args.sample and args.modules:
        module_ids = [m.strip() for m in args.modules.split(",")]
        modules = load_modules_from_reference(reference_json, module_ids)
        persuasion_slides = []
    elif args.modules:
        print("ERROR: --modules 사용 시 --sample 또는 --curriculum-json이 필요합니다.", file=sys.stderr)
        sys.exit(1)
    else:
        modules = []
        persuasion_slides = []

    # ── 변수 구성 ──
    variables = {
        "고객명": args.customer,
        "교육제목": args.title,
        "날짜": args.date,
        "제안일": args.date,
        "산업": args.industry,
        "목표": args.goal,
        "페인포인트": args.pain,
        "모듈_요약": ", ".join(m.name for m in modules) if modules else "",
    }

    # ── PBL / 사례 ──
    pbl_parts = [p.strip() for p in args.pbl.split(",")] if args.pbl else None
    case_parts = [c.strip() for c in args.cases.split(",")] if args.cases else None

    # ── 설정 빌드 ──
    gamma_prompt = DEFAULT_GAMMA_PROMPT if args.with_gamma else None

    config = build_config(
        template_dir=tpl_dir,
        modules=modules,
        pbl_parts=pbl_parts,
        case_parts=case_parts,
        pbl_name=args.pbl_name,
        persuasion_slides=persuasion_slides or None,
        gamma_prompt=gamma_prompt,
        gamma_theme_id=args.gamma_theme,
        output_dir=out_dir,
    )

    # ── 파이프라인 실행 ──
    gamma_client = GammaHttpClient(
        api_key=GAMMA_API_KEY or "unused",
        base_url=GAMMA_BASE_URL,
    )
    replacer = PptxFileReplacer()
    merger = PptxZipMerger()

    pipeline = DefaultProposalPipeline(
        gamma_client=gamma_client,
        replacer=replacer,
        merger=merger,
    )

    # 요약 출력
    print(f"제안서 생성: {args.customer}")
    print(f"교육 제목: {args.title}")
    print(f"모듈: {', '.join(m.name for m in modules) if modules else '(없음)'}")
    if pbl_parts:
        print(f"PBL: {', '.join(pbl_parts)}")
    if case_parts:
        print(f"사례: {', '.join(case_parts)}")

    ordered = config.all_pages_ordered
    print(f"\n구성: 고정 {len(config.fixed_pages)}개 + 동적 {len(config.dynamic_pages)}개 = 총 {len(ordered)}개 파트")
    for p in ordered:
        tag = "FIXED" if p["type"] == "fixed" else "GAMMA"
        print(f"  [{p['order']:3d}] {tag:5s}  {p['name']}")
    print()

    result = pipeline.run(variables, config)

    print()
    if result.is_success:
        print(f"생성 완료: {result.output_path}")
        print(f"슬라이드 수: {result.total_slides}")
        print(f"고정: {result.fixed_count}, 동적: {result.dynamic_count}")
    else:
        print(f"에러 발생:")
        for e in result.errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
