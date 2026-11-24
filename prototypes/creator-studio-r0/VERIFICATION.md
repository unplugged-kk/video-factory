# R0 verification / 2026-11-24

Scope: standalone fixture prototype. Verified against the working prototype diff based on `c6d8ca9`; no protected files changed. No dependencies installed. No production Studio process was started or contacted. The harness checked the default port and process list before starting only its own server; the fixture listener had closed at the post-run port check.

## Reproduce

On the tested Mac, from `prototypes/creator-studio-r0/`, reuse existing Playwright and axe-core modules and the installed Chrome executable. The screenshot destination must not exist and must be outside this worktree.

```sh
E=$(mktemp -d /tmp/cutting-room.XXXXXXXX)
node check.mjs "$HOME/git/video-factory/node_modules" "$E/screens" \
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
node --check serve.mjs
node --check check.mjs
node --check site/app.mjs
node --check site/fixtures.mjs
```

## Evidence

2026-11-24 15:59:57–16:00:06 IST; Apple Silicon macOS, Node v24.22.1, Chromium 154.0.8037.93, Playwright 1.56.1. Browser command exit **0**. All four Node syntax checks exit **0**. Raw receipt and 26 screenshots are in the local external evidence directory named `cutting-room-r0.iU1wk8Hl` under `~/.contentos/checkpoints/`; screenshots are not committed. `1440-dark-<route>.png` and `390-light-<route>.png` cover all seven destinations and all three contextual workspaces. Mission Control also has both themes at 1024 and 320 CSS px, plus the opposite themes at 1440 and 390. Inspected desktop and narrow mobile Mission Control while iterating.

- HTTP: five exact paths over GET/HEAD; forbidden route, parent path, source and query variants rejected; wrong method and Host rejected; CSP header present and no redirect.
- Browser: 80 combinations (10 routes × 1440/1024/390/320 × light/dark), no page overflow and zero reported axe violations in the selected WCAG A/AA rule tags. Nine computed design-token contrasts per theme passed declared thresholds; minimum tested text contrast 7.89:1, minimum tested focus/control contrast 3.55:1. Mobile skip link, Escape/focus return, route focus, reduced-motion dialog, and Indic sample text exercised; automated results are not WCAG conformance.
- Journeys: ready/blocked creation and simulated save; 20-row validation, partial capability drift, interruption/recovery, replay and retry; campaign cancellation and pinned rebase; stale grant, storyboard scrub, independent filters and per-cut export outcome; recovery and reset. All fixture-only, with no database or file writes by the app.
- Network: Playwright deny-by-default intercepted requests and WebSockets, and monitored responses, redirects, frames, popups/downloads and CSP violations. Zero non-fixture attempts or CSP violations on normal test paths. A deliberate fixture-origin API `fetch` was stopped by CSP before reaching the Playwright request interceptor. A deliberate external navigation was caught and aborted by that interceptor before contact. The borrowed test script is injected by browser automation only; served app CSP was not relaxed. No credentials, cookies, local/session storage, IndexedDB, Cache Storage or service worker registration observed by the checks. This is fixture and harness evidence, not a claim that arbitrary code or a browser extension cannot navigate.
- Scope: baseline diff check found no production code/configuration delta. R0 server loads only its five own assets; stopping it closes only that loopback listener. No production service uses the prototype. No PR was merged.

## Earlier runs retained

- `cutting-room.aAVvd0/check.log`: exit 1; the installed Playwright default browser revision was missing. Used installed Chrome instead of downloading.
- `cutting-room.HxLQJT/check.log`: exit 1; CSP rejected the initial inline axe test injection. Moved it to the browser automation initialization hook without relaxing fixture CSP.
- `cutting-room.DkazhA/check.log`: exit 1; contrast audit during theme transition. Final audit waits for visual transitions to settle.
- `cutting-room-r0.EUkE0Gk1/check.log`: exit 1; the token contrast checker incorrectly parsed `#fff`. Corrected the test's shorthand expansion.

## Pending owner / independent review

No independent operator task study, Precision Workbench comparison, manual screen-reader pass, manual 200% zoom pass, or Safari/Firefox verification in this run. Storyboard evidence is original vector illustration and transcript, not playable media; durability, authentication, export and recovery outcomes are simulations. R1 and all production integration remain unimplemented and unauthorized.
