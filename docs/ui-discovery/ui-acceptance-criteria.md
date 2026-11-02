# UI acceptance criteria (Phase 4)

Each criterion is testable and names the existing guard it relies on. "Backend needed" marks criteria that cannot pass until a gap in test-coverage-gaps.md is closed. Journey ids are from user-journeys.md.

## Global
- AC-G1 The UI binds 127.0.0.1 only and rejects a request whose `Host` header is not `127.0.0.1:<port>` or `localhost:<port>`.
- AC-G2 Every state-changing request needs a per-server-start token header; a request without it returns 403 and changes nothing.
- AC-G3 The UI offers no control for `--allow-paid`, `PUBLISH_APPROVED`, `publish`, or any paid provider. Publishing is shown as "disabled by config" with the config value read live from `config/youtube.yaml`.
- AC-G4 The UI never prints a value from `~/.contentos/secrets/` or an environment variable; health shows names and PASS/FAIL only.
- AC-G5 Every path the UI returns or accepts stays inside the workspace or publishing roots; a job id that fails `storage.valid_job_id` returns 400.
- AC-G6 Reloading the page, closing the tab or restarting the UI server never changes job state; state is re-derived from the ledger and job manifest.
- AC-G7 The CLI works unchanged: `./contentos.sh doctor|status|pipeline run|approve` give the same output and exit codes before and after the UI lands (diff of recorded outputs).
- AC-G8 Keyboard-only use reaches every action; focus is visible; status never relies on color alone; zero serious/critical axe violations on each screen.

## Health (J1)
- AC-H1 Shows each capability (`tts stt render llm youtube_read publish_youtube decision`), its selected provider or "none", and every candidate with PASS / OPTIONAL / NOT_INSTALLED plus the existing fix hint. (Backend needed: structured doctor, G10.)
- AC-H2 When ffmpeg is a dead binary (as on 2026-10-20), shows "ffmpeg: not runnable (Bad CPU type)" with the Homebrew fix and disables Run for new jobs; it does not 500.
- AC-H3 "Re-check" re-runs probes and shows the check time; probes are cached no longer than 60 s.
- AC-H4 Shows workspace and publishing roots, writable yes/no, and refuses to display an in-repo root as healthy.

## Create and validate (J2-J4)
- AC-C1 The wizard produces a Track A spec containing only fields the pipeline reads (`content_id`, `title`, `format` 9:16|16:9, `voice`, `script[].say`, optional `headline`, `tag`, `render`) and writes it under the workspace, never the repo.
- AC-C2 `content_id` is checked live against `[A-Za-z0-9][A-Za-z0-9._-]{0,127}` and for an existing job; a collision offers "open existing job" and warns that a changed spec under the same id can reuse stale audio (see user-journeys J5).
- AC-C3 Validate returns structured errors with a field path and message (invalid format, unknown voice, empty script, script lint failures from the existing `script` stage lint, unknown `render` lane). Invalid specs cannot be run. (Backend needed: validate endpoint, G9.)
- AC-C4 The narration length estimate at 2.5 words per second is shown against the platform budget from `production.platforms`, not a number hard-coded in the UI.
- AC-C5 Remotion and MPT are selectable only if Health reports them PASS, and are labelled experimental.

## Run and observe (J5-J9)
- AC-R1 Run starts exactly one backend run per job; a second click while `.run.lock` is held shows "already running" and starts nothing.
- AC-R2 The stage timeline shows the nine `STAGES` in order with status OK / SKIP / RUNNING / FAIL / BLOCKED / STALE / PENDING, provider, duration, and the error string for FAIL/BLOCKED.
- AC-R3 When a run stops at a gate the job shows BLOCKED with the gate name and the artifact to review; no failure styling.
- AC-R4 A `transient` failure shows "retried n of 3" from the production core result; an `output` or `blocked` failure shows no retry button and says why.
- AC-R5 A job RUNNING for more than 600 s with no live process is shown STALE (existing rule) with "Recover" that calls the existing recover path; it never auto-reruns.
- AC-R6 Cancel appears only after the backend supports it; until then the UI says "cannot be cancelled" and explains that the stage will finish or time out. (Backend needed.)
- AC-R7 Batch: the Queue screen lists ledger `jobs` rows (queued, running, done, failed, blocked), supports add and requeue, and runs at concurrency 1. It never offers "approve private" without the confirmation in AC-A3.

## Logs and failures (J8)
- AC-L1 For a failed stage, shows the ledger error, the stage, provider, start/end, and the log file for that stage. (Backend needed: per-stage logs, G8.) Until then it shows the ledger error and says full logs are not captured.
- AC-L2 Log text is escaped (no HTML injection from tool output), capped in size with "download full", and secrets-looking tokens are masked by the backend before sending.

## Review and artifacts (J10-J11)
- AC-V1 Plays `video.mp4` with seeking (HTTP Range works), shows duration, resolution, size, and QA rows (9 checks) with PASS/WARN/FAIL; the two known WARN-only checks (loudness, frozen frames on text slides) are labelled non-blocking.
- AC-V2 Quality results show provenance per row: "run in pipeline" (QA, finalcheck) or "run manually" (visual gate, critic, Rule A/B), with the run time. Rows that were never run are shown as "not run", not as passed.
- AC-V3 A contact sheet and preview frames are generated only into the workspace through the existing `preview` command, and are listed under artifacts.
- AC-V4 A failing gate shows its measured value and threshold; provisional thresholds (Milestone 1 notes) carry a "provisional" tag.

## Approvals (J12)
- AC-A1 Approve SCRIPT_APPROVED is enabled only after the script and title were displayed in the same page view; the request carries the digest the user saw; the server recomputes `gate_digest` and rejects with 409 if it differs.
- AC-A2 Approve PRODUCTION_APPROVED requires the composed project digest in the same way and shows the preview frames first.
- AC-A3 "Run without gates" (`--approve-private`) is off by default, requires typing the content_id, and is shown in the job history as "private unattended grant".
- AC-A4 Editing a script after approval shows "approval no longer matches" (existing digest mismatch BLOCKED message) and requires a new approval.
- AC-A5 There is no Reject that pretends to be recorded. Until a backend reject exists, "Request changes" is a local note and is labelled as such.

## Export and destructive actions (J13-J14)
- AC-X1 Export calls `storage export` and reports the `ready/` path and sidecar; `force` needs a confirm naming the file that would be replaced.
- AC-X2 `storage cleanup` / `recover` show their dry-run listing first; Apply needs typed confirmation and is absent in UI v1 (CLI-only).
- AC-X3 No UI action deletes a file in v1.
