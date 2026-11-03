---
name: red-rap-lyrics
description: "A fast rap lyric video in one red grade, like the Hola Amigo (KR$NA ft. Seedhe Maut) video: a red glass lyrics card that peels in like a page over a tilted wall of lyric words, then neon..."
metadata:
  bundle: video-factory-skills
  category: music-and-lyrics
  version: "1.0.0"
---

# Red Rap Lyrics

## Purpose

A fast rap lyric video in one red grade, like the Hola Amigo (KR$NA ft. Seedhe Maut) video: a red glass lyrics card that peels in like a page over a tilted wall of lyric words, then neon words standing on a rainy street with ripple reflections, then the rapper's photo turned into a monochrome particle portrait with stacked italic lyrics lighting up word by word, and a 3D tower of words where the camera eases to every new word, ending on a DAMN! slam.

## When to use

Use this skill when the user explicitly requests `/red-rap-lyrics`, asks for this visual format, or the Video Factory director selects it after explaining the recommendation. Do not select it merely because a keyword appears in the script.

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

Original invocation brief: Save it as .claude/skills/red-rap-lyrics/SKILL.md so I can run /red-rap-lyrics with a rap song MP3 (or a clip of it), its lyrics (Hindi in Devanagari works), one photo of the rapper and your reference reels for each section attached.

Original creative intent: A fast rap lyric video in one red grade, like the Hola Amigo (KR$NA ft. Seedhe Maut) video: a red glass lyrics card that peels in like a page over a tilted wall of lyric words, then neon words standing on a rainy street with ripple reflections, then the rapper's photo turned into a monochrome particle portrait with stacked italic lyrics lighting up word by word, and a 3D tower of words where the camera eases to every new word, ending on a DAMN! slam.

Original workflow steps:
1. Separate the vocals (demucs) and force-align every word of my lyrics on the vocal track, exactly as I wrote them. Find the beats and kicks (librosa). Split the song into 4 sections and tell me which lines go in each.
2. Analyze each reference reel at 2 frames per second and write down its fonts, sizes, colours, how words appear and the exact ease of every camera move, so each section copies its reference.
3. Section 1, lyrics card: a dark red glass card (cover art, song title, artists, star and dots icons) that unfolds from a page curl at the corner. Behind it, a huge tilted wall of the lyric words in deep red, drifting slowly. The lines scroll up with an ease-in-out and each word goes from dim red to glowing white exactly when it is sung.
4. Section 2, rainy street: a dark red night street with city blocks, street lamps and their light cones, rain streaks and splash ripples. Each line stands on the ground as 2–3 rows (a big bold condensed row, then a smaller row in red neon that flickers on), word by word on the voice, with a rippling reflection on the wet road below. Slow push-in.
5. Section 3, particle portrait: remove the photo background and turn the rapper into 20–35k white stipple dots (local contrast + edges so the face reads) on a deep red-black glow. The dots fly in, breathe with the beat and drift off the edges with red and white embers. Beside him, each line as stacked italic condensed rows (Teko), each row scaled to a similar width, all words dim grey first and flashing white (keywords red) when sung.
6. Section 4, word tower: place every word in 3D on a corner, front-face words right-aligned to the corner and some words on the side face, key words big and red. On every sung word, move the camera (target, yaw, pitch, roll, distance) to that word with a smooth ease-in-out, then pull back to show the whole tower at the end of the verse.
7. End on the last ad-lib as a huge white condensed word (DAMN!) that slams in with a shake and red echo trails. Mask and mute any swear words I name: show the first letter plus *** and replace only the voice with the instrumental stem at that moment, so the beat keeps playing.
8. Red flash or zoom-blur cuts between sections, grain and a vignette on everything, 30 fps with the song. Render 9:16 1080×1920 and 16:9 1920×1080.

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
