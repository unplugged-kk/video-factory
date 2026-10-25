---
name: repurpose-video
description: Use to turn a long video into chaptered content and vertical clips. Thin entry to create-video.
---

# repurpose-video

Shortcut for `create-video` with intent `repurpose`. Follow `.claude/skills/create-video/SKILL.md` exactly; this skill adds no workflow of its own.

`python -m contentos.videojob select --intent repurpose --input ...`

Inputs: the long video or its file. Pick moments from the full transcript, not from guesses. Each clip needs a strong first line and a complete thought.
