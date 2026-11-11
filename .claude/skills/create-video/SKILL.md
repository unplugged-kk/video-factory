---
name: create-video
description: Use for any video request - new video from a topic, script, audio, song, images or data; editing a recording; lyric video; repurposing a long video; or an unfamiliar format. Reads the inputs, builds a videojob/1 manifest, selects the smallest set of capabilities, and runs them through the video-production-orchestrator phases and gates. Do not add a topic- or style-specific skill for a new request.
---

# Create video (universal entry)

You turn one request into one finished, checked video. Topic, language, character and colour palette never justify a new skill; they are job configuration. The look is data (`style/1` cards, `look/1` presets); the workflow is chosen from the inputs.

## 1. Read the request
Collect: objective, supplied files and links, language, audience, platform, duration, aspect ratios, style wishes. Inspect supplied media with `ffprobe` before deciding anything. Ask only when a missing decision changes the result and cannot be inferred (for example no audio for a lyric video). State every default you pick. Never invent lyrics, spoken words, figures or timestamps.

## 2. Select the workflow
```
./contentos.sh videojob select [--intent create|edit|lyric|repurpose|assets|news] --input topic:"..." --input audio:song.mp3 --input lyrics:l.txt [--duration SECONDS]
```
Exit 1 means a blocker (say what is needed); `warnings` must be repeated to the user. The result is the capability list, in order, with a reason for each. Run only those. Record the result in `videojob.json` (`videojob.new_job` / `videojob.write`) inside the job folder under `$VIDEO_FACTORY_WORKSPACE/jobs/YYYY/MM/DD/<job>/`, never in the repo and never over an existing file.

## 3. Capabilities and their current state
State is data, not prose: the selector prints each capability with `state` (`exists` or `planned`), the artifact that implements it (`by`), the reason it was chosen and any `note` limit. Run the command and report what it says instead of copying a list from here.
| Capability | Covers |
|---|---|
| research | sources gathered and verified before scripting, kept for credits |
| voice | narration from the script (Kokoro) |
| video-understanding | transcription and word timing of speech |
| storyboard-director | scenes, shots and narrative structure |
| visual-style-engine | the look: palette, type, texture, motion, captions |
| motion-graphics-engine | captions, titles and motion on word timings |
| talking-head-editor | cutting, reframing and cutaways in a supplied recording |
| lyric-video-engine | animating lyrics from word timings and beats |
| asset-library | indexing and searching local media |
| video-renderer | composition and encode |
| video-quality-checker | technical and visual verification |

`contentos/videojob.py` holds the state of each of these (`IMPLEMENTED_BY`) and `tests/test_videojob.py` fails when the two disagree, so edit the code and this table together.
If a selected capability is `planned`, say so, do the parts that exist, and report the gap. Do not fake it.

### Choosing a look
`python -m contentos.intelligence.looks list --kind look` then `show <id>`. Pick by what the content needs, not by topic. Two looks can be merged with `combine <base> <overlay>` (base keeps type and captions, overlay gives accent, texture and fitting effects). For an unfamiliar style write a new `look/1` JSON in `config/presets/looks/` and run `looks validate`; do not add a skill. Fonts named in a look are not bundled (only Outfit is): check availability before render and report a fallback. Old spec names map to presets in `docs/generic-video/migration-map.json`.

## 4. Run
Follow `video-production-orchestrator` phases P0-P11 for the selected capabilities only. Before a substantial render show a storyboard or shot list and a contact sheet (`./contentos.sh preview ... --sheet`). Gates are unchanged: `SCRIPT_APPROVED` before voice, `PRODUCTION_APPROVED` before render. Low-risk edits with clear instructions need no extra pause.

## 5. Timing honesty
Drive animation from stored word timestamps. Report the real granularity (word, phrase, sentence) and tool in `timing`. If forced alignment or a language is unsupported, use the named fallback and say so; never claim word accuracy the tool did not give.

## 6. Finish
`ffprobe` the outputs (dimensions, duration, fps, codec), run the QA gates, look at frames at phone size. Report: output paths, what was verified, what could not be, open risks. Never publish, never spend money, never overwrite an existing deliverable.

## Never
Create a new skill for a topic, language, character or palette. Copy protected characters, logos or named creators; use original ones. Edit `config/*.yaml`, the gates, or `hyperframes-*`. Register a capability in `config/capabilities.json` before a smoke test passes and the owner agrees.
