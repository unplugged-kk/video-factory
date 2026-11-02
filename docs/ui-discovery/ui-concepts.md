# UI concepts, screens and navigation (Phases 5-6)

## Who it is for (evidence-based)
One owner who is also the operator, plus agents that build the videos. `contentos status` on this Mac shows runs for ids like `m3-sample-01-hf-sketch` and `self-healing-infrastructure-001`; the dashboard read 44 jobs. The human touches the system at two gates, a review, an export, and when something breaks. So: creator/reviewer first, debugger second, batch operator third.

## Journey ranking (frequency x value x complexity x failure impact; 5 = highest)
| Rank | Journey | Freq | Value | Complexity | Failure impact |
|---|---|---|---|---|---|
| 1 | J11/J10 Review output and quality gates | 5 | 5 | 3 | 4 |
| 2 | J12 Approve at the two gates | 5 | 5 | 2 | 5 (digest-bound) |
| 3 | J7/J8 Observe stages and diagnose failure | 4 | 5 | 4 | 4 |
| 4 | J5 Run a job (resume) | 4 | 4 | 2 | 3 |
| 5 | J1 Health | 3 | 5 | 2 | 5 (ffmpeg gone today) |
| 6 | J2-J4 Create and validate | 3 | 4 | 4 | 3 |
| 7 | J6 Queue | 2 | 3 | 3 | 3 |
| 8 | J14 Export | 3 | 4 | 2 | 4 |

## Screen inventory (only what the code supports)
Navigation (4 items): **Jobs**, **Queue**, **Health**, **Help**. "New job" is a button on Jobs. Job detail is a page with tabs, not nav.

| Screen | Purpose and main actions | Data | Loading / empty / error / success |
|---|---|---|---|
| Jobs (default) | Find a job; see state at a glance; New job | `/jobs` | skeleton rows / "No jobs yet. New job or run the CLI" / banner "Server cannot read the ledger" with path / list |
| New job | Wizard: Basics (id, title, format, voice) -> Script lines -> Review + Validate -> Save spec, optional Run | validate API, voices (Kokoro allowlist), budget | inline field errors / n/a / validation summary / "Saved to <path>" |
| Job detail > Overview | Stage timeline (9 stages), next action card ("Review script and approve", "Running voice"), Run/Resume | `/jobs/{id}` | polls 2 s; stale/blocked/failed banners as in architecture state model |
| Job detail > Script | Script, title, lint result; Approve SCRIPT_APPROVED with digest check | script.md, script-lint.json | "Script not written yet" |
| Job detail > Review | Video player, QA rows with provenance, preview frames and sheet, Approve PRODUCTION_APPROVED (composed project) | video.mp4, qa.json, gates | "No render yet" |
| Job detail > Logs | Stage selector, log text, ledger error, attempts | stage log or ledger error | "Logs are not captured for this stage yet" until backend B3 |
| Job detail > Files | Artifact list with sizes and absolute paths (copy button), Export action | manifest artifacts | empty until stages run |
| Queue | Ledger `jobs` rows, add specs, requeue failed/blocked | `/queue` | "Nothing queued" |
| Health | Capability table, fix hints, storage roots, Re-check | `/health` | spinner while probing / n/a / per-row failure with fix command / all green |
| Help | CLI reference for expert flows, the "never published" explanation, link to docs | static | n/a |

Deliberately omitted: KPI cards, analytics, a Settings screen (config files are owner-edited and are protected by AGENTS.md), Research/Competitor/Jev screens (network/credit side effects; CLI-only), a publish screen.

## Three concepts
### A. Operations dashboard
Primary user: operator watching many jobs. Home is a wide table of jobs x nine stage cells (Airflow grid style), with a right drawer for logs and a worker/queue status bar. Create is a modal. Monitoring is the whole point; review is a link out to the job page.
- Errors: red cell, click opens the log drawer. Long tasks: running cell with elapsed time.
- Weakness: optimises the rarest persona here; 44 jobs but concurrency is 1 and nothing has run in parallel. Review, the most important journey, is secondary. Cost: medium (grid component, polling of many jobs).

### B. Creator studio
Primary user: the owner making and approving individual videos. Home is a job list; each job opens a single page organised around "what do I need to do next": a next-action card, then the stage timeline, tabs for Script / Review / Logs / Files. Gates are first-class: Approve buttons sit beside the artifact they approve, with the digest check explained.
- Errors: failed stage becomes the next-action card ("voice failed: ffmpeg not runnable. Fix: brew install ffmpeg. [Open Health]"). Long tasks: progress is stage-level from ledger rows, no fake percentage.
- Weakness: batch work is a second-class Queue tab; needs good empty/loading states to avoid feeling sparse. Cost: medium.

### C. Automation control center
Primary user: someone driving the factory from agents, schedules and ContentForge. Home is a live event feed, worker controls, scheduler status, rules and approvals inbox.
- Weakness: builds for features that are PARKED or not implemented (ContentForge, scheduler, cancel, concurrency). Highest cost, lowest current value, risks showing controls that do nothing. Cost: large.

## Recommendation
**B, Creator studio, with a minimal Queue tab and a first-class Health screen.** It matches the real flow (two gates, one reviewer), puts the highest-ranked journeys first, and every screen maps to existing code. Concept A's stage grid is reused only inside the Queue screen later. C is rejected until the underlying capabilities exist.

## Responsive behaviour
Desktop-first (laptop, 1280 px). Under 900 px the tabs become a select and the stage timeline goes vertical. Video review is the only phone-relevant view: vertical 9:16 player fills width. No mobile app, no touch-specific work.
