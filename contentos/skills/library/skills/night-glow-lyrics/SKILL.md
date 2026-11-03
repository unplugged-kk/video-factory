---
name: night-glow-lyrics
description: "A 16:9 lyric video that makes people feel the song, like the Dooron Dooron (Paresh Pahuja ft. Harleen Sethi) video: one night-blue look with glowing white light, emotional clips that..."
metadata:
  bundle: video-factory-skills
  category: music-and-lyrics
  version: "1.0.0"
---

# Night Glow Lyrics

## Purpose

A 16:9 lyric video that makes people feel the song, like the Dooron Dooron (Paresh Pahuja ft. Harleen Sethi) video: one night-blue look with glowing white light, emotional clips that follow the story of each line, an Instagram post that dives into the title, and lyrics that change style with the music (small tracked caps + one huge serif word for the key lines, simple bottom lines in between), ending with the last line turning to light.

## When to use

Use this skill when the user explicitly requests `/night-glow-lyrics`, asks for this visual format, or the Video Factory director selects it after explaining the recommendation. Do not select it merely because a keyword appears in the script.

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

Original invocation brief: Save it as .claude/skills/night-glow-lyrics/SKILL.md so I can run /night-glow-lyrics with a song MP3 (or a clip of it), its lyrics, 2–4 emotional video clips (glowing / dreamy couple clips work best) and the song title + artists attached.

Original creative intent: A 16:9 lyric video that makes people feel the song, like the Dooron Dooron (Paresh Pahuja ft. Harleen Sethi) video: one night-blue look with glowing white light, emotional clips that follow the story of each line, an Instagram post that dives into the title, and lyrics that change style with the music (small tracked caps + one huge serif word for the key lines, simple bottom lines in between), ending with the last line turning to light.

Original workflow steps:
1. Separate the vocals (demucs) and force-align every word of my lyrics on the vocal track. Find the beats (librosa). Read the lyrics for meaning and the feeling of the song, and tell me the story in one line before you build.
2. Watch every clip at 2 frames per second and list each usable moment (time range + what happens: holding hands, looking from behind, reaching, alone). Map each lyric line to the moment that matches its meaning in a shot table, and never use the same moment twice.
3. One look for the whole video: night blue grade, glowing whites, soft light motes drifting, slow push-ins and crossfades between shots. Keep one font family: Inter 300 tracked caps for small words and Instrument Serif italic for the lyrics, white with a soft blue glow and a dark shadow under the text so it reads over bright clips.
4. Opening: the first clip quiet with no text, then an Instagram post of the second clip (likes, the lyric as the caption, a hashtag) that the camera dives into, landing on the song title in big glowing serif with the artists in small caps.
5. Lyric variety, timed to the voice: for the key lines a hierarchy block placed in the empty space beside the people (a small caps row, one huge serif key word, a medium row), entering with a smooth slide, rise, scale or letter-by-letter fade on the sung words. For the in-between lines a simple centred line at the bottom. Mix both so it never looks like captions.
6. Meaning moments: split lines like mitti / pari into a grey dusty word and a glowing word with sparkles, let words like dooron dooron drift apart letter by letter, and make the last line (kahan main) dissolve into light.
7. Dim any blown-out clip moment (brightness + contrast per shot) so the text always wins. Short fade in and out of the audio, 1920×1080 at 30 fps with the song.

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
