# templates/parts/ -- PPTX 파트 가이드

PowerPoint 슬라이드 골격 파일. 각 파트는 1~2슬라이드짜리 PPTX로, `{{변수명}}` 플레이스홀더를 포함한다. 파이프라인이 변수를 치환하고 순서대로 합성하여 최종 제안서를 만든다.


## 현재 파트 목록

### 고정 위치 파트

| 파일 | 역할 | order | 플레이스홀더 | 비고 |
|------|------|-------|-------------|------|
| `00_표지.pptx` | 표지 | 10 | `{{고객명}}`, `{{교육제목}}`, `{{날짜}}` | |
| `01_도입부.pptx` | AI 트렌드 도입 | 20 | `{{고객명}}` | 2슬라이드 |
| `99_엔딩.pptx` | 마무리 | 990 | | |

### 모듈 반복 파트 (order 100~)

모듈 수만큼 반복 삽입된다. order는 `build_config()`가 자동 할당.

| 파일 | 역할 | 플레이스홀더 | 비고 |
|------|------|-------------|------|
| `part_구간표지.pptx` | 모듈별 구간 표지 | `{{과정명}}` | |
| `part_설계배경.pptx` | 설계 배경 및 목적 | `{{과정명}}`, `{{시간}}` | 이미지 shape(가장 큰 PICTURE)를 프로그래밍으로 PNG 교체 |
| `part_타임테이블.pptx` | 커리큘럼 테이블 | `{{과정명}}`, `{{시간}}` | 테이블에 TopicRow 데이터 주입. 다페이지 가능 |
| `part_산출물.pptx` | 교육 산출물 예시 | | |

### PBL 파트

| 파일 | 역할 |
|------|------|
| `part_pbl_레벨무관.pptx` | PBL 레벨 무관 설명 |
| `part_pbl_로드맵.pptx` | PBL 로드맵 |
| `part_pbl_마일스톤.pptx` | PBL 마일스톤 |
| `part_pbl_피드백.pptx` | PBL 피드백 구조 |

### 사례 파트

| 파일 | 역할 |
|------|------|
| `part_사례_르노코리아.pptx` | 르노코리아 사례 |
| `part_사례_성과공유.pptx` | 성과 공유 사례 |
| `part_사례_한투증권.pptx` | 한국투자증권 사례 |
| `part_사례_현대차.pptx` | 현대자동차 사례 |


## 파트 추가 방법

### 1단계: PPTX 제작

PowerPoint에서 1슬라이드(또는 소수 슬라이드) PPTX를 만든다.

- 슬라이드 크기: 와이드스크린(16:9) 기본
- 텍스트에 Mustache 형식 플레이스홀더를 사용한다: `{{변수명}}`
- 변수명은 한글 가능, `\w` 패턴에 매칭되어야 한다

```
예시: {{고객명}} 맞춤 교육 과정 — {{교육제목}}
```

주의: PowerPoint가 `{{고객명}}`을 여러 run으로 분리할 수 있다.
이를 방지하려면 한 번에 붙여넣기하거나, 다른 편집기에서 작성 후 복사한다.
파이프라인은 paragraph 단위로 재조합하므로 분리되어도 동작하지만, 가급적 한 run에 유지하는 것이 안전하다.

### 2단계: 파일 저장

`templates/parts/`에 저장한다.

네이밍 규칙:
- 고정 위치: `NN_이름.pptx` (NN = 순번)
- 반복/선택: `part_카테고리_이름.pptx`

### 3단계: 파이프라인 등록

`src/pipeline/models.py`의 `build_config()` 함수에서 해당 파트를 FixedPage로 등록한다.

```python
fixed.append(FixedPage(
    name="새파트",
    templatePath=template_dir / "part_새파트.pptx",
    order=200,                # 삽입 순서
    partVariables={"키": "값"},  # 파트 전용 변수 (선택)
))
```

- `order` 값이 작을수록 앞에 배치된다
- `partVariables`는 전역 변수보다 우선한다 (동일 키 시 파트 변수가 덮어씀)

### 4단계: (선택) 테이블 주입

파트에 테이블이 있고 데이터를 동적 주입해야 하면, FixedPage의 `tableRows`에 `TopicRow` 리스트를 전달한다. 헤더 행(0행)은 유지되고, 데이터 행이 자동 추가/삭제된다.

### 5단계: (선택) 이미지 교체

파트에 PICTURE shape가 있고 비주얼 이미지로 교체해야 하면, FixedPage의 `designBg`에 `DesignBackground` 데이터를 전달한다. 파이프라인이 HTML 렌더링 -> PNG 캡처 -> 가장 큰 PICTURE shape의 blob을 교체한다.


## 참고

- PPTX 파트 치환 엔진: `src/pptx_replacer/replacer.py` (`PptxFileReplacer`)
- 파트 합성 엔진: `src/pptx_merger/merger.py` (`PptxZipMerger`)
- 설정 빌더: `src/pipeline/models.py` (`build_config()`)
