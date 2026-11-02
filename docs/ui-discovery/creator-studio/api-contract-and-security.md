# API contract and security

Status labels: Existing, Adapter, Backend change, Out of scope. All routes are under `/api/v1` except the current read-only routes, which stay until the Jobs screen replaces them. Errors use `{"error":{"code","message","field?"}}`.

| Operation | Route | Status | Calls |
|---|---|---|---|
| Health | `GET /health` | Backend change | `providers.candidates`, storage preflight, FFmpeg runnable check |
| List and read jobs | `GET /jobs`, `GET /jobs/{id}` | Adapter | Ledger `runs`, approvals, manifest, `qa.json` |
| Validate spec | `POST /specs/validate` | Backend change | New `validate_spec`, reusing id checks and script lint |
| Create spec | `POST /specs` | Backend change | Writes `<workspace>/specs/<content_id>.yaml` |
| Run or resume | `POST /jobs/{id}/run` | Adapter | `./contentos.sh production run SPEC` with no `--approve-private` |
| Stage history | Included in job detail | Existing data | Ledger rows for the spec `content_id` |
| Stage log | `GET /jobs/{id}/stages/{stage}/log` | Backend change | New `<job>/logs/<stage>.log` capture |
| Approve | `POST /jobs/{id}/approve` | Adapter | Same digest and `ledger.approve` path as `cmd_approve` |
| Media | `GET /media/{id}/{file}` | Existing, needs streaming | Current whitelist. Stream instead of `read_bytes` |
| Preview | `POST /jobs/{id}/preview` | Adapter | Existing `preview` command, output in the workspace |
| Queue | `GET /queue`, `POST /queue`, `POST /queue/{id}/requeue` | Implemented | Queue rows and saved-spec entries. The worker runs `production run`, defaults to concurrency 1, and stops a timed-out process group. The UI does not start the worker. |
| Export preview and export | `GET /jobs/{id}/export`, `POST /jobs/{id}/export` | Implemented | `export.export_job`. POST requires `confirm: true` and rejects a caller-selected path. |
| One-stage rerun | `GET /jobs/{id}/rerun`, `POST /jobs/{id}/rerun` | Implemented | Preview plus `pipeline run --only STAGE --force`, downstream sentinel removal, and approval revocation. |
| QA rerun | `POST /jobs/{id}/qa` | Implemented | Existing `run_qa` against the job-local video. |
| Progress | `GET /jobs/{id}/events` | Implemented | Server-sent invalidation hints. The client refetches canonical job state and falls back to polling. |

Out of scope: publish, `PUBLISH_APPROVED`, `--allow-paid`, cancel, persisted reject, ContentForge submission, Remotion and MPT selection, and any request that accepts a raw filesystem path.

## Run contract

A full run or resume returns 202 and starts one subprocess. The process result is the JSON line `{ok, failureClass, stage, error, attempts, elapsedS}` when core returns normally. A non-zero exit with no JSON line, including a held lock, storage preflight failure, or invalid lane, becomes a process error. It must not be parsed from a traceback.

`POST /jobs/{id}/run` rejects `only` and `force`. One-stage rerun is a separate confirmed route. It runs `pipeline run --only STAGE --force`, deletes later sentinels inside the job directory, and revokes `SCRIPT_APPROVED` or `PRODUCTION_APPROVED` only when the selected stage can change that reviewed artifact. Publish is not rerunnable from Creator Studio.

Progress events are invalidation hints, not a second job model. On each hint, disconnect, or unsupported browser, the client reads `GET /jobs/{id}` again. Polling continues every 2 seconds while the overview is open.

## Approval contract

`SCRIPT_APPROVED` and `PRODUCTION_APPROVED` are the only gates the UI can grant. The request includes the digest shown to the owner. The server recomputes `script_digest` or `production_digest` and returns 409 `digest_changed` when they differ. `PUBLISH_APPROVED` returns 403.

Track A run and rerun do not call `s_voice` or `s_render` directly. Those stages stay inside `production run` and `pipeline run`, and their gate checks live in `pipeline._stages`.

## Track B contract

Track B routes accept only a job id. The server resolves it with `storage.find_job_dir` and rejects a caller-supplied path, `allowPaid`, `approvePrivate`, and `publish`.

- `POST /api/v1/jobs/{id}/track-b/intake` records a Track B manifest when the job directory contains `project/index.html` and a spoken script. A video is not required. An existing Track A manifest is refused.
- `POST /api/v1/jobs/{id}/track-b/register` adopts a finished `video.mp4`. External ledger rows are written for stages this studio did not already complete. A present video does not mark render or either gate successful.
- `POST /api/v1/jobs/{id}/track-b/voice` requires `SCRIPT_APPROVED` for the current script digest, then calls Kokoro. `align` writes `timing.json` from the takes already in the job.
- `POST /api/v1/jobs/{id}/track-b/render` requires `PRODUCTION_APPROVED` for the current production digest, then calls the HyperFrames renderer. It does not rebuild `project/index.html`.
- `POST /api/v1/jobs/{id}/track-b/qa` stores technical QA, visual plan, visual check, and rendered-scene results separately. The critic result is read from an existing report. Missing checks stay `NOT_RUN`. A changed composition marks a stored visual report `STALE`.

`POST /jobs/{id}/run`, one-stage rerun, and queue add return 409 `TRACK_B_JOB` for a Track B manifest. Export still requires both grants. The CLI `job register` command is unchanged.

## Security boundary

- Bind `127.0.0.1` only.
- Check `Host` against `127.0.0.1:<port>` and `localhost:<port>`.
- Require a per-start token on every state-changing request. Do not use a cookie for this local boundary.
- Check `Origin` on writes.
- Validate job ids with `storage.valid_job_id`.
- Resolve artifact paths and require them to stay inside the job directory. Serve only the existing filename whitelist.
- Parse spec YAML with `yaml.safe_load`, cap its size, and reject unknown keys.
- Run `storage.scrub` on logs before sending them. Never return environment values or secret file contents.
- Start children in a new session and record pid plus start time so a later cancel, when one exists, cannot signal a reused pid.
- On startup, recover only jobs this server owns. Do not auto-resume work.

## Known risks to preserve in tests

- `scrub_interrupted` currently runs before the per-job lock. The server must refuse a second run before cleanup starts.
- Queue recovery records the worker pid, so a UI-owned child needs its own pid record.
- Factory-worker `findJobDir` does not use the day folder. The Studio uses `storage.find_job_dir` and does not call that worker.
- Changing only the bind address does not make this boundary safe on a VPS.

## Compatibility

The URL version accepts additive fields. Removing or renaming a field requires `/api/v2`. CLI commands, their text, and their exit codes stay stable. The API is an additional caller of the same functions.
