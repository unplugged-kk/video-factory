# CLI to UI matrix (Phase 3, updated 2026-10-20)

Source: argparse definitions and command bodies in `contentos/cli.py` and `contentos/storage_cli.py`, plus safe `./contentos.sh --help` output for every public command on 2026-10-20. No job, worker, render, publish, migration, cleanup, or recovery command was executed. Class: A read-only, B local configuration/state change, C job creation/execution, D destructive, E external side effect or paid.

| Command | Class | Purpose and side effects | Repeat-safe | Long | Cancel/resume | UI action |
|---|---|---|---|---|---|---|
| `doctor` | A (shells out to probe tools) | provider health per capability; exit 1 if none selected | yes | seconds | n/a | Health screen, Re-check |
| `status` | A | last ledger rows | yes | no | n/a | Activity list |
| `route CAP [--allow-paid]` | A | selected provider | yes | no | n/a | Within Health; hide `--allow-paid` |
| `storage paths [--check]` | A, B with `--check` (creates and test-writes roots) | show roots | yes | no | n/a | Health, Check button |
| `storage inventory [--json]` | A | job inventory | yes | no | n/a | Jobs library data source |
| `storage ready [--project --status --check]` | A | exported videos, integrity compare | yes | no | n/a | Exports tab |
| `pipeline run SPEC [--force --only --allow-paid --approve-private]` | C (writes job folder, ledger, approvals with `--approve-private`) | one job through stages; stops BLOCKED at gates | resume by artifact; `--force` re-runs | minutes | lock per job; no cancel | Run / Resume / Re-run stage; `--approve-private` only via explicit owner-confirm dialog; `--allow-paid` never |
| `production run SPEC [--approve-private]` | C | same plus interrupted-artifact scrubbing, transient retries and one JSON result line | as above | minutes; 360 s caps starting another retry, not the running render | no cancel | Preferred backend entry for a full Run/Resume; handle non-zero exits that produce no JSON |
| `approve ID GATE [--note --spec]` | B (ledger write, never revoked) | records a gate; digest-bound | duplicates accumulate | no | none | Approve buttons at gates 1 and 2 after showing artifact; PUBLISH_APPROVED hidden or disabled |
| `qa VIDEO [--format]` | A | nine checks | yes | seconds | n/a | Re-run QA on a video |
| `preview TARGET --at --out [--sheet --cols]` | A, writes frames under OUT | frames and contact sheet | yes | seconds | n/a | Review screen, generate to the workspace only |
| `job register PATH --track B [--title --project --project-name]` | B (writes manifest.json, ledger EXTERNAL rows) | adopt a finished Track B folder | already-registered is a no-op | no | n/a | CLI command unchanged. Creator Studio intake takes a workspace job id before a video exists; Register adopts `video.mp4` and writes external rows only for stages the studio did not complete. Voice, align, HyperFrames render, and QA are job-id actions and are refused for Track A. |
| `queue [--approve-private] [--priority N] add SPEC.. / list / requeue ID` | C / A / C | ledger jobs table | add skips duplicates | no | requeue only failed/blocked | Queue panel; do not expose `--approve-private` in the first UI slice |
| `worker [--concurrency N --once]` | C (long-lived process) | runs queue through `production run` | n/a | indefinite, with a queue timeout and process-group kill | no UI cancellation | CLI-owned. Default concurrency is 1. Creator Studio can add and requeue jobs but does not start the worker. |
| `factory-worker [--once] [--port PORT] [--host HOST]` | C (Node worker plus read-only HTTP manifest, default :4300) | ContentForge exchange | n/a | indefinite unless `--once` | n/a | CLI only (parked) |
| `dashboard [--port 4310]` | A (serves) | existing UI | yes | indefinite | Ctrl-C | becomes the UI host |
| `research TOPIC [--days --deep]` | E (network: Reddit, HN) | writes research file | yes | seconds | no | Optional Research panel; confirm network use |
| `competitor URLS` | E (network) | channel analysis | yes | seconds | no | CLI only for now |
| `jev status / triage` | E (calls TypeSafe, cookie, may use credits) | decisions | yes | seconds | no | CLI only; status pill exists |
| `learn {providers,cost,calibration,platforms,packaging}` / `recommend ID [--jev]` | A (`--jev` is E) | reports | yes | no | n/a | Read-only reports, later |
| `storage migrate [--apply]` | B/D (copies, never deletes; dry run default) | move legacy artifacts | dry run yes | maybe | no | CLI only |
| `storage adopt JOB` | B | adopt job | yes | no | n/a | internal |
| `storage export JOB [--force] [--mode {nested,flat}]` | C (copies to publishing library) | validated export | `--force` overwrites | seconds | n/a | Export button, confirm if `--force` |
| `storage cleanup [--apply]` | D with `--apply` | removes expired scratch | dry run yes | maybe | no | Show dry-run result; Apply behind typed confirm, owner approval to delete |
| `storage recover [--apply]` | D with `--apply` | interrupted export leftovers | dry run yes | no | no | same pattern |

Not present as CLI commands (so no UI action without new backend work): validate spec, create spec, cancel job, reject gate, tail logs, structured doctor output, publish.

`pipeline run` is the stage-level escape hatch: a UI-requested re-run uses `--only STAGE --force`. A full attended run and resume use `production run` without `--approve-private`; completed stages resume from their sentinels. Neither CLI provides live progress as structured stdout, so the UI reads stage rows from `ledger.db`.

## Class handling
- A: no confirmation, show loading and last-run timestamp.
- B: show the diff or target path, single confirm.
- C: confirm with job id and track; show stage timeline; disable duplicate run for a job whose `.run.lock` is held.
- D: dry run first, list exact paths, typed confirmation; the harness rule that deletion needs the owner's explicit approval carries into the UI.
- E: label the external call, off by default, no paid options in the UI at all (AGENTS.md: never spend money).

## Stay CLI-only
factory-worker, competitor, jev, storage migrate/adopt, learn loops (until a use case appears), anything with `--allow-paid`.
