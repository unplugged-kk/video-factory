# Agent brief: how to use the video factory

Give any coding agent (Claude Code, Codex, Cursor, etc.) the one-paragraph PROMPT below plus a topic.
Everything else the agent needs is in this repo; this file tells it where to look and what it may not do.

## 1. Copy-paste prompt (short)

> You are operating my local video factory at `~/git/video-factory` (contentos). Read `docs/AGENT_BRIEF.md`,
> then `README.md`, then follow the workflow in the brief. Make one video about: **<TOPIC>**.
> Format: <9:16 short | 16:9>. Length: <~45 s>. Language: <English>. Tone: <calm-precise>.
> Script: <"write it yourself" | paste my script below>.
> Stop at every approval gate and ask me. Never publish, never spend money.
> When done, give me the path to `video.mp4`, the QA result, and anything you were unsure about.

## 2. What the factory is
Local-first pipeline on an Apple Silicon Mac: `brief > script > voice > compose > render > qa > package > publish`.
- Voice: Kokoro (local, English). Captions: whisper.cpp (English-only model). Render: HyperFrames (HTML to MP4) by default; `mpt` lane for stock b-roll.
- Every stage writes to `workspace/projects/<content_id>/` and resumes if the artifact exists. Ledger is SQLite.
- Entry point: `./contentos.sh` (put `/opt/homebrew/bin` first; the stale x86 ffmpeg in /usr/local/bin fails).

## 3. Workflow the agent must follow
1. `./contentos.sh doctor` . Stop and report if anything the plan needs is NOT_INSTALLED.
2. Optional research: `./contentos.sh research "<topic>"` (Reddit+HN, keyless). Verify every fact; put sources in the spec `sources:`.
3. Plan with the `video-director` skill (`.claude/skills/video-director`): audience, one takeaway, hook, arc, scene-by-scene treatment, using only capabilities listed in `config/capabilities.json`.
4. Write the spec YAML in `workspace/factory-specs/<content_id>.yaml` (template in section 4; examples in `examples/`). ~2.5 words per second of narration.
5. Show me the script and title. **GATE 1: wait for SCRIPT_APPROVED** before voice.
6. Voice, compose. For animation quality use `explainer-motion-craft` and `hyperframes-core` skills.
7. **GATE 2: wait for PRODUCTION_APPROVED** before render.
8. `./contentos.sh pipeline run <spec> --approve-private` only after I approve (omit the flag to park at the gate).
9. QA: `./contentos.sh qa workspace/projects/<id>/video.mp4`, then visual check with the `explainer-visual-qa` skill (look at frames at phone size).
10. Report: video path, QA table, open risks, claims still to verify. Nothing else happens without me.

## 4. Spec template (minimum)
```yaml
content_id: my-video-slug
title: "Title under 70 chars"
thumb_text: "2-3 WORDS"
description: "One or two sentences. Sources: ..."
tags: [tag1, tag2]
format: "9:16"          # or "16:9"
voice: af_heart
render: hyperframes     # or mpt (needs docker compose up -d, or mpt.source: local)
sources:
  - {claim: "what it supports", url: "https://..."}
script:
  - say: "Hook line the narrator speaks."
    headline: "On-screen text"
    tag: HOOK
  - say: "Next idea, one idea per line."
    headline: "Short headline"
    tag: STEP 1
    # tts: "respelling for hard names"   # optional pronunciation override
    # broll: "stock search phrase"       # mpt lane only
  - say: "Call to action."
    headline: "Follow for more"
    tag: CTA
```

## 5. Hard rules
- No public upload. Publish is DRY_RUN; `config/youtube.yaml` has `publish.enabled: false`. Do not change it.
- No paid services or APIs without my explicit approval. Do not pass paid MPT sources or music.
- Do not edit `config/*.yaml`, gates, or the pinned `hyperframes` version (0.8.114) unless I ask.
- Do not invent facts, numbers or quotes; unverifiable claims go in the report, not the video. Label illustrative data as illustrative.
- English only for now: Kokoro and the installed Whisper model have no Odia, and Hindi voices are low grade. Odia/Hindi needs Indic Parler-TTS and a native reviewer first.
- Third-party audio/footage needs a rights decision from me.
- Files outside this repo and `~/.contentos` are off limits. Never print secrets from `~/.contentos/secrets`.

## 6. Known limits (as of 2026-10-10)
- Not built: niche discovery, analytics ingestion, thumbnails, multi-platform, YouTube uploader.
- OpenMontage (cinematic/avatar) has no adapter: manual handoff only.
- Pexels/Pixabay/Coverr stock needs a free key in `vendor/MoneyPrinterTurbo/config.toml`; untested.
- `frozen_frames` QA WARN on text slides is expected.
- More detail: `docs/factory-v2/`, `docs/report.md`.

## 7. Using it from another system (ContentForge)
`./contentos.sh factory-worker` watches the exchange folder (`~/.contentos/exchange`) for job folders and renders them; see README "ContentForge exchange".
