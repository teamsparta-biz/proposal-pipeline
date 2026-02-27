"""Gamma API 요청/응답 데이터 모델."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# --- 공통 ---

class Credits(BaseModel):
    deducted: int = 0
    remaining: int = 0


# --- Generate API ---

class TextOptions(BaseModel):
    amount: Optional[str] = None          # brief | medium | detailed | extensive
    tone: Optional[str] = None            # generate 모드에서만 유효
    audience: Optional[str] = None        # generate 모드에서만 유효
    language: Optional[str] = None        # 언어 코드 (예: ko, en)


class ImageOptions(BaseModel):
    source: Optional[str] = None          # aiGenerated | pexels | pictographic | noImages 등
    model: Optional[str] = None           # AI 이미지 모델 (source=aiGenerated 시)
    style: Optional[str] = None           # 스타일 디렉션 (1~500자)


class SharingOptions(BaseModel):
    workspace_access: Optional[str] = Field(None, alias="workspaceAccess")
    external_access: Optional[str] = Field(None, alias="externalAccess")

    model_config = {"populate_by_name": True}


class GenerateRequest(BaseModel):
    """POST /v1.0/generations 요청 바디."""
    input_text: str = Field(alias="inputText")
    text_mode: str = Field(alias="textMode")            # generate | condense | preserve
    format: Optional[str] = "presentation"               # presentation | document | webpage | social
    theme_id: Optional[str] = Field(None, alias="themeId")
    num_cards: Optional[int] = Field(10, alias="numCards")
    card_split: Optional[str] = Field("auto", alias="cardSplit")
    additional_instructions: Optional[str] = Field(None, alias="additionalInstructions")
    folder_ids: Optional[list[str]] = Field(None, alias="folderIds")
    export_as: Optional[str] = Field(None, alias="exportAs")  # pdf | pptx
    text_options: Optional[TextOptions] = Field(None, alias="textOptions")
    image_options: Optional[ImageOptions] = Field(None, alias="imageOptions")
    sharing_options: Optional[SharingOptions] = Field(None, alias="sharingOptions")

    model_config = {"populate_by_name": True}


# --- Create from Template API ---

class TemplateRequest(BaseModel):
    """POST /v1.0/generations/from-template 요청 바디."""
    gamma_id: str = Field(alias="gammaId")
    prompt: str
    theme_id: Optional[str] = Field(None, alias="themeId")
    folder_ids: Optional[list[str]] = Field(None, alias="folderIds")
    export_as: Optional[str] = Field(None, alias="exportAs")  # pdf | pptx
    image_options: Optional[ImageOptions] = Field(None, alias="imageOptions")
    sharing_options: Optional[SharingOptions] = Field(None, alias="sharingOptions")

    model_config = {"populate_by_name": True}


# --- 응답 ---

class GenerationError(BaseModel):
    message: str = ""
    status_code: int = Field(0, alias="statusCode")

    model_config = {"populate_by_name": True}


class GenerationStatus(BaseModel):
    """GET /v1.0/generations/{id} 응답."""
    generation_id: str = Field(alias="generationId")
    status: str                            # pending | processing | completed | failed
    gamma_id: Optional[str] = Field(None, alias="gammaId")
    gamma_url: Optional[str] = Field(None, alias="gammaUrl")
    export_url: Optional[str] = Field(None, alias="exportUrl")
    credits: Optional[Credits] = None
    error: Optional[GenerationError] = None

    model_config = {"populate_by_name": True}

    @property
    def is_done(self) -> bool:
        return self.status in ("completed", "failed")

    @property
    def is_success(self) -> bool:
        return self.status == "completed"


# --- 보조 API ---

class Theme(BaseModel):
    id: str
    name: str
    type: str = ""                        # standard | custom
    color_keywords: list[str] = Field(default_factory=list, alias="colorKeywords")
    tone_keywords: list[str] = Field(default_factory=list, alias="toneKeywords")

    model_config = {"populate_by_name": True}


class Folder(BaseModel):
    id: str
    name: str


class PaginatedResponse(BaseModel):
    """테마/폴더 목록 응답."""
    data: list = Field(default_factory=list)
    has_more: bool = Field(False, alias="hasMore")
    next_cursor: Optional[str] = Field(None, alias="nextCursor")

    model_config = {"populate_by_name": True}
