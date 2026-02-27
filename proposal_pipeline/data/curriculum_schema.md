# 커리큘럼 JSON 스키마 가이드

제안서 파이프라인(`generate.py --curriculum-json`)에 입력하는 JSON의 형식과 품질 기준.


## 입력 정보 (컨설턴트가 제공)

| 항목 | 설명 | 예시 |
|------|------|------|
| 고객사 | 제안 대상 기업명 | 삼성전자 |
| 상품/주제 | 교육 과정 주제 | Midjourney 비주얼 AI |
| 직무 | 수강 대상 직무/부서 | 마케팅팀, 기획팀 |
| 사용 툴 | 교육에서 다루는 도구 | Midjourney, Canva |
| 시간 | 총 교육 시간 | 6시간 |
| 제한사항 | 고객 요청, 금지 사항 | 비개발자 대상, 코딩 없음 |
| 실습 케이스 | 원하는 구체적 실습 | SNS 콘텐츠 제작, 보고서 표지 |
| 추가 정보 | 기타 맥락 | Discord 미경험자 다수 |


## JSON 출력 형식

```json
[
  {
    "id": "kebab-case-id",
    "name": "과정명 ({{과정명}} 치환에 사용)",
    "total_hours": "6시간",
    "table_pages": [
      {
        "label": "",
        "rows": [
          {
            "subject": "주제명",
            "hours": "2시간",
            "content": "• 학습 내용 1\n• 학습 내용 2\n• 학습 내용 3\n• 학습 내용 4",
            "exercise": "구체적 실습 과제 설명"
          }
        ]
      }
    ],
    "design_bg": {
      "purpose": "HTML 형식의 과정 목적 텍스트",
      "steps": [
        {"title": "한글 단계명", "subtitle": "English", "description": "1줄 설명"}
      ]
    },
    "consultant_context": "대상자 특성, 실습 비중, 유의사항"
  }
]
```


## 필드별 규칙

### id
- kebab-case (예: `midjourney-visual`, `rag-agent`)
- 영문, 소문자, 하이픈 구분

### name
- 한글 과정명 (예: "Midjourney 비주얼 AI 실전 과정")
- 제안서 구간표지, 설계배경, 타임테이블의 `{{과정명}}`에 표시됨

### total_hours
- "N시간" 형식 (예: "6시간", "8시간")
- 장기 과정: "7h X 5일" 형식 가능
- **rows의 hours 합계와 반드시 일치**

### table_pages (타임테이블 페이지 분할)

자동 분할 규칙:
- 4행 이하 → 1페이지 (label: "")
- 5~8행 → 2페이지 (label: "1차", "2차")
- 9~12행 → 3페이지
- 행 수 / 4 올림 = 페이지 수
- 각 페이지 행 수는 균등 분배 (올림)

### rows[].subject (주제명)
- 15자 내외, 테이블 셀 너비에 맞게
- 줄바꿈(\n) 사용 가능 (2줄 이내)
- 예: "RAG 아키텍처 및 핵심 개념", "사내 문서 기반 \n지식 에이전트 구축 실전"

### rows[].hours (시간)
- "1시간", "1.5시간", "2시간" 등
- 0.5시간 단위
- **모든 rows의 hours 합계 = total_hours**

### rows[].content (학습 내용)
- bullet point 형식: "• " 로 시작
- 3~4개 항목, 각 40~80자
- 줄바꿈(\n)으로 구분
- **구체적 실무 행동/도구/개념 언급** (추상적 표현 금지)
- 좋은 예: "• Postman 도구를 활용해 외부 데이터(환율, 날씨)를 내 PC로 불러오는 원리 파악"
- 나쁜 예: "• API에 대해 학습합니다"

### rows[].exercise (실습 과제)
- 1~2문장
- **구체적 산출물이 있어야 함** ("~작성", "~제출", "~실습", "~제작")
- 줄바꿈(\n) 가능
- 좋은 예: "팀별로 '차기 분기 사업 보고서 표지' 이미지를 제작하고,\n프롬프트·설정값·선택 이유를 포함한 1페이지 가이드 제출"
- 나쁜 예: "실습을 진행합니다"

### design_bg.purpose (설계 배경 및 목적)
- 2~3줄 텍스트
- HTML 태그 허용:
  - `<strong>과정명/핵심 키워드</strong>` — 볼드 강조
  - `<span class="highlight">핵심 가치</span>` — 빨간색 강조
  - `<br>` — 줄바꿈
- 구조: "본 과정은 ~을 위해 설계되었습니다. ~를 넘어, ~까지 확보하여, ~를 목표로 합니다."

### design_bg.steps (교육 핵심 흐름)
- 3~4단계 (마지막 단계는 빨간 카드로 강조됨)
- 학습 여정 흐름: 이해/인식 → 학습/도구 → 설계/심화 → 실전/산출
- title: 한글 2~4자 (예: "패러다임 전환", "도구 숙련")
- subtitle: 영문 1단어 (예: "Mindset", "Skill-up", "Output")
- description: 1줄, 15~25자

### consultant_context
- 대상자 특성, 실습 비중, 주의사항
- 제안서에 직접 표시되지 않음 (메타 정보)
- 예: "비개발자 대상, 마케팅/기획 부서 실무자 중심. 실습 비중 60% 이상."


## 설득 파트 (persuasion_slides)

설득 파트는 도입부와 커리큘럼 사이에 배치되는 고객 맞춤 슬라이드. JSON 배열의 첫 번째 모듈 객체에 `persuasion_slides` 키로 포함한다.

```json
{
  "id": "...",
  "persuasion_slides": [
    {
      "visual_type": "gap_analysis",
      "title": "PPTX 제목",
      "subtitle": "PPTX 부제",
      "data": { ... }
    }
  ]
}
```

### visual_type별 data 구조

#### gap_analysis (Gap 분석)
```json
{
  "header_title": "Gap 분석 제목",
  "to_be": { "label": "To-Be", "items": ["목표1", "목표2", "목표3", "목표4"] },
  "as_is": { "label": "As-Is", "items": ["현재1", "현재2", "현재3", "현재4"] },
  "gap": { "label": "Gap", "items": ["격차1", "격차2", "격차3", "격차4"] },
  "summary": "요약 배너 텍스트 (선택)"
}
```

#### solution (솔루션 제안)
```json
{
  "header_title": "솔루션 제목",
  "stages": [
    { "title": "단계명", "subtitle": "부제", "description": "설명", "items": ["세부1", "세부2"] }
  ],
  "principles": [
    { "title": "원칙명", "description": "설명" }
  ],
  "banner": "하단 배너 텍스트 (HTML 허용, 선택)"
}
```

#### framework (프레임워크)
```json
{
  "header_title": "과정명",
  "duration": "4시간",
  "target": "대상자",
  "objectives": ["학습 목표1", "학습 목표2"],
  "highlights": ["과정 특징1", "과정 특징2"],
  "deliverables": ["산출물1", "산출물2"],
  "tools": ["도구1", "도구2"],
  "keywords": ["키워드1", "키워드2"]
}
```

#### roadmap (로드맵)
```json
{
  "header_title": "로드맵 제목",
  "phases": [
    {
      "title": "단계명", "subtitle": "영문", "period": "기간",
      "description": "설명", "activities": ["활동1", "활동2"]
    }
  ],
  "summary": "요약 텍스트 (선택)"
}
```

#### roi (기대 가치 및 ROI)
```json
{
  "header_title": "ROI 제목",
  "values": [
    { "icon": "efficiency", "metric": "30%", "title": "가치명", "description": "설명" }
  ],
  "quote": "인용 텍스트 (선택)",
  "banner": "하단 배너 텍스트 (선택)"
}
```

**icon 옵션**: `efficiency`, `productivity`, `quality`, `innovation`, `collaboration`, `growth`, `achievement`, `target`

### 설득 파트 구성 권장 순서

1. `gap_analysis` — 현재 상태와 목표 간 격차 분석
2. `solution` — 교육 솔루션 제안 (2~3단계)
3. `framework` — 핵심 과정 프레임워크 (과정별 1장, 최대 3장)
4. `roadmap` — 전체 교육 로드맵
5. `roi` — 기대 가치 및 ROI


## 품질 체크리스트

- [ ] hours 합계가 total_hours와 일치하는가
- [ ] content가 "• " bullet point 형식인가
- [ ] exercise에 구체적 산출물이 있는가
- [ ] design_bg.steps가 학습 여정 흐름(이해→실습→적용→산출)인가
- [ ] table_pages 분할이 4행 기준 규칙을 따르는가
- [ ] subject가 15자 내외로 테이블 셀에 맞는가


## 전체 예시

`data/test_midjourney.json` 참조 — Midjourney 비주얼 AI 실전 과정 (6시간, 4주제, design_bg 포함)
