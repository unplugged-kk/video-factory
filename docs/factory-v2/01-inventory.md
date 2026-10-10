# 01 - Infrastructure inventory (Milestone A)

Audited 2026-10-10, read-only. No credentials, `.env` files or `secrets.json` were opened. Facts below were observed on this Mac unless marked otherwise.

## Hardware and OS
| Item | Value |
|---|---|
| Machine | MacBook Pro, Apple M5 Pro (base), arm64 |
| RAM | 24 GB unified (hyperframes doctor saw only ~4.6 GB free during an earlier test, so close other apps before renders) |
| Disk | 926 GiB total, ~563 GiB free |
| OS | macOS 27.0.1 |
| GPU | Apple integrated (Metal/MPS/MLX). No NVIDIA/CUDA |

## Tooling present
ffmpeg, ffprobe (Homebrew, arm64), node, npm, npx, bun, python3 (Homebrew), uv, git, gh, brew, yt-dlp, whisper-cli (whisper.cpp), Docker via Dory, Claude Code CLI. Missing: ollama, sox, espeak-ng, whisperx, remotion.

## Models on disk (hyperframes cache)
| Model | File | Size | Consequence |
|---|---|---|---|
| Whisper | `ggml-small.en.bin` | 465 MB | **English-only.** Cannot transcribe Hindi or Odia as installed |
| Kokoro | `kokoro-v1.0.onnx` + `voices-v1.0.bin` | 310 MB + 27 MB | English voices usable; Hindi voices exist upstream but need testing; no Odia |

## Repositories (all under ~/git)
| Repo | State | License | Role in the factory |
|---|---|---|---|
| `video-factory` (contentos) | main, clean, last commit 2026-10-04 | none file found (private) | **The base to extend.** Python CLI, SQLite ledger, approval gates, hyperframes render lane, QA, queue + worker, provider routing |
| `ContentForge` | feat/auth0-migration, 37 uncommitted files | none file found | Owns research, decisions (Jev), publications. Has video factory contract/provider code. **Do not touch** the dirty branch |
| `openshorts` | main, 2 dirty files | MIT | Long-to-short repurposing (clip selection, camera inset, burned subtitles, hooks). Reuse via adapter |
| `MoneyPrinterTurbo` | main, 14 dirty files | MIT | Stock-footage short lane (`render: mpt`); its API on :8081 answered the doctor probe |
| `reelmimic` | main, 4 dirty files | MIT | Not yet inspected beyond listing |
| `AI-Content-Studio`, `clipbrain`, `OpenCut`, `postiz-app` | present | not checked | `postiz-app` is a possible multi-platform publisher; others unevaluated |
| `video-factory/vendor/OpenMontage` | vendored | **AGPL-3.0** | Architecture reference only. Do not copy code into non-AGPL work |

## What video-factory already does (verified)
- `./contentos.sh doctor` ran: Kokoro PASS, whisper.cpp PASS, hyperframes PASS (v0.8.114), ffmpeg PASS, MPT PASS, yt-dlp PASS.
- `pytest tests`: **39 passed in 4.6 s** (README still says 15; stale).
- Pipeline `brief > script > voice > compose > render > qa > package > publish`, resumable, with gates (`SCRIPT_APPROVED`, `PRODUCTION_APPROVED`, `PUBLISH_APPROVED`). Publish is DRY_RUN only; `publish.enabled: false`.
- Local-first provider routing (`config/local-first-policy.yaml`, `allow_paid: false`).
- Worker with heartbeat, lock, reclaim and retries; ContentForge exchange folder at `~/.contentos/exchange`.
- Existing output: `~/videos/india-tax-explainer.mp4`, 1080x1920, 30 fps, h264 + aac, 91.2 s, 8.4 MB.
- 434 skills in `~/.claude/skills`, including `hyperframes`, `hyperframes-core/-audio/-animation/-cli/-registry`, `music-to-video`, `captions-overlay`, `remotion-to-hyperframes`, `short`, and `yt-plan/-script/-seo/-shorts/-package/-retention/-audit`.

## Gaps against the mission (observed)
1. No LLM provider: `doctor` shows `[llm] selected: NONE`. Scripts must be supplied by hand.
2. No Hindi/Odia speech-to-text (English-only Whisper model).
3. No Odia TTS (not in Kokoro). Hindi Kokoro voices untested.
4. No scene-plan schema separate from the render lane, so there is no landscape/vertical reframe from one plan.
5. No music workflow (no beat sync, mixing policy, or licensed-music tracking). `hyperframes beats` exists but is not wired.
6. No lyric workflow and no podcast-explainer template.
7. No localization layer (glossary, pronunciation dictionary, subtitle validation).
8. Publishing: no OAuth, no upload adapter. Analytics: none.
9. No `CLAUDE.md`/`AGENTS.md` in video-factory, and no project-level factory skill.
10. `~/.voice-clone-venv` (chatterbox) is missing; this is optional.

## Not inspected
ContentForge internals beyond file names, `reelmimic`, `AI-Content-Studio`, `OpenCut`, `postiz-app`, and the `OpenMontage` code. Nothing was modified.

## Skill inventory (project-scoped, added 2026-10-10)
| Skill | Location | Source / pin | Status |
|---|---|---|---|
| `hyperframes-core` | `.claude/skills/hyperframes-core/` | heygen-com/hyperframes `skills/hyperframes-core`, tag v0.8.114 (`01c6f600`), Apache-2.0 | Vendored, gitignored, hash-verified |
| `hyperframes-animation` | `.claude/skills/hyperframes-animation/` | same pin; includes `scripts/animation-map.mjs` | Vendored, gitignored, hash-verified |
| `hyperframes-keyframes` | `.claude/skills/hyperframes-keyframes/` | same pin | Vendored, gitignored, hash-verified |
| `explainer-motion-craft` | `.claude/skills/explainer-motion-craft/` | Ours (rules distilled from the audit) | Not ignored (commit with the repo) |
| `explainer-visual-qa` | `.claude/skills/explainer-visual-qa/` | Ours | Not ignored (commit with the repo) |
Not installed on purpose: the other 18 HyperFrames skills, all Remotion and Motion Canvas skills (audit sections 6 and 9). The 434 personal skills in `~/.claude/skills` are unchanged; 25 entries there dangle (audit section 12).
