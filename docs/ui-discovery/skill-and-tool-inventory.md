# Skill and tool inventory (Phase 0, 2026-10-19)

Status: partial. Verified items come from commands run in the repo; anything marked NOT INSPECTED could not be read.

## Repo-local skills (verified: `.claude/skills/*/SKILL.md`)
| Skill | Use for this mission |
|---|---|
| video-production-orchestrator | Understand the intended end-to-end workflow and phases (journey source). |
| video-director | Scene planning and capability choices (read for the Track B journey). |
| explainer-visual-qa | Gates, phone-scale inspection, independent critic (read for the review journey). |
| explainer-motion-craft | Motion rules; background only. |
| hyperframes-core / -animation / -keyframes | Generated, hash-verified, vendored. Read only; never modify. |

No frontend-design, browser-automation, E2E or accessibility skill is installed in the repo.

## Global skills (verified 2026-10-20 from this session's skill list)
Installed and listed: Matt Pocock (`mattpocock-skills:grilling`, `:tdd`, `:domain-modeling`, `:codebase-design`, `:code-review`, `:diagnosing-bugs`, `:research`, `:prototype`, `:writing-for-agents`), Poteto (`poteto-mode`, `portable-pstack:*`, agent `poteto-agent`), Obra Superpowers style skills (`brainstorming`, `executing-plans`, `writing-plans`, `systematic-debugging`, `verification-before-completion`, `test-driven-development`, `using-superpowers`), frontend/design (`frontend-design`, `design`, `design-system`, `design:accessibility-review`, `design:design-critique`, `ui-ux-pro-max`, `web-accessibility`), browser (`agent-browser`, `browser-use`, `browser-qa`, `webapp-testing`).
Used here: `graft` for code lookup, `caveman`/`ponytail` output modes (hook-injected). Chosen for the implementation phase, not used now: `test-driven-development` + `mattpocock-skills:tdd` (tests-first for each API milestone), `design:accessibility-review` + `web-accessibility` (AC-G8), `frontend-design` + `design-system` (screens), `browser-qa`/`agent-browser` (manual screenshots), `verification-before-completion` (reporting). Not duplicated or installed.
The browser-use MCP daemon failed to start (`daemon default didn't come up`); a screenshot run needs Chrome remote-debugging enabled by the owner.

## Tooling in the repo (verified)
- Python CLI: `./contentos.sh`, `contentos/cli.py` (253 lines); venv `~/.contentos/venv`.
- Existing UI: `contentos/dashboard.py` (124 lines, stdlib `ThreadingHTTPServer`, 127.0.0.1:4310 default) and `contentos/dashboard.html` (70 lines). Treated as the starting point, not greenfield. Capabilities audited in Phase 1.
- Node: `node_modules` present; no Playwright, Vite, Vitest or Cypress in `node_modules/.bin`. A browser/E2E runner would be a new dependency and needs owner approval.
- Test runners: pytest (`~/.contentos/venv/bin/python -m pytest tests`) and `node --test contentos/adapters/v1/*.test.mjs`.

## Missing capabilities (nothing installed)
Browser E2E runner; accessibility checker; screenshot tooling for the UI. Candidates to evaluate in Phase 8 with licence and rationale. Browser tools exist on the owner's machine (Claude in Chrome, built-in browser) and may serve manual checks.

## Repo state at inspection
`main` at eab249a. Only change: the untracked `docs/ui-discovery/` folder. `node_modules` contains `puppeteer-core` and `@puppeteer/browsers` as transitive dependencies of the pinned HyperFrames; no Playwright, Vitest, jsdom or axe.
