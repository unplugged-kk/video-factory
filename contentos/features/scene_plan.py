"""Lane M2-B: Scene plans consumption.

Consumes contentos.production.sceneplan so the builder gets per-scene structure
(element lists, timing anchors, title, visual action) instead of one heading + paragraph.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..production import sceneplan
from . import registry


def scene_plan_hook(ctx: dict, spec: dict) -> list[dict]:
    """Consume or generate structured scene plan.

    Activated when spec['features']['scene_plan'] is truthy.
    Returns a list of per-scene plan dicts with timing anchors, element tags, and layout keys.
    """
    feat_cfg = spec.get("features", {}).get("scene_plan")
    if not feat_cfg:
        return []

    # If explicit scene plan provided in spec or file, load it
    plan_data = None
    if isinstance(feat_cfg, dict) and "plan" in feat_cfg:
        plan_data = feat_cfg["plan"]
    elif isinstance(feat_cfg, str) and feat_cfg.endswith(".json") and Path(feat_cfg).exists():
        plan_data = json.loads(Path(feat_cfg).read_text(encoding="utf-8"))
    elif "scene_plan" in spec:
        plan_data = spec["scene_plan"]

    script_lines = spec.get("script", [])
    if not plan_data:
        # Synthesize a structured sceneplan/1 from script lines
        scenes = []
        for i, ln in enumerate(script_lines, 1):
            say_words = ln["say"].split()
            first_phrase = " ".join(say_words[:min(3, len(say_words))])
            tag = ln.get("tag", f"{i}/{len(script_lines)}")
            # Identify scene role and visual cues
            visual_type = "diagram" if "tool" in ln["say"].lower() or "loop" in ln["say"].lower() else "concept"
            scenes.append({
                "id": f"s{i}",
                "title": ln.get("headline", f"Scene {i}"),
                "tag": tag,
                "starts_at": first_phrase,
                "visual": f"{visual_type}: {ln.get('headline', '')}",
                "elements": [
                    {"type": "tag", "content": tag},
                    {"type": "heading", "content": ln.get("headline", "")},
                    {"type": "body", "content": ln["say"]},
                ],
                "layout": "centered" if i == 1 or i == len(script_lines) else "split",
            })
        plan_data = {"schema": "sceneplan/1", "scenes": scenes}

    # Store resolved plan in ctx for downstream visual builder
    ctx["scene_plan"] = plan_data
    return plan_data.get("scenes", [])


registry.register("scene_plan", scene_plan_hook)
