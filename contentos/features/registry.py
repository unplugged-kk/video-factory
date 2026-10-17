"""Feature registry: maps feature names to their handler modules.

Each handler module must expose a single callable matching the hook signature
documented here. When a feature is not in spec['features'] or its value is falsy,
get() returns the appropriate pass-through so the pipeline never sees None.

Hook signatures (must be matched exactly by lane modules):
  style_card(ctx, spec) -> None           # may mutate ctx['style_card']
  scene_plan(ctx, spec) -> list           # returns per-scene dicts (or [] pass-through)
  visual_layer(ctx, scene_idx, scene_html, anim_js, spec) -> (scene_html, anim_js)
  audio_bed(ctx, mp4_path, spec) -> Path  # returns final mp4 path (may be new file)
  captions_hook(ctx, spec) -> dict        # returns {scenes: [...], anim: [...]} overrides
  qa_extra(ctx, mp4_path, spec) -> list   # returns [(check, status, detail), ...]
"""
from __future__ import annotations

from typing import Any, Callable

# Registry: filled by each lane's module at import time via register().
_REGISTRY: dict[str, Callable] = {}


def register(name: str, fn: Callable) -> None:
    """Lane modules call this at module level to register their handler."""
    _REGISTRY[name] = fn


# Pass-through implementations — returned when a feature is off.
def _pt_style_card(ctx, spec): return None
def _pt_scene_plan(ctx, spec): return []
def _pt_visual_layer(ctx, scene_idx, scene_html, anim_js, spec): return scene_html, anim_js
def _pt_audio_bed(ctx, mp4_path, spec): return mp4_path
def _pt_captions_hook(ctx, spec): return {}
def _pt_qa_extra(ctx, mp4_path, spec): return []


_PASS_THROUGH = {
    "style_card": _pt_style_card,
    "scene_plan": _pt_scene_plan,
    "visual_layer": _pt_visual_layer,
    "audio_bed": _pt_audio_bed,
    "captions_hook": _pt_captions_hook,
    "qa_extra": _pt_qa_extra,
}


def get(name: str, spec: dict) -> Callable:
    """Return the handler for `name` if the feature is enabled in spec, else the pass-through.

    A feature is enabled when spec.get('features', {}).get(name) is truthy.
    The handler must be registered before get() is called with it enabled;
    an unregistered-but-enabled feature raises KeyError (fail loud, not silent).
    """
    features = spec.get("features") or {}
    if not features.get(name):
        return _PASS_THROUGH[name]
    if name not in _REGISTRY:
        raise KeyError(f"feature '{name}' is enabled in spec but not registered; "
                       f"import its module before calling pipeline.run()")
    return _REGISTRY[name]
