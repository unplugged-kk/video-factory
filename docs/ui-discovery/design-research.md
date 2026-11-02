# Design research (Phase 6)

Method and honesty note: three web searches were run on 2026-10-20 (links below). Search results returned documentation landing pages; their pages were not opened in full, so claims are limited to what the search summaries state. Observations about DaVinci Resolve, Temporal and similar tools are general product knowledge and are NOT sourced here; they are marked "(general knowledge)". Nothing below is copied design.

## Patterns worth borrowing
| Need | Pattern | Source / status |
|---|---|---|
| See a run's stages at a glance, then drill to one stage | Airflow's Grid View: status at a glance by colour and tooltip, click a task cell to view logs, retried tasks identifiable | [Airflow UI docs](https://airflow.apache.org/docs/apache-airflow/stable/ui.html) |
| Failure diagnosis | A task-instance view with Logs as the default tab, plus metadata tabs | Airflow docs, same link |
| Step timeline with per-step duration and deep-linkable log lines | GitHub Actions run page: graph of jobs, per-step time, link to a log line, re-run failed jobs | [GitHub Docs: use workflow run logs](https://docs.github.com/en/enterprise-server@3.21/actions/how-tos/monitor-workflows/use-workflow-run-logs) |
| Partial re-run clarity | GitHub notes that after a partial re-run the log archive contains only the jobs re-run, so earlier attempts keep their own logs | same link; applies to our resume model: show attempts separately |
| Automated accessibility checks in browser tests | `@axe-core/playwright` with `AxeBuilder.analyze()`; the Playwright docs state automated checks catch only part of WCAG issues (a secondary summary says up to about half) so manual checks remain | [Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing) |
| Review a rendered cut against approval gates | Timeline + scrub + side-by-side frames with explicit approve | (general knowledge) NLEs and review tools such as Frame.io; used only as a pattern for "watch, then approve" |

What these tools teach us, mapped to the repo: the unit is a run with ordered stages (our nine `STAGES`); the default drill-down is the log of the failing stage; re-runs are attempts, not edits. What they do not teach: our hard gates, digest-bound approvals, and the "never publish" rule. Those are product-specific and drive the design.

## Frontend technology comparison
Evaluated against: no new dependencies unless justified, local deployment, accessibility, browser automation, and what exists in the repo.

| Option | For | Against | Verdict |
|---|---|---|---|
| Vanilla ES modules, no build, served by stdlib server | Zero install; fits `dashboard.html` starting point; nothing new to pin; pairs with `node --test` for pure modules | No type-checking; manual component discipline; more hand-written a11y | Recommended for v1 |
| Preact + htm via import maps, no build | Declarative views with tiny size | Needs vendored copy or CDN (CDN is off-limits for a local-first tool); a dependency to pin | Consider if views get unwieldy |
| React + Vite + TypeScript | Best tooling, ecosystem, component testing | Introduces npm build chain next to a repo whose node deps exist only to pin HyperFrames; owner approval; more to maintain for one user | Not now |
| FastAPI + SPA | Validation, OpenAPI, async | Adds Python deps (none installed), second server model | Revisit only if API passes about 30 endpoints or needs WebSockets |
| Electron/Tauri | Native feel | Packaging for one user; not needed since `localhost` works | Rejected |

Browser automation (test tier): `puppeteer-core` is present in `node_modules` but only as a transitive dependency of the pinned HyperFrames, so it must not be relied on. Playwright is the usual choice and is the only option here with first-party axe integration; it would be a new dev-only dependency and needs owner approval. Chrome is installed at `/Applications/Google Chrome.app`. Detail in e2e-strategy.md.

## Visual direction (summary; tokens in design-system.md)
A quiet, dense, utilitarian tool: neutral surfaces, one accent, status colours reserved for status, monospace for ids/paths/logs, video as the only large visual. The current `dashboard.html` already defines dark and light variables (`--bg --panel --line --ok --run --fail --blk --pend --acc`); the system extends those instead of replacing them, so the migration is incremental.

Sources: [Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing), [Airflow UI](https://airflow.apache.org/docs/apache-airflow/stable/ui.html), [GitHub workflow run logs](https://docs.github.com/en/enterprise-server@3.21/actions/how-tos/monitor-workflows/use-workflow-run-logs).
