# Screen specifications

Navigation is Jobs, Queue, Health, and Help. New Job and the job workspace are contextual. Every status uses an icon and text. Unsupported operations are absent.

## Application shell

- Desktop uses a 224 px rail and a fluid work area capped at 1440 px. The work area, rather than the rail, scrolls.
- At 900 px the rail becomes a compact top bar. At 390 px the four destinations remain visible in a bottom-free top navigation so video controls do not compete with fixed UI.
- The page title, current section, Health blocker, and one global notice appear before page actions.
- Sticky chrome sets `scroll-padding-top`; focus must remain visible when a field or row is targeted.

## Jobs

- **Goal and primary action:** find the job that needs attention; open it or start New Job.
- **Hierarchy:** next-action state, title, stage progress, id, format, and updated time. The table has no KPI header.
- **Components:** search, state filter, `JobTable`, nine compact stage marks, status label, New Job button.
- **Layout:** stable desktop columns. Title and state keep priority; the id column has `min-width: 0` and middle truncation. Activating or focusing the id exposes the full value and copy action.
- **States:** skeleton rows with reserved height; an empty state with one New Job action and the CLI equivalent; ledger-unreadable banner; populated list.
- **Responsive:** below 720 px each row becomes a labelled record. Stage marks wrap as a collection; one status pill never wraps internally.
- **Accessibility:** the job title is the row link. Status changes are not independent live regions. Search has a visible label.
- **Data:** `GET /api/v1/jobs`, joined on spec `content_id`.
- **Hidden:** analytics cards, publish actions, paid-provider filters, and bulk actions.

## New Job

- **Goal:** write a valid Track A spec inside the workspace.
- **Hierarchy:** step title and consequence, fields, validation summary, Back/Continue. Steps are identity and format, voice, script lines, and review.
- **Components:** labelled inputs, native radio/select controls, script-line editor, narration estimate, error summary, inline errors, review panel.
- **Layout:** one readable form column up to 720 px. Script rows may use two columns at desktop and one at 390 px.
- **States:** untouched; validating; invalid with a focusable linked summary and inline errors; id collision with Open existing job; valid; saved with workspace path.
- **Responsive:** buttons stack at 390 px with Continue first in DOM order. Long paths wrap using `overflow-wrap: anywhere`.
- **Accessibility:** failed submit focuses the summary once. Blur validation never steals focus. Every error is referenced through `aria-describedby`.
- **Validation:** id pattern, 9:16 or 16:9, known Kokoro voice, at least one spoken line, and script lint. HyperFrames is the only lane.
- **Hidden:** Remotion, MPT, feature hooks, and `--approve-private`.

## Job workspace

The page starts with `NextActionCard`, then the timeline, then Overview, Script, Review, Logs, and Files. The job id is secondary to the title and remains copyable.

### Overview and stage timeline

- **Goal:** understand what happened and the next safe action.
- **Hierarchy:** next action, nine stages, current attempt, prior runs.
- **Components:** `NextActionCard`, `StageTimeline`, attempt summary, run history disclosure.
- **Layout:** horizontal connected stages at 900 px and wider; a vertical ordered list below 900 px. The current stage receives the strongest emphasis.
- **States:** running polls every 2 seconds; blocked names the gate without failure styling; failed names the class and multiline error; stale requires an old row and a free lock.
- **Responsive:** provider and duration move below the stage name. Errors use a Details region and do not stretch every timeline row.
- **Accessibility:** the timeline is an ordered list. One contextual `role="status"` announces a real state change. No fake percentage.
- **Action:** Run or Resume calls `production run` once. A held lock returns Already running.
- **Hidden:** Cancel and percentage progress.

### Script review and approval

- **Goal:** review the exact title and spoken lines bound by the grant.
- **Hierarchy:** approval state, title, script, lint evidence, consequence, Approve.
- **Components:** digest-state banner, readable script article, lint panel, `GateApprovalPanel`, native confirmation dialog.
- **Layout:** script is the primary column; approval evidence is a 320 px companion column at desktop and follows the script below 900 px.
- **States:** not written; lint warning; waiting for approval; digest mismatch; approved for the current digest.
- **Responsive:** script line numbers stay fixed while spoken text wraps. The digest is secondary monospace text and may wrap.
- **Accessibility:** the article has headings by scene. The dialog initially focuses its heading, describes the consequence, and returns focus to Approve.
- **Action:** the request carries the displayed digest and the server recomputes it.

### Video review and production approval

- **Goal:** inspect the composition or rendered output and its evidence before approval.
- **Hierarchy:** video, next action, blocking QA, all checks, preview frames, technical metadata.
- **Components:** `VideoReviewPanel`, QA summary and rows, provenance tags, frames, `GateApprovalPanel`, export status.
- **Layout:** at desktop the reserved-aspect video occupies two-thirds and evidence one-third. A 9:16 video has a bounded height and centered canvas; 16:9 uses the available width.
- **States:** no composition; no render; rendered with checks not run; checking; PASS/WARN/FAIL; digest mismatch; approved; exported.
- **Responsive:** below 900 px evidence follows the player. Preview frames use a horizontal scroller with labelled position; no auto-play.
- **Accessibility:** native video controls, captions when available, click-to-play, and no auto-play. Checks say pipeline, manual, or not run. A color is never the result.
- **Action:** production approval appears only after the composition digest and preview evidence are displayed.

### Logs and failure diagnosis

- **Goal:** understand a failed stage without returning to the terminal.
- **Hierarchy:** failure summary, stage/provider/times, ledger error, captured log when available.
- **Components:** stage selector, severity label, multiline error, `LogViewer`, wrap/follow controls, copy and download.
- **Layout:** metadata remains compact; log content is the only horizontal scroller.
- **States:** no failure; ledger error only; loading log; captured log; unavailable log with an honest explanation.
- **Responsive:** controls wrap as a group; labels stay whole. The monospace viewport has a bounded height.
- **Accessibility:** log text is selectable and escaped. Follow mode can be paused and does not repeatedly announce appended lines.

### Files and export

- **Goal:** inspect artifacts and export the validated result.
- **Hierarchy:** final output, export action, then intermediate artifacts.
- **Components:** artifact records, size/type metadata, copy-path control, export confirmation.
- **Layout:** paths occupy a flexible column and may wrap anywhere; actions do not shrink.
- **States:** no artifacts; partial artifacts; ready to export; replacing an existing export; exported with destination.
- **Responsive:** records stack below 720 px.
- **Accessibility:** copy confirms through one polite status message. Export confirmation names the exact destination.
- **Hidden:** delete.

## Track B intake

- **Goal:** attach a hand-built HyperFrames job that already exists in the workspace.
- **Hierarchy:** job id, discovered composition, script line count, scene-plan schema result, link into the job workspace.
- **Components:** one text field, error alert, evidence summary.
- **States:** missing job, missing composition, invalid scene plan, intake complete.
- **Action:** `POST /track-b/intake` with the job id only. There is no filesystem path field and no composition editor.
- **Hidden:** paid providers, private approval, publish, and Track A Run.

## Track B job workspace

The job header shows a Track B label. Track A Run and one-stage rerun are absent. The next action is script review, voice, alignment, composition review, render, diagnostics, or export.

- **Script:** spoken lines plus the scene-plan schema result, then the existing digest approval dialog.
- **Review:** composition path, preview frames, and the video player. Production approval stays bound to the current digest.
- **Diagnostics:** voice, alignment, render, technical QA, visual plan, visual check, rendered scenes, critic, and registration stay separate. `NOT_RUN` remains visible. External ledger rows use the External label.
- **Export:** the existing confirmation. The result reports the ready-library path. Publishing stays off.

## Queue

- **Goal:** inspect queued, running, blocked, failed, and done rows.
- **Hierarchy:** active job, waiting jobs, jobs requiring action, recent completion.
- **Components:** state filter, `QueueTable`, add validated spec, Requeue on eligible rows.
- **Layout:** production-console density is used here only: 44 px rows, compact metadata, no dashboard cards.
- **States:** empty with Add job; running; blocked; failed; done.
- **Responsive:** table becomes labelled records below 720 px. It does not force the full table into a narrow horizontal viewport.
- **Accessibility:** requeue names the job. A running row explains that cancellation is unsupported.
- **Constraint:** concurrency is one.

## Health and capabilities

- **Goal:** explain why a job can or cannot run.
- **Hierarchy:** blocking prerequisites, storage, optional capabilities, last check.
- **Components:** page-level blocker, `HealthCapabilityRow`, storage-root rows, Re-check.
- **Layout:** a single list rather than green KPI cards. Each row places status first, then provider and remediation.
- **States:** checking; healthy; required missing; optional missing; probe error; storage refused.
- **Responsive:** remediation commands wrap in a code block with copy. Long paths wrap anywhere.
- **Accessibility:** PASS, OPTIONAL, and NOT_INSTALLED are words. Re-check announces one completion message.
- **Behavior:** results cache for at most 60 seconds. A dead FFmpeg result disables Run and links here.

## Help

- **Goal:** map each screen to the CLI operation it wraps.
- **Content:** primary journey, gates, publish-disabled statement, and CLI-only commands.
- **Layout:** readable document width with deep links.
- **Behavior:** static and network-free.

## Responsive acceptance

- 1280 px: navigation rail, desktop tables, horizontal timeline, split review.
- 900 px: top navigation, vertical timeline, single-column approval and review.
- 390 px: labelled records, full-width controls, reserved 9:16 player, no horizontal page scroll.
- Dense tables, long ids, multiline errors, paths, and status collections must be exercised at all three widths in both themes.
