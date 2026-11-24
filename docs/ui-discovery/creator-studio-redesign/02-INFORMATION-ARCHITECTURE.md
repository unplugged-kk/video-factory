# 02 / Information architecture

**Research date:** 2026-11-24. **Scope:** proposed navigation. **Evidence / sources:** [00](00-RECONCILIATION.md), `contentos/ui/main.js`, prior Studio screen specifications. **Verified:** hash navigation and deep-linked job tabs exist; routes below are proposals.

| Primary route (hash) | Question it answers | Contextual destinations |
|---|---|---|
| `/mission` | What needs my decision next? | Link to precise job stage, queue or failing prerequisite |
| `/create` | What can I make with these inputs? | Draft → plan → validation → saved job |
| `/batch` | Which rows are ready and which need help? | `/batch/:id/{intake,validate,monitor}`; `/campaign/:id/{brief,episodes,assets,history}` |
| `/library` | What is in production or delivered? | `/jobs/:id/{overview,brief,script,composition,review,files,logs}` |
| `/creative` | What can I reuse or apply? | Looks, effects, voice, assets and capability evidence |
| `/review` | What exact revision needs review? | Job review tab with subject, digest and change context |
| `/operations` | Is there a local execution problem? | Queue, health, stage activity, CLI/manual handoff |

Batch Studio is the parent of campaigns, not an eighth top-level item. Review is an inbox; its deep link opens the same job review surface, never a second approval implementation. Universal Create owns input discovery, Creative Library reuse, Video Library records. Maintain current `#/jobs` and `#/jobs/:id/:tab` links and map old static routes without breaking bookmarked tabs. Keep shareable filter/sort for lists in route parameters; do not put brief text, paths or auth tokens in URLs. Keep job ID and conversation/task context stable across tabs. Breadcrumb: `Batch Studio / [Group] / [Job]` only when there is real group context; direct links present `Video Library / [Job]`.

Desktop uses a labeled left rail; tablet collapses to icon+tooltip with visible route heading; mobile uses a nav drawer behind a labeled button, restores focus when dismissed, and keeps per-screen actions in view. Unsaved draft guard applies before changing route, not when changing layout. [Screens](05-SCREEN-SPECIFICATIONS.md).

**Assumptions:** workspace selector is hidden until more than one real workspace exists. **Open questions:** whether deep links should default to the last selected filter across sessions.
