# T5 — Additive optional fields in `timeline/1` (still shadow mode)

**Goal:** let the timeline *describe* audio cues, transition windows, beat markers and review markers, with validation, **without** changing what any existing timeline means or how any existing code behaves. Nothing consumes these fields yet.
**Prereq:** T0 CLEARED. (Q2: `timeline.py` is **not** one of the owner-WIP files.)
**You modify (additive only):** `contentos/production/timeline.py`. **You create:** `tests/test_timeline_cues.py`.

## 1. Read first
All of `contentos/production/timeline.py` (214 lines) and all of `tests/test_timeline_shadow.py`. Note: `validate(tl)` returns `[{level, code, msg}]`; word dicts have `i, text, t0, t1, source`; scenes have `id, t0, t1, w0, w1, min_hold_s`; the existing `cues` (kind `visual`) stay exactly as they are.

## 2. Snapshot
`bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/before-T5.txt`; also `cp contentos/production/timeline.py $HOME/audit-scratch/timeline.py.before` (a reading aid; **do not** restore from it).

## 3. New OPTIONAL top-level keys (schema string stays `"timeline/1"`)

```json
"audio_cues": [{"id": "a01", "kind": "sfx", "scene": "s2", "at": {"word": 17, "offset_s": 0.0}, "t": 4.31,
                "dur_s": 0.4, "level_db": -18.0, "source": {"id": "synth:tick", "licence": "original"}, "note": ""}],
"transition_windows": [{"id": "t01", "from_scene": "s1", "to_scene": "s2", "t0": 5.8, "t1": 6.2, "kind": "wipe"}],
"beats": [{"t": 1.25, "strength": 0.8}],
"markers": [{"id": "m01", "t": 3.0, "kind": "review", "note": "check caption/fx overlap"}]
```
Allowed: `audio_cues[].kind` ∈ `sfx|duck|music`; `transition_windows[].kind` ∈ the `transition_family` values in `styles.AXES` (`cut|wipe|morph|dissolve|push`) — import the tuple **lazily inside the function** (`from contentos.intelligence import styles`) to avoid a hard import cycle at module load; `markers[].kind` ∈ `review|chapter`; `level_db` ≤ 0; `dur_s` > 0; `strength` 0–1.

## 4. Validation rules to add (codes are exact; levels as shown)

| code | level | when |
|---|---|---|
| `audio_cue_kind` | error | kind not allowed |
| `audio_cue_scene` | error | unknown scene |
| `audio_cue_word` | error | word index not in `words` |
| `audio_cue_not_in_scene` | error | word outside the named scene |
| `audio_cue_time` | error | `t` differs from `words[word].t0 + offset_s` by > `EPS` |
| `audio_cue_dur` | error | `dur_s` ≤ 0, or cue end `t+dur_s` > `duration_s + EPS` |
| `audio_cue_level` | error | `level_db` > 0 or not a number |
| `audio_cue_on_interpolated_word` | warning | anchor word `source == "interpolated"` |
| `transition_scene` | error | `from_scene`/`to_scene` unknown, or not adjacent (`to` must directly follow `from`) |
| `transition_window` | error | `t1 <= t0`, or window does not contain the boundary `from.t1` (±EPS) |
| `transition_kind` | error | kind not allowed |
| `beat_order` | error | beats not non-decreasing in `t`, or `t` outside `[0, duration_s]` |
| `marker_range` | error | `t` outside `[0, duration_s]` |
| `id_duplicate` | error | duplicate `id` within one list |

Plus a helper `cue_budget(tl, max_per_minute)` → `[{level:"warning", code:"cue_budget", msg}]` if the number of `audio_cues` of kind `sfx` in any rolling 60 s window exceeds `max_per_minute` (for videos shorter than 60 s, scale: allowed = ceil(max_per_minute * duration_s / 60)). **Not** called from `validate` (budget comes from a style card, which `timeline` must not import).

## 5. Implementation shape (additive only)
1. Add `def add_extensions(tl, audio_cues=None, transition_windows=None, beats=None, markers=None):` → returns a **deep copy** of `tl` with the given lists attached; for each audio cue given as `{id, kind, scene, word, offset_s=0.0, dur_s, level_db, source, note}` compute `at` and `t = round(words[word]["t0"] + offset_s, 3)`. Never mutates the input.
2. Add `def _validate_extensions(tl, words, scenes):` implementing §4 and returning a list of issue dicts in the same shape as `validate`.
3. In `validate`, immediately before the final `return iss`, add exactly: `iss.extend(_validate_extensions(tl, words, scenes))`.
4. Add `def cue_budget(...)` as above.
5. Update the module docstring with two sentences describing the optional keys. **Do not** change `SCHEMA`, `build_timeline`, `compare_legacy`, `build_from_project`, `main`, or any existing line other than the one-line insertion in step 3 and the docstring.
6. `compare_legacy` must ignore the new keys (it already only reads known keys) — prove it in a test.

## 6. Tests first (`tests/test_timeline_cues.py`)
Import `make` helpers by copying the small `make()` / `codes()` pattern from `test_timeline_shadow.py` into the new file (do **not** import from the old test file).
1. `test_existing_timeline_without_extensions_validates_exactly_as_before` — `codes(make()) == []`.
2. `test_existing_shadow_tests_still_pass` — a no-op marker; the real proof is the suite run (note it in the report).
3. One test per validation code in §4 (a good fixture mutated to be bad, assert the code is present at the expected level), plus a clean fully-extended fixture → `codes == []`.
4. `test_add_extensions_does_not_mutate_input` (deepcopy compare) and `test_add_extensions_computes_cue_time_from_word_start_plus_offset`.
5. `test_compare_legacy_ignores_extension_keys` — `compare_legacy(extended, legacy_of(extended))["ok"] is True`.
6. `test_cue_budget_flags_dense_sfx_and_ignores_ducks`; `test_cue_budget_scales_for_short_videos`.
7. `test_schema_string_unchanged` — `timeline.SCHEMA == "timeline/1"`.
8. `test_extended_timeline_json_round_trips`.

## 7. Verify
```bash
~/.contentos/venv/bin/python -m pytest tests/test_timeline_cues.py tests/test_timeline_shadow.py -q
~/.contentos/venv/bin/python -m pytest tests -q
git diff --stat contentos/production/timeline.py          # additions only; no deleted lines except none
git diff contentos/production/timeline.py | grep '^-[^-]' # must print NOTHING (no removed lines)
bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/after-T5.txt && diff $HOME/audit-scratch/before-T5.txt $HOME/audit-scratch/after-T5.txt
```
If the real Ep3 workspace project exists, the existing real-artifact test inside `test_timeline_shadow.py` also runs; report whether it ran or skipped.

## 8. Acceptance
Zero removed lines in `git diff timeline.py`; old timeline tests pass unedited; new tests pass; `main()` output for an unchanged project is byte-identical to before (if a project is available, run `python -m contentos.production.timeline <project>` before and after and compare — otherwise say "no project available").

## 9. Rollback / Do not
Owner reviews `git diff contentos/production/timeline.py` and restores it themselves; `rm tests/test_timeline_cues.py`. Do not make `compose`, captions, QA or `pipeline.py` read the new keys; do not promote timeline out of shadow; do not import `styles` at module top.
