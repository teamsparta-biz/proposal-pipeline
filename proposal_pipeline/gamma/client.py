"""Gamma API 클라이언트 — ABC 인터페이스 + HTTP 구현체."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import httpx

from .models import (
    Folder,
    GenerateRequest,
    GenerationStatus,
    PaginatedResponse,
    TemplateRequest,
    Theme,
)


class GammaClient(ABC):
    """Gamma API 추상 인터페이스."""

    # --- 생성 ---

    @abstractmethod
    def generate(self, request: GenerateRequest) -> str:
        """Generate API 호출. generationId를 반환."""

    @abstractmethod
    def create_from_template(self, request: TemplateRequest) -> str:
        """Create from Template API 호출. generationId를 반환."""

    @abstractmethod
    def get_status(self, generation_id: str) -> GenerationStatus:
        """생성 상태 조회."""

    # --- 보조 ---

    @abstractmethod
    def list_themes(self, query: str = "", limit: int = 50) -> list[Theme]:
        """테마 목록 조회."""

    @abstractmethod
    def list_folders(self, query: str = "", limit: int = 50) -> list[Folder]:
        """폴더 목록 조회."""

    # --- 편의 메서드 (구현체 공통) ---

    def wait_for_completion(
        self,
        generation_id: str,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
    ) -> GenerationStatus:
        """생성 완료까지 폴링. 타임아웃 시 예외 발생."""
        start = time.time()
        while True:
            status = self.get_status(generation_id)
            if status.is_done:
                return status
            elapsed = time.time() - start
            if elapsed + poll_interval > timeout:
                raise TimeoutError(
                    f"Gamma 생성 타임아웃 ({timeout}초 초과). "
                    f"generation_id={generation_id}, 마지막 상태={status.status}"
                )
            time.sleep(poll_interval)

    def generate_and_wait(self, request: GenerateRequest, **poll_kwargs) -> GenerationStatus:
        """Generate API 호출 + 완료까지 대기."""
        gen_id = self.generate(request)
        return self.wait_for_completion(gen_id, **poll_kwargs)

    def template_and_wait(self, request: TemplateRequest, **poll_kwargs) -> GenerationStatus:
        """Template API 호출 + 완료까지 대기."""
        gen_id = self.create_from_template(request)
        return self.wait_for_completion(gen_id, **poll_kwargs)


class GammaHttpClient(GammaClient):
    """httpx 기반 Gamma API 구현체."""

    def __init__(self, api_key: str, base_url: str = "https://public-api.gamma.app/v1.0"):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            timeout=60.0,
        )

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def _check_response(self, resp: httpx.Response) -> dict:
        if resp.status_code == 401:
            raise PermissionError("Gamma API 인증 실패. API Key를 확인하세요.")
        if resp.status_code == 400:
            body = resp.json()
            raise ValueError(f"Gamma API 요청 오류: {body.get('message', resp.text)}")
        resp.raise_for_status()
        return resp.json()

    # --- 생성 ---

    def generate(self, request: GenerateRequest) -> str:
        body = request.model_dump(by_alias=True, exclude_none=True)
        resp = self._client.post(self._url("/generations"), json=body)
        data = self._check_response(resp)
        return data["generationId"]

    def create_from_template(self, request: TemplateRequest) -> str:
        body = request.model_dump(by_alias=True, exclude_none=True)
        resp = self._client.post(self._url("/generations/from-template"), json=body)
        data = self._check_response(resp)
        return data["generationId"]

    def get_status(self, generation_id: str) -> GenerationStatus:
        resp = self._client.get(self._url(f"/generations/{generation_id}"))
        data = self._check_response(resp)
        return GenerationStatus.model_validate(data)

    # --- 보조 ---

    def list_themes(self, query: str = "", limit: int = 50) -> list[Theme]:
        params: dict = {"limit": min(limit, 50)}
        if query:
            params["query"] = query
        resp = self._client.get(self._url("/themes"), params=params)
        data = self._check_response(resp)
        page = PaginatedResponse.model_validate(data)
        return [Theme.model_validate(t) for t in page.data]

    def list_folders(self, query: str = "", limit: int = 50) -> list[Folder]:
        params: dict = {"limit": min(limit, 50)}
        if query:
            params["query"] = query
        resp = self._client.get(self._url("/folders"), params=params)
        data = self._check_response(resp)
        page = PaginatedResponse.model_validate(data)
        return [Folder.model_validate(f) for f in page.data]

    # --- 파일 다운로드 ---

    def download_export(self, export_url: str, output_path: Path) -> Path:
        """exportUrl에서 PPTX/PDF 파일을 다운로드한다."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream("GET", export_url, timeout=60.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        return output_path

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
