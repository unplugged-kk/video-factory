---
name: spotify-particle-lyrics
description: "A 16:9 lyric video in four looks, like the Kalyani (ARJN × KDS × Fifty4 × Ronn ft. Shreya Ghoshal) video: a tilted Spotify lyrics card where every sung word lights up with glowing..."
metadata:
  bundle: video-factory-skills
  category: music-and-lyrics
  version: "1.0.0"
---

# Spotify Particle Lyrics

## Purpose

A 16:9 lyric video in four looks, like the Kalyani (ARJN × KDS × Fifty4 × Ronn ft. Shreya Ghoshal) video: a tilted Spotify lyrics card where every sung word lights up with glowing sparks, then the artists' photo turned into a monochrome particle portrait that morphs into a second photo while red-and-white lyrics pop on the right and dance on the beat, then gold motion-graphic lyrics with fast blur word changes for the singer's part, and a black-and-white rain-on-glass music player to end.

## When to use

Use this skill when the user explicitly requests `/spotify-particle-lyrics`, asks for this visual format, or the Video Factory director selects it after explaining the recommendation. Do not select it merely because a keyword appears in the script.

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

Original invocation brief: Save it as .claude/skills/spotify-particle-lyrics/SKILL.md so I can run /spotify-particle-lyrics with a song MP3 (or a clip of it), its lyrics, 1–2 photos (the artists, and a second photo to morph into), the Spotify logo PNG and a reference reel for the motion-graphic part attached.

Original creative intent: A 16:9 lyric video in four looks, like the Kalyani (ARJN × KDS × Fifty4 × Ronn ft. Shreya Ghoshal) video: a tilted Spotify lyrics card where every sung word lights up with glowing sparks, then the artists' photo turned into a monochrome particle portrait that morphs into a second photo while red-and-white lyrics pop on the right and dance on the beat, then gold motion-graphic lyrics with fast blur word changes for the singer's part, and a black-and-white rain-on-glass music player to end.

Original workflow steps:
1. Separate the vocals (demucs) and force-align every word of my lyrics on the vocal track. Find the beat and the kicks (librosa). Tell me which lines are rap and which are sung, and propose the sections: Spotify card → particles → Spotify again → motion graphics → rain ending.
2. Analyze the reference reel at 2 frames per second and write down its fonts, colours, word timing, transitions and camera moves, so the motion-graphic part copies that style.
3. Spotify card: a deep maroon card with the cover art, song title, artists and my Spotify logo (white behind its transparent bars), lyrics in big Inter bold. Tilt the card in 3D with a slow camera drift and blur the lines far from the sung one. Each word fades from dark to white with an ease-in-out as it is sung, with a soft glow, a burst of spark particles from across the word, small cross glints and a light point that rides along the word.
4. Particle portrait: remove the photo backgrounds, then turn each one into 20–25k stipple dots (local contrast + edges so the faces read) in white on near-black. Dots breathe with the beat and drift with red and white embers. On a chosen word, morph every dot from the first photo into the second with a fast staggered swirl and a flash ring. At the end, blow the dots apart. No artist names on screen.
5. Right-side lyrics during the particles, like the Let Me Love You kinetic video: rows alternating Inter 900 white caps and Instrument Serif italic red, each word popping in with a small overshoot on its sung time, letters bouncing on every beat, and each block blurring out before the next.
6. Motion graphics for the sung part in the reference style: gold serif words stacked and changing fast with a blur in and out, a moon on a starfield, and a curved lyric wall that turns like a cylinder. Show each lyric only once on screen, never a duplicate big word.
7. Rain ending: a blurred black-and-white music player (cover card, progress bar, lyric rows lighting up as sung) seen through glass, with hundreds of small water drops that each refract the scene, a few running drops with trails, grain and a vignette.
8. White flash or blur cuts between sections, a short fade in and out of the audio, and 1920×1080 at 30 fps with the song.

Source-specific run instructions to preserve where compatible:
- Draw everything in code (an HTML canvas rendered frame by frame in headless Chrome, encoded with ffmpeg). No stock footage or image generators, so the look is the same every time.
- Time every word with forced alignment (torchaudio MMS_FA). Never guess timings.
- Show me a contact sheet of stills before the full render, and ask before overwriting files.
- Render the MP4 with the original audio, plus a 720p copy under 20 MB for WhatsApp.

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
