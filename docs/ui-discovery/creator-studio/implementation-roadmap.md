# Implementation roadmap

Each milestone is independently reviewable. The CLI remains usable after every step. No milestone installs a package unless `owner-decisions.md` records approval for that package.

## M0 Test baseline

- Scope: catch `OSError` in `sheet._drawtext_available` and add a regression test. No UI.
- Dependencies: none. A green full suite also needs the owner to install arm64 FFmpeg and whisper.cpp.
- Likely files: `contentos/production/sheet.py`, `tests/test_sheet.py`.
- Tests: collection succeeds when FFmpeg is a dead binary.
- Acceptance: pytest collects. Remaining failures are reported individually and are not hidden by the collection crash.
- Risk: low. Rollback by reverting the guard.

## M1 Health

- Scope: `contentos/ui/` server, loopback bind, token and Host checks, `GET /api/v1/health`, and the Health screen.
- Dependencies: M0.
- Likely files: `contentos/dashboard.py`, `contentos/ui/*`, `tests/test_ui_api.py`.
- Tests: AC-G1 through AC-G5 and AC-H1 through AC-H4.
- Acceptance: the existing `./contentos.sh dashboard` still serves.
- Risk: a new local port surface. Rollback by leaving the old dashboard untouched.

## M2 Create and validate

- Scope: `validate_spec`, `contentos validate SPEC --json`, and the New Job wizard.
- Dependencies: M1.
- Likely files: a validation module beside the pipeline, `contentos/cli.py`, wizard modules.
- Tests: AC-C1 through AC-C5, including rejection of 1:1, empty script, bad id, and unknown lane.
- Acceptance: an invalid spec cannot be run.
- Risk: a second copy of the Kokoro voice list. Read the adapter allowlist or move it once. Do not fork it.
- Rollback: remove the endpoints.

## M3 Run, observe, and logs

- Scope: per-stage log capture, a subprocess supervisor for `production run`, Jobs, Overview, and Logs.
- Dependencies: M2.
- Likely files: `contentos/pipeline.py` `sh`, supervisor module, job page modules.
- Tests: non-JSON exit, lock-aware stale rule, one run per click, scenarios 4, 6, 9, and 10.
- Acceptance: AC-R1 through AC-R5 and AC-L1 through AC-L2.
- Risk: a child process outlives the server. Start it in a new session and record its pid. Take the run lock before interrupted-artifact cleanup.
- Rollback: `CONTENTOS_UI_RUN=0` returns the UI to read-only.

## M4 Review and approvals

- Scope: video playback, QA provenance, script and production approval.
- Dependencies: M3.
- Likely files: review and approval modules, media streaming in the server.
- Tests: AC-V1 through AC-V4 and AC-A1 through AC-A5, written before the buttons are wired.
- Acceptance: a changed script cannot reuse the old grant.
- Risk: an approval recorded for content the owner did not see. The server recomputes the digest.
- Rollback: disable the approval routes.

## M5 Browser and accessibility gate

- Scope: manual checklist immediately; Playwright and axe only after approval.
- Dependencies: M4 and the dependency decision.
- Tests: keyboard journeys, screenshots at 1280 and 390 px, both themes, axe on every primary screen.
- Acceptance: AC-G8.
- Rollback: remove the test directory and CI job. The product keeps running.

## M6 Queue and export

- Scope: queue screen at concurrency 1, requeue, and export confirmation.
- Dependencies: M3. It does not block M4.
- Backend change: queue execution uses `production run`, with a timeout and process-group kill, before the screen can start workers.
- Tests: AC-R7 and AC-X1.
- Rollback: keep queue and export CLI-only.

## M7 One-stage rerun

Status: implemented. `pipeline.invalidate_downstream` removes later sentinels and revokes only the gates whose reviewed artifact can change. Creator Studio exposes a confirmed preview and `POST /jobs/{id}/rerun`. This is the canonical M7; the parent discovery roadmap's older "M7 real smoke" label is retired.

- Scope: a core operation for `pipeline run SPEC --only STAGE --force` that removes stale downstream sentinels before the stage runs.
- Dependencies: M4, because reviewers rely on QA results.
- Tests: a forced render cannot leave old `qa.json` looking current; a changed composition demands a new production grant.
- Acceptance: the rerun and every downstream check describe the same artifact.
- Rollback: remove the API action. The CLI escape hatch remains.

## M8 Real-pipeline smoke and polish

- Scope: one opt-in HyperFrames job through the Studio, then copy and keyboard polish.
- Dependencies: M4, M5, arm64 FFmpeg, and whisper.cpp.
- Acceptance: the job reaches `ready/` and the recorded CLI commands still match.
- Rollback: skip the smoke job. Do not treat its absence as a product failure on a machine that cannot render.

## Minimum useful slice

M0 through M4. That covers Health, one validated job, a real or stubbed run, stage progress, logs, both approvals, and export evidence. Queue, one-stage rerun, and the real smoke test come after that journey is trustworthy.

## CLI-only until a later decision

`factory-worker`, competitor, Jev, research, `storage migrate`, `storage cleanup --apply`, `storage recover --apply`, `--allow-paid`, `--approve-private`, and publish.
