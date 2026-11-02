# Creator Studio rollout

Verified on 2026-10-21 against the local working tree. The CLI remains usable. Publishing, paid providers, `--approve-private`, cancellation, destructive storage apply, worker administration, research, and Track B composition authoring stay outside Creator Studio. Track B review, voice, alignment, HyperFrames render, diagnostics, and export are in the workbench.

## Implemented

- Versioned job and capabilities read models, including draft, gate, retry, stale, budget, quality provenance, and export state.
- Vanilla ES-module shell with responsive workbench layout, both themes, keyboard focus, and URL-addressable job filters.
- New Job uses server voices, platform budgets, validation, collision recovery, and an unsaved local draft.
- Live progress is a server-sent invalidation hint with canonical refetch and polling fallback.
- Script and production approvals remain digest-bound. QA can be rerun from the existing local checker.
- One-stage rerun previews its effects, then runs `pipeline run --only STAGE --force`.
- Queue add, list, and requeue are authenticated. The worker executes `production run`, defaults to one job, and kills the timed-out process group. The screen does not start the worker.
- Export preview and confirmed export use the existing validated exporter and reject caller-selected paths.
- Track B intake, registration, voice, alignment, HyperFrames render, and split QA/visual/critic diagnostics use the job id only. Track B jobs cannot be sent through Track A `production run`. The CLI `job register` command is unchanged.

## Verification

- `~/.contentos/venv/bin/python -m pytest tests/test_ui_api.py tests/test_track_b.py tests/test_queue_production.py tests/test_rerun_invalidation.py tests/test_ui_runner.py tests/test_specs.py -q`
- `node --test contentos/ui/*.test.mjs`
- Browser coverage: `npx playwright test` passed 6 fixture journeys on 2026-10-21, covering both themes, 1280px and 390px, keyboard navigation, axe, and Track B intake. The Track B journey never starts HyperFrames. No real pipeline run is used.
- A real render is opt-in: `CONTENTOS_UI_SMOKE=1 ~/.contentos/venv/bin/python -m pytest tests/test_ui_smoke.py -q`. It stops at the first human gate and does not publish.
- A real Track B render is opt-in and stops before publish: `CONTENTOS_TRACK_B_RENDER=1 CONTENTOS_TRACK_B_JOB=<id> ~/.contentos/venv/bin/python -m pytest tests/test_track_b.py::test_opt_in_render_stops_before_publish -q`. The fixture browser journey never starts HyperFrames.

## Rollback

- Remove the new `/api/v1` routes in `contentos/ui_api.py` to return the UI to its previous actions. Saved specs and ledger rows remain valid CLI inputs.
- Queue execution can be restored to the old pipeline command by reverting `contentos/queue.py`; queued rows do not change schema.
- Downstream invalidation lives in `pipeline.invalidate_downstream` and runs only for `only` plus `force`.

## Still CLI-only

Worker start and stop, cancellation, persisted rejection, private approval, paid providers, publishing, research, competitor inspection, ContentForge, and storage cleanup or recovery `--apply`.
