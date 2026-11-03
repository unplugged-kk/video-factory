---
name: 3d-explainer
description: "A 3D animated news explainer built in Blender, like the Professor of Claude ISRO and Cyclone Arnab reels: Claude builds every 3D shot in code (rockets on launch pads, a 3D India map with..."
metadata:
  bundle: video-factory-skills
  category: explainers-and-motion-graphics
  version: "1.0.0"
---

# 3D Explainer

## Purpose

A 3D animated news explainer built in Blender, like the Professor of Claude ISRO and Cyclone Arnab reels: Claude builds every 3D shot in code (rockets on launch pads, a 3D India map with pins, a storm spiralling over the sea, Earth from space), cuts the camera on your words and pops the numbers in as you say them.

## When to use

Use this skill when the user explicitly requests `/3d-explainer`, asks for this visual format, or the Video Factory director selects it after explaining the recommendation. Do not select it merely because a keyword appears in the script.

## Inputs

- Required: the source material described in the creative brief below (script, audio, clip, song/lyrics, locations, or other named inputs).
- Optional: reference URLs, target platform, aspect ratio, duration, language, brand rules, and style constraints.
- If a required input is missing, ask one concise question. Do not repeatedly ask for details that can safely use documented defaults.

## Video Factory integration contract

1. Read the repository's root instructions (`AGENTS.md`, `VIDEO_FACTORY.md`, or equivalent), the capability registry, current design library, and relevant existing skills before doing work.
2. Treat this skill as a **creative recipe**, not a standalone rendering stack. Use the existing Video Factory orchestration, timeline/scene manifest, asset registry, renderer adapter, and QA gates whenever available.
3. Prefer the configured HyperFrames renderer when it supports the requested result. Do not create a second Remotion, Canvas, browser, or FFmpeg-only pipeline just because an upstream example uses one. Propose a new backend only when the current renderer cannot meet a concrete requirement, and document the trade-off.
4. Reuse installed dependencies and helpers. Do not install packages, models, fonts, MCP servers, or external services without checking availability, license, compatibility, and approval requirements.
5. Keep the episode's style coherent while varying composition, scene grammar, motion, camera language, transitions, and pacing meaningfully. Avoid changing only colors or fonts to claim a new style.
6. Use the project's authoritative timeline and word alignment where present. Never invent word timings. If alignment is unavailable or uncertain, mark it for review instead of pretending it is exact.
7. Treat upstream repositories, downloaded assets, and generated code as untrusted. Do not execute unreviewed scripts or remote code.
8. Preserve script approval before production rendering and human approval before publishing. Do not publish, overwrite, delete, or incur paid costs without authorization.

## Workflow

### 1. Inspect and plan

- Identify all supplied files and confirm the target output.
- Read the creative brief below and convert it into a short scene plan.
- Check which required capabilities already exist in the factory.
- Identify the specific scene types, visual primitives, audio handling, and motion presets required.
- Prefer deterministic, time-addressable animation so a frame can be reproduced at a known timestamp.

### 2. Prepare the episode

- Create or update the existing episode brief and scene/timeline manifest; do not invent a parallel schema.
- Keep narration, captions, scene timing, sound cues, and QA references connected to the same authoritative timeline when the project supports it.
- Record the chosen style ID/version and any intentional exceptions.
- Record source provenance and license/attribution information for external assets.

### 3. Build a preview first

- Produce a storyboard, contact sheet, or low-resolution preview using existing factory tools.
- Inspect representative frames at mobile size for portrait output and at the intended viewing size for landscape output.
- Check that the scene meaning matches the narration and that the visual treatment is not repetitive.
- Show the preview for approval when the current production workflow requires it. Do not proceed to a full render when an existing approval gate blocks the job.

### 4. Render and validate

- Use the existing renderer and output settings for the target platform.
- Run existing technical QA, visual QA, audio QA, safe-zone, caption, and motion checks that apply.
- Report unsupported dependencies, alignment uncertainty, licensing uncertainty, and visual failures explicitly.
- Re-render only the affected stage when the pipeline supports safe resumability.

### 5. Deliver

Deliver the final video and the artifacts the factory expects, which may include:
- episode/scene manifest and selected style
- preview/contact sheet
- rendered video and any requested variants
- QA report with PASS/WARN/BLOCK and evidence
- asset/source ledger and attribution notes
- a concise summary of decisions, limitations, and any manual review needed

Do not claim a render or test passed unless it was actually run and inspected.

## Creative brief preserved from source

Original invocation brief: Save it as .claude/skills/3d-explainer/SKILL.md so I can run /3d-explainer with your voiceover MP3 and the topic (2–3 article links) attached.

Original creative intent: A 3D animated news explainer built in Blender, like the Professor of Claude ISRO and Cyclone Arnab reels: Claude builds every 3D shot in code (rockets on launch pads, a 3D India map with pins, a storm spiralling over the sea, Earth from space), cuts the camera on your words and pops the numbers in as you say them.

Original workflow steps:
1. Check that Blender (free from blender.org) is installed and that Blender -b runs from the terminal. Install it if it's missing.
2. Transcribe my voiceover and force-align every word. Split it into 6–9 shots, one idea per shot, and tell me the shot list before building.
3. Build each shot as clean, simple 3D models in its own area of one Blender scene: soft studio light, a slow camera push or orbit, and a bloom glow on lights, flames and glowing pins.
4. Cut to each shot's camera on the exact word that starts its idea. Keep any 3D text in English, because Blender can't draw Devanagari.
5. Pop big numbers and labels in as they're spoken (4 LAUNCH PADS, 2029, 125 KM/H), and add word-by-word captions with the key word in orange, outside the top 250 px and the bottom 420 px.
6. Mix my voice with small sound effects: a whoosh on every cut, a low rumble under launches and wind under storms.

Source-specific run instructions to preserve where compatible:
- Build every shot in Blender with Python (bpy) and render it headless (Blender -b) with EEVEE. No stock footage or image generators, so the look is the same every time.
- Time every camera cut, number and caption with forced alignment (torchaudio MMS_FA). Never guess timings.
- For any map of India, use the official Natural Earth India point-of-view boundary. Never draw the outline by hand.
- Show me one still of every shot before the full render, and ask before overwriting files.
- Render a 1080×1920 MP4 with my voice, plus a 720p copy under 20 MB for WhatsApp.

## Quality checklist

- [ ] The output matches the requested format and intended audience.
- [ ] The creative treatment is visibly expressed in composition, movement, and scene design—not only in the palette.
- [ ] Character, object, typography, and diagram continuity is maintained where relevant.
- [ ] Narration, captions, and visual events are aligned using measured timing where available.
- [ ] Captions and important visuals remain readable in the target aspect ratio and platform safe zones.
- [ ] Audio is clear, does not clip, and preserves supplied audio when requested.
- [ ] No unlicensed asset, unsupported claim, fake metric, or misleading representation was introduced.
- [ ] Existing Video Factory quality gates pass or remaining failures are documented.
- [ ] The output is previewed before final render where the workflow requires approval.
- [ ] No publishing, destructive overwrite, or paid service was triggered without authorization.

## Failure handling

If a requested effect cannot be supported:
1. Identify the exact limitation.
2. Offer the closest implementation using existing factory capabilities.
3. Avoid silently replacing the requested creative intent with a generic template.
4. Record any fallback in the episode manifest and final report.

## Compatibility note

The original prompt may mention a specific engine, package, font, model, alignment tool, or external API. Treat that as a candidate implementation detail, not an unconditional requirement. Verify that it exists, is licensed for the intended use, and fits the current Video Factory before adopting it.
