"""Common rendering provider contract and abstract base class for Video Factory.

Defines the formal protocol and interface for video rendering engines (HyperFrames, Remotion, MPT).
A provider must not report a successful render until output verification passes.
"""
from __future__ import annotations

import abc
from pathlib import Path
from typing import Any, Protocol


class RenderProvider(abc.ABC):
    """Abstract rendering provider protocol."""

    @property
    @abc.abstractmethod
    def id(self) -> str:
        """Provider unique identifier (e.g. 'hyperframes', 'remotion')."""
        ...

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """Provider package or engine version."""
        ...

    @abc.abstractmethod
    def capabilities(self) -> dict[str, Any]:
        """Declared provider capabilities, supported formats, and features."""
        ...

    @abc.abstractmethod
    def preflight(self, ctx: dict) -> None:
        """Verify environment, binaries, dependencies and runtime before job execution.

        Raises Blocked or RuntimeError if prerequisites are missing.
        """
        ...

    @abc.abstractmethod
    def validate(self, spec: dict) -> list[str]:
        """Validate input spec for provider-specific constraints. Returns list of errors (empty if valid)."""
        ...

    @abc.abstractmethod
    def compose(self, ctx: dict) -> tuple[str, list[Path]]:
        """Generate provider-specific composition project from spec and audio.

        Returns (provider_id, list_of_artifacts).
        """
        ...

    @abc.abstractmethod
    def render(self, ctx: dict) -> tuple[str, list[Path]]:
        """Render the composition into the output MP4 and verify output integrity.

        Returns (provider_id, [output_mp4_path]).
        """
        ...

    @abc.abstractmethod
    def inspect(self, artifact: Path) -> dict[str, Any]:
        """Inspect a rendered video artifact (dimensions, duration, streams)."""
        ...
