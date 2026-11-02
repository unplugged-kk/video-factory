# Executive report: Video Factory UI discovery (2026-10-20)

Files: skill-and-tool-inventory, current-architecture, capability-inventory, integration-map, user-journeys, cli-to-ui-matrix, test-inventory, test-coverage-gaps, ui-acceptance-criteria, design-research, ui-concepts, design-system, ui-architecture, e2e-strategy, implementation-roadmap (all in `docs/ui-discovery/`). No code, config, dependency or git history was changed.

## 1. What the application does today
`contentos` is a local Python CLI (`./contentos.sh`) that turns a spec YAML (content_id, title, format, voice, script lines) into an MP4 through nine stages: brief, script, voice (Kokoro), compose, render (HyperFrames by default; Remotion and MoneyPrinterTurbo as opt-in lanes), qa, package, export, publish. Two hard gates (SCRIPT_APPROVED before voice, PRODUCTION_APPROVED before render) are bound to content digests. Publish is a dry run and is blocked by design. State lives in a SQLite ledger (`runs`, `approvals`, `jobs`, `decisions`), a per-job manifest and a job folder outside the repo. A read-only stdlib dashboard (127.0.0.1:4310) already exists.

## 2. Primary user journey
Health check -> write a spec -> run (stops BLOCKED at gate 1) -> read script, approve -> voice/compose -> review composition, approve gate 2 -> render, QA, preview, independent critic -> export to `ready/`. Never publish.

## 3. CLI capabilities
19 top-level commands (doctor, status, route, pipeline, production, qa, preview, approve, job, jev, learn, recommend, dashboard, research, competitor, queue, worker, storage, factory-worker). Classified A-E in cli-to-ui-matrix.md. Missing as commands: validate spec, cancel, reject, tail logs, structured doctor.

## 4. What tests actually cover (run on this Mac)
Node adapter tests: 44/44 pass. Python: `pytest tests` cannot start (collection crash in `test_sheet.py` when ffmpeg is a dead binary). Excluding that file: 591 pass, 48 fail, 177 error, 6 skip; 223 of those 225 are `Bad CPU type` from the x86 ffmpeg/ffprobe because `/opt/homebrew/bin/ffmpeg` and `whisper-cli` are not installed right now. Unit coverage of validators, storage, approvals, export and gates is deep; the only real-render E2E is opt-in and slow; dashboard, queue worker and CLI parsing have no tests; no browser or accessibility tests exist.

## 5. Largest gaps
Usability: no spec validation, no logs, no cancel, no reject, doctor is text. Architecture: queue and pipeline kill/timeout behaviour differ; quality gates other than QA/finalcheck are not in the pipeline; `scrub_interrupted` runs before the run lock. Environment: the machine cannot render today.

## 6. Concepts
A Operations dashboard, B Creator studio, C Automation control center. Recommended: **B**, because the real flow is one owner and two gates, and it puts review and approval first.

## 7. Architecture
Extend the existing stdlib server into a versioned JSON API; vanilla ES modules, no build; runs as subprocess `./contentos.sh production run`; state always derived from ledger and manifest; token + Host/Origin guards; digest-checked approvals; no publish, no paid, no path inputs. Zero new dependencies for the product.

## 8. Navigation and screens
Jobs (default) | Queue | Health | Help; New job wizard; Job detail tabs Overview, Script, Review, Logs, Files.

## 9. E2E plan
Six tiers: pytest unit, API contract, node unit, stub-runner integration, Playwright browser + axe, one real-render smoke (needs ffmpeg). Sixteen scenarios, thirteen automatable once the backend slice exists.

## 10. Roadmap
M0 green baseline, M1 server + Health, M2 create/validate, M3 run/observe/logs (first full slice), M4 review/approve, M5 browser E2E, M6 queue/export, M7 real smoke. MVP = M0-M4.

## 11. Decisions needed from you
1. Install arm64 `ffmpeg` and `whisper-cpp` (`brew install ffmpeg whisper-cpp`) so tests and renders work; I did not install anything.
2. Approve the stdlib server + vanilla JS direction (vs React/Vite or FastAPI).
3. Approve Playwright as a dev-only dependency, or choose manual browser checks.
4. Allow small backend changes the UI needs: `contentos validate --json`, structured doctor, per-stage log files, queue using `production run` with timeout and group kill.
5. Cancel and a persisted Reject: build now or leave out of v1 (default: leave out).
6. Whether `--approve-private` may appear in the UI at all (default: no).
7. Whether to fix the `test_sheet.py` collection crash as part of M0 (recommended, it is a one-line guard plus a test).

## 12. Exact next implementation prompt
"Implement M0 and M1 from docs/ui-discovery/implementation-roadmap.md in video-factory. M0: guard `sheet._drawtext_available` against OSError with a test, then run `pytest tests` with arm64 ffmpeg on PATH and report every remaining failure. M1: add `contentos/ui/` with a stdlib server bound to 127.0.0.1, token/Host/Origin checks, `/api/v1/health` returning structured doctor output (reuse `providers.candidates`, add an ffmpeg runnable check), and a Health screen using the tokens in design-system.md. Write `tests/test_ui_api.py` first covering AC-G1..G5 and AC-H1..H4. Keep `./contentos.sh dashboard` working. No new dependencies, no config changes, no git operations, no publishing, no paid services. Report test results honestly."

## Verified vs assumed
Verified by running: doctor output, status rows, node and pytest results, dashboard probe, package imports, repo file listings. Read in source only: pipeline, core, queue, ledger, dashboard code paths. Assumed or unsourced: GitHub-hosted Chrome availability, general-knowledge notes on other tools in design-research.md, and anything about CI results (not fetched). Not done: real render, screenshots.
