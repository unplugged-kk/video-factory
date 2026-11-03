# Prompt: Independent video review and QA

Act as an independent critic, not the author of the video.

Inspect the rendered file, manifest, contact sheet, source script, and QA report. Where possible, sample frames at scene boundaries and visually inspect the full video or relevant sections.

Check:
- technical validity, resolution, frame rate, duration, decode errors;
- black/frozen frames, broken transitions, clipping, visual collisions;
- caption timing, readability, spelling, safe zones;
- audio loudness, clipping, silence, narration/music balance;
- scene-to-script alignment and technical accuracy;
- style coherence and actual visual diversity;
- excessive repeated layouts/transitions;
- source attribution and license status;
- consistency with the approved storyboard.

For each issue provide severity (BLOCK/WARN/NOTE), timestamp/scene, evidence, remediation, and whether human review is needed. Never invent a pass result. Run existing deterministic gates first and use visual-model assessment only where it adds value. Return a computed verdict based on explicit thresholds.
