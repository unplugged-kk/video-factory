# T3 — Creative-decision record, variety report, and (optional) critic dimension

Two parts. **T3a** is new files only. **T3b** modifies `critic.py` and runs **only if the owner answered yes to Q3 in T0**.
**Prereq:** T0 CLEARED, T2 DONE (`config/styles/*.json` and `styles.py` exist).

## T3a — `contentos/intelligence/creative.py` + `tests/test_creative.py`

**Goal:** for a brief, propose **three materially different** style cards, record the choice and why the other two were rejected, and report how varied the last N videos were. Advisory only: no pipeline wiring, no workspace writes by default, no network.

### 1. Read first
`contentos/intelligence/styles.py` (T2), `contentos/intelligence/visual.py` docstring (Rule B vocabulary — different system, do not modify), `tests/test_styles.py` (test header).

### 2. Snapshot
`bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/before-T3a.txt`

### 3. Data contracts

**Brief** (input JSON, validated):
```json
{"job": "ep4-example", "topic": "how DNS works", "content_type": "architecture-lesson",
 "length_kind": "short", "factual_density": "high", "register": "curious"}
```
`content_type` ∈ `styles.CONTENT_TYPES`; `length_kind` ∈ `short|long`; `factual_density` ∈ `low|medium|high`; `register` ∈ `neutral|curious|urgent|reflective`; `job` matches `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`; `topic` non-empty.

**Decision record** `creative-decision/1` (one JSON file per video, written only where `--out` says):
```json
{"schema": "creative-decision/1", "job": "ep4-example", "created": "2026-10-12",
 "brief": {…the brief…},
 "candidates": [
   {"style": "blueprint-diagram", "score": 9, "fit": 2, "novelty": 5, "repeat_penalty": 0, "experimental": true,
    "axes": {…six axes…}},
   {"style": "punch-split", …}, {"style": "slow-parallax-story", …}],
 "chosen": "blueprint-diagram",
 "rejected": [{"style": "punch-split", "reason": "…"}, {"style": "slow-parallax-story", "reason": "…"}],
 "requires_explicit_approval": true,
 "axes": {…six axes of the chosen style…},
 "sound_strategy": {"mode": "narration-led", "max_cues_per_minute": 4},
 "notes": ""}
```
Rules baked into the code:
- Every card in this repo is `unvalidated` today → `experimental: true` on the candidate and `requires_explicit_approval: true` on the record. (Consequential creative approvals stay explicit.)
- `chosen` must be one of `candidates`; `rejected` must contain every other candidate with a non-empty `reason` (≥ 8 chars).
- Candidates must differ pairwise on ≥ 3 axes (reuse `styles.check_distinct`).
- `created` is passed in, never read from the clock inside pure functions.

### 4. Scoring (deterministic, integer, explainable)
For each card:
```
fit            = +2 if brief.content_type in best_for.content_types
                 -5 if brief.content_type in best_for.avoid
                  0 otherwise
novelty        = number of axes (0-6) where the card differs from the MOST RECENT record in history (0 if no history)
repeat_penalty = -3 if the card's six-axis combination equals any of the last `window` records' combinations, else 0
score          = 2*fit + novelty + repeat_penalty
```
Sort by `(-score, style_id)`; top 3 = candidates. If fewer than 3 valid cards exist, return what exists plus a `warnings` list entry. Palette/colour is **not** an input.

### 5. Variety report
`variety_report(records, window=5)` returns:
```json
{"videos": N, "window": 5,
 "per_video": [{"job": …, "style": …, "axes_differing_from_previous": 0-6, "combo_repeated_within_window": bool, "transition_family": …}],
 "transition_families_used": {"wipe": 2, …},
 "motion_grammars_used": {…},
 "meets_novelty_budget": bool,      # every video after the first differs from its predecessor on >= 2 axes AND no combo repeats within window
 "failures": ["ep5-x: differs from ep4-y on only 1 axis"]}
```
`meets_novelty_budget` mirrors the framework in `05-creative-decision-framework.md` §2 step 4.

### 6. Code (reference implementation — write the tests first; the tests are the arbiter)

```python
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
    count = lambda key: {v: sum(1 for r in records if r["axes"][key] == v) for v in sorted({r["axes"][key] for r in records})}
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
```

### 7. Tests (`tests/test_creative.py`) — write first
Build tiny in-test cards with a helper `card(id, **axes)` (copy a seed card via `styles.load_all()[0][0]`, `deepcopy`, change id/axes). Required:
1. `test_brief_validation_rejects_bad_fields` (each field).
2. `test_propose_is_deterministic` — same inputs twice → equal.
3. `test_fit_rewards_matching_content_type_and_penalises_avoid`.
4. `test_novelty_counts_axes_against_most_recent_record_only`.
5. `test_repeat_penalty_applies_for_same_combo_within_window_and_not_outside`.
6. `test_palette_is_not_an_input` — add a `palette` key to a card copy; scores unchanged.
7. `test_three_seed_cards_give_three_candidates_and_no_warning`; `test_fewer_cards_gives_warning`.
8. `test_unvalidated_cards_require_explicit_approval`.
9. `test_record_requires_reason_for_every_rejected_candidate` (7-char reason fails, 8 passes).
10. `test_record_chosen_must_be_a_candidate`.
11. `test_validate_record_round_trip` (make_record → validate_record == []).
12. `test_variety_report_flags_one_axis_change_and_combo_repeat` and `test_variety_report_passes_for_distinct_sequence`.
13. `test_cli_record_writes_and_refuses_overwrite` using `tmp_path`; second run returns 1.
14. `test_cli_report_exit_code_reflects_budget`.
15. `test_load_history_orders_by_created_then_job`.
16. `test_creative_does_not_touch_repo_files` — hash `config/` JSON files before/after a full `propose` run.

### 8. Verify (same pattern as T2)
```bash
~/.contentos/venv/bin/python -m pytest tests/test_creative.py -q
printf '%s' '{"job":"demo-1","topic":"how DNS works","content_type":"architecture-lesson","length_kind":"short","factual_density":"high","register":"curious"}' > $HOME/audit-scratch/brief-demo.json
~/.contentos/venv/bin/python -m contentos.intelligence.creative propose --brief $HOME/audit-scratch/brief-demo.json
~/.contentos/venv/bin/python -m pytest tests -q
bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/after-T3a.txt && diff $HOME/audit-scratch/before-T3a.txt $HOME/audit-scratch/after-T3a.txt
```
Expected for the demo brief: `blueprint-diagram` ranks first (fit +2, no history → novelty 0 → score 4); the other two follow. Report what you actually saw.

### Acceptance
New tests pass; whole suite unchanged otherwise; only `creative.py` and `test_creative.py` are new; demo `propose` output pasted in the report; nothing written in the repo by the CLI.

### Rollback / Do not
`rm contentos/intelligence/creative.py tests/test_creative.py`. Do not write records into the repo or workspace; do not wire into `pipeline.py`; do not read `visual-languages.seed.json` (a different ledger, Rule B stays independent).

---

## T3b — optional `style_fidelity` score in `critic.py` (ONLY if Q3 = yes)

**Why it is safe:** the 8 existing dimensions, `MIN_EACH`, `MIN_AVG`, the average, and every verdict for existing reports stay **exactly** as they are. `style_fidelity` is optional; when absent nothing changes. When present it is **not** part of the average; it only adds one rule: a score below `MIN_EACH` turns `pass` into `revise` (never overrides `reject`).

### Steps
1. Snapshot: `before-T3b.txt`. Read `contentos/production/critic.py` and `tests/test_critic.py` completely.
2. Write the new tests first, in a **new file** `tests/test_critic_style_fidelity.py` (do not edit `test_critic.py`):
   - `test_reports_without_style_fidelity_are_unchanged` — build a valid report; `critic.check(r)` equals what it was (use a literal expected dict).
   - `test_style_fidelity_is_accepted_when_present_and_integer_0_to_10`.
   - `test_style_fidelity_bool_or_out_of_range_is_rejected`.
   - `test_low_style_fidelity_turns_pass_into_revise`.
   - `test_style_fidelity_does_not_change_the_average_or_rescue_a_revise`.
   - `test_hard_failure_still_rejects_regardless_of_style_fidelity`.
   - `test_dimensions_and_thresholds_unchanged` — `critic.DIMENSIONS` has the same 8 names in the same order; `MIN_EACH == 7`; `MIN_AVG == 8.0`.
3. Edit `critic.py` — **three small additions, nothing removed**:
   a. After `HARD_FAILURES` add: `OPTIONAL_DIMENSIONS = ("style_fidelity",)   # scored only when a style card was used; not in the average`.
   b. In `validate`, change the unknown-dimension loop to ignore optional ones: `for extra in set(scores) - set(DIMENSIONS) - set(OPTIONAL_DIMENSIONS):`. After the `for d in DIMENSIONS:` loop add: `for d in OPTIONAL_DIMENSIONS: if d in scores: v = scores[d]; if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 10: p.append(f"score {d!r} must be an integer 0-10")`.
   c. In `verdict`, after the existing `s = [...]` computation and **before** the final `return "pass"`, add: `if report["scores"].get("style_fidelity", MIN_EACH) < min_each: return "revise"`. (`validate` has already guaranteed the type.)
4. Run `tests/test_critic.py` (must pass untouched) and the new file.
5. Do **not** edit `.claude/skills/explainer-visual-qa/SKILL.md`; tell the owner the critic prompt would need a one-line mention if they want critics to score it.

### Acceptance
`git diff contentos/production/critic.py` shows only additions plus the one changed `for extra in …` line; all old critic tests pass unedited; new tests pass; thresholds unchanged (`grep -n "MIN_EACH, MIN_AVG" critic.py` still `7, 8.0`).

### Rollback
Owner reviews `git diff contentos/production/critic.py` and restores it themselves; `rm tests/test_critic_style_fidelity.py`.
