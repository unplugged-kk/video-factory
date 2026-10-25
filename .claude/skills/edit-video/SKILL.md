---
name: edit-video
description: Use to edit a supplied recording (talking head, interview, screen recording): cut silences, captions, cutaways, reframing. Thin entry to create-video.
---

# edit-video

Shortcut for `create-video` with intent `edit`. Follow `.claude/skills/create-video/SKILL.md` exactly; this skill adds no workflow of its own.

`python -m contentos.videojob select --intent edit --input ...`

Inputs: the source video (required), optional broll folder, style wishes. Keep the person's appearance unchanged unless a look is requested. Keep text out of platform UI zones.
