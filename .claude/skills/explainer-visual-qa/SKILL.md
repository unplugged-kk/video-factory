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
