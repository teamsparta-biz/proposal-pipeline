# proposal-pipeline

AI 교육 제안서 자동 생성 파이프라인. 커리큘럼 JSON을 입력하면 PPTX 제안서를 생성합니다.

## 설치

### 1. 패키지 설치

```bash
pip install "git+https://github.com/teamsparta-biz/proposal-pipeline.git#egg=proposal-pipeline[visual]"
```

> `[visual]`은 Playwright(HTML→PNG 비주얼 렌더링)를 포함합니다. 비주얼 없이 쓰려면 `[visual]` 생략.

### 2. 브라우저 설치 (최초 1회)

비주얼 렌더링(설계배경, 설득 파트 이미지)을 사용하려면 Chromium이 필요합니다.

```bash
proposal-install-browsers
```

### 3. 환경변수 설정

작업 디렉토리에 `.env` 파일을 생성합니다.

```bash
# .env
GAMMA_API_KEY=sk-gamma-xxxxxxxxxx
```

> Gamma 설득 파트(`--with-gamma`)를 사용하지 않으면 API 키 없이도 동작합니다.

## 사용법

### 기본: 커리큘럼 JSON으로 제안서 생성

```bash
proposal-generate \
  --customer "삼성전자" \
  --curriculum-json curriculum.json
```

### 샘플 데이터로 테스트

```bash
proposal-generate \
  --customer "테스트" \
  --modules process-structuring,rag-agent \
  --sample
```

### PBL + 사례 포함

```bash
proposal-generate \
  --customer "현대자동차" \
  --modules prompt-rubric \
  --sample \
  --pbl part_pbl_로드맵,part_pbl_마일스톤 \
  --cases part_사례_르노코리아,part_사례_현대차
```

### Gamma 설득 파트 포함

```bash
proposal-generate \
  --customer "삼성전자" \
  --modules process-structuring \
  --sample \
  --with-gamma
```

### 전체 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--customer` | 고객사명 (필수) | - |
| `--title` | 교육 제목 | AI 교육 제안서 |
| `--date` | 제안 날짜 | 오늘 |
| `--curriculum-json` | LLM 생성 커리큘럼 JSON 경로 | - |
| `--modules` | 모듈 ID (쉼표 구분) | - |
| `--sample` | 내장 참조 데이터 사용 | false |
| `--pbl` | PBL 파트 파일명 (쉼표 구분) | - |
| `--cases` | 사례 파트 파일명 (쉼표 구분) | - |
| `--pbl-name` | PBL 구간 표지 과정명 | PBL 멘토링 |
| `--with-gamma` | Gamma API 설득 파트 생성 | false |
| `--gamma-theme` | Gamma 테마 ID | jdvmtofxo715647 |
| `--output-dir` | 출력 디렉토리 | ./output |
| `--template-dir` | 커스텀 템플릿 디렉토리 | 패키지 내장 |
| `-v` | 상세 로그 | false |

## 커리큘럼 JSON 형식

`proposal_pipeline/data/curriculum_schema.md`에 전체 스키마가 문서화되어 있습니다. 핵심 구조:

```json
[
  {
    "id": "kebab-case-id",
    "name": "과정명",
    "total_hours": "6시간",
    "table_pages": [
      {
        "label": "",
        "rows": [
          {
            "subject": "주제명 (15자 내외)",
            "hours": "2시간",
            "content": "• 학습 내용 1\n• 학습 내용 2\n• 학습 내용 3",
            "exercise": "구체적 실습 과제"
          }
        ]
      }
    ],
    "design_bg": {
      "purpose": "과정 목적 (HTML 태그 허용)",
      "steps": [
        {"title": "단계명", "subtitle": "English", "description": "설명"}
      ]
    },
    "persuasion_slides": [
      {"visual_type": "gap_analysis", "title": "...", "subtitle": "...", "data": {}}
    ]
  }
]
```

## Claude Code 스킬

Claude Code 사용자는 `/proposal` 스킬로 인터뷰 → JSON 생성 → PPTX 생성을 자동화할 수 있습니다.

```
/proposal 삼성전자
```

## 파이프라인 구조

```
커리큘럼 JSON
    │
    ▼
proposal-generate CLI
    │
    ├─ 고정 페이지: 템플릿 PPTX → 변수 치환 + 테이블 주입 + 이미지 렌더링
    ├─ 동적 페이지: Gamma API → PPTX 다운로드 (선택)
    │
    ▼
PptxZipMerger (ZIP-level 합성, 디자인 완전 보존)
    │
    ▼
[팀스파르타] 고객명 제안서.pptx
```

## 개발

```bash
git clone https://github.com/teamsparta-biz/proposal-pipeline.git
cd proposal-pipeline
pip install -e ".[visual]"
proposal-install-browsers
```
