---
name: lyric-video
description: Use to make a lyric video from a song and lyrics in any language or style. Thin entry to create-video.
---

# lyric-video

Shortcut for `create-video` with intent `lyric`. Follow `.claude/skills/create-video/SKILL.md` exactly; this skill adds no workflow of its own.

`python -m contentos.videojob select --intent lyric --input ...`

Inputs: song audio (required), lyrics text (strongly preferred). Without lyrics the text comes from transcription and is flagged. Use the original audio.
