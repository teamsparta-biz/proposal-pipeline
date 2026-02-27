# templates/ -- 템플릿 시스템 개요

제안서 자동화의 템플릿 레이어. PPTX 슬라이드 골격, HTML 비주얼 이미지, 디자인 규칙을 관리한다.


## 디렉토리 구조

```
templates/
├── parts/      # PPTX 파트 (슬라이드 골격)
├── visuals/    # HTML 비주얼 템플릿 (인포그래픽 이미지)
└── rules/      # 디자인 토큰 + 아이콘 라이브러리
```


## 3층 아키텍처

제안서 생성은 **콘텐츠 - 템플릿 - 디자인 규칙** 세 레이어로 분리되어 있다.

| 레이어 | 위치 | 역할 | 변경 주체 |
|--------|------|------|-----------|
| 콘텐츠 레퍼런스 | `data/` | 교육 과정 데이터 (커리큘럼, 토픽) | 컨설턴트 / LLM |
| PPTX 파트 | `templates/parts/` | 슬라이드 골격 + 플레이스홀더 | 디자이너 |
| HTML 비주얼 | `templates/visuals/` | 인포그래픽 이미지 템플릿 | 디자이너 / 개발자 |
| 디자인 규칙 | `templates/rules/` | 색상, 폰트, 아이콘, 간격 토큰 | 디자이너 |

레이어가 분리되어 있으므로, 예를 들어 브랜드 색상을 변경할 때는 `rules/tokens.json`만 수정하면 모든 비주얼에 자동 반영된다.


## 파이프라인 흐름

```
1. 콘텐츠 (data/)
   커리큘럼 JSON (모듈, 토픽, 설계배경 텍스트)
          |
          v
2. 템플릿 + 규칙
   parts/*.pptx     -- {{변수}} 치환, 테이블 주입
   visuals/*.html    -- HTML 렌더링 -> PNG 캡처
   rules/*.json      -- CSS 변수로 변환하여 비주얼에 주입
          |
          v
3. 파이프라인 (src/)
   PptxReplacer: 변수 치환 + 테이블 주입
   Renderer:     HTML -> Playwright -> PNG -> PPTX 이미지 교체
   PptxMerger:   파트들을 순서대로 합성
          |
          v
4. 최종 PPTX
   [팀스파르타] {고객명} 제안서.pptx
```


## 주요 참조 파일

| 파일 | 설명 |
|------|------|
| `generate.py` | CLI 진입점. 모듈 선택 -> 설정 빌드 -> 파이프라인 실행 |
| `src/pipeline/models.py` | `build_config()` -- 파트 순서/변수 자동 구성 |
| `src/pipeline/pipeline.py` | `DefaultProposalPipeline` -- 전체 실행 흐름 |
| `src/image_gen/renderer.py` | HTML 비주얼 렌더링 엔진 |
| `src/pptx_replacer/replacer.py` | PPTX 변수 치환 + 테이블 주입 |


## 하위 디렉토리 README

- [parts/README.md](parts/README.md) -- PPTX 파트 가이드
- [visuals/README.md](visuals/README.md) -- HTML 비주얼 템플릿 가이드
- [rules/README.md](rules/README.md) -- 디자인 토큰 레퍼런스
