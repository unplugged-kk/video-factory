# Test coverage gaps (Phase 4)

Each gap was checked by grep or by running the suite (see test-inventory.md). Severity is about the risk of building a UI on top, not about the pipeline in general.

| # | Gap | Evidence | Why it matters for a UI | Close with |
|---|---|---|---|---|
| G1 | The default `pytest tests` run cannot start on a machine with a dead ffmpeg: `test_sheet.py` raises at import (`@pytest.mark.skipif(not drawing_ok(), ...)` calls `ffmpeg`) | Run on this Mac: "1 error during collection", zero tests executed | A broken environment hides every other result, which is exactly what a Health screen must prevent | Catch `OSError` in `sheet._drawtext_available`; add a test with a fake non-executable ffmpeg |
| G2 | 225 tests need a working arm64 ffmpeg/ffprobe, and CI is the only place that guarantees one | 218 + 5 `Bad CPU type` errors | The UI's E2E backbone (render + QA) is the same dependency | `doctor` as a precondition of E2E; CI keeps `brew install ffmpeg` |
| G3 | No test touches `dashboard.py` or `dashboard.html` | grep `dashboard` in `tests/*.py`: no match | Any server code extended for the UI starts at zero coverage; the media whitelist and Range code is security-relevant | Add `tests/test_dashboard_api.py` before adding any endpoint (M1) |
| G4 | `queue.py` and the worker are untested; a worker run was never observed concurrently (owner notes) | grep `queue` finds two incidental files | Batch screen would drive an untested path; no timeout, `subprocess.run` without kill in `_run` | Test with an injected command (the module already runs `contentos.sh`); keep UI concurrency at 1 |
| G5 | Real-render E2E exists but is opt-in and slow: `CONTENTOS_E2E=1 pytest tests/test_e2e_features.py` (6 fixtures, about 5 min) | docs/E2E-VERIFICATION.md section 1 | It is the only test that proves a job reaches an MP4; it has not run in CI and cannot run on this Mac today | Make it the nightly/local "real" tier of the UI strategy |
| G6 | `test_remotion_render.py` is named E2E but is a single test gated by `needs_remotion` | file is 62 lines, one `def test_` | Remotion should not be offered in the UI until evidence exists | Hide Remotion in UI v1 |
| G7 | No automated check that gates are in the pipeline: `visual_gate`, `critic`, Rule A/B, `cue_audibility` are standalone CLIs; only `qa.run_qa` and export `finalcheck` run in `pipeline.run` | pipeline.py stage list; AGENTS.md section 3 steps 10 | The Quality screen must label which results came from the pipeline and which were run by hand | Store gate results in the job folder with a provenance field |
| G8 | No per-job log is persisted. `pipeline.sh()` keeps only the last 400 chars of stderr/stdout in the exception message; the ledger stores that string | `pipeline.py sh()` lines 64-75 | "Logs and failure investigation" screen has nothing but ledger `error` text | Capture stage stdout/stderr to `<job>/logs/<stage>.log` in `sh()` (backend change, M3) |
| G9 | No cancel, no reject, no `validate spec` command | `cli.py` subcommand list | UI must not show these controls until backend support exists | Add `contentos validate SPEC --json` first (M2); cancel later |
| G10 | `doctor` output is human text; `dashboard._health()` already builds a structured form | cli.py cmd_doctor vs dashboard.py `_health` | A Health screen should not parse text | Expose `providers.candidates` as `/api/health` |
| G11 | Pre-existing: `docs/factory-v2/01-inventory.md` is reported stale on Remotion (docs/E2E-VERIFICATION.md section 2) | that doc | Docs are not evidence; the UI should read live capabilities | Generate the capability table from `doctor` JSON |
| G12 | No browser, accessibility or visual-regression test infrastructure of any kind | no Playwright/Vitest/Cypress in node_modules/.bin or venv (checked) | Needs an owner decision on a dev dependency | See e2e-strategy.md |

## Fragile spots to watch (read in source, not exploited)
- `dashboard.state()` opens a SQLite connection per request and never closes it; `/api/state` read 51 KB in 27 ms against 44 jobs on this Mac, so fine now.
- Dashboard `/media` reads the whole file with `read_bytes()` and slices it for Range; a 5 MB mp4 is fine, a long render is not.
- `scrub_interrupted` runs before the per-job lock is taken (noted in discovery notes); a UI that lets two clicks start two runs can race it. The UI must disable Run while a run is active and the backend must take the lock before scrubbing.
- `queue._run` has no timeout and no process-group kill, while `pipeline.sh()` has `_kill_tree` and a 600 s timeout, so the two paths differ.
