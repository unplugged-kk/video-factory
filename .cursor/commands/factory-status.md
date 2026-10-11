Give me a status snapshot of the factory. Read-only — change nothing, and do not run any command with
`--apply`, `--force` or `--approve`.

Read `AGENTS.md` first, then run and summarise:

- `./contentos.sh doctor` — the tool readiness table, flagging anything `NOT_INSTALLED` that a normal short
  video would need.
- `./contentos.sh storage paths --check` — workspace and publishing library present and writable.
- `./contentos.sh status` — the recent ledger rows: what ran, what passed, what failed and why.
- `./contentos.sh queue list` — anything queued, running, blocked or failed.
- `./contentos.sh storage ready` — what has actually shipped to the publishing library.
- The ContentForge worker's heartbeat at `$VIDEO_FACTORY_WORKSPACE/.factory_worker.heartbeat` (pid,
  `heartbeatAt`, `queueDepth`, `activeJob`; a heartbeat older than 60 s means it is not healthy). If the file
  is absent, say the worker is not running rather than guessing.
- `git status --short` and `git log --oneline -5` — report the branch and any uncommitted or untracked work.
  Do not stage, commit, stash or push anything.
- `python -m contentos.production.platforms budget --kind short` — the length ceiling currently in force.

Then report a compact table of what is ready, what is missing, what is stuck, and the one thing you would do
next. Be explicit about anything you could not verify, and do not repair anything without asking me first —
this command only observes.
