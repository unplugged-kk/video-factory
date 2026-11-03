---
name: glass-to-neon-lyrics
description: "An emotional 16:9 lyric video that keeps changing mood with the song, like the Arz Kiya Hai (Anuv Jain × Lost Stories) video: a red glass Apple-Music-style lyrics card over a wall of..."
metadata:
  bundle: video-factory-skills
  category: music-and-lyrics
  version: "1.0.0"
---

# Glass To Neon Lyrics

## Purpose

An emotional 16:9 lyric video that keeps changing mood with the song, like the Arz Kiya Hai (Anuv Jain × Lost Stories) video: a red glass Apple-Music-style lyrics card over a wall of giant red words that cracks and shatters, then full-screen clips with the lyrics standing in the empty space (a starry red field with twinkling and shooting stars, a sunny hill, a man against the clouds), a key line cut out as giant letters with fire burning inside them, and a pink neon ending where lyrics fall in, splash and reflect in water while it rains.

## When to use

Use this skill when the user explicitly requests `/glass-to-neon-lyrics`, asks for this visual format, or the Video Factory director selects it after explaining the recommendation. Do not select it merely because a keyword appears in the script.

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

Original invocation brief: Save it as .claude/skills/glass-to-neon-lyrics/SKILL.md so I can run /glass-to-neon-lyrics with a song MP3 (or a clip of it), its lyrics, the cover art, and 4–6 clips or photos with the mood you want for each part attached.

Original creative intent: An emotional 16:9 lyric video that keeps changing mood with the song, like the Arz Kiya Hai (Anuv Jain × Lost Stories) video: a red glass Apple-Music-style lyrics card over a wall of giant red words that cracks and shatters, then full-screen clips with the lyrics standing in the empty space (a starry red field with twinkling and shooting stars, a sunny hill, a man against the clouds), a key line cut out as giant letters with fire burning inside them, and a pink neon ending where lyrics fall in, splash and reflect in water while it rains.

Original workflow steps:
1. Separate the vocals (demucs) and force-align every word of my lyrics on the vocal track, exactly as I wrote them. Find the beats (librosa). Read the lyrics for meaning and split the song into parts: card, clips, key line, neon ending. Tell me which clip goes with which lines and use every clip only once.
2. Part 1, glass card: a dark red frosted-glass card (cover art, song title, artists) like the Apple Music lyrics screen, tilted slightly in 3D. Each word fills from dim to bright exactly when it is sung, the next line waits blurred below, and a soft shine sweeps across on every line change. Behind it, a slow scrolling wall of the lyric words in giant deep-red caps.
3. At the end of part 1, crack the card with thin light lines, then shatter it into glass shards that fly toward the camera with a red bloom into the next part.
4. Part 2, clips: each clip full-screen in its natural colours, with a slow push-in. Place the lyrics in the empty space of each shot (above the person or below the horizon, never over a face): a small tracked caps row, one big Inter 800 caps row and one word in red Great Vibes script that writes itself on, all word by word on the voice. On a still photo (like a starry field), make it alive: twinkling stars, a few shooting stars and light drifting.
5. Key line: cut the words out of black as giant Inter 900 letters so a fire (or any bright clip) burns only inside the letters, then let the letters grow until the clip fills the screen. Soft white flashes or red burns between shots.
6. Part 3, pink neon ending: all clips in a pink duotone, darker at the bottom. Neon lyric words drop in one by one with a small bounce, flicker on like a sign, and land with a splash ripple and drops on a wet floor that mirrors them. Add light rain and a few drops on glass. On the last word, hold the frame and fade out.
7. Grain and a soft vignette on everything, a short fade in and out of the audio, 1920×1080 at 30 fps with the song.

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
