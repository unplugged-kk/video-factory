---
name: video-qa-critic
description: "Independently reviews rendered video for technical validity, visual quality, audio, captions, style coherence, and accuracy."
metadata:
  bundle: video-factory-skills
  kind: core-workflow
  version: "1.0.0"
---

# Video QA Critic

Review the source script, approved storyboard, episode manifest, rendered file, contact sheet, and automated QA output.

Check:
- decoding, dimensions, frame rate, duration, black/frozen frames, and transition failures;
- caption accuracy, timing, readability, spelling, and platform safe zones;
- audio presence, clipping, loudness, silence, and narration/music balance;
- technical claims, diagram correctness, and script-to-scene alignment;
- style coherence and meaningful variation across scene composition and motion;
- asset provenance, attribution, and license status.

Report each finding with severity (BLOCK/WARN/NOTE), timestamp or scene ID, evidence, remediation, and human-review requirement. Run existing deterministic gates rather than duplicating them. Do not invent a PASS result or numerical quality score without a defined rubric.
