"""비주얼 이미지 렌더러 — HTML 템플릿 + 디자인 토큰 → Playwright → PNG.

templates/rules/tokens.json 에서 디자인 토큰을 읽어
templates/visuals/*.html 템플릿에 CSS 변수로 주입한 뒤,
Playwright (Chromium headless)로 렌더링하여 PNG 이미지를 생성한다.

새 비주얼 템플릿을 추가하려면 templates/visuals/README.md 참조.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..curriculum.models import DesignBackground, PersuasionSlide
from .._resources import get_template_dir


def _load_tokens() -> dict:
    """tokens.json을 로드한다."""
    path = get_template_dir("rules") / "tokens.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_icons() -> list[dict]:
    """icons.json에서 step_icons 목록을 로드한다."""
    path = get_template_dir("rules") / "icons.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["step_icons"]


def _tokens_to_css(tokens: dict) -> str:
    """tokens.json → CSS custom properties (:root { ... }) 블록 생성."""
    lines = [":root {"]

    # 색상
    for key, val in tokens["color"].items():
        lines.append(f"  --color-{key}: {val};")

    # 폰트
    lines.append(f"  --font-family: {tokens['font']['family']};")
    lines.append(f"  --font-cdn: {tokens['font']['cdn']};")

    # 뷰포트
    lines.append(f"  --viewport-w: {tokens['viewport']['width']}px;")
    lines.append(f"  --viewport-h: {tokens['viewport']['height']}px;")

    # 간격
    for key, val in tokens["spacing"].items():
        lines.append(f"  --spacing-{key}: {val};")

    # 타이포그래피
    for name, props in tokens["typography"].items():
        for prop, val in props.items():
            lines.append(f"  --typo-{name}-{prop}: {val};")

    lines.append("}")

    # @import는 :root 밖에 있어야 하므로 별도 추가
    cdn = tokens["font"]["cdn"]
    return f"@import url('{cdn}');\n" + "\n".join(lines)


# ── Playwright 렌더링 공통 함수 ──────────────────────────────────────

def _render_html_to_png(html: str, output_path: Path) -> Path:
    """완성된 HTML 문자열을 Playwright로 PNG 캡처한다."""
    from playwright.sync_api import sync_playwright

    tokens = _load_tokens()
    vw = tokens["viewport"]["width"]
    vh = tokens["viewport"]["height"]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_html = output_path.with_suffix(".html")
    tmp_html.write_text(html, encoding="utf-8")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": vw, "height": vh})
            page.goto(f"file:///{tmp_html.as_posix()}")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)
            page.screenshot(path=str(output_path), type="png")
            browser.close()
    finally:
        tmp_html.unlink(missing_ok=True)

    return output_path


def _load_template(template_name: str) -> str:
    """비주얼 템플릿 HTML을 로드하고 토큰 CSS를 주입한다."""
    tokens = _load_tokens()
    template_path = get_template_dir("visuals") / template_name
    template = template_path.read_text(encoding="utf-8")
    return template.replace("{{TOKENS_CSS}}", _tokens_to_css(tokens))


# ══════════════════════════════════════════════════════════════════════
# 설계배경 (design_bg)
# ══════════════════════════════════════════════════════════════════════

def _build_step_html(step_index: int, title: str, subtitle: str,
                     desc: str, is_last: bool, icons: list[dict]) -> str:
    """한 단계 카드의 HTML을 생성한다."""
    icon_data = icons[min(step_index, len(icons) - 1)]
    svg = icon_data["svg"]
    cls = "step-card last" if is_last else "step-card"
    return f"""
      <div class="{cls}">
        <div class="step-number">{step_index + 1}</div>
        <div class="step-icon">{svg}</div>
        <div class="step-title">{title}</div>
        <div class="step-subtitle">({subtitle})</div>
        <div class="step-desc">{desc}</div>
      </div>"""


def _build_design_bg_html(bg: DesignBackground) -> str:
    """DesignBackground 데이터 + 토큰 + 아이콘으로 완성된 HTML을 생성한다."""
    icons = _load_icons()
    template = _load_template("design_bg.html")

    purpose_html = bg.purpose.replace("\n", "<br>")
    template = template.replace("{{PURPOSE}}", purpose_html)

    steps_html = ""
    for i, step in enumerate(bg.steps):
        if i > 0:
            steps_html += '<div class="step-arrow">›</div>'
        is_last = i == len(bg.steps) - 1
        steps_html += _build_step_html(
            i, step.title, step.subtitle, step.description, is_last, icons
        )

    template = template.replace("{{STEPS}}", steps_html)
    return template


def render_design_bg(bg: DesignBackground, output_path: Path) -> Path:
    """DesignBackground → PNG 이미지를 생성한다."""
    html = _build_design_bg_html(bg)
    return _render_html_to_png(html, output_path)


# ══════════════════════════════════════════════════════════════════════
# 설득 파트 비주얼 (persuasion)
# ══════════════════════════════════════════════════════════════════════

# ── SVG 아이콘 (인라인) ──

_SVG_TARGET = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>'
_SVG_CHART = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>'
_SVG_ARROW_UP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>'
_SVG_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
_SVG_LIGHTBULB = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0018 8 6 6 0 006 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 018.91 14"/></svg>'
_SVG_USERS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>'
_SVG_ROCKET = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 00-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 012-3.95A12.88 12.88 0 0122 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 01-4 2z"/></svg>'
_SVG_TROPHY = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 010-5H6"/><path d="M18 9h1.5a2.5 2.5 0 000-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20 17 22"/><path d="M18 2H6v7a6 6 0 0012 0V2z"/></svg>'

_PERSUASION_ICONS = {
    "efficiency": _SVG_CHART,
    "productivity": _SVG_ARROW_UP,
    "quality": _SVG_CHECK,
    "innovation": _SVG_LIGHTBULB,
    "collaboration": _SVG_USERS,
    "growth": _SVG_ROCKET,
    "achievement": _SVG_TROPHY,
    "target": _SVG_TARGET,
}

# ── gap_analysis 빌더 ──

def _build_gap_analysis_html(slide: PersuasionSlide) -> str:
    """Gap 분석 비주얼 HTML을 생성한다."""
    d = slide.data
    template = _load_template("gap_analysis.html")

    template = template.replace("{{HEADER_TITLE}}", d.get("header_title", "Gap 분석"))

    # 3컬럼 빌드
    columns_html = ""
    for col_key, col_class, icon_svg in [
        ("to_be", "col-tobe", _SVG_TARGET),
        ("as_is", "col-asis", _SVG_CHART),
        ("gap", "col-gap", _SVG_ARROW_UP),
    ]:
        col = d.get(col_key, {})
        label = col.get("label", col_key.replace("_", " ").title())
        items = col.get("items", [])

        items_html = ""
        for item in items:
            items_html += f'<div class="item"><span class="item-bullet">•</span>{_esc(item)}</div>'

        columns_html += f"""
    <div class="column {col_class}">
      <div class="column-header">
        <div class="column-icon">{icon_svg}</div>
        <div class="column-label">{_esc(label)}</div>
      </div>
      <div class="column-body">{items_html}</div>
    </div>"""

    template = template.replace("{{COLUMNS}}", columns_html)

    # 요약 배너
    summary = d.get("summary", "")
    if summary:
        template = template.replace("{{SUMMARY}}", f"""
  <div class="summary-banner">
    <div class="summary-icon">{_SVG_LIGHTBULB}</div>
    <div>{_esc(summary)}</div>
  </div>""")
    else:
        template = template.replace("{{SUMMARY}}", "")

    return template


# ── solution 빌더 ──

def _build_solution_html(slide: PersuasionSlide) -> str:
    """솔루션 제안 비주얼 HTML을 생성한다."""
    d = slide.data
    template = _load_template("solution.html")

    template = template.replace("{{HEADER_TITLE}}", d.get("header_title", "솔루션 제안"))

    # 스테이지 카드
    stages = d.get("stages", [])
    stages_html = ""
    for i, stage in enumerate(stages):
        items_html = ""
        for item in stage.get("items", []):
            items_html += f"<li>{_esc(item)}</li>"

        stages_html += f"""
    <div class="stage-card">
      <div class="stage-number">{i + 1}</div>
      <div class="stage-title">{_esc(stage.get('title', ''))}</div>
      <div class="stage-subtitle">{_esc(stage.get('subtitle', ''))}</div>
      <div class="stage-desc">{_esc(stage.get('description', ''))}</div>
      <ul class="stage-items">{items_html}</ul>
    </div>"""

    template = template.replace("{{STAGES}}", stages_html)

    # 핵심 원칙
    principles = d.get("principles", [])
    principles_html = ""
    icons_list = [_SVG_LIGHTBULB, _SVG_ROCKET, _SVG_CHECK, _SVG_USERS]
    for i, pr in enumerate(principles):
        icon = icons_list[i % len(icons_list)]
        principles_html += f"""
    <div class="principle">
      <div class="principle-icon">{icon}</div>
      <div>
        <div class="principle-title">{_esc(pr.get('title', ''))}</div>
        <div class="principle-desc">{_esc(pr.get('description', ''))}</div>
      </div>
    </div>"""

    template = template.replace("{{PRINCIPLES}}", principles_html)

    # 배너
    banner = d.get("banner", "")
    if banner:
        template = template.replace("{{BANNER}}", f'<div class="bottom-banner">{banner}</div>')
    else:
        template = template.replace("{{BANNER}}", "")

    return template


# ── framework 빌더 ──

def _build_framework_html(slide: PersuasionSlide) -> str:
    """프레임워크 비주얼 HTML을 생성한다."""
    d = slide.data
    template = _load_template("framework.html")

    template = template.replace("{{HEADER_TITLE}}", d.get("header_title", ""))

    # 배지
    badges_html = ""
    if d.get("duration"):
        badges_html += f'<span class="badge badge-time">{_esc(d["duration"])}</span>'
    if d.get("target"):
        badges_html += f'<span class="badge badge-target">{_esc(d["target"])}</span>'
    template = template.replace("{{BADGES}}", badges_html)

    # 좌측 섹션
    left_html = ""
    objectives = d.get("objectives", [])
    if objectives:
        items = "".join(f"<li>{_esc(o)}</li>" for o in objectives)
        left_html += f"""
      <div class="section-card stretch">
        <div class="section-card-header">
          <div class="section-icon objectives">{_SVG_TARGET}</div>
          <div class="section-card-title">학습 목표</div>
        </div>
        <div class="section-card-body">
          <ul class="item-list objectives-list">{items}</ul>
        </div>
      </div>"""

    highlights = d.get("highlights", [])
    if highlights:
        items = "".join(f"<li>{_esc(h)}</li>" for h in highlights)
        left_html += f"""
      <div class="section-card stretch">
        <div class="section-card-header">
          <div class="section-icon highlights">{_SVG_LIGHTBULB}</div>
          <div class="section-card-title">과정 특징</div>
        </div>
        <div class="section-card-body">
          <ul class="item-list highlights-list">{items}</ul>
        </div>
      </div>"""

    template = template.replace("{{LEFT_SECTIONS}}", left_html)

    # 우측 섹션
    right_html = ""
    deliverables = d.get("deliverables", [])
    if deliverables:
        items = "".join(f"<li>{_esc(dl)}</li>" for dl in deliverables)
        right_html += f"""
      <div class="section-card stretch">
        <div class="section-card-header">
          <div class="section-icon deliverables">{_SVG_CHECK}</div>
          <div class="section-card-title">핵심 산출물</div>
        </div>
        <div class="section-card-body">
          <ul class="item-list deliverables-list">{items}</ul>
        </div>
      </div>"""

    tools = d.get("tools", [])
    if tools:
        items = "".join(f"<li>{_esc(t)}</li>" for t in tools)
        right_html += f"""
      <div class="section-card stretch">
        <div class="section-card-header">
          <div class="section-icon tools">{_SVG_CHART}</div>
          <div class="section-card-title">활용 도구</div>
        </div>
        <div class="section-card-body">
          <ul class="item-list tools-list">{items}</ul>
        </div>
      </div>"""

    template = template.replace("{{RIGHT_SECTIONS}}", right_html)

    # 키워드
    keywords = d.get("keywords", [])
    if keywords:
        tags_html = ""
        for i, kw in enumerate(keywords):
            cls = "keyword-tag accent" if i == 0 else "keyword-tag"
            tags_html += f'<span class="{cls}">{_esc(kw)}</span>'
        template = template.replace("{{KEYWORDS}}", f'<div class="keywords-bar">{tags_html}</div>')
    else:
        template = template.replace("{{KEYWORDS}}", "")

    return template


# ── roadmap 빌더 ──

def _build_roadmap_html(slide: PersuasionSlide) -> str:
    """로드맵 비주얼 HTML을 생성한다."""
    d = slide.data
    template = _load_template("roadmap.html")

    template = template.replace("{{HEADER_TITLE}}", d.get("header_title", "교육 로드맵"))

    phases = d.get("phases", [])
    phases_html = ""
    for i, phase in enumerate(phases):
        is_last = i == len(phases) - 1

        activities_html = ""
        for act in phase.get("activities", []):
            activities_html += f"<li>{_esc(act)}</li>"

        phases_html += f"""
    <div class="phase">
      <div class="phase-top">
        <div class="phase-number">PHASE {i + 1}</div>
        <div class="phase-period">{_esc(phase.get('period', ''))}</div>
      </div>
      <div class="timeline-track">
        <div class="timeline-bar"></div>
        <div class="timeline-dot"></div>
      </div>
      <div class="phase-card">
        <div class="phase-title">{_esc(phase.get('title', ''))}</div>
        <div class="phase-subtitle">{_esc(phase.get('subtitle', ''))}</div>
        <div class="phase-desc">{_esc(phase.get('description', ''))}</div>
        <ul class="phase-activities">{activities_html}</ul>
      </div>
    </div>"""

    template = template.replace("{{PHASES}}", phases_html)

    # 요약
    summary = d.get("summary", "")
    if summary:
        template = template.replace("{{SUMMARY}}", f"""
  <div class="summary">
    <div class="summary-icon">{_SVG_ROCKET}</div>
    <div>{_esc(summary)}</div>
  </div>""")
    else:
        template = template.replace("{{SUMMARY}}", "")

    return template


# ── roi 빌더 ──

def _build_roi_html(slide: PersuasionSlide) -> str:
    """ROI/기대 가치 비주얼 HTML을 생성한다."""
    d = slide.data
    template = _load_template("roi.html")

    template = template.replace("{{HEADER_TITLE}}", d.get("header_title", "기대 가치 및 ROI"))

    # 가치 카드
    values = d.get("values", [])
    values_html = ""
    for i, v in enumerate(values):
        icon_key = v.get("icon", "target")
        icon_svg = _PERSUASION_ICONS.get(icon_key, _SVG_TARGET)
        values_html += f"""
    <div class="value-card">
      <div class="value-icon icon-{i % 3}">{icon_svg}</div>
      <div class="value-metric">{_esc(v.get('metric', ''))}</div>
      <div class="value-title">{_esc(v.get('title', ''))}</div>
      <div class="value-desc">{_esc(v.get('description', ''))}</div>
    </div>"""

    template = template.replace("{{VALUES}}", values_html)

    # 인용
    quote = d.get("quote", "")
    if quote:
        template = template.replace("{{QUOTE}}", f"""
  <div class="quote-section">
    <div class="quote-mark">"</div>
    <div class="quote-text">{_esc(quote)}</div>
  </div>""")
    else:
        template = template.replace("{{QUOTE}}", "")

    # 배너
    banner = d.get("banner", "")
    if banner:
        template = template.replace("{{BANNER}}", f"""
  <div class="bottom-banner">{_SVG_ROCKET} {banner}</div>""")
    else:
        template = template.replace("{{BANNER}}", "")

    return template


# ── 디스패치 테이블 ──

_PERSUASION_BUILDERS: dict[str, Any] = {
    "gap_analysis": _build_gap_analysis_html,
    "solution": _build_solution_html,
    "framework": _build_framework_html,
    "roadmap": _build_roadmap_html,
    "roi": _build_roi_html,
}


def render_persuasion(slide: PersuasionSlide, output_path: Path) -> Path:
    """PersuasionSlide → PNG 이미지를 생성한다.

    visual_type에 따라 적절한 HTML 빌더를 선택하여 렌더링한다.
    """
    builder = _PERSUASION_BUILDERS.get(slide.visual_type)
    if builder is None:
        valid = ", ".join(_PERSUASION_BUILDERS.keys())
        raise ValueError(f"알 수 없는 visual_type: {slide.visual_type} (가능: {valid})")

    html = builder(slide)
    return _render_html_to_png(html, output_path)


# ── 유틸리티 ──

def _esc(text: str) -> str:
    """HTML 이스케이프 (기본적인 XSS 방지)."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
