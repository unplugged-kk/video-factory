---
name: explainer-visual-qa
description: Use after rendering a Video Factory explainer and before calling it ready - objective gates, phone-scale frame inspection, an independent critic report, and reproducible A/B comparison of builder or skill changes. Not for authoring animation.
---

# Explainer visual QA

A video is not "done" because it rendered. Run these in order; stop and fix at the first failure.

## 1. Objective gates (already in the factory)
- `config/quality.yaml` via `contentos.qa.run_qa`: resolution, fps >= 24, duration limits, loudness -14 LUFS +/- 3, true peak <= -0.5, black > 0.5 s fails, freeze > 3 s warns.
- `npx --no-install hyperframes lint` and `check` (errors, warnings, WCAG contrast) in each format project.
- Script-to-ASR alignment (`contentos.production.align`): every script word matched, WER near 0.
- `ffprobe` the final MP4s. Do not trust the render log.
- **Rendered-frame gate** (`contentos.production.visual_gate`): run it against the real render, because lint and exit codes passed while the picture was still wrong (KF-004 shader transitions rendered as cuts or black frames, KF-005 an opaque scene hid the captions). JSON on stdout; exit `0` ok, `1` finding, `2` unreadable input (message on stderr, no JSON).
  - `python -m contentos.production.visual_gate log <render.log> [--shader]` — failure and fallback codes in the log. The log is evidence of what broke, not proof the render is right.
  - `... visual_gate layers <project dir | index.html>` — caption layer order read from the source, so it is a static pre-check, not a substitute for the render checks.
  - `... visual_gate captions <video.mp4> --region x,y,w,h --canvas 1080x1920 (--timing timing.json | --windows a:b,...)` — text-like ink in the caption region. `--timing` needs scenes with `start`/`end` (or `dur`); a `timeline/1` file uses `t0`/`t1`, yields no windows and reports a false `visible_ratio: 0.0` that is not a caption failure. A `--project` with a px-sized `#captions` rule can supply the region instead of `--region`.
  - `... visual_gate transitions <video.mp4> --at start:duration[:kind] [--at ...] [--allow-dip]` — one verdict per cut: `blend`, `hard_cut`, `black` or `inconclusive`.
  - A non-zero exit is evidence to inspect, not a verdict: `inconclusive` means the samples could not tell, and the gate never judges whether a transition looks good. Thresholds are provisional, calibrated on synthetic fixtures and the Ep3 spike renders only — do not tune them to make a run pass.
  - Known blind spot (H.3 in `docs/video-intelligence/04-visual-reliability-gate.md`): `layers` reads CSS and inline styles only, so a canvas injected from JavaScript (HyperShader's `z-index: 100`) is invisible to it — it returned ok on all five Mac arms, including the two that lose their captions. Only `captions` on a render catches that.
  - Run only the checks that have evidence, and say which ones you skipped and why: no render, no log, no region or no ffmpeg (`exit 2`) is reported as a gap, never as a pass. Do not report the video as ready on the checks that did run. Pure Python plus ffmpeg: no network, no new dependency.

## 2. Motion gates
- `contentos.production.motion_audit.ease_inventory(index_html)`: overshoot easings should be 0 unless the brief wants playful.
- `video_ydif` + `motion_stats`: report `pops` (one-frame jumps). Cross-check each pop time against scene boundaries and the storyboard: a pop at a scene start with a continuous camera is a snap (see `explainer-motion-craft` R3); caption swaps and intended hard cuts are expected.
- A pop count is evidence to inspect, not a verdict.

## 3. Look at it
- `python -m contentos preview <project-or-mp4> --at 1.5,5,9 --out <dir> --sheet` for frames and contact sheets in both formats. View at phone size. Check clipping, caption band collisions, empty areas, label overlaps, anything unreadable.
- Inspect the 2 frames around every scene cut.

## 4. Independent critic
Spawn a reviewer that did NOT build the video (a separate agent or the person). Give it the contact sheets, the narration and the brief, not your reasoning. It returns JSON shaped like `templates/critic-output.example.json` (dimensions and hard failures in `references/critic-rubric.md`). Then:
```
python -m contentos.production.critic report.json    # exit 0 only if well-formed and the verdict matches the scores
```
Thresholds (each score >= 7, average >= 8) are provisional and uncalibrated. A `reject` or `revise` goes back to the builder; do not edit the report.

## 5. A/B discipline for any change to a rule, template or skill
Use `scripts/motion_compare.py` on a COPY of a finished project: identical script, narration, audio, plan, assets, resolution and fps; same renderer; both variants rebuilt and rendered in the same session. Report counted metrics and show frames. Rules:
- One render per variant cannot establish a time difference (Pilot 001 control re-render varied about 2 s against its original); repeat before claiming speed.
- Size and pop counts are objective. "Looks better" is a human judgement: say so and ask for it.
- Never modify the source project. Verify its tree hash before and after.

## 6. Ready means
Gates 1-4 pass, the report is on file with the project, and the human has been shown the frames. Publishing still needs PUBLISH_APPROVED.
