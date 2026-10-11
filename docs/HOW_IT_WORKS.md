# How the video factory works (and how an agent uses it)

Status as of 2026-10-11. This is a guide to what exists today, including what is automated, what is still manual, and what is only planned. The short command reference is in [`README.md`](../README.md); the rules an agent must obey are in [`AGENT_BRIEF.md`](AGENT_BRIEF.md).

## 1. What it is, in one minute
A local-first video factory for an Apple Silicon Mac. You give it a topic (or a ready script) and it produces a captioned MP4 with a Kokoro voice-over, rendered by HyperFrames (HTML/GSAP to video), and checks the result with automated QA. Every stage is recorded in a SQLite ledger, human approval gates sit before voice and render, and publishing is disabled (dry run only). Nothing costs money by default.

The parts:

| Part | What it does | Where |
|---|---|---|
| ContentOS (`contentos`) | Python CLI: stage engine, ledger, gates, queue, worker | `contentos/`, entry point `./contentos.sh` |
| HyperFrames 0.8.114 | Turns an HTML/GSAP composition into MP4 (pinned in `package.json`) | `node_modules/`, run via `npx --no-install hyperframes` |
| Kokoro TTS | Local English voice (`af_heart` etc.), via `hyperframes tts` | `config/providers.yaml` |
| whisper.cpp | Word timings for captions and alignment | via `hyperframes transcribe` |
| ffmpeg / ffprobe | Rendering support and QA measurements | `/opt/homebrew/bin` must come first |
| Skills | Instructions an agent reads before doing a kind of work | `.claude/skills/` |
| Capability registry | The list of techniques an agent may choose from | `config/capabilities.json` |
| Platform limits | Maximum lengths and formats per platform | `config/platforms.json` |

## 2. Two ways to make a video
There are two tracks. They share the voice, QA and gates but differ in how much creative direction goes in.

**Track A: the template pipeline (fully automated).** You write a spec YAML (title, script lines with on-screen headlines). `contentos pipeline run` produces the video: one scene per script line on a minimal template with word-highlight captions. Good for quick text/data shorts. This is what the worker and queue run.

**Track B: the director-led explainer (agent-planned, partly manual).** The `video-director` skill plans the video (audience, takeaway, hook, scenes, chosen techniques, 16:9 and 9:16 notes) into a validated `sceneplan/1` file. A builder (an agent or script) then writes a custom HyperFrames composition from that plan, renders it, and the QA and visual-critic tools check it. Pilot 001 was made this way, with a hand-written build script in its `src/` folder. **The ContentOS builder does not read scene plans yet**; that integration is a planned milestone, so Track B's composition step is done by the agent with the HyperFrames skills.

| | Track A | Track B |
|---|---|---|
| Input | spec YAML | topic, then plan, script, composition |
| Look | template, captions | custom diagrams and motion |
| Planning | none (you supply the script) | `video-director` + validator |
| Status | working end to end | planning/validation built; builder integration not built |

## 3. Track A, stage by stage
`brief > script > voice > compose > render > qa > package > export > publish`, each stage writing an artifact to `$VIDEO_FACTORY_WORKSPACE/jobs/YYYY/MM/<content_id>/` (outside the repo; finals go to `$VIDEO_FACTORY_PUBLISH_DIR/ready/` via the `export` stage, see [STORAGE.md](STORAGE.md)). If the artifact exists the stage is skipped on the next run; a failed stage deletes its own artifact so a resume never trusts half-built output.

| Stage | What happens | Gate |
|---|---|---|
| brief | records the spec and sources | RESEARCH_APPROVED |
| script | stores the script from the spec (no local LLM yet) | SCRIPT_APPROVED |
| voice | Kokoro speaks each line to a WAV | needs SCRIPT_APPROVED |
| compose | builds a HyperFrames project: scenes timed to the audio, captions from whisper word timings, then lints it | |
| render | HyperFrames renders `video.mp4` | needs PRODUCTION_APPROVED |
| qa | ffprobe/ffmpeg checks: resolution, fps, duration, audio, loudness, clipping, black and frozen frames | |
| package | title, description, tags, thumbnail text files | |
| publish | **dry run only**: needs PUBLISH_APPROVED and `config/youtube.yaml` has `publish.enabled: false`; no uploader exists | |

Failed voice, compose or render stages are retried twice (after 15 s and 45 s); QA failures and blocked gates are not retried. The `mpt` render lane replaces the picture with stock footage from MoneyPrinterTurbo (needs Docker and a free stock key, or local clips); the OpenMontage lane is a manual handoff only.

## 4. Track B, step by step (how an agent makes a planned explainer)
1. **Check the toolchain.** `./contentos.sh doctor`. Stop if something the plan needs is NOT_INSTALLED.
2. **Get the length budget.** Short-form or long-form is your choice; the factory knows the limits:
   `python -m contentos.production.platforms budget --kind short`.
3. **Research (optional) and verify.** `./contentos.sh research "<topic>"`. Every claim needs a source; unverifiable claims stay out of the video or are labelled.
4. **Plan with the `video-director` skill** (`.claude/skills/video-director/SKILL.md`). It writes, into one experiment folder: `brief.md`, `script.txt`, `storyboard.md`, `scene-plan.json`, `decision-log.md`, a capability report and validation output. Scenes are anchored to narration words, not seconds, and may only use techniques that exist in `config/capabilities.json`.
5. **Validate the plan** (read-only, nothing is rendered):
   ```
   python -m contentos.production.direction validate PLAN.json
   python -m contentos.production.director check PLAN.json --script SCRIPT.txt --kind short
   ```
   `check` runs the registry validator, story coherence rules (hook first, recap or call to action last, not every scene animated), anchor checks (every scene start and cue phrase must be in the script) and the platform length budget.
6. **Approve the script (gate 1).** A human grants SCRIPT_APPROVED: `./contentos.sh approve <content_id> SCRIPT_APPROVED`.
7. **Voice and word timings.** Kokoro voice-over, then whisper timings aligned to the script (`contentos/production/align.py` keeps the script's own spelling and reports a word error rate).
8. **Resolve the plan to real times.** `sceneplan.resolve()` turns word anchors into seconds from the aligned audio, so one plan drives both 16:9 and 9:16.
9. **Compose.** Build a HyperFrames composition (one paused, seek-safe GSAP timeline) following `hyperframes-core` and `explainer-motion-craft`. Lint it with the HyperFrames CLI.
10. **Approve production (gate 2).** PRODUCTION_APPROVED, then render each aspect ratio.
11. **QA.** `./contentos.sh qa video.mp4` for the numbers; `./contentos.sh preview <video> --at 2,10,30 --out DIR --sheet` for contact sheets; then the `explainer-visual-qa` skill, where a **separate** reviewer scores the frames (`contentos/production/critic.py` checks the report and computes the verdict so a builder cannot grade itself).
12. **Report.** Video path, QA table, open risks, claims still to verify. Publishing stays off.

## 5. The agent toolkit
- **Skills** (`.claude/skills/`)
  - `video-production-orchestrator`: runs a whole video end to end, or audits a finished one — the phase order (P0-P11), the two background rules and the gates. Start here for any complete video (this repo's own).
  - `video-director`: planning (this repo's own).
  - `explainer-motion-craft`: the house motion rules R1 to R6 (smooth settle with no bounce, reveal on the spoken cue, one camera move per scene, no ambient motion, safe zones, short statements at about 2.5 words per second). Authoritative for motion.
  - `explainer-visual-qa`: post-render review.
  - `hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes`: pinned upstream HyperFrames skills. They are not committed; `python scripts/upstream_skills.py sync` restores them from `config/upstream-skills.lock.json`.
- **Precedence when guidance conflicts:** the user's brief, then `hyperframes-core`, then `explainer-motion-craft`, then `video-director` and `video-production-orchestrator` (same level; the orchestrator places `video-director` first, planning before execution), then upstream animation skills, then `references/motion-intent.md` (advisory), with `explainer-visual-qa` applied after rendering.
- **Capability registry** (`config/capabilities.json`): 93 entries, each `installed`, `available` (needs an opt-in), `candidate` (experimental only, for example p5.brush) or `unavailable` (for example the vibe filters). "Installed" means the file is present and lock-verified, not that it has been render-tested. An agent may name only ids that are in this file; `director.select_capability` picks the simplest usable one and records any substitution.
- **Platform limits** (`config/platforms.json`): see section 6.

## 6. Short-form, long-form and platforms
Tell the agent "make a short" or "make a long video" and it takes its length from the platform registry instead of guessing.

Owner policy: short-form never exceeds 5 minutes (hard ceiling), targets at most 3 minutes by default, and shorter is fine. Long-form has no ceiling set yet.

| Platform | Short-form limit | Long-form | Confidence |
|---|---|---|---|
| YouTube | Shorts 3 min | 15 min default, longer once verified | official |
| Instagram | Reels 3 min safe limit | not recorded | partly official |
| X | 140 s | up to 4 h but only with paid Premium (off by default) | mostly official |
| Threads | 5 min | none | official |
| LinkedIn | about 10 min | about 10 min | third-party only |
| TikTok | 3 or 10 min (sources disagree) | n/a | conflicting; blocked in India, so off by default |

A 3-minute master fits YouTube Shorts, Instagram, Threads and LinkedIn but not X (cut an X version of 140 s or less). A 5-minute master fits only Threads and LinkedIn. Not yet researched: Facebook Reels, Snapchat and the Indian apps (Moj, Josh, ShareChat). Limits change; see [`factory-v2/13-platform-limits.md`](factory-v2/13-platform-limits.md) for sources and re-check anything not marked official.

Check commands: `platforms list | budget | check`, with `--platforms`, `--tier youtube=verified`, `--opt-in x`, `--ceiling SECONDS`.

## 7. Running things
```
./contentos.sh doctor                                   # what is installed
./contentos.sh pipeline run SPEC.yaml                   # stops at the gates
./contentos.sh approve <content_id> SCRIPT_APPROVED     # grant a gate (PRODUCTION_APPROVED the same way)
./contentos.sh pipeline run SPEC.yaml --approve-private # grants research, script, production gates; never publish
./contentos.sh qa "$VIDEO_FACTORY_WORKSPACE"/jobs/YYYY/MM/<id>/video.mp4
./contentos.sh preview VIDEO --at 2,10,30 --out DIR --sheet
./contentos.sh queue add specs/*.yaml                   # batch; add --approve-private to skip parking
./contentos.sh worker --concurrency 2                   # runs the queue (--once drains and exits)
./contentos.sh factory-worker                           # ContentForge exchange (README has details)
./contentos.sh status                                   # recent ledger rows
```
Tests: `~/.contentos/venv/bin/python -m pytest tests` (Python 3.12 or later). One known failure exists, `test_core.py::test_local_beats_paid_even_when_both_healthy`, unrelated to the director work and not yet investigated.

## 8. Where things live
```
config/            capabilities.json, platforms.json, providers.yaml, quality.yaml, youtube.yaml, policies
contentos/         CLI, pipeline.py (stages), ledger, queue, QA, worker adapters
contentos/production/  sceneplan, align, direction (validator), director, platforms, critic, motion_audit, preview,
                       sheet (labelled sheets, sheet/1, shadow), timeline (timeline/1, shadow), visual_gate (rendered-frame gate), core (retries)
.claude/skills/    video-production-orchestrator, video-director, explainer-* (pinned hyperframes-* are generated)
docs/              this guide, AGENT_BRIEF.md, factory-v2/ (audits, reports)
examples/          sample specs
~/Desktop/VideoFactory-Workspace   ALL generated work (outside the repo, VIDEO_FACTORY_WORKSPACE)
~/Desktop/Video-Publishing         validated finals + sidecars for schedulers (VIDEO_FACTORY_PUBLISH_DIR)
workspace/         legacy in-repo artifacts (git-ignored; migrate with `contentos storage migrate`)
```
A project folder (for example Pilot 001) holds `script/`, `audio/`, `captions/`, `storyboard/`, `landscape/` and `portrait/` compositions, `renders/`, `qa/`, `delivery/` and `manifest.json`. A dry-run planning folder holds only text artifacts.

## Storage rules for every agent
- Producing or auditing a whole video: use the `video-production-orchestrator` skill (`.claude/skills/video-production-orchestrator/`). It sets the order of phases, the two background rules (`python -m contentos.intelligence.visual ...`) and technique lookup (`python -m contentos.intelligence.catalogue query ...`). Design and known failures: `docs/video-intelligence/`.
- Generated files (audio, images, scenes, renders, caches, logs) live **outside Git**, in `$VIDEO_FACTORY_WORKSPACE` (default `~/Desktop/VideoFactory-Workspace`), one folder per job: `jobs/YYYY/MM/<job-id>/`. Never write them into the repo and never `git add` media.
- Only validated finals go to the publishing library `$VIDEO_FACTORY_PUBLISH_DIR` (default `~/Desktop/Video-Publishing`) via the pipeline `export` stage or `./contentos.sh storage export <job-id>`. Output: `ready/<project>/YYYY/MM/<content>__<job>.mp4` plus a `.publish.json` sidecar. Failed or unvalidated videos are never exported.
- Optional spec fields that feed the sidecar (never guessed if absent): `project`, `project_name`, `content`, `topic`, `description`, `tags`, `platform_targets`, `language`, `kind` (short|long), `require_audio`.
- If a configured folder is missing or unwritable, stop and report it. Do not fall back to the repo, and never delete files to free space (`storage cleanup` is dry-run unless the owner passes `--apply`).
- Schedulers read `ready/`, claim with `python -m contentos.handoff claim`, and own `.state/claims/`; agents do not edit sidecars or claim files.
- Full guide: [STORAGE.md](STORAGE.md). Check setup with `./contentos.sh storage paths --check`.

## 9. Safety rules (the short list)
No public upload and no paid service without explicit approval; do not change gates, `config/*.yaml` or the pinned HyperFrames version unless asked; do not invent facts; label illustrative data; English only for now; third-party audio or footage needs a rights decision; stay inside this repo and `~/.contentos`; never print secrets. Details in `AGENT_BRIEF.md`.

## 10. What is built and what is not
Working: the Track A pipeline, Kokoro voice, whisper captions, HyperFrames render, QA, gates, ledger, queue and worker, ContentForge exchange, the capability registry and validator, the director check, platform limits, the contact-sheet and critic tools.
New and in shadow mode: `production/sheet.py` (timeline-labelled contact sheets, `sheet/1`) and `production/timeline.py` (`timeline/1`). Nothing imports the timeline yet, and the labelled sheet needs an ffmpeg built with `drawtext`: the `/opt/homebrew` build on this Mac has no freetype, so there it fails closed and the plain `preview --sheet` is the fallback. `--allow-unlabelled` produces an unlabelled sheet, which is not the same artifact; the labelled path enters the QA workflow only after a labelled sheet has been generated on this Mac and its labels inspected. Nothing invokes the timeline: `visual_gate captions --timing` reads scenes with `start`/`end`, so a `timeline/1` file (`t0`/`t1`) yields no windows and a misleading `visible_ratio: 0.0`. `visual scenes --timing` is the tool that does accept `t0`.
Built but not wired into the builder: scene-plan consumption (Track B composition is agent-built).
Tested only as a dry run: the `video-director` plan for "What Happens When an AI Agent Uses a Tool?" (`workspace/experiments/m2-director-dryrun-001/`, not rendered).
Not built: a YouTube uploader and OAuth, multi-platform publishing, niche discovery, analytics ingestion, thumbnails, Odia/Hindi voices, automatic skill triggering tests.

## 11. Recommended next steps
1. M3: build the dry-run plan for real (voice, alignment, composition, lint, two renders, visual QA) to test legibility and cue timing.
2. Wire scene plans into the ContentOS builder only after M3 succeeds.
3. Research the remaining platforms and decide long-form length.
4. Decide on a publishing adapter per platform behind the existing gate.
