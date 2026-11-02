# E2E strategy (Phase 8)

Principle: never depend on publishing or paid services (there are none to call: publish is a dry run and paid providers are off). The expensive part is a real render (about 28 s render + 15 s voice for a 5-line short on 2026-10-19 per the ledger; about 5 min for the six-fixture suite). So the strategy has tiers, and only the top tier renders.

## Tiers
| Tier | What | Tools | Runs |
|---|---|---|---|
| T1 Python unit | spec validation, state derivation (ledger + manifest -> UI state), digest recheck, token/Host checks, path containment, log scrub | pytest (installed), temp workspace like `tests/storage_helpers.py` | every PR (CI) |
| T2 API contract | each `/api/v1` endpoint against a real server on an ephemeral port with a temp workspace; JSON shapes frozen as fixtures; negative cases (bad id, no token, wrong Host, `allowPaid`, `PUBLISH_APPROVED`) | pytest + stdlib `http.client` | every PR |
| T3 UI module unit | pure JS modules (formatters, state mappers, form validation) | `node --test` (already used in CI) | every PR |
| T4 Stub-render integration | full UI flow with a fake pipeline: a stub `contentos.sh` target that writes ledger rows, a tiny pre-made `video.mp4` fixture, `qa.json`, logs, with scripted failures | pytest drives the server; browser tier drives the page | every PR |
| T5 Browser E2E | Chrome driving the real page against the T4 stub server: journeys below; axe scan per screen; screenshot at 1280 and 390 px | Playwright (new dev dependency, needs approval) | PR, headless |
| T6 Real-pipeline smoke | one 3-line fixture through real Kokoro + HyperFrames + ffmpeg to an MP4, via the UI Run button | same as T5 + `doctor` precondition; reuse `tests/fixtures/m3/m3-sample-01-hf-sketch.yaml` (HyperFrames lane) | nightly/local, `CONTENTOS_E2E=1`-style opt-in; cannot run on this Mac until ffmpeg is installed |

Stub mode: the server reads `CONTENTOS_UI_RUNNER` (a path to the command that "runs a job"). Default `./contentos.sh production run`; tests point it to a script that emits a configured sequence (OK, FAIL transient, BLOCKED at gate, crash) and writes the same ledger rows. This avoids mocking inside the UI code and exercises the real subprocess supervision.

## Scenarios (status: A = automatable now once the backend slice exists, B = needs extra infrastructure)
| # | Scenario | Tier | Status |
|---|---|---|---|
| 1 | Start the app; Health lists capabilities; with `ffmpeg` shadowed by a dead binary on PATH it shows "not runnable" and disables Run | T2, T5 | A (dead-binary fixture is easy: a non-executable file named ffmpeg) |
| 2 | Create a valid job via the wizard; spec file lands in the workspace, not the repo | T2, T5 | A |
| 3 | Invalid job (bad id, 1:1 format, empty script) shows field errors; Run stays disabled | T1, T5 | A |
| 4 | Run a job; timeline moves brief -> ... -> stops BLOCKED at SCRIPT_APPROVED | T4, T5 | A |
| 5 | Open Logs for a failing stage; error and log shown | T4, T5 | B: needs per-stage log capture (B3); before that, only ledger error text |
| 6 | Transient failure retried (stub emits FAIL twice then OK); UI shows attempts 3 | T4 | A |
| 7 | Artifacts: video plays and seeks (Range request returns 206), QA rows render | T2, T5 | A |
| 8 | Quality-gate failure displays measured value, threshold and provenance | T4, T5 | B: needs persisted gate results (B5) |
| 9 | Renderer crash: stub exits non-zero mid-stage; UI shows failed with class `output` or `transient`, lock released, rerun works | T4 | A |
| 10 | Reload and restart the server mid-run; state re-derived; no duplicate run; STALE after 600 s with a dead pid | T2, T4 | A (use an injectable clock for the 600 s rule) |
| 11 | Safety: no Publish control; POST `PUBLISH_APPROVED` -> 403; `allowPaid` -> 400; approve with an outdated digest -> 409; no token -> 403 | T2, T5 | A |
| 12 | CLI unchanged: run recorded CLI commands before/after and diff output/exit codes; run the UI-created spec through `./contentos.sh pipeline run` | T1 | A |
| 13 | Approve script; edit script; UI shows "approval no longer matches" and Run blocks at voice | T4 | A (existing `check_gate` mismatch path) |
| 14 | Accessibility: axe on Jobs, New job, Job detail (each tab), Health; keyboard-only run of scenarios 2-4 | T5 | A |
| 15 | Visual regression: screenshots of the same five screens in dark and light | T5 | A after design stabilises; start with manual review |
| 16 | Real render through the UI | T6 | B: needs ffmpeg + whisper-cpp on this Mac |

## Open decisions for the owner
- Approve Playwright as a dev-only dependency (Apache-2.0; downloads its own browsers into `~/Library/Caches/ms-playwright` or use `channel: "chrome"` with the installed Chrome). Alternative with no new dependency: drive Chrome through `puppeteer-core`, which exists in `node_modules` only as a transitive dependency of the pinned HyperFrames; it can vanish on a HyperFrames upgrade, so not recommended.
- Where the T5 job runs: CI (`macos-latest`, Chrome preinstalled on GitHub-hosted macOS runners per general knowledge, not verified here) vs local only.

## Preconditions that gate the whole plan
Fix G1 (test_sheet import crash) and install arm64 ffmpeg so `pytest tests` runs fully green before UI tests are added; otherwise a red baseline hides regressions.
