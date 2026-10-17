"""MoneyPrinterTurbo rendering provider adapter for Video Factory."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import mpt
from ..qa import probe_video
from .base import RenderProvider


class MPTRenderer(RenderProvider):
    """MoneyPrinterTurbo containerized B-roll rendering engine."""

    @property
    def id(self) -> str:
        return "mpt"

    @property
    def version(self) -> str:
        return "1.0.0"

    def capabilities(self) -> dict[str, Any]:
        return {
            "engine": "mpt",
            "formats": ["9:16"],
            "features": ["stock_broll", "burned_subtitles", "docker_container"],
            "default": False,
        }

    def preflight(self, ctx: dict) -> None:
        pass

    def validate(self, spec: dict) -> list[str]:
        errors = []
        if not spec.get("script"):
            errors.append("Spec missing required 'script' lines")
        return errors

    def compose(self, ctx: dict) -> tuple[str, list[Path]]:
        return "mpt", mpt.compose(ctx)

    def render(self, ctx: dict) -> tuple[str, list[Path]]:
        return "mpt", mpt.render(ctx)

    def inspect(self, artifact: Path) -> dict[str, Any]:
        info = probe_video(artifact)
        if not info:
            raise ValueError(f"Unable to probe video artifact: {artifact}")
        return info
