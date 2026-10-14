"""creative-decision/1: record WHY a video's visual language was chosen, and report how varied recent videos were.

Advisory and deterministic: scores are small integers from content fit, axis novelty against recent records and a repeat
penalty. Palette is deliberately not an input. Reads style cards (config/styles) and decision records from a directory
you name; writes only to the --out path you name, and never overwrites. No pipeline, renderer, network or clock use in the
pure functions (`created` is passed in).

  python -m contentos.intelligence.creative propose --brief BRIEF.json [--history DIR] [--window 5]
  python -m contentos.intelligence.creative record  --brief BRIEF.json --choose ID --out FILE [--history DIR] [--created YYYY-MM-DD] [--note TEXT]
  python -m contentos.intelligence.creative report  --history DIR [--window 5]
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

from . import styles

SCHEMA = "creative-decision/1"
LENGTHS = ("short", "long")
DENSITIES = ("low", "medium", "high")
REGISTERS = ("neutral", "curious", "urgent", "reflective")
_JOB = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def validate_brief(b):
    p = []
    if not isinstance(b, dict):
        return ["brief must be an object"]
    if not isinstance(b.get("job"), str) or not _JOB.match(b["job"]):
        p.append("job must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}")
    if not isinstance(b.get("topic"), str) or not b["topic"].strip():
        p.append("topic must be a non-empty string")
    for k, allowed in (("content_type", styles.CONTENT_TYPES), ("length_kind", LENGTHS),
                       ("factual_density", DENSITIES), ("register", REGISTERS)):
        if b.get(k) not in allowed:
            p.append(f"{k} {b.get(k)!r} not in {allowed}")
    return p


def combo(axes):
    return tuple(axes[k] for k in styles.AXES)


def axes_differing(a, b):
    return sum(1 for k in styles.AXES if a[k] != b[k])


def load_history(history_dir):
    """Decision records in `history_dir` (*.json, schema creative-decision/1), oldest first by (created, job)."""
    if not history_dir:
        return []
    d = Path(history_dir)
    if not d.is_dir():
        raise OSError(f"history directory not found: {d}")
    recs = []
    for f in sorted(d.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        if r.get("schema") == SCHEMA:
            recs.append(r)
    return sorted(recs, key=lambda r: (r.get("created", ""), r.get("job", "")))


def score_card(card, brief, history, window=5):
    ct = brief["content_type"]
    fit = 2 if ct in card["best_for"]["content_types"] else (-5 if ct in card["best_for"]["avoid"] else 0)
    last = history[-1]["axes"] if history else None
    novelty = axes_differing(card["axes"], last) if last else 0
    recent = {combo(r["axes"]) for r in history[-window:]}
    penalty = -3 if combo(card["axes"]) in recent else 0
    return {"style": card["id"], "score": 2 * fit + novelty + penalty, "fit": fit, "novelty": novelty,
            "repeat_penalty": penalty, "experimental": card["status"] != "validated", "axes": dict(card["axes"])}


def propose(brief, cards, history=(), window=5):
    probs = validate_brief(brief)
    if probs:
        raise ValueError("; ".join(probs))
    history = list(history)
    scored = sorted((score_card(c, brief, history, window) for c in cards), key=lambda s: (-s["score"], s["style"]))
    top = scored[:3]
    distinct = styles.check_distinct([{"id": c["style"], "axes": c["axes"]} for c in top])
    if distinct:
        raise ValueError("; ".join(distinct))
    warnings = [] if len(top) == 3 else [f"only {len(top)} valid style card(s); three materially different directions need three cards"]
    return {"candidates": top, "warnings": warnings}


def make_record(brief, candidates, chosen, rejection_reasons, created, cards, note=""):
    ids = [c["style"] for c in candidates]
    if chosen not in ids:
        raise ValueError(f"chosen {chosen!r} is not one of the candidates {ids}")
    card = next(c for c in cards if c["id"] == chosen)
    rejected = []
    for c in candidates:
        if c["style"] == chosen:
            continue
        reason = (rejection_reasons or {}).get(c["style"], "").strip()
        if len(reason) < 8:
            raise ValueError(f"rejection reason for {c['style']!r} is required (>= 8 characters)")
        rejected.append({"style": c["style"], "reason": reason})
    return {"schema": SCHEMA, "job": brief["job"], "created": created, "brief": brief, "candidates": candidates,
            "chosen": chosen, "rejected": rejected,
            "requires_explicit_approval": any(c["style"] == chosen and c["experimental"] for c in candidates),
            "axes": dict(card["axes"]), "sound_strategy": dict(card["sound"]), "notes": note}


def validate_record(r):
    p = []
    if r.get("schema") != SCHEMA:
        p.append(f"schema is {r.get('schema')!r}")
    ids = [c.get("style") for c in r.get("candidates", [])]
    if r.get("chosen") not in ids:
        p.append("chosen is not among candidates")
    got = {x.get("style") for x in r.get("rejected", [])}
    if got != set(ids) - {r.get("chosen")}:
        p.append("rejected must list every non-chosen candidate")
    if any(len(x.get("reason", "").strip()) < 8 for x in r.get("rejected", [])):
        p.append("every rejection needs a reason (>= 8 chars)")
    return p


def variety_report(records, window=5):
    per, fails = [], []
    for i, r in enumerate(records):
        prev = records[i - 1] if i else None
        diff = axes_differing(r["axes"], prev["axes"]) if prev else None
        seen = {combo(x["axes"]) for x in records[max(0, i - window):i]}
        repeated = combo(r["axes"]) in seen
        per.append({"job": r["job"], "style": r["chosen"], "axes_differing_from_previous": diff,
                    "combo_repeated_within_window": repeated, "transition_family": r["axes"]["transition_family"]})
        if diff is not None and diff < 2:
            fails.append(f"{r['job']}: differs from {prev['job']} on only {diff} axis(es); need >= 2")
        if repeated:
            fails.append(f"{r['job']}: six-axis combination repeats within the last {window}")
    def count(key):
        return dict(sorted(Counter(r["axes"][key] for r in records).items()))

    return {"videos": len(records), "window": window, "per_video": per,
            "transition_families_used": count("transition_family"), "motion_grammars_used": count("motion_grammar"),
            "meets_novelty_budget": not fails, "failures": fails}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("propose", "record", "report"):
        sp = sub.add_parser(n)
        sp.add_argument("--history")
        sp.add_argument("--window", type=int, default=5)
        if n != "report":
            sp.add_argument("--brief", required=True)
        if n == "record":
            sp.add_argument("--choose", required=True)
            sp.add_argument("--out", required=True)
            sp.add_argument("--created", default=None)
            sp.add_argument("--note", default="")
            sp.add_argument("--reject", action="append", default=[], help="STYLE=reason (repeat once per rejected candidate)")
    a = ap.parse_args(argv)
    try:
        hist = load_history(a.history)
        if a.cmd == "report":
            rep = variety_report(hist, a.window)
            print(json.dumps(rep, indent=1))
            return 0 if rep["meets_novelty_budget"] else 1
        brief = json.loads(Path(a.brief).read_text(encoding="utf-8"))
        cards, problems = styles.load_all()
        if problems:
            print(json.dumps({"style_card_problems": problems}, indent=1), file=sys.stderr)
            return 2
        prop = propose(brief, cards, hist, a.window)
        if a.cmd == "propose":
            print(json.dumps(prop, indent=1))
            return 0
        reasons = dict(x.split("=", 1) for x in a.reject)
        rec = make_record(brief, prop["candidates"], a.choose, reasons, a.created or datetime.date.today().isoformat(), cards, a.note)
        probs = validate_record(rec)
        if probs:
            print(json.dumps(probs), file=sys.stderr)
            return 1
        out = Path(a.out)
        if out.exists():
            print(f"refusing to overwrite {out}", file=sys.stderr)
            return 1
        out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
        print(f"wrote {out}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
