"""style/1: a style card is a CONTRACT for a visual language, not a palette.

A card fixes six structural axes (layout, motion grammar, rhythm, depth, illustration mode, transitions), a few dials, the
motion it forbids, the sound strategy and a frame checklist a reviewer can tick. Two cards must differ on >= 3 axes, so
changing only colours or fonts cannot pass as a new style. Status is `unvalidated` until a real render in OUR pipeline
records evidence; a card names its reviewer (`reviewed_by`) and cites a repo file for every ease (`ease_sources`); nothing in this module renders, calls a network, or edits any project. Shadow mode: no pipeline reads cards yet.

  python -m contentos.intelligence.styles validate [--dir DIR]     exit 0 ok, 1 problems, 2 unreadable
  python -m contentos.intelligence.styles list [--dir DIR]
  python -m contentos.intelligence.styles show <id> [--dir DIR]
  python -m contentos.intelligence.styles distinct [--dir DIR]
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STYLES_DIR = ROOT / "config" / "styles"
SCHEMA = "style/1"

AXES = {
    "layout_system": ("grid", "full-bleed", "split", "stacked-cards", "centered-stage"),
    "motion_grammar": ("eased-glide", "snap-cut", "draw-on", "parallax", "type-driven"),
    "scene_rhythm": ("even", "accelerating", "punctuated"),
    "depth_model": ("flat", "layered", "pseudo-3d"),
    "illustration_mode": ("diagrammatic", "iconographic", "photographic", "typographic", "textural"),
    "transition_family": ("cut", "wipe", "morph", "dissolve", "push"),
}
DIALS = ("energy", "density", "formality", "warmth", "pace")
STATUSES = ("unvalidated", "validated")
SOUND_MODES = ("narration-led", "silent")
CONTENT_TYPES = ("architecture-lesson", "ai-workflow", "historical-explainer", "product-launch",
                 "science-concept", "how-to", "news-opinion")
MIN_DIFFERING_AXES = 3
_ID = re.compile(r"^[a-z][a-z0-9-]{2,40}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_REQUIRED = ("schema", "id", "name", "summary", "status", "evidence", "axes", "dials", "motion", "layout_vocabulary",
             "sound", "requires", "frame_checklist", "best_for", "source_techniques", "licence_notes", "reviewed_by")


def _strs(v, minimum):
    return isinstance(v, list) and len(v) >= minimum and all(isinstance(x, str) and x.strip() for x in v)


def _valid_date(v):
    if not isinstance(v, str) or not _DATE.match(v):
        return False
    try:
        date.fromisoformat(v)
    except ValueError:
        return False
    return True


def _check_ease_sources(eases, sources):
    """Every ease in ease_family needs a repo file that contains its name. Returns problem strings."""
    if not isinstance(sources, list):
        return ["motion.ease_sources must be a list of {ease, file} objects"]
    p, covered = [], set()
    for s in sources:
        if not isinstance(s, dict) or set(s) != {"ease", "file"}:
            p.append("motion.ease_sources entries must have exactly 'ease' and 'file'")
            continue
        e, f = s["ease"], s["file"]
        if e not in eases:
            p.append(f"motion.ease_sources {e!r} is not in motion.ease_family")
            continue
        covered.add(e)
        if not isinstance(f, str) or Path(f).is_absolute() or ".." in Path(f).parts or not (ROOT / f).is_file():
            p.append(f"motion.ease_sources {e!r}: file {f!r} is not a file inside the repo")
        elif e not in (ROOT / f).read_text(encoding="utf-8", errors="replace"):
            p.append(f"motion.ease_sources {e!r}: {f!r} does not contain that ease name")
    for e in eases:
        if e not in covered:
            p.append(f"motion.ease_family {e!r} has no motion.ease_sources entry")
    return p


def validate_card(card, registry=None, filename_stem=None):
    """Return a list of problem strings (empty = valid). Never mutates `card`."""
    p = []
    if not isinstance(card, dict):
        return ["card must be a JSON object"]
    for k in _REQUIRED:
        if k not in card:
            p.append(f"missing field {k!r}")
    if p:
        return p
    cid = card["id"]
    if card["schema"] != SCHEMA:
        p.append(f"schema is {card['schema']!r}, expected {SCHEMA!r}")
    if not isinstance(cid, str) or not _ID.match(cid):
        p.append(f"id {cid!r} must match {_ID.pattern}")
    elif filename_stem is not None and cid != filename_stem:
        p.append(f"id {cid!r} does not match file name {filename_stem!r}")
    for k in ("name", "summary", "licence_notes"):
        if not isinstance(card[k], str) or not card[k].strip():
            p.append(f"{k} must be a non-empty string")
    if card["status"] not in STATUSES:
        p.append(f"status {card['status']!r} not in {STATUSES}")
    if not isinstance(card["evidence"], list):
        p.append("evidence must be a list")
    elif card["status"] == "validated" and not card["evidence"]:
        p.append("status 'validated' requires non-empty evidence (paths to real render records)")
    axes = card["axes"]
    if not isinstance(axes, dict):
        p.append("axes must be an object")
    else:
        for a, allowed in AXES.items():
            if a not in axes:
                p.append(f"axes.{a} is missing")
            elif axes[a] not in allowed:
                p.append(f"axes.{a} = {axes[a]!r} not in {allowed}")
        for extra in set(axes) - set(AXES):
            p.append(f"unknown axis {extra!r}")
    dials = card["dials"]
    if not isinstance(dials, dict):
        p.append("dials must be an object")
    else:
        for d in DIALS:
            v = dials.get(d)
            if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 5:
                p.append(f"dials.{d} must be an integer 1-5")
    m = card["motion"]
    if not isinstance(m, dict):
        p.append("motion must be an object")
    else:
        if not _strs(m.get("ease_family"), 1):
            p.append("motion.ease_family needs >= 1 non-empty string")
        else:
            p.extend(_check_ease_sources(m["ease_family"], m.get("ease_sources")))
        if not _strs(m.get("forbidden"), 2):
            p.append("motion.forbidden needs >= 2 non-empty strings")
        if m.get("respects_r1_r6") is not True:
            p.append("motion.respects_r1_r6 must be true (read explainer-motion-craft R1-R6 first)")
    if not _strs(card["layout_vocabulary"], 3):
        p.append("layout_vocabulary needs >= 3 non-empty strings")
    if not _strs(card["frame_checklist"], 4):
        p.append("frame_checklist needs >= 4 non-empty strings")
    s = card["sound"]
    if not isinstance(s, dict):
        p.append("sound must be an object")
    else:
        if s.get("mode") not in SOUND_MODES:
            p.append(f"sound.mode {s.get('mode')!r} not in {SOUND_MODES} (music-led needs beat analysis, which does not exist)")
        n = s.get("max_cues_per_minute")
        if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= 12:
            p.append("sound.max_cues_per_minute must be an integer 0-12")
        elif s.get("mode") == "silent" and n != 0:
            p.append("sound.mode 'silent' requires max_cues_per_minute 0")
    rb = card["reviewed_by"] if isinstance(card["reviewed_by"], dict) else {}
    if not isinstance(rb.get("name"), str) or not rb["name"].strip():
        p.append("reviewed_by.name must be a non-empty string (who signed off the card)")
    if not _valid_date(rb.get("date")):
        p.append("reviewed_by.date must be a real YYYY-MM-DD date")
    b = card["best_for"]
    if not isinstance(b, dict):
        p.append("best_for must be an object")
    else:
        for k in ("content_types", "avoid"):
            v = b.get(k)
            if not isinstance(v, list) or any(x not in CONTENT_TYPES for x in v):
                p.append(f"best_for.{k} must be a list drawn from {CONTENT_TYPES}")
        if isinstance(b.get("content_types"), list) and not b["content_types"]:
            p.append("best_for.content_types needs >= 1 entry")
    if not isinstance(card["source_techniques"], list):
        p.append("source_techniques must be a list")
    req = card["requires"]
    if not isinstance(req, list):
        p.append("requires must be a list")
    elif registry is not None:
        for cap in req:
            if cap not in registry:
                p.append(f"requires {cap!r}: not in config/capabilities.json")
            elif registry.get(cap)["status"] != "installed":
                p.append(f"requires {cap!r}: status is {registry.get(cap)['status']!r}, only 'installed' is allowed on a card")
    return p


def differing_axes(a, b):
    return [k for k in AXES if a["axes"].get(k) != b["axes"].get(k)]


def check_distinct(cards, min_axes=MIN_DIFFERING_AXES):
    """Every pair of cards must differ on >= min_axes axes. Returns problem strings."""
    p = []
    for a, b in itertools.combinations(cards, 2):
        d = differing_axes(a, b)
        if len(d) < min_axes:
            p.append(f"{a['id']} and {b['id']} differ on only {len(d)} axes {d}; need >= {min_axes} (a palette variant is not a style)")
    return p


def _registry():
    from contentos.production import direction
    return direction.load_registry()


def load_all(styles_dir=None, registry=None):
    """Return (cards, problems). Problems are prefixed with the file name. Raises OSError if the directory is unreadable."""
    d = Path(styles_dir) if styles_dir else STYLES_DIR
    if not d.is_dir():
        raise OSError(f"styles directory not found: {d}")
    reg = registry if registry is not None else _registry()
    cards, problems = [], []
    for f in sorted(d.glob("*.json")):
        try:
            card = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{f.name}: cannot read: {exc}")
            continue
        issues = validate_card(card, reg, filename_stem=f.stem)
        problems.extend(f"{f.name}: {i}" for i in issues)
        if not issues:
            cards.append(card)
    problems.extend(check_distinct(cards))
    return cards, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "list", "show", "distinct"):
        sp = sub.add_parser(name)
        sp.add_argument("--dir")
        if name == "show":
            sp.add_argument("id")
    a = ap.parse_args(argv)
    try:
        cards, problems = load_all(a.dir)
    except Exception as exc:      # unreadable directory or registry
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if a.cmd == "validate":
        print(json.dumps({"cards": len(cards), "problems": problems}, indent=1))
        return 1 if problems else 0
    if a.cmd == "list":
        for c in cards:
            print(f"{c['id']:28} {c['status']:12} {' / '.join(c['axes'][k] for k in AXES)}")
        return 0
    if a.cmd == "distinct":
        for x, y in itertools.combinations(cards, 2):
            print(f"{x['id']} vs {y['id']}: {len(differing_axes(x, y))} axes differ")
        return 1 if check_distinct(cards) else 0
    card = next((c for c in cards if c["id"] == a.id), None)
    if not card:
        print(f"no valid card {a.id!r}", file=sys.stderr)
        return 1
    print(json.dumps(card, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
