# T6 — Negative controls: prove our gates can actually fail

**Why:** a check that has never been shown to fail on a known-bad input might be passing everything. Student-kit's lesson: calibrate validators with seeded faults.
**Goal:** one new test file where each existing gate gets (a) a known-good input that passes and (b) a seeded-bad input that fails with the *expected* finding. We **report** gaps; we never change thresholds or gate code.
**Prereq:** T0 CLEARED. **You create:** `tests/test_gate_negative_controls.py` and `docs/research/motion-design-integration/negative-controls.md`. **You modify:** nothing.

## 1. Read first
`motion_audit.py` (whole), `critic.py` (whole), `timeline.py` `validate`, `visual_gate.py` (read-only!), `intelligence/visual.py` docstring + public functions, `tests/test_motion_audit.py`, `tests/test_visual_gate.py` (to reuse their fixture ideas).

**Owner-WIP warning:** `visual_gate.py` has uncommitted additions. List them so you test only code that is in HEAD:
```bash
git diff -U0 contentos/production/visual_gate.py | grep -E '^\+def |^\+class '
```
Every function printed is WIP (likely the safe-zone family: `default_zones`, `parse_zone`, `validate_zones`, `_edge_fraction`, `check_safe_zones`, `check_canvas_matches_video`, `parse_canvas`, `video_size`). **Do not test those.** List them in the doc as "not covered: owner WIP".

## 2. Snapshot
`before-T6.txt` as usual.

## 3. Coverage table you must fill (this table becomes the doc)

| Gate | Known-bad seeded input | Expected result | Known-good input | Expected |
|---|---|---|---|---|
| `motion_audit.motion_stats` | `ydif=[0.0]*100` | `still_fraction == 1.0`, `longest_still_s` = 100/fps | smooth ramp `[0.5]*100` | `still_fraction == 0.0`, `pop_count == 0` |
| `motion_audit.motion_stats` | `[0.2]*50+[5.0]+[0.2]*50` (one-frame jump) | `pop_count == 1` | smooth plateau `[0.2]*50+[3.0]*10+[0.2]*50` | `pop_count == 0` |
| `motion_audit.ease_inventory` | HTML with no `ease:` | empty/low variety result (inspect what it returns and assert on it) | HTML with 4 different eases | ≥4 distinct |
| `critic.verdict` | any hard failure | `"reject"` | all scores ≥8, no failures | `"pass"` |
| `critic.verdict` | one score 6, others 9 | `"revise"` | all 8 | `"pass"` |
| `critic.check` | claimed `pass` with low scores | `ok False`, problem mentions mismatch | consistent | `ok True` |
| `critic.validate` | `critic != "independent"` | problem | `"independent"` | none |
| `timeline.validate` | scene gap | error `scene_gap` | contiguous | no errors |
| `timeline.validate` | word outside its scene | error `word_outside_scene` | inside | none |
| `timeline.validate` | cue anchored to word in another scene | error `cue_not_in_scene` | in scene | none |
| `timeline.validate` | `timing_trust` claims more than unverified without anchors | error `trust` | default | none |
| `visual_gate.check_caption_layering` | CSS where the caption layer sits under an opaque full-frame panel (read the function to learn what it flags) | finding present | CSS with caption above | no finding |
| `visual_gate.scan_render_log` | a log line the function documents as a fatal pattern | finding | clean log | none |
| `visual_gate.check_transition` (needs ffmpeg) | synthetic clip with a hard black dip mid-transition | finding (unless `allow_dip`) | clip with smooth blend | pass |
| `intelligence.visual` Rule A (pure function if one exists) | all scenes the same backdrop | fails | distinct backdrops | passes |

For rows you cannot build from reading the code (unclear inputs, requires a render, only a CLI exists), write `NOT COVERED: <reason>` in the doc instead of guessing. **Never invent an API.**

Making a test clip with ffmpeg (only if `shutil.which("ffmpeg")`, else `pytest.skip`), into `tmp_path`:
```bash
ffmpeg -y -f lavfi -i color=c=black:s=320x180:d=1:r=30 black.mp4
ffmpeg -y -f lavfi -i testsrc=s=320x180:d=1:r=30 test.mp4
ffmpeg -y -i test.mp4 -i black.mp4 -filter_complex "[0][1]concat=n=2:v=1:a=0" dip.mp4
```
Use `subprocess.run([...], check=True, capture_output=True)`; never in the repo.

## 4. Writing the tests
- File header as in other tests. One test per table row, named `test_<gate>_<fault>_is_caught` / `test_<gate>_<good>_passes`.
- Each bad-input test asserts the **specific** expected finding, not just "something failed".
- If a "known-bad" input is **not** caught, do not weaken the assertion and do not touch the gate: mark the test `@pytest.mark.xfail(strict=True, reason="GAP: gate does not catch <fault>")` and list it prominently in the doc and report. A strict xfail keeps the suite green *and* alerts us when a gate later improves.
- Import only stdlib + `contentos.*`. No network, no repo writes, no `import pipeline`.

## 5. The doc (`negative-controls.md`)
Sections: purpose; the filled coverage table with the actual observed result for each row (what the function returned); **Gaps found** (strict xfails); **Not covered** (WIP functions, render-dependent, CLI-only) with reasons; how to re-run.

## 6. Verify
```bash
~/.contentos/venv/bin/python -m pytest tests/test_gate_negative_controls.py -q -rx
~/.contentos/venv/bin/python -m pytest tests -q
bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/after-T6.txt && diff $HOME/audit-scratch/before-T6.txt $HOME/audit-scratch/after-T6.txt
git status --porcelain      # new: the test file and the doc only
```

## 7. Acceptance
Every table row is either a passing test, a strict xfail with a GAP note, or a `NOT COVERED` line with a reason. No gate or threshold edited. Full suite green (xfails allowed, listed).

## 8. Rollback / Do not
`rm tests/test_gate_negative_controls.py docs/research/motion-design-integration/negative-controls.md`. Do not "fix" a gap; do not touch `visual_gate.py`; do not lower or loosen any assertion to get green; do not run a real render.
