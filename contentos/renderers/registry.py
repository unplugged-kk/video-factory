"""Renderer registry and router for Video Factory.

Provides unified provider lookup, capability discovery, and selection.
Defaults to HyperFrames unless Remotion or MPT is explicitly requested.
"""
from __future__ import annotations

from typing import Any

from .base import RenderProvider
from .hyperframes import HyperFramesRenderer
from .mpt import MPTRenderer
from .remotion import RemotionRenderer

_REGISTRY: dict[str, RenderProvider] = {}


def register(renderer: RenderProvider) -> None:
    """Register a rendering provider instance."""
    _REGISTRY[renderer.id] = renderer


def get_renderer(spec_or_id: dict | str | None = None) -> RenderProvider:
    """Retrieve the appropriate renderer for a spec or by provider ID.

    Defaults to 'hyperframes' when unspecified or when spec has no explicit render key.
    """
    if spec_or_id is None:
        target_id = "hyperframes"
    elif isinstance(spec_or_id, dict):
        target_id = spec_or_id.get("render") or spec_or_id.get("provider") or "hyperframes"
    elif isinstance(spec_or_id, str):
        target_id = spec_or_id
    else:
        target_id = "hyperframes"

    if target_id not in _REGISTRY:
        raise KeyError(
            f"Renderer '{target_id}' is not registered. Available renderers: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[target_id]


def list_renderers() -> list[dict[str, Any]]:
    """Return catalog of available rendering engines and capabilities."""
    return [
        {
            "id": r.id,
            "version": r.version,
            "capabilities": r.capabilities(),
        }
        for r in _REGISTRY.values()
    ]


# Auto-register default providers
register(HyperFramesRenderer())
register(RemotionRenderer())
register(MPTRenderer())
