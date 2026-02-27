"""리소스 경로 관리 — 템플릿/데이터 디렉토리의 단일 진입점.

우선순위:
  1. set_*() API로 명시 지정
  2. 환경변수 PROPOSAL_TEMPLATE_DIR / PROPOSAL_DATA_DIR
  3. importlib.resources (패키지 번들 리소스)
"""

from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path

_custom_template_dir: Path | None = None
_custom_data_dir: Path | None = None


def set_template_dir(path: Path | str) -> None:
    """커스텀 템플릿 루트 디렉토리를 지정한다."""
    global _custom_template_dir
    _custom_template_dir = Path(path)


def set_data_dir(path: Path | str) -> None:
    """커스텀 데이터 디렉토리를 지정한다."""
    global _custom_data_dir
    _custom_data_dir = Path(path)


def get_template_dir(subdir: str = "parts") -> Path:
    """템플릿 하위 디렉토리 경로를 반환한다.

    Args:
        subdir: "parts", "visuals", "rules" 중 하나.
    """
    root = _resolve_template_root()
    return root / subdir


def get_data_dir() -> Path:
    """데이터 디렉토리 경로를 반환한다."""
    if _custom_data_dir is not None:
        return _custom_data_dir
    env = os.getenv("PROPOSAL_DATA_DIR")
    if env:
        return Path(env)
    return Path(str(files("proposal_pipeline") / "data"))


def _resolve_template_root() -> Path:
    """템플릿 루트 디렉토리를 결정한다."""
    if _custom_template_dir is not None:
        return _custom_template_dir
    env = os.getenv("PROPOSAL_TEMPLATE_DIR")
    if env:
        return Path(env)
    return Path(str(files("proposal_pipeline") / "templates"))
