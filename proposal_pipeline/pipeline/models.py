"""파이프라인 설정 및 데이터 모델."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from ..curriculum.models import CurriculumModule, DesignBackground, PersuasionSlide, TopicRow


class FixedPage(BaseModel):
    """고정 페이지 정의 — 치환 후 합성에 포함될 PPTX.

    v2 확장:
      - part_variables: 파트별 치환 변수 (전역 변수보다 우선)
      - table_rows: 테이블 주입 데이터 (있으면 슬라이드 0의 테이블에 주입)
    """
    name: str
    template_path: Path = Field(alias="templatePath")
    order: int
    part_variables: dict[str, str] = Field(default_factory=dict, alias="partVariables")
    table_rows: Optional[list[TopicRow]] = Field(None, alias="tableRows")
    design_bg: Optional[DesignBackground] = Field(None, alias="designBg")
    persuasion_slide: Optional[PersuasionSlide] = Field(None, alias="persuasionSlide")

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class DynamicPage(BaseModel):
    """동적 페이지 정의 — Gamma API로 생성될 콘텐츠.

    mode:
      - "template": Create from Template API (gammaId 필수)
      - "generate": Generate API (gammaId 불필요, promptTemplate을 inputText로 사용)
    """
    name: str
    mode: Literal["template", "generate"] = "generate"
    gamma_id: Optional[str] = Field(None, alias="gammaId")
    prompt_template: str = Field(alias="promptTemplate")
    order: int
    num_cards: int = Field(8, alias="numCards")
    export_as: str = Field("pptx", alias="exportAs")

    model_config = {"populate_by_name": True}


class PipelineConfig(BaseModel):
    """제안서 생성 파이프라인 설정."""
    fixed_pages: list[FixedPage] = Field(default_factory=list, alias="fixedPages")
    dynamic_pages: list[DynamicPage] = Field(default_factory=list, alias="dynamicPages")
    output_dir: Path = Field(Path("output"), alias="outputDir")
    gamma_theme_id: Optional[str] = Field(None, alias="gammaThemeId")

    model_config = {"populate_by_name": True}

    @property
    def all_pages_ordered(self) -> list[dict]:
        """고정 + 동적 페이지를 order 기준으로 정렬하여 반환."""
        pages = []
        for fp in self.fixed_pages:
            pages.append({"type": "fixed", "name": fp.name, "order": fp.order, "ref": fp})
        for dp in self.dynamic_pages:
            pages.append({"type": "dynamic", "name": dp.name, "order": dp.order, "ref": dp})
        return sorted(pages, key=lambda x: x["order"])


class PipelineResult(BaseModel):
    """파이프라인 실행 결과."""
    output_path: Path = Field(alias="outputPath")
    fixed_count: int = Field(0, alias="fixedCount")
    dynamic_count: int = Field(0, alias="dynamicCount")
    total_slides: int = Field(0, alias="totalSlides")
    errors: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @property
    def is_success(self) -> bool:
        return len(self.errors) == 0


# ── 설정 빌더 ──────────────────────────────────────────────────────────

def build_config(
    template_dir: Path,
    modules: list[CurriculumModule],
    pbl_parts: list[str] | None = None,
    case_parts: list[str] | None = None,
    pbl_name: str = "PBL 멘토링",
    persuasion_slides: list[PersuasionSlide] | None = None,
    gamma_prompt: str | None = None,
    gamma_theme_id: str | None = None,
    output_dir: Path = Path("output"),
) -> PipelineConfig:
    """모듈 선택 → FixedPage/DynamicPage 목록 자동 생성.

    Args:
        template_dir: 템플릿 PPTX 디렉토리 (00_표지.pptx, part_*.pptx 등)
        modules: 포함할 커리큘럼 모듈 목록
        pbl_parts: PBL 설명 파트 파일명 (예: ["part_pbl_로드맵", "part_pbl_마일스톤"])
        case_parts: 사례 파트 파일명 (예: ["part_사례_르노코리아"])
        pbl_name: PBL 구간 표지에 표시할 과정명
        persuasion_slides: 설득 파트 슬라이드 목록 (order 30~39)
        gamma_prompt: Gamma 설득 파트 프롬프트 (None이면 생략)
        gamma_theme_id: Gamma 테마 ID
        output_dir: 출력 디렉토리
    """
    fixed: list[FixedPage] = []

    # ── 1. 표지 (order=10) ──
    fixed.append(FixedPage(
        name="표지",
        templatePath=template_dir / "00_표지.pptx",
        order=10,
    ))

    # ── 2. 도입부 (order=20) ──
    fixed.append(FixedPage(
        name="도입부",
        templatePath=template_dir / "01_도입부.pptx",
        order=20,
    ))

    # ── 3. 설득 파트 (order=30~39) ──
    if persuasion_slides:
        persuasion_template = template_dir / "part_설득.pptx"
        for i, ps in enumerate(persuasion_slides):
            fixed.append(FixedPage(
                name=f"설득/{ps.visual_type}",
                templatePath=persuasion_template,
                order=30 + i,
                partVariables={"설득_제목": ps.title, "설득_부제": ps.subtitle},
                persuasionSlide=ps,
            ))

    # ── 4. 커리큘럼 모듈들 (order=100~) ──
    order = 100
    for mod in modules:
        mod_vars = {"과정명": mod.name, "시간": mod.total_hours}

        # 구간표지
        fixed.append(FixedPage(
            name=f"{mod.id}/구간표지",
            templatePath=template_dir / "part_구간표지.pptx",
            order=order,
            partVariables={"과정명": mod.name},
        ))
        order += 1

        # 설계배경
        fixed.append(FixedPage(
            name=f"{mod.id}/설계배경",
            templatePath=template_dir / "part_설계배경.pptx",
            order=order,
            partVariables=mod_vars,
            designBg=mod.design_bg,
        ))
        order += 1

        # 타임테이블 (N장 — table_pages 수만큼)
        for tp in mod.table_pages:
            suffix = f"/{tp.label}" if tp.label else ""
            fixed.append(FixedPage(
                name=f"{mod.id}/타임테이블{suffix}",
                templatePath=template_dir / "part_타임테이블.pptx",
                order=order,
                partVariables=mod_vars,
                tableRows=tp.rows,
            ))
            order += 1

        # 산출물
        fixed.append(FixedPage(
            name=f"{mod.id}/산출물",
            templatePath=template_dir / "part_산출물.pptx",
            order=order,
        ))
        order += 1

        # 모듈 간 10단위 경계 맞춤
        order = ((order // 10) + 1) * 10

    # ── 5. PBL ──
    if pbl_parts or case_parts:
        fixed.append(FixedPage(
            name="pbl/구간표지",
            templatePath=template_dir / "part_구간표지.pptx",
            order=order,
            partVariables={"과정명": pbl_name},
        ))
        order += 1

        for part in (pbl_parts or []):
            fname = f"{part}.pptx" if not part.endswith(".pptx") else part
            fixed.append(FixedPage(
                name=f"pbl/{Path(fname).stem}",
                templatePath=template_dir / fname,
                order=order,
            ))
            order += 1

        for case in (case_parts or []):
            fname = f"{case}.pptx" if not case.endswith(".pptx") else case
            fixed.append(FixedPage(
                name=f"pbl/{Path(fname).stem}",
                templatePath=template_dir / fname,
                order=order,
            ))
            order += 1

    # ── 6. 엔딩 (order=990) ──
    fixed.append(FixedPage(
        name="엔딩",
        templatePath=template_dir / "99_엔딩.pptx",
        order=990,
    ))

    # ── Dynamic pages ──
    dynamic: list[DynamicPage] = []
    if gamma_prompt:
        dynamic.append(DynamicPage(
            name="설득파트",
            mode="generate",
            promptTemplate=gamma_prompt,
            order=30,
            numCards=7,
            exportAs="pptx",
        ))

    return PipelineConfig(
        fixedPages=fixed,
        dynamicPages=dynamic,
        outputDir=output_dir,
        gammaThemeId=gamma_theme_id,
    )
