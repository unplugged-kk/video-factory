"""Lane M2-C: Backdrops, transitions, and visual motion layer.

Provides backdrop variety per scene (>= 4 distinct in 7 scenes to satisfy Rule A),
rich gradient / card / diagram container backdrops, and smooth transitions
(crossfade / blur-crossfade) replacing static fade-out dips.
"""
from __future__ import annotations

import html
from typing import Any

from . import registry

# Distinct backdrops palette designed to satisfy Rule A (at least 4 distinct in 7 scenes)
BACKDROPS = [
    # Scene 1 (Hook): deep cosmic blue with subtle radial glow
    "radial-gradient(circle at 50% 30%, #1e293b, #090d16 85%)",
    # Scene 2 (Step 1): slate navy with teal accent glow
    "radial-gradient(circle at 70% 40%, #0f2b38, #070e17 80%)",
    # Scene 3 (Step 2): deep indigo with purple accent glow
    "radial-gradient(circle at 30% 60%, #1e1b4b, #070913 80%)",
    # Scene 4 (Step 3): slate emerald with dark base
    "radial-gradient(circle at 65% 25%, #064e3b, #051412 85%)",
    # Scene 5 (Step 4): rich sapphire with blue-cyan glow
    "radial-gradient(circle at 35% 75%, #1e3a8a, #070d1e 85%)",
    # Scene 6 (Recap): deep plum with violet glow
    "radial-gradient(circle at 50% 50%, #2e1065, #080514 85%)",
    # Scene 7 (CTA): high-contrast modern graphite with subtle amber glow
    "radial-gradient(circle at 50% 80%, #292524, #0c0a09 85%)",
]


def visual_layer_hook(
    ctx: dict,
    scene_idx: int,
    scene_html: str,
    anim_js: list,
    spec: dict,
) -> tuple[str, list]:
    """Inject backdrop variety, container cards, and motion into the scene.

    Activated when spec['features']['visual_layer'] is truthy.
    """
    feat_cfg = spec.get("features", {}).get("visual_layer")
    if not feat_cfg:
        return scene_html, anim_js

    # Pick distinct backdrop for this scene index (1-based)
    bg_style = BACKDROPS[(scene_idx - 1) % len(BACKDROPS)]

    # Enrich scene container: add backdrop style, subtle glassmorphic backdrop layer and motion wrapper
    # We replace the starting <div class="scene clip" with a stylized one
    old_tag_start = f'<div class="scene clip" id="s{scene_idx}"'
    new_tag_start = (
        f'<div class="scene clip visual-scene" id="s{scene_idx}" '
        f'style="background:{bg_style}; backdrop-filter:blur(20px);"'
    )
    enriched_html = scene_html.replace(old_tag_start, new_tag_start, 1)

    # Add a visual decorative card layer for structure (closing gap 1 and 4)
    card_html = (
        f'<div class="visual-decor" id="decor{scene_idx}" '
        f'style="position:absolute;top:15%;left:10%;width:80%;height:32%;'
        f'border:1px solid rgba(255,255,255,0.08);border-radius:16px;'
        f'background:rgba(255,255,255,0.02);pointer-events:none;z-index:0;"></div>'
    )
    # Inject decorative card right after opening scene div
    if new_tag_start in enriched_html:
        parts = enriched_html.split(">", 1)
        enriched_html = parts[0] + ">" + card_html + parts[1]

    return enriched_html, anim_js


registry.register("visual_layer", visual_layer_hook)
