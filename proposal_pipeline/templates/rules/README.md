# templates/rules/ -- 디자인 토큰 레퍼런스

비주얼 템플릿(HTML)에 적용되는 디자인 규칙을 JSON으로 관리한다. 색상, 폰트, 간격, 아이콘을 중앙에서 제어하여 일관된 비주얼을 보장한다.


## 파일 목록

| 파일 | 역할 |
|------|------|
| `tokens.json` | 색상, 폰트, 뷰포트, 간격, 타이포그래피 토큰 |
| `icons.json` | 단계별 SVG 아이콘 라이브러리 |


## tokens.json 구조

### color -- 색상 팔레트

| 키 | 값 | 용도 |
|----|-----|------|
| `brand` | `#FA0030` | 브랜드 메인 컬러 (강조, 하이라이트) |
| `text-primary` | `#1a1a1a` | 제목, 주요 텍스트 |
| `text-body` | `#333333` | 본문 텍스트 |
| `text-muted` | `#555555` | 보조 텍스트 |
| `text-subtle` | `#999999` | 부제, 약한 텍스트 |
| `border` | `#e5e5e5` | 카드/구분선 테두리 |
| `arrow` | `#cccccc` | 흐름 화살표 |
| `white` | `#ffffff` | 흰색 (반전 텍스트, 배경) |
| `bg-default` | `#ffffff` | 기본 배경색 |

### font -- 폰트 설정

| 키 | 값 |
|----|-----|
| `family` | `'Pretendard', -apple-system, 'Segoe UI', sans-serif` |
| `cdn` | Pretendard CDN URL (렌더링 시 자동 로드) |

### viewport -- 비주얼 이미지 해상도

| 키 | 값 | 설명 |
|----|-----|------|
| `width` | 1760 | 이미지 가로 (px) |
| `height` | 816 | 이미지 세로 (px) |

PPTX 와이드스크린(16:9) 슬라이드의 이미지 영역에 맞춘 크기이다.

### spacing -- 여백/간격

| 키 | 값 | 용도 |
|----|-----|------|
| `section-px` | 36px | 섹션 좌우 패딩 |
| `section-pt` | 28px | 섹션 상단 패딩 |
| `section-pb` | 24px | 섹션 하단 패딩 |
| `flow-pt` | 20px | 흐름 섹션 상단 패딩 |
| `card-px` | 20px | 카드 좌우 패딩 |
| `card-py-top` | 28px | 카드 상단 패딩 |
| `card-py-bottom` | 24px | 카드 하단 패딩 |
| `card-radius` | 16px | 카드 모서리 radius |

### typography -- 타이포그래피

각 요소별 `size`, `weight`, `line-height`를 정의한다.

| 요소 | size | weight | line-height |
|------|------|--------|-------------|
| `purpose-title` | 20px | 700 | 1.4 |
| `purpose-text` | 15.5px | 400 | 1.75 |
| `flow-title` | 19px | 700 | 1.4 |
| `step-number` | 15px | 700 | -- |
| `step-title` | 18px | 700 | -- |
| `step-subtitle` | 13px | 400 | -- |
| `step-desc` | 13.5px | 400 | 1.6 |


## icons.json 구조

`step_icons` 배열에 단계별 SVG 아이콘을 정의한다.

### 현재 아이콘 목록

| index | name | label | 용도 |
|-------|------|-------|------|
| 0 | `mindset` | 뇌/마인드셋 | 1단계: 패러다임 전환 |
| 1 | `analyze` | 분해/진단 | 2단계: 분석/진단 |
| 2 | `design` | 설계/도구 | 3단계: 설계/실습 |
| 3 | `verify` | 검증/완성 | 4단계: 검증/완성 |
| 4 | `expand` | 확장/반복 | 5단계: 확장/반복 |

### SVG 작성 규칙

- `viewBox="0 0 48 48"` 고정
- `fill="none"` + `stroke="currentColor"` -- CSS에서 `color` 속성으로 색상 제어
- `stroke-width="2.5"`, `stroke-linecap="round"`, `stroke-linejoin="round"`
- 아이콘은 48x48 공간 안에서 중앙 정렬

렌더러는 `FlowStep`의 index에 해당하는 아이콘을 자동 선택한다. 단계 수가 아이콘 수를 초과하면 마지막 아이콘이 반복된다.


## 토큰 수정 가이드

### 색상 변경

`tokens.json`의 `color` 섹션만 수정하면 모든 비주얼 템플릿에 자동 반영된다.

```json
{
  "color": {
    "brand": "#0066FF"
  }
}
```

비주얼 HTML에서 `var(--color-brand)`로 참조하므로, 템플릿 파일 수정 없이 색상이 변경된다.

### 폰트 변경

`font.family`와 `font.cdn`을 함께 변경한다.

```json
{
  "font": {
    "family": "'Noto Sans KR', sans-serif",
    "cdn": "https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap"
  }
}
```

### 아이콘 추가

`icons.json`의 `step_icons` 배열에 항목을 추가한다.

```json
{
  "name": "present",
  "label": "발표/공유",
  "svg": "<svg viewBox=\"0 0 48 48\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\">...</svg>"
}
```

아이콘 index 순서가 교육 흐름 단계 순서에 대응하므로, 배열 내 위치를 고려하여 삽입한다.

### 간격/타이포 조정

`spacing` 또는 `typography` 값을 변경한다. CSS 변수명 매핑 규칙:

- `spacing.card-px` -> `--spacing-card-px`
- `typography.step-title.size` -> `--typo-step-title-size`


## 참고

- CSS 변환 로직: `src/image_gen/renderer.py`의 `_tokens_to_css()` 함수
- 비주얼 템플릿: `../visuals/` (자세한 내용은 [visuals/README.md](../visuals/README.md))
