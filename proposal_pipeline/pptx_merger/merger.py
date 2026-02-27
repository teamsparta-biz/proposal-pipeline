"""PPTX 합성 엔진 — ZIP-level merge로 원본 디자인을 완벽히 보존한다.

python-pptx shape 복사 대신 ZIP 내 XML 파트를 통째로 이동하므로
슬라이드 배경·테마·이미지·벡터 등 원본 디자인이 100% 보존된다.
"""

from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from lxml import etree
from pptx.presentation import Presentation as PresentationType

# XML namespaces
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"


class PptxMerger(ABC):
    """PPTX 합성 추상 인터페이스."""

    @abstractmethod
    def merge_and_save(
        self, sources: list[Union[Path, PresentationType]], output_path: Path
    ) -> Path:
        """여러 PPTX를 순서대로 합쳐서 output_path에 저장."""


class PptxZipMerger(PptxMerger):
    """ZIP-level PPTX 합성 — 원본 디자인 완전 보존."""

    def merge_and_save(self, sources, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        paths, tmps = [], []
        for s in sources:
            if isinstance(s, PresentationType):
                tf = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
                s.save(tf.name)
                tf.close()
                paths.append(Path(tf.name))
                tmps.append(tf.name)
            else:
                paths.append(Path(s))

        if not paths:
            raise ValueError("합성할 소스가 없습니다.")

        try:
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                base = td / "base"
                _unzip(paths[0], base)

                for i, p in enumerate(paths[1:], 2):
                    src = td / f"s{i}"
                    _unzip(p, src)
                    _append(base, src)
                    shutil.rmtree(src)

                _fix_app_xml(base)
                _zipdir(base, output_path)
        finally:
            for t in tmps:
                Path(t).unlink(missing_ok=True)

        return output_path


# 하위 호환용 alias
PptxFileMerger = PptxZipMerger


# ── helpers ──────────────────────────────────────────────────────────

def _write_xml(tree, path: Path):
    """lxml 트리를 PowerPoint 호환 XML로 저장 (쌍따옴표 선언)."""
    raw = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
    # lxml은 작은따옴표를 쓰지만 PowerPoint는 쌍따옴표를 기대
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


# ── scan ─────────────────────────────────────────────────────────────

def _nums(directory: Path, prefix: str) -> list[int]:
    """prefix + N + .xml 파일에서 숫자를 추출."""
    pat = re.compile(rf"^{re.escape(prefix)}(\d+)\.xml$")
    if not directory.exists():
        return []
    return sorted(int(m.group(1)) for f in directory.iterdir() if (m := pat.match(f.name)))


def _scan(d: Path) -> dict:
    return {
        "slides": _nums(d / "ppt/slides", "slide"),
        "layouts": _nums(d / "ppt/slideLayouts", "slideLayout"),
        "masters": _nums(d / "ppt/slideMasters", "slideMaster"),
        "themes": _nums(d / "ppt/theme", "theme"),
        "sld": max(_nums(d / "ppt/slides", "slide"), default=0),
        "lay": max(_nums(d / "ppt/slideLayouts", "slideLayout"), default=0),
        "mst": max(_nums(d / "ppt/slideMasters", "slideMaster"), default=0),
        "thm": max(_nums(d / "ppt/theme", "theme"), default=0),
    }


# ── append ───────────────────────────────────────────────────────────

def _append(base: Path, src: Path):
    """src의 모든 슬라이드를 base에 추가한다."""
    b, s = _scan(base), _scan(src)

    sld = {n: n + b["sld"] for n in s["slides"]}
    lay = {n: n + b["lay"] for n in s["layouts"]}
    mst = {n: n + b["mst"] for n in s["masters"]}
    thm = {n: n + b["thm"] for n in s["themes"]}
    med = _copy_media(base, src)

    _copy_parts(src, base, "ppt/slides", "slide", sld)
    _copy_parts(src, base, "ppt/slideLayouts", "slideLayout", lay)
    _copy_parts(src, base, "ppt/slideMasters", "slideMaster", mst)
    _copy_parts(src, base, "ppt/theme", "theme", thm, rels=False)
    # notesSlides/notesMasters는 복사하지 않음 — 복원 에러 유발

    # rewrite rels
    for n in sld.values():
        _rewrite_rels(base / f"ppt/slides/_rels/slide{n}.xml.rels",
                      {"slideLayout": lay}, med)
        _strip_notes_refs(base / f"ppt/slides/_rels/slide{n}.xml.rels")
    for n in lay.values():
        _rewrite_rels(base / f"ppt/slideLayouts/_rels/slideLayout{n}.xml.rels",
                      {"slideMaster": mst}, med)
    for n in mst.values():
        _rewrite_rels(base / f"ppt/slideMasters/_rels/slideMaster{n}.xml.rels",
                      {"slideLayout": lay, "theme": thm}, med)
        _fix_master_layout_ids(base, base / f"ppt/slideMasters/slideMaster{n}.xml")

    _register_slides(base, sld, mst)
    _register_content_types(base, sld, lay, mst, thm)
    _copy_default_types(base, src)
    _harmonize_size(base, src)


# ── copy ─────────────────────────────────────────────────────────────

def _copy_parts(src, dst, rel_dir, prefix, num_map, rels=True):
    for old, new in num_map.items():
        s = src / f"{rel_dir}/{prefix}{old}.xml"
        d = dst / f"{rel_dir}/{prefix}{new}.xml"
        if s.exists():
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(s), str(d))
        if rels:
            sr = src / f"{rel_dir}/_rels/{prefix}{old}.xml.rels"
            dr = dst / f"{rel_dir}/_rels/{prefix}{new}.xml.rels"
            if sr.exists():
                dr.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(sr), str(dr))


def _copy_media(base: Path, src: Path) -> dict[str, str]:
    """미디어 파일 복사. 충돌 시 리네임. {원본: 새이름} 반환."""
    src_media = src / "ppt" / "media"
    dst_media = base / "ppt" / "media"
    rename: dict[str, str] = {}
    if not src_media.exists():
        return rename
    dst_media.mkdir(parents=True, exist_ok=True)
    existing = {f.name for f in dst_media.iterdir() if f.is_file()}
    for f in sorted(src_media.iterdir()):
        if not f.is_file():
            continue
        name = f.name
        if name in existing:
            stem, ext = f.stem, f.suffix
            c = 1
            while name in existing:
                name = f"{stem}_m{c}{ext}"
                c += 1
            rename[f.name] = name
        shutil.copy2(str(f), str(dst_media / name))
        existing.add(name)
    return rename


# ── rewrite rels ─────────────────────────────────────────────────────

def _strip_notes_refs(rels_path: Path):
    """slide rels에서 notesSlide 참조를 제거한다."""
    if not rels_path.exists():
        return
    tree = etree.parse(str(rels_path))
    root = tree.getroot()
    removed = False
    for rel in list(root):
        rtype = rel.get("Type", "")
        if "notesSlide" in rtype:
            root.remove(rel)
            removed = True
    if removed:
        _write_xml(tree, rels_path)


def _rewrite_rels(rels_path: Path, part_maps: dict, media_map: dict):
    if not rels_path.exists():
        return
    tree = etree.parse(str(rels_path))
    for rel in tree.getroot():
        if rel.tag != f"{{{_NS_REL}}}Relationship":
            continue
        target = rel.get("Target", "")

        # part references (slideLayout, slideMaster, theme)
        for prefix, num_map in part_maps.items():
            m = re.search(rf"{re.escape(prefix)}(\d+)\.xml", target)
            if m:
                old = int(m.group(1))
                if old in num_map:
                    rel.set("Target", target.replace(
                        f"{prefix}{old}.xml", f"{prefix}{num_map[old]}.xml"))
                break

        # media references
        for old_name, new_name in media_map.items():
            if old_name in target:
                rel.set("Target", target.replace(old_name, new_name))

    _write_xml(tree, rels_path)


def _collect_all_ids(base: Path, exclude: Path | None = None) -> set[int]:
    """sldMasterId + sldLayoutId 전체를 수집 (같은 ID 공간 공유)."""
    used: set[int] = set()
    # presentation.xml의 sldMasterId
    pres = base / "ppt" / "presentation.xml"
    if pres.exists():
        for el in etree.parse(str(pres)).getroot().iter(f"{{{_NS_P}}}sldMasterId"):
            used.add(int(el.get("id", "0")))
    # 모든 master의 sldLayoutId
    masters_dir = base / "ppt" / "slideMasters"
    if masters_dir.exists():
        for f in masters_dir.glob("slideMaster*.xml"):
            if exclude and f == exclude:
                continue
            for el in etree.parse(str(f)).getroot().iter(f"{{{_NS_P}}}sldLayoutId"):
                used.add(int(el.get("id", "0")))
    return used


def _fix_master_layout_ids(base: Path, master_xml: Path):
    """slideMaster XML의 <p:sldLayoutId> id를 유니크하게 갱신."""
    if not master_xml.exists():
        return

    # masterId + layoutId 공유 ID 공간 — 자기 자신 제외
    used = _collect_all_ids(base, exclude=master_xml)

    tree = etree.parse(str(master_xml))
    id_lst = tree.getroot().find(f".//{{{_NS_P}}}sldLayoutIdLst")
    if id_lst is None:
        return

    next_id = max(used, default=2147483647) + 1
    for elem in id_lst.findall(f"{{{_NS_P}}}sldLayoutId"):
        elem.set("id", str(next_id))
        next_id += 1

    _write_xml(tree, master_xml)


# ── register in presentation.xml ─────────────────────────────────────

def _register_slides(base: Path, sld_map, mst_map):
    pres_xml = base / "ppt" / "presentation.xml"
    pres_rels = base / "ppt" / "_rels" / "presentation.xml.rels"

    pt = etree.parse(str(pres_xml))
    pr = pt.getroot()
    rt = etree.parse(str(pres_rels))
    rr = rt.getroot()

    # max rId
    max_rid = 0
    for rel in rr:
        m = re.match(r"rId(\d+)", rel.get("Id", ""))
        if m:
            max_rid = max(max_rid, int(m.group(1)))

    # slides
    sld_lst = pr.find(f"{{{_NS_P}}}sldIdLst")
    if sld_lst is None:
        sld_lst = etree.SubElement(pr, f"{{{_NS_P}}}sldIdLst")
    max_sid = max((int(e.get("id", "0")) for e in sld_lst), default=255)

    for old in sorted(sld_map):
        new = sld_map[old]
        max_rid += 1
        max_sid += 1
        rId = f"rId{max_rid}"
        el = etree.SubElement(sld_lst, f"{{{_NS_P}}}sldId")
        el.set("id", str(max_sid))
        el.set(f"{{{_NS_R}}}id", rId)
        r = etree.SubElement(rr, f"{{{_NS_REL}}}Relationship")
        r.set("Id", rId)
        r.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide")
        r.set("Target", f"slides/slide{new}.xml")

    # masters — sldMasterId와 sldLayoutId는 같은 ID 공간을 공유
    mst_lst = pr.find(f"{{{_NS_P}}}sldMasterIdLst")
    if mst_lst is None:
        mst_lst = etree.SubElement(pr, f"{{{_NS_P}}}sldMasterIdLst")
    max_mid = max(_collect_all_ids(base), default=2147483647)

    for old in sorted(mst_map):
        new = mst_map[old]
        max_rid += 1
        max_mid += 1
        rId = f"rId{max_rid}"
        el = etree.SubElement(mst_lst, f"{{{_NS_P}}}sldMasterId")
        el.set("id", str(max_mid))
        el.set(f"{{{_NS_R}}}id", rId)
        r = etree.SubElement(rr, f"{{{_NS_REL}}}Relationship")
        r.set("Id", rId)
        r.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster")
        r.set("Target", f"slideMasters/slideMaster{new}.xml")

    _write_xml(pt, pres_xml)
    _write_xml(rt, pres_rels)


# ── content types ────────────────────────────────────────────────────

def _register_content_types(base, sld, lay, mst, thm):
    ct = base / "[Content_Types].xml"
    tree = etree.parse(str(ct))
    root = tree.getroot()
    defs = [
        (sld, "/ppt/slides/slide{}.xml",
         "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"),
        (lay, "/ppt/slideLayouts/slideLayout{}.xml",
         "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"),
        (mst, "/ppt/slideMasters/slideMaster{}.xml",
         "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"),
        (thm, "/ppt/theme/theme{}.xml",
         "application/vnd.openxmlformats-officedocument.theme+xml"),
    ]
    for num_map, pat, ctype in defs:
        for n in num_map.values():
            ov = etree.SubElement(root, f"{{{_NS_CT}}}Override")
            ov.set("PartName", pat.format(n))
            ov.set("ContentType", ctype)
    _write_xml(tree, ct)


def _copy_default_types(base: Path, src: Path):
    """source의 Default extension 엔트리 중 base에 없는 것을 복사."""
    bct = base / "[Content_Types].xml"
    sct = src / "[Content_Types].xml"
    if not sct.exists():
        return
    bt = etree.parse(str(bct))
    st = etree.parse(str(sct))
    existing = {e.get("Extension") for e in bt.getroot()
                if e.tag == f"{{{_NS_CT}}}Default"}
    for e in st.getroot():
        if e.tag == f"{{{_NS_CT}}}Default":
            ext = e.get("Extension")
            if ext and ext not in existing:
                from copy import deepcopy
                bt.getroot().insert(0, deepcopy(e))
                existing.add(ext)
    _write_xml(bt, bct)


# ── slide size ───────────────────────────────────────────────────────

def _harmonize_size(base: Path, src: Path):
    """두 PPTX 중 큰 슬라이드 크기를 채택한다."""
    bp = base / "ppt/presentation.xml"
    sp = src / "ppt/presentation.xml"
    bw, bh = _get_size(bp)
    sw, sh = _get_size(sp)
    if sw > bw or sh > bh:
        _set_size(bp, max(bw, sw), max(bh, sh))


def _get_size(pres_xml: Path) -> tuple[int, int]:
    tree = etree.parse(str(pres_xml))
    sz = tree.getroot().find(f"{{{_NS_P}}}sldSz")
    if sz is not None:
        return int(sz.get("cx", "0")), int(sz.get("cy", "0"))
    return 0, 0


def _set_size(pres_xml: Path, cx: int, cy: int):
    tree = etree.parse(str(pres_xml))
    sz = tree.getroot().find(f"{{{_NS_P}}}sldSz")
    if sz is not None:
        sz.set("cx", str(cx))
        sz.set("cy", str(cy))
    _write_xml(tree, pres_xml)


# ── app.xml metadata ─────────────────────────────────────────────

_NS_EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
_NS_VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"


def _fix_app_xml(base: Path):
    """docProps/app.xml의 슬라이드/테마 카운트를 실제 파일과 맞춘다."""
    app_xml = base / "docProps" / "app.xml"
    if not app_xml.exists():
        return

    slide_count = len(_nums(base / "ppt/slides", "slide"))
    theme_count = len(_nums(base / "ppt/theme", "theme"))

    tree = etree.parse(str(app_xml))
    root = tree.getroot()

    # <Slides> 갱신
    for tag, val in [("Slides", slide_count)]:
        el = root.find(f"{{{_NS_EP}}}{tag}")
        if el is not None:
            el.text = str(val)

    # HeadingPairs + TitlesOfParts를 테마·슬라이드 기준으로 재작성
    # 테마 이름 수집
    theme_names = []
    for n in sorted(_nums(base / "ppt/theme", "theme")):
        tf = base / f"ppt/theme/theme{n}.xml"
        if tf.exists():
            ttree = etree.parse(str(tf))
            name = ttree.getroot().get("name", f"Theme {n}")
            theme_names.append(name)

    # 슬라이드 타이틀 (간단히 "Slide N")
    slide_titles = [f"Slide {n}" for n in sorted(_nums(base / "ppt/slides", "slide"))]

    # HeadingPairs
    hp = root.find(f"{{{_NS_EP}}}HeadingPairs")
    if hp is not None:
        root.remove(hp)
    hp = etree.SubElement(root, f"{{{_NS_EP}}}HeadingPairs")
    vec = etree.SubElement(hp, f"{{{_NS_VT}}}vector")
    vec.set("size", "4")
    vec.set("baseType", "variant")
    for label, count in [("Theme", theme_count), ("Slide Titles", slide_count)]:
        v1 = etree.SubElement(vec, f"{{{_NS_VT}}}variant")
        lp = etree.SubElement(v1, f"{{{_NS_VT}}}lpstr")
        lp.text = label
        v2 = etree.SubElement(vec, f"{{{_NS_VT}}}variant")
        i4 = etree.SubElement(v2, f"{{{_NS_VT}}}i4")
        i4.text = str(count)

    # TitlesOfParts
    tp = root.find(f"{{{_NS_EP}}}TitlesOfParts")
    if tp is not None:
        root.remove(tp)
    tp = etree.SubElement(root, f"{{{_NS_EP}}}TitlesOfParts")
    vec2 = etree.SubElement(tp, f"{{{_NS_VT}}}vector")
    vec2.set("size", str(theme_count + slide_count))
    vec2.set("baseType", "lpstr")
    for name in theme_names + slide_titles:
        lp = etree.SubElement(vec2, f"{{{_NS_VT}}}lpstr")
        lp.text = name

    _write_xml(tree, app_xml)
