"""Feature flags and modules for Milestone 2.

Imports all feature modules so they register their hooks into contentos.features.registry.
"""
from . import audio_bed, captions_hook, extra_gates, registry, scene_plan, style_card

__all__ = [
    "audio_bed",
    "captions_hook",
    "extra_gates",
    "registry",
    "scene_plan",
    "style_card",
]
