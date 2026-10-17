"""Lane M2-A: Style card and creative decision record.

Wires contentos.intelligence.creative and styles to pick a style card automatically
within registered capabilities, write a decision record (what was chosen and why,
overridable by the owner via spec).
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from ..intelligence import creative, styles
from . import registry


def style_card_hook(ctx: dict, spec: dict) -> None:
    """Resolve and record style card choice.

    Activated when spec['features']['style_card'] is truthy.
    If spec['features']['style_card'] is a string or dict, it can specify or override
    the chosen card or brief.
    """
    feat_cfg = spec.get("features", {}).get("style_card")
    if not feat_cfg:
        return

    # 1. Load available style cards
    cards, problems = styles.load_all()
    catalog_dir = styles.STYLES_DIR / "catalog"
    if catalog_dir.is_dir():
        cat_cards, cat_probs = styles.load_all(styles_dir=catalog_dir)
        cards.extend(cat_cards)
        problems.extend(cat_probs)
    if problems:
        raise ValueError(f"style card problems: {problems}")

    # 2. Build brief for creative decision
    # If spec has explicit creative_brief, use it; otherwise infer from spec fields
    job_id = ctx.get("id") or spec.get("content_id", "default-job")
    topic = spec.get("topic") or spec.get("title") or "Technology Explainer"
    content_type = spec.get("content_type", "ai-workflow")
    if content_type not in styles.CONTENT_TYPES:
        content_type = "ai-workflow"

    brief = {
        "job": job_id,
        "topic": topic,
        "content_type": content_type,
        "length_kind": spec.get("kind", "short"),
        "factual_density": spec.get("factual_density", "medium"),
        "register": spec.get("register", "curious"),
    }

    # 3. Load history if available
    history_dir = None
    if isinstance(feat_cfg, dict):
        history_dir = feat_cfg.get("history_dir")
    history = creative.load_history(history_dir) if history_dir else []

    # 4. Propose candidates
    prop = creative.propose(brief, cards, history)
    candidates = prop["candidates"]

    # 5. Determine chosen card
    chosen = None
    if isinstance(feat_cfg, dict) and feat_cfg.get("chosen"):
        chosen = feat_cfg["chosen"]
    elif isinstance(feat_cfg, str) and feat_cfg not in ("true", "1"):
        chosen = feat_cfg

    if not chosen:
        chosen = candidates[0]["style"]
    elif chosen not in [c["style"] for c in candidates]:
        chosen_card = next((c for c in cards if c["id"] == chosen), None)
        if chosen_card:
            candidates.append(creative.score_card(chosen_card, brief, history))
        else:
            candidates.append({"style": chosen, "score": 5, "fit": 2, "novelty": 0, "experimental": False, "axes": {}})

    # Rejection reasons for non-chosen candidates
    rejection_reasons = {}
    for c in candidates:
        if c["style"] != chosen:
            rejection_reasons[c["style"]] = f"Lower fit or novelty score ({c.get('score', 0)}) compared to {chosen}"

    today = datetime.date.today().isoformat()
    record = creative.make_record(
        brief=brief,
        candidates=candidates,
        chosen=chosen,
        rejection_reasons=rejection_reasons,
        created=today,
        cards=cards,
        note="Automated selection by Milestone 2 Track A style_card hook",
    )

    # 6. Save decision record in job directory if present
    job_dir = ctx.get("dir")
    if job_dir:
        job_dir = Path(job_dir)
        job_dir.mkdir(parents=True, exist_ok=True)
        rec_path = job_dir / "creative-decision.json"
        import json
        rec_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    # Attach chosen card to ctx
    chosen_card = next(c for c in cards if c["id"] == chosen)
    ctx["style_card"] = chosen_card
    ctx["creative_decision"] = record


# Register with features registry
registry.register("style_card", style_card_hook)
