"""표준 PPT를 모듈별 템플릿 PPTX로 분리하는 스크립트.

ZIP-level에서 불필요한 슬라이드를 제거하여 원본 디자인을 100% 보존한다.

사용법:
  python tools/split_pptx.py
"""

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

# XML namespaces
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"

# 분리 대상 정의: (출력 파일명, 1-based 슬라이드 번호 리스트)
#
# 파트 타입 (각 1장, 조합하여 모듈 구성):
#   구간표지     — 모듈 시작 커버
#   설계배경     — 과정 개요 (과정명, 시간)
#   타임테이블   — 커리큘럼 테이블 (데이터 주입용)
#   산출물       — 교육 산출물 예시
#   사례         — 고객 사례 (PBL 등)
#
# 조합 예시:
#   커리큘럼 모듈 = 구간표지 + 설계배경 + 타임테이블(×N) + 산출물
#   PBL 모듈     = 구간표지 + pbl설명(×4) + 사례(×N)
SPLITS = [
    # 고정 파트
    ("00_표지.pptx", [1]),
    ("01_도입부.pptx", [2, 3]),
    ("99_엔딩.pptx", [45]),
    # 파트 템플릿 (커리큘럼 모듈 구성 블록)
    ("part_구간표지.pptx", [11]),
    ("part_설계배경.pptx", [12]),
    ("part_타임테이블.pptx", [13]),
    ("part_산출물.pptx", [14]),
    # PBL 설명 (설계배경 카테고리, static)
    ("part_pbl_로드맵.pptx", [37]),
    ("part_pbl_레벨무관.pptx", [38]),
    ("part_pbl_마일스톤.pptx", [39]),
    ("part_pbl_피드백.pptx", [40]),
    # 사례 (static, 개별 선택 가능)
    ("part_사례_성과공유.pptx", [41]),
    ("part_사례_르노코리아.pptx", [42]),
    ("part_사례_현대차.pptx", [43]),
    ("part_사례_한투증권.pptx", [44]),
]


def _write_xml(tree, path: Path):
    raw = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
    raw = raw.replace(
        b"<?xml version='1.0' encoding='UTF-8' standalone='yes'?>",
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        1,
    )
    path.write_bytes(raw)


def _unzip(zip_path: Path, dest: Path):
    with zipfile.ZipFile(str(zip_path), "r") as z:
        z.extractall(str(dest))


def _zipdir(src_dir: Path, zip_path: Path):
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(src_dir.rglob("*")):
            if f.is_file() and f.name != "desktop.ini":
                z.write(str(f), f.relative_to(src_dir).as_posix())


def _get_slide_order(base: Path) -> list[int]:
    """presentation.xml의 sldIdLst에서 슬라이드 순서를 파악한다.

    Returns: 1-based 슬라이드 번호 리스트 (표시 순서대로)
    """
    pres_xml = base / "ppt" / "presentation.xml"
    tree = etree.parse(str(pres_xml))
    root = tree.getroot()

    # presentation.xml.rels에서 rId → slide 번호 매핑
    pres_rels = base / "ppt" / "_rels" / "presentation.xml.rels"
    rels_tree = etree.parse(str(pres_rels))
    rid_to_slide = {}
    for rel in rels_tree.getroot():
        target = rel.get("Target", "")
        m = re.search(r"slides/slide(\d+)\.xml", target)
        if m:
            rid_to_slide[rel.get("Id")] = int(m.group(1))

    # sldIdLst 순서대로 슬라이드 번호 수집
    sld_lst = root.find(f"{{{_NS_P}}}sldIdLst")
    order = []
    if sld_lst is not None:
        for sld_id in sld_lst:
            rid = sld_id.get(f"{{{_NS_R}}}id")
            if rid in rid_to_slide:
                order.append(rid_to_slide[rid])
    return order


def _remove_slides(base: Path, keep_indices: list[int]):
    """keep_indices(0-based)에 해당하지 않는 슬라이드를 제거한다."""
    slide_order = _get_slide_order(base)
    keep_slide_nums = {slide_order[i] for i in keep_indices if i < len(slide_order)}
    remove_slide_nums = {n for n in slide_order if n not in keep_slide_nums}

    if not remove_slide_nums:
        return

    # 1. presentation.xml에서 sldId 제거 + rels에서 관계 제거
    pres_xml = base / "ppt" / "presentation.xml"
    pres_rels = base / "ppt" / "_rels" / "presentation.xml.rels"

    pres_tree = etree.parse(str(pres_xml))
    pres_root = pres_tree.getroot()
    rels_tree = etree.parse(str(pres_rels))
    rels_root = rels_tree.getroot()

    # rId → slide 번호 매핑
    rid_to_slide = {}
    for rel in list(rels_root):
        target = rel.get("Target", "")
        m = re.search(r"slides/slide(\d+)\.xml", target)
        if m:
            slide_num = int(m.group(1))
            rid_to_slide[rel.get("Id")] = slide_num
            if slide_num in remove_slide_nums:
                rels_root.remove(rel)

    # sldIdLst에서 제거
    sld_lst = pres_root.find(f"{{{_NS_P}}}sldIdLst")
    if sld_lst is not None:
        for sld_id in list(sld_lst):
            rid = sld_id.get(f"{{{_NS_R}}}id")
            if rid in rid_to_slide and rid_to_slide[rid] in remove_slide_nums:
                sld_lst.remove(sld_id)

    _write_xml(pres_tree, pres_xml)
    _write_xml(rels_tree, pres_rels)

    # 2. 슬라이드 XML + rels 파일 삭제
    for n in remove_slide_nums:
        slide_xml = base / f"ppt/slides/slide{n}.xml"
        slide_rels = base / f"ppt/slides/_rels/slide{n}.xml.rels"
        if slide_xml.exists():
            slide_xml.unlink()
        if slide_rels.exists():
            slide_rels.unlink()

    # 3. [Content_Types].xml에서 제거된 슬라이드 Override 제거
    ct_xml = base / "[Content_Types].xml"
    ct_tree = etree.parse(str(ct_xml))
    ct_root = ct_tree.getroot()
    for override in list(ct_root):
        part_name = override.get("PartName", "")
        m = re.search(r"/ppt/slides/slide(\d+)\.xml", part_name)
        if m and int(m.group(1)) in remove_slide_nums:
            ct_root.remove(override)
    _write_xml(ct_tree, ct_xml)

    # 4. app.xml 슬라이드 카운트 갱신
    _fix_app_xml(base, len(keep_slide_nums))


def _fix_app_xml(base: Path, slide_count: int):
    _NS_EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
    app_xml = base / "docProps" / "app.xml"
    if not app_xml.exists():
        return
    tree = etree.parse(str(app_xml))
    root = tree.getroot()
    el = root.find(f"{{{_NS_EP}}}Slides")
    if el is not None:
        el.text = str(slide_count)
    _write_xml(tree, app_xml)


def _strip_notes(base: Path):
    """notesSlides 참조를 슬라이드 rels에서 제거한다 (복원 에러 방지)."""
    slides_rels = base / "ppt" / "slides" / "_rels"
    if not slides_rels.exists():
        return
    for rels_file in slides_rels.glob("*.xml.rels"):
        tree = etree.parse(str(rels_file))
        root = tree.getroot()
        changed = False
        for rel in list(root):
            if "notesSlide" in rel.get("Type", ""):
                root.remove(rel)
                changed = True
        if changed:
            _write_xml(tree, rels_file)


def extract_slides(source_pptx: Path, output_pptx: Path, slide_numbers_1based: list[int]):
    """source_pptx에서 지정된 슬라이드만 추출하여 output_pptx로 저장한다.

    Args:
        source_pptx: 원본 PPTX 경로
        output_pptx: 출력 PPTX 경로
        slide_numbers_1based: 추출할 슬라이드 번호 (1-based, 표시 순서 기준)
    """
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "work"
        _unzip(source_pptx, work)

        # 표시 순서 → 0-based index 변환
        slide_order = _get_slide_order(work)
        keep_indices = []
        for target_num in slide_numbers_1based:
            # slide_order에서 target_num번째 슬라이드의 index를 찾음
            # slide_numbers_1based는 "표시 순서 기준 N번째"를 의미
            if 1 <= target_num <= len(slide_order):
                keep_indices.append(target_num - 1)

        _remove_slides(work, keep_indices)
        _strip_notes(work)

        output_pptx.parent.mkdir(parents=True, exist_ok=True)
        _zipdir(work, output_pptx)


def main():
    base_dir = Path(__file__).parent.parent
    source = base_dir.parent / "[팀스파르타] SKI E&S 26년 AX 커리큘럼.pptx"
    templates_dir = base_dir / "templates"

    if not source.exists():
        print(f"원본 PPT를 찾을 수 없습니다: {source}")
        return

    templates_dir.mkdir(parents=True, exist_ok=True)

    print(f"원본: {source}")
    print(f"출력: {templates_dir}")
    print()

    for filename, slides in SPLITS:
        output = templates_dir / filename
        print(f"  {filename} ← 슬라이드 {slides} ... ", end="", flush=True)
        try:
            extract_slides(source, output, slides)
            # 검증: 슬라이드 수 확인
            from pptx import Presentation
            prs = Presentation(str(output))
            actual = len(prs.slides)
            expected = len(slides)
            status = "OK" if actual == expected else f"WARN({actual}장)"
            print(f"{status}")
        except Exception as e:
            print(f"FAIL: {e}")

    print()
    print("분리 완료. 각 파일을 PowerPoint에서 열어 디자인을 확인하세요.")


if __name__ == "__main__":
    main()
