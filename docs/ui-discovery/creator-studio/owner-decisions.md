# Owner decisions

These decisions are not implied by the planning documents. Defaults are what implementation will use if you say to proceed without choosing otherwise.

## 1. Product direction

Default: Creator Studio, with Jobs as the home screen and review plus approval as the main work.

Alternative: an operations grid. It was rejected because batch operation is less common than the two approval gates.

## 2. Frontend stack

Default: extend the Python standard-library server and use vanilla ES modules.

Alternative: React, Vite, and TypeScript. Reconsider only for the conditions in `frontend-architecture-decision.md`.

## 3. Browser-test dependencies

Default for now: manual Chrome review of the fixture prototype. No installation.

Approved and installed as dev-only dependencies: Playwright `1.56.1` and `@axe-core/playwright` `4.10.2`. They are test tools only. `puppeteer-core` is not used. The pinned HyperFrames release remains `0.8.114`.

## 4. Local tools

The current Mac cannot complete the Python suite or a real render while `/usr/local/bin/ffmpeg` is the wrong architecture and Homebrew FFmpeg and whisper.cpp are absent.

Approval needed before M0 can finish green and before M8 can run:

```bash
brew install ffmpeg whisper-cpp
```

Installing those tools is outside this planning package.

## 5. Backend changes required by the Studio

Approve these as product changes, not as drive-by cleanup:

- structured Health output
- `contentos validate SPEC --json`
- per-stage log files
- queue execution through `production run` with a timeout and process-group kill
- lock taken before interrupted-artifact cleanup
- downstream sentinel invalidation for a forced one-stage rerun

The UI will not parse human CLI output when these functions exist.

## 6. Controls intentionally absent

Default: no Cancel, no persisted Reject, and no `--approve-private` button.

A local "request changes" note may exist only if it is labelled as not recorded. A typed confirmation can add `--approve-private` later, but it is not part of the first slice.

## 7. Future VPS

Default: do not deploy this server remotely.

A VPS plan needs its own authentication, HTTPS, authorization, secret storage, resource limits, backups, and renderer capability check. Binding `0.0.0.0` or placing the current token server behind a reverse proxy does not meet that bar.

## Approval to begin implementation

The next implementation prompt is M0 and M1 from this roadmap. It is authorized only after you explicitly accept decisions 2 and 5. Decisions 3, 4, 6, and 7 can keep their defaults.
