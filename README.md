# video-factory / contentos

Local-first YouTube content pipeline for an Apple Silicon Mac. Thin Python CLI that routes work to
tools you already have (hyperframes, ffmpeg, Kokoro, whisper.cpp, the `yt-*` Agent Skills), records
every stage in a SQLite ledger, and refuses to publish without a gate.

```bash
./scripts/bootstrap-mac.sh                      # idempotent installs + doctor
./contentos.sh doctor                           # PASS / NOT_INSTALLED / OPTIONAL per provider, with fix commands
./contentos.sh route tts                        # which provider wins, and why (local-first policy)
./contentos.sh pipeline run examples/youtube-short.yaml --approve-private
./contentos.sh qa workspace/projects/<id>/video.mp4
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

Pipeline: `brief > script > voice > compose > render > qa > package > publish`. Each stage writes an
artifact under `workspace/projects/<content_id>/` and resumes (skips) if it exists. A failed stage
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
