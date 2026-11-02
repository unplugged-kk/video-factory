# Browser, end-to-end, and accessibility plan

This plan keeps the six tiers in `docs/ui-discovery/e2e-strategy.md`. Browser checks are an acceptance gate for the Studio, but no browser dependency is installed by this planning package.

| Tier | Proves | When |
|---|---|---|
| T1 Python unit | Validation, state derivation, digest checks, path containment, log scrubbing | Every change |
| T2 API contract | Routes, token, Host, Origin, bad ids, forbidden publish and paid fields | Every change |
| T3 JavaScript unit | Formatters, state mapping, form validation, API error handling through `node --test` | Every change |
| T4 Stub runner | Lifecycle against a deterministic fake `CONTENTOS_UI_RUNNER` | Every change |
| T5 Browser | Real Chrome flows, screenshots, keyboard journeys, axe | Every UI change, after owner approval of the runner |
| T6 Real pipeline | One small HyperFrames job through voice, render, QA, approval, and export | Opt-in, after arm64 FFmpeg and whisper.cpp exist |

The stub runner writes the same ledger rows and artifacts the UI reads. Tests do not mock the page's state reducer to pretend a job advanced.

## Browser scenarios

| Scenario | Expected evidence |
|---|---|
| Health with a dead FFmpeg binary | "not runnable", remediation text, Run unavailable |
| Valid and invalid job creation | Workspace spec path; field errors; no run for an invalid spec |
| Run once | One subprocess for one click; second click shows already running |
| Script approval and edited script | 200 for the displayed digest; mismatch copy and 409 after the script changes |
| Blocked gate versus failure | Different labels, icons, and next actions |
| Transient retry and stale state | Attempt count from the core result; stale only after the lock is free |
| Video Range | `206` and a playable seek |
| Logs | HTML in tool output is shown as text; secret-like tokens are masked |
| Security | Wrong Host, missing token, traversal, and an invalid job id are rejected |
| Absent controls | No Publish, paid-provider, or Cancel control in the DOM |
| Keyboard | Scenarios for create, approve, and run complete without a pointer |
| CLI compatibility | Recorded `doctor`, `status`, `pipeline run`, and `approve` output and exit codes stay the same |

Screenshots are taken at 1280 px and 390 px in dark and light themes. Review them manually until a baseline is accepted. After that, visual comparison can be added. Automated axe scans cover Jobs, New Job, every job tab, Queue, Health, and Help. A human still checks whether the approval sentence is understandable and whether focus order feels right.

## Tool choice

Use the installed Chrome and an already working browser skill for the fixture prototype. `puppeteer-core` is only present transitively through HyperFrames, so it is not the test runner.

Playwright and `@axe-core/playwright` are the proposed dev-only tools for T5 because they can drive Chrome, capture screenshots, and run axe repeatedly. They require a separate owner approval. Until that approval, T5 is a manual checklist, not a claim of automated coverage.

## Local and CI boundaries

T1 through T4 run against a temporary workspace and an ephemeral port. They do not call network research, paid providers, or publish. T6 is local or nightly and refuses to start when `doctor` reports a required tool missing. CI placement for Playwright is undecided because this planning pass did not inspect the hosted runner image.

## Baseline precondition

M0 must make `pytest tests` collect when FFmpeg is absent or has the wrong architecture. Environment skips stay visible. A partially skipped suite is not evidence that the Studio is healthy.
