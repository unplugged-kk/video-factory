"""Design library: which upstream design, palette, style and transition suits a topic, ranked with the reasons shown.

config/design-library.json (Git, seed) lists HyperFrames' frame presets, palettes, visual styles, shader transitions and
CSS transitions, each tagged by register, mood, topic, energy and aspect. Run evidence lives in
<workspace>/intelligence/design-evidence.json and may only change `confidence`, `evidence_count` and `verified` of ids
that already exist; without it every entry stays `unverified`.

  python -m contentos.intelligence.designs validate
  python -m contentos.intelligence.designs recommend --topic ai-ml --mood futuristic --aspect 9:16 --register dark
  python -m contentos.intelligence.designs list --kind shader_transition
  python -m contentos.intelligence.designs show preset:broadside

Ranking is plain addition of visible components, printed with every result, not a learned score:
  topic match +3, mood match +2 each, register match +2 (mixed +1), energy exact +2 (adjacent +1),
  confidence bonus preferred +3 / validated +2 / experimental +1 / unverified 0, slow render cost -1 with --prefer-fast.
Entries that do not document the requested aspect, are deprecated, or have verified.result == "fail" are excluded
(--include-failed shows failures). This picks CANDIDATES by subject; Rule A/B (contentos.intelligence.visual) still
decides whether the result is different enough from recent videos. Exit codes: 0 ok, 1 finding/no match, 2 unreadable."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import storage

REPO = Path(__file__).resolve().parent.parent.parent
SEED = REPO / "config" / "design-library.json"
SCHEMA = "design-library/1"
CONF_BONUS = {"preferred": 3, "validated": 2, "experimental": 1, "unverified": 0}
ENERGY = ("calm", "medium", "high")
OVERLAY_FIELDS = {"confidence", "evidence_count", "verified"}
KIND_ORDER = ("frame_preset", "palette", "visual_style", "shader_transition", "css_transition")
DEFAULT_TOP = {"frame_preset": 3, "palette": 2, "visual_style": 2, "shader_transition": 3, "css_transition": 4}


class DesignError(Exception):
    pass


def _read(path, what):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DesignError(f"cannot read {what} {path}: {exc}") from exc


def evidence_path():
    return storage.workspace_root() / "intelligence" / "design-evidence.json"


def load(seed=SEED, overlay=None):
    """Seed + evidence overlay. Returns (doc, {id: entry}). The overlay can only touch OVERLAY_FIELDS of known ids."""
    doc = _read(seed, "design library")
    entries = {k: dict(v) for k, v in doc.get("entries", {}).items()}
    if overlay is None:
        try:
            p = evidence_path()
            overlay = _read(p, "design evidence overlay").get("entries", {}) if p.exists() else {}
        except storage.StorageError:
            overlay = {}
    for eid, patch in overlay.items():
        if eid in entries:
            entries[eid].update({k: v for k, v in patch.items() if k in OVERLAY_FIELDS})
    return doc, entries


def validate(doc, entries):
    """Return a list of problems (empty = valid)."""
    out = []
    vocab = doc.get("vocabulary", {})
    if doc.get("schema") != SCHEMA:
        out.append(f"schema must be {SCHEMA}, got {doc.get('schema')!r}")
    topics, moods = set(vocab.get("topics", [])), set(vocab.get("moods", []))
    kinds, conf = set(vocab.get("kinds", [])), set(vocab.get("confidence", []))
    for eid, e in entries.items():
        if e.get("kind") not in kinds:
            out.append(f"{eid}: kind {e.get('kind')!r} not in vocabulary")
        if not eid.startswith({"frame_preset": "preset:", "palette": "palette:", "visual_style": "style:",
                               "shader_transition": "shader:", "css_transition": "css-transition:"}.get(e.get("kind"), "?")):
            out.append(f"{eid}: id prefix does not match kind {e.get('kind')}")
        for t in e.get("topics", []):
            if t not in topics:
                out.append(f"{eid}: topic {t!r} not in vocabulary")
        for m in e.get("moods", []):
            if m not in moods:
                out.append(f"{eid}: mood {m!r} not in vocabulary")
        if e.get("energy") not in ENERGY:
            out.append(f"{eid}: energy {e.get('energy')!r} invalid")
        if e.get("confidence") not in conf:
            out.append(f"{eid}: confidence {e.get('confidence')!r} invalid")
        if not e.get("topics") or not e.get("moods"):
            out.append(f"{eid}: needs at least one topic and one mood")
        for ref in e.get("pairs_with", []):
            if ref not in entries:
                out.append(f"{eid}: pairs_with {ref!r} does not exist")
        v = e.get("verified")
        if v is not None and v.get("result") not in ("pass", "fail", "partial"):
            out.append(f"{eid}: verified.result must be pass|fail|partial")
        if e.get("confidence") in ("validated", "preferred") and not (v and v.get("result") == "pass"):
            out.append(f"{eid}: {e['confidence']} requires verified.result == pass")
    return out


def _energy_points(want, have):
    if not want:
        return 0, None
    if want == have:
        return 2, f"energy {have} +2"
    if abs(ENERGY.index(want) - ENERGY.index(have)) == 1:
        return 1, f"energy {have} ~{want} +1"
    return 0, None


def score(eid, e, topic=None, moods=(), register=None, energy=None, aspect=None, prefer_fast=False):
    """(score, [visible components]) or None when excluded outright."""
    if aspect and aspect not in e.get("aspects", []):
        return None
    pts, why = 0, []
    if topic and topic in e.get("topics", []):
        pts += 3
        why.append(f"topic {topic} +3")
    for m in moods:
        if m in e.get("moods", []):
            pts += 2
            why.append(f"mood {m} +2")
    if register and e.get("register") not in (None, "n/a"):
        if e["register"] == register:
            pts += 2
            why.append(f"register {register} +2")
        elif e["register"] == "mixed":
            pts += 1
            why.append("register mixed +1")
    p, w = _energy_points(energy, e.get("energy"))
    if w:
        pts += p
        why.append(w)
    b = CONF_BONUS.get(e.get("confidence"), 0)
    if b:
        pts += b
        why.append(f"{e['confidence']} +{b}")
    if prefer_fast and str(e.get("cost", "")).startswith("slow"):
        pts -= 1
        why.append("slow render -1")
    return pts, why


def recommend(entries, topic=None, moods=(), register=None, energy=None, aspect=None, kinds=None, top=None,
              avoid=(), prefer_fast=False, include_failed=False):
    """{kind: [(score, id, entry, why)]} best first; ties broken by id for determinism."""
    top = top or {}
    out = {}
    for kind in (kinds or KIND_ORDER):
        rows = []
        for eid, e in entries.items():
            if e.get("kind") != kind or eid in avoid or e.get("confidence") == "deprecated":
                continue
            if (e.get("verified") or {}).get("result") == "fail" and not include_failed:
                continue
            s = score(eid, e, topic, moods, register, energy, aspect, prefer_fast)
            if s is None or (topic or moods or register or energy) and s[0] <= 0:
                continue
            rows.append((s[0], eid, e, s[1]))
        rows.sort(key=lambda r: (-r[0], r[1]))
        out[kind] = rows[: top.get(kind, DEFAULT_TOP[kind])]
    return out


def _line(row):
    pts, eid, e, why = row
    ver = (e.get("verified") or {}).get("result")
    tag = f" [{e['confidence']}{', ' + ver if ver else ''}]"
    return f"  {pts:>2}  {eid}{tag}  ({'; '.join(why) or 'no criteria given'})"


def _cmd_validate(args):
    doc, entries = load(args.seed)
    problems = validate(doc, entries)
    for p in problems:
        print(f"FAIL {p}")
    from collections import Counter
    print(f"{len(entries)} entries: " + ", ".join(f"{k} {n}" for k, n in sorted(Counter(e['kind'] for e in entries.values()).items())))
    print("valid" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def _cmd_recommend(args):
    _, entries = load(args.seed)
    kinds = [args.kind] if args.kind else None
    res = recommend(entries, args.topic, tuple(args.mood or ()), args.register, args.energy, args.aspect, kinds,
                    {args.kind: args.top} if args.kind and args.top else None, set(args.avoid or ()), args.prefer_fast,
                    args.include_failed)
    if args.json:
        print(json.dumps({k: [{"id": r[1], "score": r[0], "why": r[3]} for r in v] for k, v in res.items()}, indent=1))
    else:
        crit = {k: v for k, v in (("topic", args.topic), ("mood", args.mood), ("register", args.register),
                                  ("energy", args.energy), ("aspect", args.aspect)) if v}
        print("criteria:", crit or "none")
        for kind, rows in res.items():
            print(f"{kind}:")
            print("\n".join(_line(r) for r in rows) if rows else "  (no match)")
    return 0 if any(res.values()) else 1


def _cmd_list(args):
    _, entries = load(args.seed)
    n = 0
    for eid, e in sorted(entries.items()):
        if args.kind and e["kind"] != args.kind:
            continue
        n += 1
        print(f"{eid}  [{e['confidence']}]  {e.get('register', '')}  {e.get('energy')}  topics={','.join(e.get('topics', []))}")
    return 0 if n else 1


def _cmd_show(args):
    _, entries = load(args.seed)
    if args.id not in entries:
        print(f"unknown id {args.id}", file=sys.stderr)
        return 1
    print(json.dumps({args.id: entries[args.id]}, indent=1, ensure_ascii=False))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="designs", description=__doc__.split("\n")[0])
    ap.add_argument("--seed", default=SEED)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    r = sub.add_parser("recommend")
    r.add_argument("--topic")
    r.add_argument("--mood", action="append")
    r.add_argument("--register", choices=["dark", "light", "mixed"])
    r.add_argument("--energy", choices=list(ENERGY))
    r.add_argument("--aspect")
    r.add_argument("--kind", choices=list(KIND_ORDER))
    r.add_argument("--top", type=int)
    r.add_argument("--avoid", action="append", help="id to exclude (repeatable), e.g. a preset used recently")
    r.add_argument("--prefer-fast", action="store_true")
    r.add_argument("--include-failed", action="store_true")
    r.add_argument("--json", action="store_true")
    ls = sub.add_parser("list")
    ls.add_argument("--kind", choices=list(KIND_ORDER))
    sh = sub.add_parser("show")
    sh.add_argument("id")
    args = ap.parse_args(argv)
    try:
        return {"validate": _cmd_validate, "recommend": _cmd_recommend, "list": _cmd_list, "show": _cmd_show}[args.cmd](args)
    except DesignError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
