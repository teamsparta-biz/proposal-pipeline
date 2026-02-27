"""제안서 생성 파이프라인 — ABC 인터페이스 + 구현체."""

from __future__ import annotations

import logging
import re
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..gamma.client import GammaClient
from ..image_gen.renderer import render_design_bg, render_persuasion
from ..gamma.models import GenerateRequest, GenerationStatus, TemplateRequest
from ..pptx_merger.merger import PptxMerger
from ..pptx_replacer.replacer import PptxReplacer
from .models import DynamicPage, FixedPage, PipelineConfig, PipelineResult

logger = logging.getLogger(__name__)


class ProposalPipeline(ABC):
    """제안서 생성 파이프라인 추상 인터페이스."""

    @abstractmethod
    def run(self, variables: dict[str, str], config: PipelineConfig) -> PipelineResult:
        """고객 변수와 설정을 받아 최종 PPTX를 생성한다."""


class DefaultProposalPipeline(ProposalPipeline):
    """10~30 모듈을 조합하는 기본 파이프라인 구현체."""

    def __init__(
        self,
        gamma_client: GammaClient,
        replacer: PptxReplacer,
        merger: PptxMerger,
    ):
        self._gamma = gamma_client
        self._replacer = replacer
        self._merger = merger

    def run(self, variables: dict[str, str], config: PipelineConfig) -> PipelineResult:
        errors: list[str] = []
        work_dir = config.output_dir / "_work"
        work_dir.mkdir(parents=True, exist_ok=True)

        ordered_pages = config.all_pages_ordered
        pptx_paths: list[Path] = []

        # 각 페이지를 순서대로 처리
        for page in ordered_pages:
            try:
                if page["type"] == "fixed":
                    path = self._process_fixed(page["ref"], variables, work_dir)
                    pptx_paths.append(path)
                elif page["type"] == "dynamic":
                    path = self._process_dynamic(page["ref"], variables, config, work_dir)
                    if path:
                        pptx_paths.append(path)
            except Exception as e:
                msg = f"[{page['name']}] 처리 실패: {e}"
                logger.error(msg)
                errors.append(msg)

        if not pptx_paths:
            return PipelineResult(
                outputPath=config.output_dir / "제안서.pptx",
                errors=errors + ["합성할 PPTX가 없습니다."],
            )

        # PPTX 합성
        output_filename = self._build_filename(variables)
        output_path = config.output_dir / output_filename

        try:
            result_prs = self._merger.merge_and_save(pptx_paths, output_path)
            logger.info(f"합성 완료: {output_path}")
        except Exception as e:
            msg = f"PPTX 합성 실패: {e}"
            logger.error(msg)
            errors.append(msg)
            return PipelineResult(outputPath=output_path, errors=errors)

        # 슬라이드 수 카운트 (ZIP-level — SVG 등 python-pptx 미지원 미디어 호환)
        total_slides = self._count_slides(output_path)

        fixed_count = sum(1 for p in ordered_pages if p["type"] == "fixed" and p["name"] not in [e.split("]")[0].lstrip("[") for e in errors])
        dynamic_count = sum(1 for p in ordered_pages if p["type"] == "dynamic" and p["name"] not in [e.split("]")[0].lstrip("[") for e in errors])

        return PipelineResult(
            outputPath=output_path,
            fixedCount=fixed_count,
            dynamicCount=dynamic_count,
            totalSlides=total_slides,
            errors=errors,
        )

    def _process_fixed(self, page: FixedPage, variables: dict[str, str], work_dir: Path) -> Path:
        """고정 페이지: 템플릿 치환 (+ 테이블 주입) → 작업 디렉토리에 저장."""
        safe_name = page.name.replace("/", "_")
        output_path = work_dir / f"{page.order:03d}_{safe_name}.pptx"

        # 전역 변수 + 파트별 변수 병합 (파트 변수가 우선)
        merged_vars = {**variables, **page.part_variables}

        # 치환
        prs = self._replacer.replace(page.template_path, merged_vars)

        # 테이블 주입
        if page.table_rows:
            self._replacer.inject_table(prs, 0, page.table_rows)

        # 설계배경 이미지 생성 + 교체
        if page.design_bg:
            img_path = work_dir / f"{page.order:03d}_{safe_name}_design_bg.png"
            render_design_bg(page.design_bg, img_path)
            self._replacer.replace_slide_image(prs, 0, img_path)
            img_path.unlink(missing_ok=True)
            logger.info(f"설계배경 이미지 생성 및 교체: {page.name}")

        # 설득 파트 이미지 생성 + 교체
        if page.persuasion_slide:
            img_path = work_dir / f"{page.order:03d}_{safe_name}_persuasion.png"
            render_persuasion(page.persuasion_slide, img_path)
            self._replacer.replace_slide_image(prs, 0, img_path)
            img_path.unlink(missing_ok=True)
            logger.info(f"설득 파트 이미지 생성 및 교체: {page.name}")

        # 저장
        output_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(output_path))

        logger.info(f"고정 페이지 처리 완료: {page.name} → {output_path}")
        return output_path

    def _process_dynamic(
        self, page: DynamicPage, variables: dict[str, str], config: PipelineConfig, work_dir: Path
    ) -> Optional[Path]:
        """동적 페이지: prompt에 변수 주입 → Gamma API 호출 → PPTX 다운로드."""
        # prompt_template에 변수 주입
        prompt = page.prompt_template
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

        # mode에 따라 API 선택
        if page.mode == "template":
            if not page.gamma_id:
                raise ValueError(f"template 모드에서는 gammaId가 필수입니다: {page.name}")
            request = TemplateRequest(
                gammaId=page.gamma_id,
                prompt=prompt,
                exportAs=page.export_as,
                themeId=config.gamma_theme_id,
            )
            logger.info(f"Gamma Template API 호출: {page.name} (gammaId={page.gamma_id})")
            status = self._gamma.template_and_wait(request)
        else:
            request = GenerateRequest(
                inputText=prompt,
                textMode="generate",
                format="presentation",
                numCards=page.num_cards,
                exportAs=page.export_as,
                themeId=config.gamma_theme_id,
            )
            logger.info(f"Gamma Generate API 호출: {page.name} ({page.num_cards}카드)")
            status = self._gamma.generate_and_wait(request)

        if not status.is_success:
            error_msg = status.error.message if status.error else "알 수 없는 오류"
            raise RuntimeError(f"Gamma 생성 실패: {error_msg}")

        # exportUrl에서 PPTX 다운로드
        output_path = work_dir / f"{page.order:02d}_{page.name}.pptx"
        if status.export_url:
            self._gamma.download_export(status.export_url, output_path)
            logger.info(f"동적 페이지 다운로드 완료: {page.name} → {output_path}")
            return output_path
        else:
            logger.warning(f"동적 페이지 exportUrl 없음: {page.name}")
            return None

    @staticmethod
    def _count_slides(pptx_path: Path) -> int:
        """PPTX ZIP 내 슬라이드 파일 수를 카운트한다."""
        pat = re.compile(r"^ppt/slides/slide\d+\.xml$")
        with zipfile.ZipFile(str(pptx_path), "r") as z:
            return sum(1 for name in z.namelist() if pat.match(name))

    def _build_filename(self, variables: dict[str, str]) -> str:
        """고객명 기반으로 파일명 생성."""
        customer = variables.get("고객명", "제안서")
        return f"[팀스파르타] {customer} 제안서.pptx"
