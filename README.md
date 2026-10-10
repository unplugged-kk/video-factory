# video-factory / contentos

Local-first YouTube content pipeline for an Apple Silicon Mac. Thin Python CLI that routes work to
tools you already have (hyperframes, ffmpeg, Kokoro, whisper.cpp, the `yt-*` Agent Skills), records
every stage in a SQLite ledger, and refuses to publish without a gate.

**New here, or an agent?** Read [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) for how the factory works end to end, then [docs/AGENT_BRIEF.md](docs/AGENT_BRIEF.md) for the rules.

```bash
./scripts/bootstrap-mac.sh                      # idempotent installs + doctor
./contentos.sh doctor                           # PASS / NOT_INSTALLED / OPTIONAL per provider, with fix commands
./contentos.sh route tts                        # which provider wins, and why (local-first policy)
./contentos.sh pipeline run examples/youtube-short.yaml --approve-private
./contentos.sh qa "$VIDEO_FACTORY_WORKSPACE"/jobs/YYYY/MM/<id>/video.mp4
./contentos.sh status                           # recent ledger rows
./contentos.sh jev status | jev triage "topic"  # decision layer
./contentos.sh recommend <content_id>           # PUBLISH/HOLD/REVISE/ABANDON with reasons
./contentos.sh research "topic"                # last30days dossier (Reddit+HN keyless)
./contentos.sh competitor <youtube-url...>      # teardown of public videos via agent-reach
./contentos.sh queue add specs/*.yaml --approve-private   # batch; omit flag to park jobs at the gate
./contentos.sh worker --concurrency 2 [--once]            # runs queued jobs; queue list / requeue <id>
./contentos.sh learn providers|cost|calibration|platforms|packaging
docker compose up -d                           # container side: MoneyPrinterTurbo (UI :8501, API :8081) + OpenMontage Backlot (:4750)
~/.contentos/venv/bin/python -m pytest tests    # 15 tests
```

Pipeline: `brief > script > voice > compose > render > qa > package > export > publish`. Each stage writes an
artifact under `$VIDEO_FACTORY_WORKSPACE/jobs/YYYY/MM/<content_id>/` (outside the repo; default `~/Desktop/VideoFactory-Workspace`; the `export` stage copies validated finals to `~/Desktop/Video-Publishing/ready/`, see [docs/STORAGE.md](docs/STORAGE.md)) and resumes (skips) if it exists. A failed stage
deletes its own artifact so resume never trusts half-built output.

## Render lanes
`render:` in a spec picks the lane. The script, voice, gates and QA are always contentos'; a lane only makes the picture.

| `render:` | Use for | Needs |
|---|---|---|
| `hyperframes` (default) | text/data explainers, branded word-highlight captions, fully local | nothing |
| `mpt` | faceless shorts that need real b-roll: MoneyPrinterTurbo sources free stock clips, cuts them to OUR Kokoro voice, burns subtitles | `docker compose up -d`; a free Pexels/Pixabay/Coverr key in `vendor/MoneyPrinterTurbo/config.toml`, or `mpt.source: local` |
| OpenMontage | cinematic, animated, long-form, avatars | agent-driven, not an API: not wired. Hand off by hand, then `pipeline run <spec> --only qa` on a `video.mp4` placed in the project dir |

`mpt` details: `compose` writes a reviewable `project/mpt-request.json` (the render gate reviews it); `render` runs MPT's CLI inside its container,
copies `final-1.mp4` to `video.mp4` and writes `assets-rights.json`. Paid MPT sources and background music are never passed. Add `broll:` to script lines
for stock-search phrases. See `examples/mpt-black-holes.yaml`.

## ContentForge exchange (v1 worker)
`./contentos.sh factory-worker` runs the production jobs ContentForge drops into a shared folder. That folder is the **exchange root**:
data only (`building queue work done failed output state`), default `~/.contentos/exchange`, set with `VIDEO_FACTORY_ROOT`. ContentForge mounts
that folder and nothing else; never point it at this repo (the worker refuses). Everything in it is untrusted input: the job id comes from the
folder and file names, symlinks are ignored, the derived spec is written to `workspace/factory-specs/`, and state and manifest carry no host paths.

    VIDEO_FACTORY_DASHBOARD_HOST=<tailscale address> ./contentos.sh factory-worker

The readiness `manifest.json` is served on `VIDEO_FACTORY_DASHBOARD_HOST:4300` (`--host`, `--port`; default `127.0.0.1`; `0.0.0.0` is refused). If the
address is not up yet (Tailscale down) the worker keeps rendering and retries the bind; ContentForge reads "not ready" meanwhile. Tests: `node --test contentos/adapters/v1/*.test.mjs`.

**What a healthy worker is, and what happens when it is not.** Each job runs as a child process group (`contentos production run`), so the worker keeps
answering readiness while a render runs. It writes a heartbeat every 10 s to `workspace/.factory_worker.heartbeat` (outside the exchange root, since the
producer can write there); `manifest.json` carries a `worker` block (pid, heartbeatAt, queueDepth, activeJob). Healthy means the process is alive and the
heartbeat is under 60 s old.

- One worker per workspace: a second start refuses (exit 3) while a live worker's heartbeat is in the file. Stop the worker before running `verify-slice`.
- After a crash or `kill -9`, the next start stops the pipeline the dead worker left running, then resumes what is in `work/`; finished stages are skipped
  and artifacts the ledger never recorded as OK are redone. Each takeover counts (`reclaimCount` in the state file); after 3 the job is failed (`reclaim_limit`).
- A claim in `work/` that nobody works on for 600 s goes back to `queue/`.
- SIGTERM or Ctrl-C stops the pipeline and leaves the job in `work/` for the next start; the heartbeat file is removed.
- The core retries a failed voice, compose or render stage twice (after 15 s and 45 s, inside a 360 s cap); QA failures and blocked gates are not retried.
  ContentForge sees `rendering` until that is over. A hung tool is killed after 600 s (render 1800 s), a hung job after 45 minutes.

Settings for tests and unusual layouts: `VIDEO_FACTORY_WORKSPACE`, `VIDEO_FACTORY_CONTENTOS`, `VIDEO_FACTORY_POLL_MS`, `VIDEO_FACTORY_HEARTBEAT_MS`,
`VIDEO_FACTORY_STALE_MS`, `VIDEO_FACTORY_JOB_TIMEOUT_MS`.

## Storage rules for every agent
- Producing or auditing a whole video: use the `video-production-orchestrator` skill (`.claude/skills/video-production-orchestrator/`). It sets the order of phases, the two background rules (`python -m contentos.intelligence.visual ...`) and technique lookup (`python -m contentos.intelligence.catalogue query ...`). Design and known failures: `docs/video-intelligence/`.
- Generated files (audio, images, scenes, renders, caches, logs) live **outside Git**, in `$VIDEO_FACTORY_WORKSPACE` (default `~/Desktop/VideoFactory-Workspace`), one folder per job: `jobs/YYYY/MM/<job-id>/`. Never write them into the repo and never `git add` media.
- Only validated finals go to the publishing library `$VIDEO_FACTORY_PUBLISH_DIR` (default `~/Desktop/Video-Publishing`) via the pipeline `export` stage or `./contentos.sh storage export <job-id>`. Output: `ready/<project>/YYYY/MM/<content>__<job>.mp4` plus a `.publish.json` sidecar. Failed or unvalidated videos are never exported.
- Optional spec fields that feed the sidecar (never guessed if absent): `project`, `project_name`, `content`, `topic`, `description`, `tags`, `platform_targets`, `language`, `kind` (short|long), `require_audio`.
- If a configured folder is missing or unwritable, stop and report it. Do not fall back to the repo, and never delete files to free space (`storage cleanup` is dry-run unless the owner passes `--apply`).
- Schedulers read `ready/`, claim with `python -m contentos.handoff claim`, and own `.state/claims/`; agents do not edit sidecars or claim files.
- Full guide: [docs/STORAGE.md](docs/STORAGE.md). Check setup with `./contentos.sh storage paths --check`.

## Status (measured 2026-10-03, M5 Pro, 24 GB)

| Piece | State |
|---|---|
| yt-* skills (11) | installed in `~/.claude/skills`, hookscore.py + title.py verified |
| Kokoro TTS | live, ~3.6 s per short line warm |
| hyperframes render | live, 24 s 1080x1920 video in 9.8 s |
| QA (ffprobe/ffmpeg) | live: resolution, fps, duration, audio, loudness, clipping, black, frozen |
| Provider routing + paid block | live, tested |
| Approval gates | live: voice needs SCRIPT_APPROVED, render needs PRODUCTION_APPROVED |
| Publish | DRY_RUN only. Disabled in `config/youtube.yaml`; upload adapter not written; no OAuth |
| LLM | none local. Script text is supplied in the spec. ContentForge gateway is the planned path |
| Jev adapter | built (`contentos jev status|triage`), fails open to `watch`. ContentForge at localhost:3000 answers 401: needs `CONTENTFORGE_COOKIE` from a logged-in session. Verified against a stub server only, not the real engine |
| Learning loops | built, read-only, thin data reports `insufficient_data`: providers, cost, calibration, opportunity ranking, packaging/platform (need ingested metrics), `recommend` (PUBLISH/HOLD/REVISE/ABANDON, publish stays gated) |
| MPT lane | live for `mpt.source: local` (full pipeline, QA all PASS, resumes, shows on the dashboard). Pexels/Pixabay/Coverr wired but UNTESTED: no key set, so the per-clip rights record is unverified |
| OpenMontage | running in Dory (Backlot :4750), no contentos adapter; manual handoff only |
| Captions | word-highlight captions from whisper.cpp timings (warm 2.9 s per 27 s audio, WER 1.4% on synthetic speech) |
| Niche discovery, analytics, multi-platform, thumbnails, n8n | planned, not built |

## Known problems
- hyperframes is pinned in `package.json` (0.8.114, lockfile committed). Unpinned `npx --no-install hyperframes` broke on 2026-10-03 when upstream published 0.8.115 and only 0.8.114 was cached (doctor said NOT_INSTALLED, renders failed). Upgrade on purpose: `npm install hyperframes@<version>`, run the tests and one render.
- `/usr/local/bin/ffmpeg` and `timeout` are x86_64 and die with "bad CPU type" (no Rosetta). `contentos.sh` puts `/opt/homebrew/bin` first. Remove the stale ones when convenient.
- Template now has word captions but is still minimal (no brand styling, B-roll or thumbnails).
- `frozen_frames` is a WARN on text slides; expected, tune in `config/quality.yaml`.
- Old chatterbox voice-clone venv (`~/.voice-clone-venv`) and `~/Desktop/voice-sample.wav` are missing.

Details: [docs/report.md](docs/report.md). Catalog: [research/tool-catalog.yaml](research/tool-catalog.yaml). Capability graph: [registry/capabilities.yaml](registry/capabilities.yaml).
