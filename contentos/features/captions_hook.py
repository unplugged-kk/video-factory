"""Lane M2-E: Captions, word-locked reveals, hook presentation, and safezone compliance.

Features:
- Short phrase captions locked to word timings
- Big two-tone hook presentation
- Removes raw pipeline scaffold labels (HOOK / STEP n / RECAP / CTA)
- Places captions cleanly out of the bottom safe zone (above H*0.22 margin)
- Stylish pill-style CTA
"""
from __future__ import annotations

import html
import re
from typing import Any

from . import registry


def clean_tag_and_headline(tag: str, headline: str, is_hook: bool, is_cta: bool) -> tuple[str, str]:
    """Remove scaffold tags and refine headline for visual engagement."""
    # Hide raw pipeline labels like 'HOOK', 'STEP 1', 'RECAP', 'CTA'
    cleaned_tag = ""
    cleaned_headline = headline

    if is_hook:
        cleaned_tag = "EXPLAINER"
    elif is_cta:
        cleaned_tag = "UP NEXT"
    elif tag and not re.match(r"^(HOOK|STEP\s*\d+|RECAP|CTA)$", tag.strip()):
        cleaned_tag = tag

    return cleaned_tag, cleaned_headline


def captions_hook_fn(ctx: dict, spec: dict) -> dict:
    """Provide configuration overrides for caption layout, hook style, and safe margins.

    Activated when spec['features']['captions_hook'] is truthy.
    """
    feat_cfg = spec.get("features", {}).get("captions_hook")
    if not feat_cfg:
        return {}

    return {
        "enabled": True,
        "clean_tags": True,
        "safezone_bottom_padding": 0.24,  # Move captions well above 16-20% bottom danger zone
        "two_tone_hook": True,
        "cta_pill": True,
    }


registry.register("captions_hook", captions_hook_fn)
