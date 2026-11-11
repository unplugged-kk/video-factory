"""HyperFrames rendering provider implementation for Video Factory.

Wraps the default local HyperFrames engine, compiling HTML/GSAP timelines
and rendering deterministic frames into MP4.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import hf
from ..qa import probe_video
from .base import RenderProvider


class HyperFramesRenderer(RenderProvider):
    """Default local HyperFrames rendering engine."""

    @property
    def id(self) -> str:
        return "hyperframes"

    @property
    def version(self) -> str:
        """The pinned engine version, read from package.json rather than a hand-maintained string."""
        try:
            pkg = json.loads((Path(__file__).resolve().parents[2] / "package.json").read_text(encoding="utf-8"))
            return str(pkg.get("dependencies", {}).get("hyperframes", "unknown"))
        except (OSError, json.JSONDecodeError):
            return "unknown"

    def capabilities(self) -> dict[str, Any]:
        return {
            "engine": "hyperframes",
            "formats": ["9:16", "16:9"],
            "features": ["gsap", "css_layers", "word_alignment", "timeline_lint"],
            "default": True,
        }

    def preflight(self, ctx: dict) -> None:
        cmd = hf.command("lint")
        if not cmd:
            raise RuntimeError("HyperFrames executable not available in environment")

    def validate(self, spec: dict) -> list[str]:
        errors = []
        if not spec.get("script"):
            errors.append("Spec missing required 'script' lines")
        return errors

    def compose(self, ctx: dict) -> tuple[str, list[Path]]:
        from ..pipeline import s_compose
        return s_compose(ctx)

    def render(self, ctx: dict) -> tuple[str, list[Path]]:
        from ..pipeline import s_render
        return s_render(ctx)

    def inspect(self, artifact: Path) -> dict[str, Any]:
        info = probe_video(artifact)
        if not info:
            raise ValueError(f"Unable to probe video artifact: {artifact}")
        return info
