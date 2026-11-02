# Implementation roadmap (Phase 9)

Order is one vertical slice first: Health -> create -> validate -> run -> observe -> inspect -> gate. Effort: S, M, L. Every milestone leaves the CLI untouched and is independently mergeable.

## M0 Green baseline (S) - prerequisite
- Scope: make `pytest tests` runnable and green; no UI. Catch `OSError` in `sheet._drawtext_available`; owner installs `brew install ffmpeg whisper-cpp`; re-run, then investigate the two unexplained failures (`render_integrity` KeyError, audio regex).
- Reuse: existing tests. New: one regression test for the dead-ffmpeg case.
- Acceptance: 0 failed, 0 collection errors; skips only for opt-in E2E and pinned skills.
- Risk/rollback: tiny diff; revert commit.

## M1 Server skeleton and Health (M)
- Scope: `contentos/ui/` server (move/extend `dashboard.py`), token/Host/Origin guards, `/api/v1/health` (structured doctor + storage + ffmpeg runnable), static shell, Health screen, design tokens.
- Reuse: `providers.candidates`, `storage.*`, existing media whitelist (stream instead of `read_bytes`).
- Tests first: `tests/test_ui_api.py` (T1/T2) incl. AC-G1..G5, AC-H1..H4. Old `/api/state` kept until Jobs screen replaces it.
- Acceptance: AC-G*, AC-H*; `./contentos.sh dashboard` still serves.
- Risk: new surface; mitigated by 127.0.0.1 + token. Rollback: remove the `ui` package, dashboard unchanged.

## M2 Create and validate (M)
- Scope: `validate_spec` in Python plus `contentos validate SPEC --json`; `POST /specs/validate`, `POST /specs`; New job wizard writing under `<workspace>/specs/`.
- Reuse: script lint, `storage.valid_job_id`, `production.platforms budget`, Kokoro voice list from the adapter allowlist (single source: move the list into Python or read the existing one; do not fork it).
- Acceptance: AC-C1..C5; invalid specs cannot be run.
- Risk: duplicating adapter validation. Rollback: remove endpoints.

## M3 Run, observe, logs (L) - the first complete slice
- Scope: per-stage log capture in `pipeline.sh()` (B3); run supervisor (spawn `production run` in its own session, record pid); Jobs list; Job detail Overview with stage timeline and next-action card; Logs tab; STALE handling; stub runner for tests (T4).
- Reuse: `core.run_until_blocked_or_done`, ledger `runs`/`jobs`, `.run.lock`.
- Tests: a non-zero `production run` that emits no JSON becomes a structured process error; a RUNNING row older than 600 s remains running while `.run.lock` is held and becomes stale only after the lock is free.
- Acceptance: AC-R1..R5, AC-L1..L2; scenarios 4, 6, 9, 10 green in T4.
- Risk: the highest. Hung child processes (use group kill + timeout), race of `scrub_interrupted` before the lock (move the lock earlier in the backend and add a test first). Rollback: feature flag `CONTENTOS_UI_RUN=0` leaves read-only UI.

## M4 Review and approvals (M)
- Scope: video player with Range, QA rows, preview frames via `preview`, Script tab, digest-checked approve endpoints, persisted gate results with provenance (B5).
- Reuse: `qa.run_qa`, `gate_digest`, `ledger.approve`, `preview`, `visual_gate` outputs.
- Acceptance: AC-V*, AC-A1..A5; scenarios 7, 8, 11, 13.
- Risk: approval correctness; every approval path covered by T2 tests before UI wiring.

## M5 Browser E2E and accessibility (M)
- Scope: Playwright (if approved), axe per screen, screenshots, scenarios 1-4, 7, 11, 14.
- Acceptance: AC-G8; CI job added.
- Risk: new dev dependency; rollback by deleting the folder and CI job.

## M6 Queue and export (M)
- Scope: queue screen at concurrency 1 (switch `queue._run` to `production run` with timeout and group kill, B4, with tests), requeue, Export button (`storage export`), Files tab.
- Acceptance: AC-R7, AC-X1.

## M7 Safe one-stage re-run (M)
- Scope: add a core operation used by CLI and API for `pipeline run SPEC --only STAGE --force`; invalidate every affected downstream sentinel before running. Keep this expert recovery action out of the first vertical slice.
- Tests: force-rendering invalidates the old `qa.json`, package and export results; a subsequent run cannot skip QA for the new `video.mp4`; changed composition or audio still requires a fresh digest-bound production approval.
- Acceptance: a user can re-run one failed stage without re-running unrelated earlier stages, and every downstream check observes the new artifact.
- Risk: stale artifacts could present an old validation result as current. Rollback: remove the API action while retaining the existing CLI escape hatch.

## M8 Real-pipeline smoke and polish (S-M)
- Scope: T6 job, visual regression baselines, copy pass, keyboard shortcuts.

## Minimum viable UI
M0 + M1 + M2 + M3 + M4. Everything the owner does today in the terminal for a Track A short, with the two gates.

## Later enhancements
SSE events; cancel (needs backend); real Reject record (B6); Track B registration form; Remotion/MPT lanes once evidence exists; Research panel (network, opt-in).

## Stays CLI-only
`factory-worker`, `competitor`, `jev`, `storage migrate/adopt/cleanup/recover --apply`, `--allow-paid`, `--approve-private` (until a typed-confirmation dialog is accepted), publishing, `learn`.
