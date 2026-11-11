---
name: video-assets
description: Use to index or search local video, image and audio assets (B-roll) in plain English, with source and license notes. Thin entry to create-video.
---

# video-assets

Shortcut for `create-video` with intent `assets`. Follow `.claude/skills/create-video/SKILL.md` exactly; this skill adds no workflow of its own.

`./contentos.sh videojob select --intent assets --input broll:"<folder>"`

Runs the `asset-library` capability alone: no voice, no render.

## Index a folder
```
python -m contentos.production.assets index "<folder>" --out "$VIDEO_FACTORY_WORKSPACE/index/<name>.json" --samples 3
```
Write the index and the frames outside the repo. The command never writes a description of its own: it also writes `<index>.notes.json`, which you fill in **after looking at the sampled frames**, then merge back with `--notes <file>`. A clip you have not looked at stays `described: false` — say that rather than describing a clip from its filename. `--samples 0` skips frames for a folder of stills.

## Search it
```
python -m contentos.production.assets search "$VIDEO_FACTORY_WORKSPACE/index/<name>.json" "me walking at night" --limit 5
```
Hits carry a score and the terms that matched (`why`). Exit 1 means nothing matched: report that and ask for more footage — never offer the nearest guess. Report `license` and `source` for any clip you propose; `unknown` is not a clearance, and third-party footage needs the owner's rights decision.

## Keep it current
Re-run `index` after adding clips (the index is a cache and is overwritten on purpose), and `verify` to catch a clip or frame that has left the disk.
