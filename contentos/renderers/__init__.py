"""Multi-renderer architecture and provider abstraction for Video Factory."""
from .base import RenderProvider
from .registry import get_renderer, list_renderers, register

__all__ = ["RenderProvider", "get_renderer", "list_renderers", "register"]
