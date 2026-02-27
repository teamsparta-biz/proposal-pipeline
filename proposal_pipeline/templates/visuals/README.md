# templates/visuals/ -- HTML 비주얼 템플릿 가이드

HTML/CSS로 작성한 인포그래픽 템플릿. Playwright(Chromium headless)로 PNG 캡처한 뒤, PPTX 슬라이드의 이미지 shape에 삽입한다.

PowerPoint에서 직접 만들기 어려운 정교한 레이아웃(카드 흐름도, 로드맵 등)을 HTML/CSS로 구현하여 이미지로 변환하는 방식이다.


## 렌더링 흐름

```
tokens.json ──> _tokens_to_css() ──> CSS custom properties
                                          |
                                          v
visuals/*.html + {{TOKENS_CSS}} ──> 완성된 HTML 문서
                                          |
                                          v
                               Playwright (headless Chrome)
                                          |
                                          v
                                    PNG (1760x816)
                                          |
                                          v
                          PPTX shape의 이미지 blob 교체
```


## 현재 비주얼 목록

| 파일 | 용도 | 렌더 함수 | 데이터 모델 |
|------|------|----------|-----------|
| `design_bg.html` | 설계배경 인포그래픽 | `render_design_bg()` | `DesignBackground` |
| `gap_analysis.html` | 설득: Gap 분석 | `render_persuasion()` | `PersuasionSlide` |
| `solution.html` | 설득: 솔루션 제안 | `render_persuasion()` | `PersuasionSlide` |
| `framework.html` | 설득: 프레임워크 | `render_persuasion()` | `PersuasionSlide` |
| `roadmap.html` | 설득: 교육 로드맵 | `render_persuasion()` | `PersuasionSlide` |
| `roi.html` | 설득: 기대 가치/ROI | `render_persuasion()` | `PersuasionSlide` |


### design_bg.html

설계 배경 및 목적 텍스트 + 교육 핵심 흐름 카드(3~5단계)를 표시하는 인포그래픽.

- `{{PURPOSE}}` -- 목적 텍스트. HTML 태그 허용 (`<strong>`, `<span class="highlight">`)
- `{{STEPS}}` -- 단계 카드 HTML. 렌더러가 `FlowStep` 데이터와 `icons.json`에서 자동 생성


### 설득 파트 비주얼 (gap_analysis / solution / framework / roadmap / roi)

`PersuasionSlide.visual_type`에 따라 해당 템플릿이 선택된다. 모두 `render_persuasion()` 함수로 렌더링.

PPTX는 `part_설득.pptx` 하나를 공유하고, `{{설득_제목}}`과 `{{설득_부제}}`로 제목/부제를 치환한다.
이미지는 `visual_type`별 HTML 템플릿 → PNG → PPTX 이미지 교체 방식.

| visual_type | 설명 | 데이터 키 |
|-------------|------|----------|
| `gap_analysis` | 3컬럼 To-Be/As-Is/Gap 분석 | `to_be`, `as_is`, `gap`, `summary` |
| `solution` | 솔루션 단계 카드 + 핵심 원칙 | `stages[]`, `principles[]`, `banner` |
| `framework` | 과정 상세 (목표/특징/산출물/도구) | `objectives[]`, `highlights[]`, `deliverables[]`, `tools[]`, `keywords[]` |
| `roadmap` | 다단계 로드맵 타임라인 | `phases[]`, `summary` |
| `roi` | 가치 카드 + 인용 + 배너 | `values[]`, `quote`, `banner` |

데이터 구조 상세는 `data/curriculum_schema.md` 참조.


## CSS 변수 시스템

모든 색상, 폰트, 간격은 CSS custom properties로 작성한다. 하드코딩된 값을 사용하지 않는다.

`{{TOKENS_CSS}}` 플레이스홀더가 필수이며, 렌더러가 `tokens.json`을 CSS `:root { ... }` 블록으로 변환하여 이 위치에 주입한다.

### 사용 예시

```css
/* tokens.json의 color.brand -> --color-brand */
.title { color: var(--color-brand); }

/* tokens.json의 typography.step-title -> --typo-step-title-size 등 */
.step-title {
  font-size: var(--typo-step-title-size);
  font-weight: var(--typo-step-title-weight);
}

/* tokens.json의 spacing -> --spacing-* */
.section { padding: var(--spacing-section-pt) var(--spacing-section-px); }
```

### 생성되는 CSS 변수 매핑

| tokens.json 경로 | CSS 변수 |
|-----------------|----------|
| `color.{key}` | `--color-{key}` |
| `font.family` | `--font-family` |
| `font.cdn` | `--font-cdn` |
| `viewport.width` | `--viewport-w` |
| `viewport.height` | `--viewport-h` |
| `spacing.{key}` | `--spacing-{key}` |
| `typography.{name}.{prop}` | `--typo-{name}-{prop}` |


## 새 비주얼 추가 방법

### 1단계: HTML 파일 생성

`templates/visuals/`에 HTML 파일을 만든다.

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
  {{TOKENS_CSS}}

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    width: var(--viewport-w);
    height: var(--viewport-h);
    font-family: var(--font-family);
    overflow: hidden;
  }

  /* 커스텀 스타일 작성 (모든 값은 var() 사용) */
</style>
</head>
<body>
  {{MY_DATA}}
</body>
</html>
```

주의사항:
- `{{TOKENS_CSS}}`는 반드시 `<style>` 블록 최상단에 배치
- `body` 크기는 `var(--viewport-w)` x `var(--viewport-h)` 고정 (1760x816)
- `overflow: hidden` 필수 (스크롤바 방지)

### 2단계: 빌더 함수 추가

`src/image_gen/renderer.py`에 빌더 함수를 추가한다.

설득 파트 타입 추가 시:
```python
def _build_my_visual_html(slide: PersuasionSlide) -> str:
    d = slide.data
    template = _load_template("my_visual.html")
    template = template.replace("{{HEADER_TITLE}}", d.get("header_title", ""))
    # ... 데이터를 HTML로 변환
    return template

# 디스패치 테이블에 등록
_PERSUASION_BUILDERS["my_visual"] = _build_my_visual_html
```

설계배경과 같은 별도 타입 추가 시:
```python
def render_my_visual(data: MyData, output_path: Path) -> Path:
    html = _load_template("my_visual.html")
    html = html.replace("{{MY_DATA}}", _build_my_data_html(data))
    return _render_html_to_png(html, output_path)
```

### 3단계: 파이프라인 연결

`FixedPage`에 필드 추가 → `build_config()`에서 데이터 연결 → `_process_fixed()`에서 렌더 호출.


## 참고

- 렌더링 엔진: `src/image_gen/renderer.py`
- 디자인 토큰: `../rules/tokens.json` (자세한 내용은 [rules/README.md](../rules/README.md))
- 아이콘 라이브러리: `../rules/icons.json`
- 뷰포트 크기 1760x816은 PPTX 와이드스크린(16:9) 슬라이드의 이미지 영역에 맞춘 것
