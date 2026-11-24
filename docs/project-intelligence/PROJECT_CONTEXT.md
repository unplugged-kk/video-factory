# Project Context

Stable facts about the project. Execution history belongs in EXECUTION_LOG.md;
the live state in CURRENT_STATE.md. Update this file only when a fact here changes.

## Objective
Video Factory (`contentos`) turns a topic or a script into a captioned, QA-checked MP4 entirely on this
Mac. Local-first: a Python CLI, no server, no account, no paid API. Two lanes exist (Track A template
pipeline, Track B agent-built HyperFrames composition) and human approval gates sit before voice and
before render.

## Product vision
An independent, complete local video platform. CEH (Creative Ecosystem Hub) is an optional extension, never
a dependency: the factory must work with CEH absent, disabled, empty or incompatible.

## Scope and non-goals
- In scope: research, script, voice, alignment, scenekit/HyperFrames composition, render, QA, preview,
  storage and export to the publishing library, plus the Studio UI and the ContentForge exchange worker.
- Non-goals: publishing (dry run only, `publish.enabled: false`, no uploader), paid providers or stock,
  multi-platform publishing, analytics ingestion, niche discovery, thumbnail images, Odia, OpenMontage
  (manual handoff, no adapter).

## Architecture
Pipeline stages are gated: `research -> script -> [SCRIPT_APPROVED] -> voice -> align -> compose -> lint ->
[PRODUCTION_APPROVED] -> render -> export`. Render lanes: `hyperframes` (default), `remotion`, `mpt`.
Export trust chain (as of `849ea6a`): ledger `renders` attestation (video sha + gate digests, written only
by the pipeline render stage, `track_b.render`, `contentos job register`) -> `export.approval_refusal`
checks attestation + digest-bound grants + unchanged content on every route. Canonical explanation:
`docs/HOW_IT_WORKS.md`.

## Technology stack
Python 3 (venv at `~/.contentos/venv`), pytest, PyYAML, numpy; Node for the ContentForge adapter
(`contentos/adapters/v1/*.test.mjs`, `node --test`); HyperFrames pinned at `0.8.114`; ffmpeg from
`/opt/homebrew/bin` (the `/usr/local/bin` one is x86_64 and unusable); whisper.cpp for ASR;
HyperFrames look/1 preset library in `config/presets/`.

## Repositories and key paths
| Path / repo | Role |
|---|---|
| `/Users/kishore/git/video-factory` | original checkout, `unplugged-kk/video-factory`, branch `feat/p1-1-lookmap`; leave it intact |
| `/Users/kishore/git/video-factory-phase2-foundation` | isolated Phase 2 continuation, `feat/phase2-foundation` |
| `~/.contentos/checkpoints/video-factory-phase2-20261124/` | checksummed Phase 1 backup plus Phase 2 local evidence |
| `/Users/kishore/git/video-factory-generic` | worktree on `feat/generic-video-system` (`4eababb`) |
| `/Users/kishore/.codex/worktrees/ceh-catalog-consumer/video-factory` | detached worktree at `36bb558` |
| `contentos/` | the package: pipeline, export, ledger, scenekit, lang, adapters, ui_state |
| `config/` | YAML config, `config/presets/` look/1 and effect presets - do not edit without the owner |
| `docs/audit/` | audits, gap register, P0 verification, independent security review, readiness report |
| `docs/project-intelligence/` | this execution baseline (created 2026-11-21) |
| `~/.contentos/exchange` | live queue/exchange root |
| `$VIDEO_FACTORY_WORKSPACE` | intermediates (default `~/Desktop/VideoFactory-Workspace`) |
| `$VIDEO_FACTORY_PUBLISH_DIR` | validated finals (default `~/Desktop/Video-Publishing`) |

## External dependencies
Optional only: CEH (decision B pending), ContentForge gateway, Ollama, MPT (docker), yt-dlp, YouTube Data
API + OAuth (publishing stays gated). None is required for the factory to run.

## Critical constraints
Never publish; never spend money; never edit `config/*.yaml`, the approval gates or the HyperFrames pin;
never write media into the repo (it refuses an in-repo workspace root on purpose); never touch git
history, `vendor/`, `.claude/skills/hyperframes-*` or `.state/claims/`; gates are hard stops keyed by
`content_id` alone, so a changed script needs a fresh approval.

## Canonical sources (do not duplicate here)
- `AGENTS.md` - the contract, gates, commands, non-negotiables.
- `README.md` - command reference and status table.
- `docs/CURRENT_STATE.md`, `docs/ROADMAP.md`, `docs/HOW_IT_WORKS.md`, `docs/AGENT_BRIEF.md`,
  `docs/STORAGE.md`, `docs/SKILLS_INVENTORY.md`, `docs/CAPABILITIES.md`.
- `docs/audit/MASTER_GAP_REGISTER.md` - authoritative status of every security finding.
- `docs/audit/PHASE_1_FINAL_READINESS_REPORT.md` - the current readiness verdict.
- `AGENT_HANDOVER.md` (repo root) and `SESSION_LOG.md` - the previous sessions' own narrative.
