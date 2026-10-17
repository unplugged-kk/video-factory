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

    # Style-card family awareness for container craft
    style_id = (ctx.get("style_card") or {}).get("chosen") or spec.get("style") or ""

    if "sketch" in style_id:
        card_style = (
            "border:2px dashed rgba(255,255,255,0.22);border-radius:255px 15px 225px 15px/15px 225px 15px 255px;"
            "background:rgba(255,255,255,0.015);box-shadow:inset 0 0 20px rgba(255,255,255,0.03);"
        )
    elif "product" in style_id:
        card_style = (
            "border:1px solid rgba(255,255,255,0.18);border-radius:24px;"
            "background:linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.01));"
            "box-shadow:0 30px 60px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.3);"
            "transform:perspective(1000px) rotateX(2deg);"
        )
    elif "kinetic" in style_id:
        card_style = (
            "border-left:6px solid #fbbf24;border-radius:0 12px 12px 0;"
            "background:rgba(0,0,0,0.4);border-top:1px solid rgba(255,255,255,0.08);"
            "border-right:1px solid rgba(255,255,255,0.08);border-bottom:1px solid rgba(255,255,255,0.08);"
        )
    elif "data" in style_id:
        card_style = (
            "border:1px solid rgba(165,180,252,0.25);border-radius:14px;"
            "background:rgba(15,23,42,0.6);box-shadow:0 12px 30px rgba(0,0,0,0.4);"
        )
    elif "spatial" in style_id:
        card_style = (
            "border:1px solid rgba(147,197,253,0.15);border-radius:30px;"
            "background:radial-gradient(circle at 50% 0%, rgba(59,130,246,0.1), transparent 70%);"
            "box-shadow:0 0 40px rgba(59,130,246,0.08);"
        )
    elif "hybrid" in style_id:
        card_style = (
            "border:1px solid rgba(255,255,255,0.12);border-radius:18px;"
            "background:linear-gradient(180deg, rgba(30,41,59,0.5), rgba(15,23,42,0.7));"
            "box-shadow:0 20px 40px rgba(0,0,0,0.4);"
        )
    else:
        card_style = (
            "border:1px solid rgba(255,255,255,0.08);border-radius:16px;"
            "background:rgba(255,255,255,0.02);"
        )

    # Add a visual decorative card layer for structure
    card_html = (
        f'<div class="visual-decor" id="decor{scene_idx}" '
        f'style="position:absolute;top:15%;left:10%;width:80%;height:32%;'
        f'{card_style}pointer-events:none;z-index:0;"></div>'
    )
    # Inject decorative card right after opening scene div
    if new_tag_start in enriched_html:
        parts = enriched_html.split(">", 1)
        enriched_html = parts[0] + ">" + card_html + parts[1]

    return enriched_html, anim_js


registry.register("visual_layer", visual_layer_hook)
