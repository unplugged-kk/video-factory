# T2 — Style cards (`style/1`): schema, validator, three cards

**Goal:** a "style" becomes a small contract with a motion grammar and structural axes, not just a palette. Three seed cards that differ on **all six axes**. Nothing reads them yet (no pipeline wiring).
**Prereq:** T0 CLEARED.
**You create (new files only):**
- `contentos/intelligence/styles.py`
- `config/styles/blueprint-diagram.json`, `config/styles/punch-split.json`, `config/styles/slow-parallax-story.json`
- `tests/test_styles.py`
**You modify:** nothing existing.

## 1. Read first (do not skip)
- `contentos/production/direction.py` lines 1–60 and `load_registry`, `Registry` (to reuse it for capability ids).
- `contentos/intelligence/designs.py` top 60 lines (to copy the module-docstring/CLI style).
- `.claude/skills/explainer-motion-craft/SKILL.md` — read rules **R1–R6** and write them in your report; a card must not contradict them.
- `tests/test_direction.py` first 30 lines (test header style).
- List installed capability ids you may reference:
  `~/.contentos/venv/bin/python -m contentos.production.direction registry` — pick only ids with `status: installed`. `renderer:hyperframes` is one.

## 2. Snapshot
`bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/before-T2.txt`

## 3. The `style/1` contract

A card is one JSON file `config/styles/<id>.json`:

```json
{
  "schema": "style/1",
  "id": "blueprint-diagram",
  "name": "Blueprint diagram",
  "summary": "One sentence: what this style is for.",
  "status": "unvalidated",
  "evidence": [],
  "axes": {
    "layout_system": "grid",
    "motion_grammar": "draw-on",
    "scene_rhythm": "even",
    "depth_model": "layered",
    "illustration_mode": "diagrammatic",
    "transition_family": "wipe"
  },
  "dials": {"energy": 2, "density": 4, "formality": 4, "warmth": 2, "pace": 2},
  "motion": {
    "ease_family": ["power2.out", "power3.inOut"],
    "forbidden": ["bounce/elastic overshoot", "continuous camera drift"],
    "respects_r1_r6": true
  },
  "layout_vocabulary": ["labelled node", "connector line", "annotation callout"],
  "sound": {"mode": "narration-led", "max_cues_per_minute": 4},
  "requires": ["renderer:hyperframes"],
  "frame_checklist": ["Every diagram label readable at phone size", "...", "...", "..."],
  "best_for": {"content_types": ["architecture-lesson", "how-to"], "avoid": ["historical-explainer"]},
  "source_techniques": ["animate: STYLE contract + frame checklist (reference only, no code copied)"],
  "licence_notes": "Original wording; no third-party assets."
}
```

Allowed values (enums, put them as constants in `styles.py`):

| Field | Allowed |
|---|---|
| `status` | `unvalidated`, `validated` (a `validated` card **must** have non-empty `evidence`: relative paths of real render records; seed cards are `unvalidated` with `evidence: []`) |
| `axes.layout_system` | `grid`, `full-bleed`, `split`, `stacked-cards`, `centered-stage` |
| `axes.motion_grammar` | `eased-glide`, `snap-cut`, `draw-on`, `parallax`, `type-driven` |
| `axes.scene_rhythm` | `even`, `accelerating`, `punctuated` |
| `axes.depth_model` | `flat`, `layered`, `pseudo-3d` |
| `axes.illustration_mode` | `diagrammatic`, `iconographic`, `photographic`, `typographic`, `textural` |
| `axes.transition_family` | `cut`, `wipe`, `morph`, `dissolve`, `push` |
| `dials.*` | integers 1–5 for `energy`, `density`, `formality`, `warmth`, `pace` |
| `sound.mode` | `narration-led`, `silent` (music-led is **not** allowed: beat analysis does not exist) |
| `sound.max_cues_per_minute` | integer 0–12 (`silent` requires 0) |
| `best_for.content_types` / `avoid` | subset of `architecture-lesson`, `ai-workflow`, `historical-explainer`, `product-launch`, `science-concept`, `how-to`, `news-opinion` |
| `frame_checklist` | ≥ 4 non-empty strings |
| `layout_vocabulary` | ≥ 3 non-empty strings |
| `motion.forbidden` | ≥ 2 non-empty strings; `motion.ease_family` ≥ 1 string |
| `motion.respects_r1_r6` | must be `true` (you confirmed it by reading R1–R6) |
| `requires` | list (may be empty) of capability ids that exist in the registry **with status `installed`** |
| `id` | `^[a-z][a-z0-9-]{2,40}$` and equals the file name stem |

**Distinctness rule (anti-"palette variant"):** any two cards must differ on **at least 3 of the 6 axes**. Palette/typeface are deliberately not part of the card.

## 4. Write the tests FIRST — `tests/test_styles.py`

Header (copy exactly):
```python
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.intelligence import styles  # noqa: E402
from contentos.production import direction  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
```
Required tests (names exact; each ≤ 15 lines):
1. `test_seed_cards_exist_and_validate` — `styles.load_all()` returns exactly 3 cards, `problems == []`.
2. `test_seed_cards_are_unvalidated_and_have_no_evidence` — every seed card has `status == "unvalidated"` and `evidence == []`. (We must not claim validation we have not done.)
3. `test_seed_cards_are_pairwise_distinct_on_all_six_axes` — for every pair, differing axes count == 6 (stronger than the rule; guards against accidental palette-variant seeds).
4. `test_distinct_check_flags_a_palette_variant` — deep-copy one card, change only `id`/`name`, call `styles.check_distinct([a, b])`; result non-empty and mentions both ids.
5. `test_missing_axis_is_rejected`, `test_bad_enum_value_is_rejected`, `test_dial_out_of_range_is_rejected`, `test_validated_without_evidence_is_rejected`, `test_music_led_sound_is_rejected`, `test_silent_with_cues_is_rejected`, `test_r1_r6_flag_false_is_rejected`, `test_short_frame_checklist_is_rejected`.
6. `test_unknown_capability_is_rejected` — `requires: ["skill:does-not-exist"]` → problem text contains `does-not-exist`.
7. `test_non_installed_capability_is_rejected` — only if the registry has a non-installed id; otherwise `pytest.skip("registry has no non-installed capability")`.
8. `test_id_must_match_filename` — load a card written to `tmp_path` under a different filename → problem.
9. `test_validate_does_not_mutate_input` — `copy.deepcopy` before/after equal.
10. `test_cli_validate_exit_codes` — `styles.main(["validate"])` returns 0; with `--dir tmp_path` containing a broken card returns 1; with a non-existent dir returns 2.
11. `test_no_existing_config_changed_by_loading` — read `config/capabilities.json` bytes before/after `styles.load_all()`; equal.

Run: `~/.contentos/venv/bin/python -m pytest tests/test_styles.py -q` → must **fail** (ImportError) before step 5. Confirm and note it.

## 5. Write `contentos/intelligence/styles.py` (reference implementation)

```python
"""style/1: a style card is a CONTRACT for a visual language, not a palette.

A card fixes six structural axes (layout, motion grammar, rhythm, depth, illustration mode, transitions), a few dials, the
motion it forbids, the sound strategy and a frame checklist a reviewer can tick. Two cards must differ on >= 3 axes, so
changing only colours or fonts cannot pass as a new style. Status is `unvalidated` until a real render in OUR pipeline
records evidence; nothing in this module renders, calls a network, or edits any project. Shadow mode: no pipeline reads cards yet.

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
_REQUIRED = ("schema", "id", "name", "summary", "status", "evidence", "axes", "dials", "motion", "layout_vocabulary",
             "sound", "requires", "frame_checklist", "best_for", "source_techniques", "licence_notes")


def _strs(v, minimum):
    return isinstance(v, list) and len(v) >= minimum and all(isinstance(x, str) and x.strip() for x in v)


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
        for cid_ in req:
            if cid_ not in registry:
                p.append(f"requires {cid_!r}: not in config/capabilities.json")
            elif registry.get(cid_)["status"] != "installed":
                p.append(f"requires {cid_!r}: status is {registry.get(cid_)['status']!r}, only 'installed' is allowed on a card")
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
    except (OSError, Exception) as exc:      # unreadable directory or registry
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
```
Notes for you: (a) `except (OSError, Exception)` — simplify to `except Exception` if your linter complains; keep exit code 2 behaviour. (b) If `direction.load_registry()` needs arguments in this repo, adapt per what you read in step 1, **not** by editing direction.py.

## 6. Create the three cards
Use the example in §3 as the pattern. Required seed values (so they differ on all six axes):

| id | layout_system | motion_grammar | scene_rhythm | depth_model | illustration_mode | transition_family | best_for.content_types | avoid |
|---|---|---|---|---|---|---|---|---|
| `blueprint-diagram` | grid | draw-on | even | layered | diagrammatic | wipe | architecture-lesson, how-to | historical-explainer |
| `punch-split` | split | snap-cut | punctuated | flat | iconographic | cut | ai-workflow, product-launch, news-opinion | science-concept |
| `slow-parallax-story` | full-bleed | parallax | accelerating | pseudo-3d | textural | dissolve | historical-explainer, science-concept | product-launch |

For every card: write real, specific `summary`, `layout_vocabulary` (3–5 items), `motion.forbidden` (≥2, e.g. "decorative looping motion", "unmotivated camera drift"), `motion.ease_family` using easings that appear in the existing motion catalogue (grep `config/motion-catalogue.json` for `ease`), `frame_checklist` (4–6 tickable sentences a human can check on a still), `source_techniques` naming the idea source as *reference only, no code copied* (e.g. `"animate: STYLE contract + frame checklist"`, `"product-launch-motion: structural axes / direction dials"`), `licence_notes: "Original wording; no third-party assets or code."`, `requires` from installed ids only, `sound.mode: "narration-led"`, `max_cues_per_minute` 3–6, `status: "unvalidated"`, `evidence: []`, `respects_r1_r6: true`.
Dials suggestion: blueprint (2,4,4,2,2); punch (4,2,2,3,4); parallax (2,2,3,5,2) as (energy, density, formality, warmth, pace).
Do **not** copy text from upstream repositories; write original sentences.

## 7. Verify
```bash
~/.contentos/venv/bin/python -m pytest tests/test_styles.py -q
~/.contentos/venv/bin/python -m contentos.intelligence.styles validate     # exit 0
~/.contentos/venv/bin/python -m contentos.intelligence.styles distinct     # 3 lines, "6 axes differ"
~/.contentos/venv/bin/python -m pytest tests -q                            # whole suite: no new failures
bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/after-T2.txt && diff $HOME/audit-scratch/before-T2.txt $HOME/audit-scratch/after-T2.txt
git status --porcelain
```
`git status` must add only: `?? contentos/intelligence/styles.py`, `?? config/styles/`, `?? tests/test_styles.py`.
Snapshot diff must show **only** the new `??` lines at the top (every block after `--- diff` identical) (the snapshot only hashes tracked tests and protected files, so new untracked files do not change it). If it differs, stop.

## 8. Acceptance
- All new tests pass; 0 existing tests fail or changed.
- `validate` exits 0; `distinct` shows every pair at 6.
- No card claims `validated`.
- Only the 5 new paths exist in `git status`.

## 9. Rollback
`rm contentos/intelligence/styles.py tests/test_styles.py && rm -r config/styles`.

## 10. Do not
Add colours/fonts to cards; wire cards into `pipeline.py`/`designs.py`/`direction.py`; add a card registry elsewhere; mark anything validated; edit `config/design-library.json`.
