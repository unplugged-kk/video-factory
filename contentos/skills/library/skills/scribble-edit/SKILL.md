---
name: scribble-edit
description: "Your own clip covered in live marker doodles, like the Justin Bieber “Where Are Ü Now” video from How to do this with Claude (Ep 5): the wall behind you fills with hand-drawn stars,..."
metadata:
  bundle: video-factory-skills
  category: music-and-lyrics
  version: "1.0.0"
---

# Scribble Edit

## Purpose

Your own clip covered in live marker doodles, like the Justin Bieber “Where Are Ü Now” video from How to do this with Claude (Ep 5): the wall behind you fills with hand-drawn stars, rockets, cats and lightning, crowns and shades stick to your face as you move, a neon line traces your body, and the whole look changes on every beat.

## When to use

Use this skill when the user explicitly requests `/scribble-edit`, asks for this visual format, or the Video Factory director selects it after explaining the recommendation. Do not select it merely because a keyword appears in the script.

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

Original invocation brief: Save it as .claude/skills/scribble-edit/SKILL.md so I can run /scribble-edit with a 9:16 clip of you moving (a plain wall behind you works best) and the song MP3 attached.

Original creative intent: Your own clip covered in live marker doodles, like the Justin Bieber “Where Are Ü Now” video from How to do this with Claude (Ep 5): the wall behind you fills with hand-drawn stars, rockets, cats and lightning, crowns and shades stick to your face as you move, a neon line traces your body, and the whole look changes on every beat.

Original workflow steps:
1. Track me on every frame with MediaPipe: a person mask split into body, hair and clothes (selfie multiclass), face landmarks and pose landmarks (wrists, elbows, knees). Smooth the points over a few frames so the doodles don't jitter.
2. Find the beat and every music hit in the song (librosa). Give the video a new doodle look on every hit and never hold one look longer than 7 frames, so it changes at least 4 times a second.
3. Wall: for every look, fill the background with 15–25 marker doodles on a loose grid so there is no empty space (stars, hearts, rockets, cats, cactus, lightning, planets, mushrooms, music notes, bombs, eyes, speech bubbles with short words like BOOM or NAH). Draw them on a layer cut out by my person mask so they sit behind me.
4. Face: draw 1–3 doodles in face space, scaled by my face width and turning with my head: crown, horns, halo, round shades, glowing eyes, skull, flower crown, beard, mask, rainbow mouth.
5. Body: most looks get a glowing neon outline around me in one bright colour, a pattern drawn on my shirt clipped to the clothes mask (ribcage, stripes, grid) and a colourful scribble clipped to my hair. Some looks swap the whole background for a full crayon backdrop (rainbow waves, stripes, op-art, galaxy, a white burst) with me pasted back on top.
6. Props: when my hands or knees do something (air guitar, a throw, a kick), draw a matching prop that follows them, like a guitar between my wrists or a ball in a parabola, with a word like ELECTRIC next to it.
7. Make it feel hand-drawn: thick wobbly marker lines in bright colours, every line redrawn slightly differently every 1–2 frames so it boils. Put my handle small in a corner.

Source-specific run instructions to preserve where compatible:
- Draw every doodle in code (an HTML canvas rendered frame by frame in headless Chrome, encoded with ffmpeg). No image generators, so the marker look is the same every time.
- Never cover my face: face doodles sit on top of it (crown, shades, horns), never instead of it.
- Show me a contact sheet of stills before the full render, and ask before overwriting files.
- Render 1080×1920 at 30 fps with the song as the audio, plus a 720p copy under 20 MB for WhatsApp. Check the render for black or empty frames before you give it to me.

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
