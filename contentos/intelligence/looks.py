"""look/1: a reusable LOOK or EFFECT preset, kept as data so a new look never needs a new skill.

A look is a visual language (palette, type, texture, motion, captions, sound) that sits on top of a style/1 card or stands
alone. An effect is one parameterised treatment that a look or a job can switch on (a trigger, params, what it needs).
Presets carry the technique, never a named third-party creator, character, franchise or logo. Status stays `unvalidated`
until a real render in our pipeline records evidence.

  python -m contentos.intelligence.looks validate [--dir DIR]     exit 0 ok, 1 problems, 2 unreadable
  python -m contentos.intelligence.looks list [--kind look|effect] [--dir DIR]
  python -m contentos.intelligence.looks show <id> [--dir DIR]
  python -m contentos.intelligence.looks combine <base-id> <overlay-id> [--dir DIR]   print a merged look (JSON)
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PRESETS_DIR = ROOT / "config" / "presets"
SCHEMA = "look/1"
KINDS = ("look", "effect")
FAMILIES = ("story", "lyric", "explainer", "talking-head", "repurpose", "any")
TRIGGERS = ("always", "beat", "word", "keyword", "number", "sentence", "scene")
STATUSES = ("unvalidated", "validated")
# Tools a preset may need. `core` means the pinned renderer plus ffmpeg, already present.
NEEDS = ("core", "forced-alignment", "beat-detection", "vocal-separation", "segmentation", "face-tracking", "map-data",
         "chart-data", "supplied-media", "tts")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
# Third-party names that must never appear in a preset: technique only, original characters (decision D4).
BLOCKED = ("attack on titan", "mirzapur", "pusho", "puneet", "latent", "samay", "raj shamani", "bieber", "honey singh",
           "banjaare", "anuv jain", "drishyam", "fireship", "aansh", "zero se freelance", "kulhad", "piramal", "tesla",
           "kaalin", "one-punch","instagram", "iphone", "apple", "ios")
LOOK_REQUIRED = {"palette", "typography", "motion", "captions"}
EFFECT_REQUIRED = {"trigger", "params"}
COMMON_REQUIRED = {"schema", "id", "name", "kind", "summary", "family", "status", "needs", "provenance"}
LOOK_KEYS = COMMON_REQUIRED | LOOK_REQUIRED | {"base_style", "texture", "effects", "audio", "layout", "forbidden",
                                                "frame_checklist", "combined_from"}
EFFECT_KEYS = COMMON_REQUIRED | EFFECT_REQUIRED | {"safe_zone", "audio", "forbidden", "frame_checklist"}


def load_dir(directory: Path = PRESETS_DIR) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in sorted(Path(directory).rglob("*.json")):
        d = json.loads(p.read_text())
        if d.get("id") in out:
            raise ValueError(f"duplicate preset id {d['id']!r} in {p}")
        out[d["id"]] = d
    return out


def check(card: dict, known: dict[str, dict] | None = None) -> list[str]:
    e: list[str] = []
    if card.get("schema") != SCHEMA:
        e.append(f"schema must be {SCHEMA!r}")
    kind = card.get("kind")
    if kind not in KINDS:
        return e + [f"kind must be one of {KINDS}"]
    allowed = LOOK_KEYS if kind == "look" else EFFECT_KEYS
    required = COMMON_REQUIRED | (LOOK_REQUIRED if kind == "look" else EFFECT_REQUIRED)
    e += [f"unknown key: {k}" for k in sorted(set(card) - allowed)]
    e += [f"missing key: {k}" for k in sorted(required - set(card))]
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(card.get("id", ""))):
        e.append("id must be lowercase-kebab")
    if card.get("family") not in FAMILIES:
        e.append(f"family must be one of {FAMILIES}")
    if card.get("status") not in STATUSES:
        e.append(f"status must be one of {STATUSES}")
    bad = set(card.get("needs", [])) - set(NEEDS)
    if bad or not card.get("needs"):
        e.append(f"needs must be a non-empty subset of {NEEDS}" + (f"; unknown {sorted(bad)}" if bad else ""))
    if kind == "effect" and card.get("trigger") not in TRIGGERS:
        e.append(f"trigger must be one of {TRIGGERS}")
    if kind == "look":
        for k, v in (card.get("palette") or {}).items():
            if not HEX.match(str(v)):
                e.append(f"palette.{k} must be a #rrggbb colour")
        if not {"bg", "fg", "accent"} <= set(card.get("palette") or {}):
            e.append("palette needs bg, fg and accent")
        if not {"display", "body"} <= set(card.get("typography") or {}):
            e.append("typography needs display and body")
        if "intensity" not in (card.get("motion") or {}) or not 1 <= card["motion"]["intensity"] <= 5:
            e.append("motion.intensity must be 1-5")
        for eff in card.get("effects", []):
            if known is not None and known.get(eff, {}).get("kind") != "effect":
                e.append(f"effects references unknown effect {eff!r}")
    text = json.dumps(card).lower()
    e += [f"third-party name not allowed: {b!r}" for b in BLOCKED if re.search(rf"\b{re.escape(b)}\b", text)]
    return e


def validate_all(directory: Path = PRESETS_DIR) -> list[str]:
    try:
        cards = load_dir(directory)
    except (OSError, ValueError) as ex:
        return [f"cannot load presets: {ex}"]
    errs = []
    for cid, c in cards.items():
        errs += [f"{cid}: {m}" for m in check(c, cards)]
    return errs


def combine(base: dict, overlay: dict, known: dict[str, dict], new_id: str | None = None) -> dict:
    """Merge two looks: `base` keeps palette bg/fg, typography, captions and motion; `overlay` contributes its accent,
    texture and the effects that fit the base family (an effect needing a filmed subject is dropped from a lyric base).
    `needs` is recomputed from what is kept. Result is a fresh look that must pass check()."""
    if base.get("kind") != "look" or overlay.get("kind") != "look":
        raise ValueError("combine needs two looks")
    out = copy.deepcopy(base)
    out["id"] = new_id or f"{base['id']}-x-{overlay['id']}"
    out["name"] = f"{base['name']} + {overlay['name']}"
    out["summary"] = f"{base['summary']} Accent, texture and effects borrowed from {overlay['name']}."
    out["palette"]["accent"] = overlay["palette"]["accent"]
    out["texture"] = sorted(set(base.get("texture", [])) | set(overlay.get("texture", [])))
    fits = [e for e in overlay.get("effects", []) if known[e]["family"] in (base["family"], "any")]
    out["effects"] = sorted(set(base.get("effects", [])) | set(fits))
    out["needs"] = sorted(set(base["needs"]).union(*(known[e]["needs"] for e in fits)))
    out["combined_from"] = [base["id"], overlay["id"]]
    out["status"] = "unvalidated"
    out.pop("base_style", None)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m contentos.intelligence.looks", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "list", "show", "combine"):
        s = sub.add_parser(name)
        s.add_argument("--dir", type=Path, default=PRESETS_DIR)
        if name == "list":
            s.add_argument("--kind", choices=KINDS)
        if name == "show":
            s.add_argument("id")
        if name == "combine":
            s.add_argument("base")
            s.add_argument("overlay")
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        errs = validate_all(a.dir)
        print(json.dumps({"ok": not errs, "problems": errs}, indent=2))
        return 1 if errs else 0
    try:
        cards = load_dir(a.dir)
    except (OSError, ValueError) as ex:
        print(ex, file=sys.stderr)
        return 2
    if a.cmd == "list":
        for c in cards.values():
            if not a.kind or c["kind"] == a.kind:
                print(f"{c['id']:32} {c['kind']:7} {c['family']:13} {c['summary'][:70]}")
        return 0
    ids = [a.id] if a.cmd == "show" else [a.base, a.overlay]
    missing = [i for i in ids if i not in cards]
    if missing:
        print(f"unknown preset: {missing}", file=sys.stderr)
        return 2
    if a.cmd == "show":
        print(json.dumps(cards[a.id], indent=2))
        return 0
    try:
        merged = combine(cards[a.base], cards[a.overlay], cards)
    except ValueError as ex:
        print(ex, file=sys.stderr)
        return 2
    errs = check(merged, cards)
    print(json.dumps(merged, indent=2))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
