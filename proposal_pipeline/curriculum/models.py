"""커리큘럼 모듈 데이터 모델.

LLM 생성 결과 또는 참조 JSON에서 파싱된 데이터를 표현한다.
PptxReplacer의 테이블 주입 엔진과 연동되는 인터페이스 역할.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TopicRow:
    """커리큘럼 테이블의 한 행."""

    subject: str
    hours: str
    content: str
    exercise: str


@dataclass
class TablePage:
    """타임테이블 슬라이드 1장에 해당하는 행 묶음."""

    label: str  # 페이지 라벨 (예: "1차", "전반부", 빈 문자열이면 단일 페이지)
    rows: list[TopicRow] = field(default_factory=list)


@dataclass
class FlowStep:
    """설계배경 교육 핵심 흐름의 한 단계."""

    title: str           # 단계 제목 (예: "패러다임 전환")
    subtitle: str        # 영문/부제 (예: "Mindset")
    description: str     # 설명 (예: "AI 이미지 기술의 원리 학습")


@dataclass
class DesignBackground:
    """설계배경 슬라이드의 콘텐츠."""

    purpose: str                              # 설계 배경 및 목적 (2~3줄 텍스트)
    steps: list[FlowStep] = field(default_factory=list)  # 교육 핵심 흐름 (3~4단계)


@dataclass
class PersuasionSlide:
    """설득 파트 슬라이드 1장의 콘텐츠.

    도입부와 커리큘럼 모듈 사이에 배치되는 고객 맞춤 설득 슬라이드.
    visual_type에 따라 templates/visuals/{type}.html 비주얼 템플릿이 선택된다.
    """

    visual_type: str    # "gap_analysis" | "solution" | "framework" | "roadmap" | "roi"
    title: str          # PPTX 제목 (예: "Gap 분석")
    subtitle: str       # PPTX 부제 (예: "AX 전략 달성을 위한 병목 지점 분석")
    data: dict = field(default_factory=dict)  # 비주얼 템플릿에 전달되는 타입별 데이터


@dataclass
class CurriculumModule:
    """하나의 교육 모듈 전체 데이터.

    파이프라인에서 모듈 하나를 처리할 때 필요한 모든 정보를 담는다.
    """

    id: str                          # 모듈 ID (예: "process-structuring")
    name: str                        # 과정명 (예: "Process 구조화 과정")
    total_hours: str                 # 총 시간 (예: "6시간")
    table_pages: list[TablePage] = field(default_factory=list)
    design_bg: DesignBackground | None = None  # 설계배경 콘텐츠 (없으면 원본 이미지 유지)
    consultant_context: str = ""     # 컨설턴트별 추가 맥락/스타일 노트
