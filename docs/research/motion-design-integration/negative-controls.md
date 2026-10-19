# Negative Controls: Calibration and Verification of Quality Gates

## 1. Purpose

A validator or quality gate that has never been observed to fail on known-bad input cannot be trusted. In accordance with the Motion Design Integration plan (T6), this document records the calibration of the pipeline's gates with seeded-bad inputs alongside known-good controls.

Per the 2026-10-18 handover brief (Section 3, item 4):
- Gates in `qa.run_qa`, `finalcheck.validate_video`, and `visual_gate` (captions, transitions, safezone, layers, render log) are thoroughly calibrated by `tests/test_gate_calibration.py` (commits `a52219f`, `8a05eb0`, `7252612`). They are cited here rather than duplicated.
- The earlier "owner-WIP warning" is obsolete because all WIP functions are committed on main as of 2026-10-18.
- New seeded negative controls have been authored in `tests/test_gate_negative_controls.py` covering motion audit, critic, timeline, visual intelligence (Rule A and Rule B), and style card validators.

---

## 2. Coverage Table

| Gate | Known-bad seeded input | Observed bad result | Known-good input | Observed good result | Status |
|---|---|---|---|---|---|
| `motion_audit.motion_stats` (stillness) | `ydif=[0.0]*100` (fps=25) | `still_fraction=1.0`, `longest_still_s=4.0` | `ydif=[0.5]*100` (fps=25) | `still_fraction=0.0`, `longest_still_s=0.0` | PASS |
| `motion_audit.motion_stats` (pops) | `[0.2]*50 + [5.0] + [0.2]*50` (1-frame spike) | `pop_count=1`, `pops=[2.0]` | `[0.2]*50 + [3.0]*10 + [0.2]*50` (plateau) | `pop_count=0`, `pops=[]` | PASS |
| `motion_audit.ease_inventory` | HTML with no `ease:` declarations | `total=0`, `by_ease={}` | HTML with 4 distinct GSAP eases | `total=4`, 4 distinct ease keys | PASS |
| `critic.verdict` (hard failures) | Report with `hard_failures: ["dead_or_black_frames"]` | Returns `"reject"` | Report with all scores >= 8, no hard failures | Returns `"pass"` | PASS |
| `critic.verdict` (thresholds) | Scores with one dimension 6 (< MIN_EACH=7), avg=8.625 | Returns `"revise"` | Report with all dimensions = 8 | Returns `"pass"` | PASS |
| `critic.check` (consistency) | Claimed verdict `"pass"` but scores require `"revise"` | `ok=False`, problem flags mismatch | Claimed verdict matching computed verdict | `ok=True`, `problems=[]` | PASS |
| `critic.validate` (independence) | Report with `critic: "author"` | Returns error requiring `critic must be 'independent'` | Report with `critic: "independent"` | Returns `[]` | PASS |
| `timeline.validate` (scene gaps) | Scene 1 ends at 3.0s, Scene 2 starts at 3.5s | Returns error `scene_gap` | Contiguous scenes (s1 ends 3.0s, s2 starts 3.0s) | No `scene_gap` error | PASS |
| `timeline.validate` (word timing) | Word starts at 4.0s but placed in scene 0.0-3.0s | Returns error `word_outside_scene` | Word timing within scene boundaries | No `word_outside_scene` error | PASS |
| `timeline.validate` (cue anchors) | Cue anchors to word in different scene | Returns error `cue_not_in_scene` | Cue anchors to word inside its scene | No `cue_not_in_scene` error | PASS |
| `timeline.validate` (trust level) | `timing_trust: "human-verified"` without anchors | Returns error `trust` | Default unverified or with anchors | No `trust` error | PASS |
| `intelligence.visual` (Rule A) | 4 scenes all with identical backdrop, no motif | `status="fail"`, `ok=False` | 4 scenes with 3 distinct backdrops | `status="pass"`, `ok=True` | PASS |
| `intelligence.visual` (Rule B) | Signature identical to recent shipped look | `ok=False`, duplicate flagged | Signature differing on >= 2 fields | `ok=True`, `duplicates=[]` | PASS |
| `styles.validate_card` | Style card with invalid status `"super-validated"` | Returns validation problem for status | Valid style card | Returns `[]` | PASS |
| `styles.check_distinct` | Two cards differing on only 1 axis | Returns problem requiring >= 3 differing axes | Two cards differing on >= 3 axes | Returns `[]` | PASS |
| `qa.run_qa` | Deliberately corrupted synthetic clips | Flags failure on corresponding QA rule | Valid synthetic test clip | All 9 QA checks pass | Covered by `test_gate_calibration.py` (L8) |
| `finalcheck.validate_video` | Invalid duration / missing audio / black frames | Rejection at export gate | Valid compliant MP4 | Pass export gate | Covered by `test_gate_calibration.py` (L8) |
| `visual_gate` (captions, safezone, layers, transitions) | Synthetic clips with caption collision, dip, bad safezone | Visual gate error recorded | Compliant frames and transitions | Visual gate pass | Covered by `test_gate_calibration.py` (L8) |

---

## 3. Gaps Found

No gaps found in the evaluated gates:
- All 17 unit test negative controls in `tests/test_gate_negative_controls.py` pass without xfails.
- In `tests/test_gate_calibration.py`, 10 out of 12 historical calibration gaps were resolved in lane L8 (commits `8a05eb0`, `7252612`). Remaining characterization tests in calibration test files function as intended.

---

## 4. How to Re-Run

Execute the negative control test suite:
```bash
~/.contentos/venv/bin/python -m pytest tests/test_gate_negative_controls.py -v
```

Execute the full gate calibration suite:
```bash
~/.contentos/venv/bin/python -m pytest tests/test_gate_calibration.py -q
```
