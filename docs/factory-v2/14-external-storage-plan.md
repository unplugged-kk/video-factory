# External storage and publishing library: plan (Phase B)

Written 2026-10-11 after inspecting the repository. Final behaviour is documented in `docs/STORAGE.md`; this file records what was found and why the design looks as it does.

## 1. What exists today
- All generated work lives in the repo's `workspace/` (git-ignored): `projects/<content_id>/` (304 MB), `experiments/` (253 MB), `research/`, `factory-specs/`, and the SQLite ledger `workspace/ledger.db`. Nothing generated is tracked by Git.
- The repo root also holds legacy exchange-style folders (`output/ state/ thumbs/ done/ queue/ work/ failed/ building/ drafts/`), all git-ignored. Only `output/`, `state/`, `thumbs/` and `done/` have files (two old videos).
- The workspace path is hardcoded as `ROOT / "workspace"` in `ledger.py`, `pipeline.py`, `production/core.py`, `mpt.py`, `dashboard.py`, `learn.py`, `research.py`, `competitor.py`. The Node worker (`adapters/v1/factory_worker.mjs`) already honours `VIDEO_FACTORY_WORKSPACE`, but the Python side ignores it, so the two can disagree today.
- The job id is `content_id`. It keys the ledger, resume, gates, dashboard and the Node worker, so it stays the job id.
- Pipeline stages: `brief script voice compose render qa package publish`, each resumable through an artifact sentinel. The queue is the `jobs` table in the ledger; the ContentForge exchange folder (`~/.contentos/exchange`) is a separate data-only contract and is left alone.
- QA already runs ffprobe/ffmpeg (`qa.run_qa`): integrity, resolution, fps, duration, audio, loudness, black and frozen frames. Publish is a dry run.

## 2. Changes
1. `contentos/storage.py` (stdlib only): resolve and validate the workspace and publishing roots (env vars, then `config/storage.yaml`, then macOS defaults); never fall back to the repo; refuse roots inside the repo; job directories at `jobs/YYYY/MM/<job-id>/`; slug and job-id sanitising; atomic JSON writes; job manifest.
2. Route every hardcoded path through `storage`. Keep test seams (`ledger.WS`, `core.PROJECTS`, `mpt.PROJECTS`) working as optional overrides.
3. Add an `export` stage between `package` and `publish`: validate the final video, stage it in `Video-Publishing/.staging/`, promote atomically into `ready/`, write the sidecar last, record the result in the manifest.
4. `contentos/handoff.py`: what a scheduler needs (discover, claim, transition, archive) without touching factory state.
5. `contentos storage ...` CLI: `paths`, `inventory`, `migrate` (dry run by default), `export`, `ready`, `cleanup` (dry run by default), `recover`.
6. Node worker: same default workspace and job-directory lookup, so the two sides agree.
7. Docs: `docs/STORAGE.md`, README link, `AGENT_BRIEF.md` and `HOW_IT_WORKS.md` updates.

## 3. Decisions
- Job id equals the existing `content_id`. A project (series) and a content slug are optional new spec fields (`project`, `project_name`, `content`); the content slug defaults to the slugified title.
- The files inside a job directory keep their current names (`audio/`, `project/` for the HyperFrames composition, `video.mp4`, `qa.json`, `metadata.yaml`), because resume sentinels, the Node worker and the mpt container depend on them. The requested sub-folders are used only where they fit; no empty folders are created.
- The sidecar `*.publish.json` is promoted last, so a video without a sidecar is never treated as ready.
- Scheduler state is separate from generation state (`.state/claims/`); the factory never rewrites a sidecar after export.
- Cleanup and migration never delete or move originals; both are dry runs unless `--apply` is given.

## 4. Risks
- The mpt container mounts the project folder; the mount path must change to the new jobs root (not testable without Docker here).
- Python and Node must agree on the workspace; both read `VIDEO_FACTORY_WORKSPACE` and share one default.
- Moving the SQLite ledger needs a consistent copy (SQLite backup API, not a file copy while in use).
- Legacy projects with their own `manifest.json` (Pilot 001) must not be overwritten.
- The environment here is a Linux VM, not the Mac, so the macOS default path cannot be exercised directly; tests and the end-to-end run use explicit overrides.

## 5. Acceptance tests
Path resolution and validation; unwritable and missing directories; job isolation; slug and traversal safety; concurrent and duplicate exports; failed render and failed validation never reach `ready/`; partial copy cleanup; atomic promotion; manifest and sidecar consistency; retry and recovery; legacy compatibility; retention dry run; Git cleanliness with generated media present; scheduler discovery and duplicate claim; an end-to-end pipeline run against a temporary workspace and publishing directory.

## Status (implementation)
Implemented as planned. See `docs/STORAGE.md` for the operating guide. Not exercised on a Mac with real Kokoro/Chrome from the build VM; mpt Docker mount change untested (needs container recreate).
