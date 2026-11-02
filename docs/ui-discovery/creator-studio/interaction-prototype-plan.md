# Interaction prototype plan

The prototype proves the primary journey with fixtures. It does not start `./contentos.sh`, write a ledger, or modify a job folder. Every screen displays "Sample data".

## Design direction

Use the Precision Workbench system from `design-system-and-visual-direction.md`. The prototype tests visual hierarchy and state comprehension, not decorative range:

- Jobs and Queue use stable rows and labelled mobile records.
- Script uses a reading column with a companion approval panel.
- Review reserves the correct video aspect before media loads.
- Health is a diagnostic list, not a set of success cards.
- Motion is limited to 150–200 ms color or opacity feedback and disappears under reduced motion.

## Fixture set

| Fixture | What it demonstrates |
|---|---|
| `draft` | Valid unsaved spec and one invalid spec with a focusable summary |
| `blocked-script` | Timeline stopped before voice, script visible |
| `running-render` | Lock held, render row older than 600 seconds, still Running |
| `failed-transient` | Voice failed, attempt 2 of 3, multiline error, next action is wait or resume |
| `blocked-production` | Composition exists, production digest is ready to grant |
| `qa-failed` | Video exists, one QA check failed, approval unavailable |
| `stale` | Old RUNNING row and no lock |
| `ready` | QA passed, both grants match, export path shown |
| `layout-stress` | 128-character job id, long title, five status labels, long path, and unbroken tool output |

Use one portrait 9:16 job and one landscape 16:9 job. Include dark and light themes and layouts at 1280, 900, and 390 px. Each fixture carries a persistent "Sample data" label in the page header and fixture selector; changing fixtures never changes repository state.

## Scenes

1. Jobs to New Job. The invalid id, 1:1 format, and empty script cannot continue. The valid spec reaches a draft summary that names a workspace path but does not write it.
2. Script approval. The owner can read the title and lines, open the dialog, and see the consequence. The blocked job does not use failure styling.
3. Progress and failure. Running shows stage text and elapsed time, not a percentage. A second Run control is absent while the fixture says the lock is held. Blocked, failed, and stale fixtures each choose a different next action.
4. Review and export. The sample video can be played from a local fixture file. QA rows distinguish pipeline, manual, and not-run checks. Export confirmation names the sample destination. There is no Publish control.
5. Health. A dead-FFmpeg fixture shows "not runnable" and the Homebrew remediation. Run is unavailable in that state.
6. Layout stress. Long ids truncate in rows and remain operably discoverable, statuses wrap as a collection but not inside a pill, errors preserve line breaks, and paths wrap without page overflow.

## Fixture implementation recommendations

- Keep fixture records in one frozen ES-module data file. Pages receive copies and cannot mutate the source object.
- Route fixture actions through a fake adapter whose method names mirror the proposed API. It returns deterministic success, 409 digest mismatch, blocked, transient failure, and process-error responses.
- Use an inert local media fixture with native controls and `preload="metadata"`. Do not auto-play it.
- Give loading skeletons the final component dimensions to avoid layout shift.
- Make theme and fixture selection prototype-only controls labelled as such. They do not appear in product navigation.
- Keep fixture labels and simulated-action banners in screenshots so prototype evidence cannot be mistaken for the real application.

## Responsive checklist

- [ ] No horizontal page scroll at 1280, 900, or 390 px.
- [ ] Desktop tables become labelled records below 720 px.
- [ ] The timeline changes from horizontal to vertical below 900 px.
- [ ] Long job ids, paths, titles, and multiline errors do not overlap actions.
- [ ] A status label stays on one line; a collection of statuses may wrap with an 8 px gap.
- [ ] 9:16 and 16:9 containers reserve their aspect ratio before media loads.
- [ ] The 9:16 player fits the 390 px viewport without hiding native controls.
- [ ] Touch targets remain at least 44 by 44 px with 8 px separation.

## Accessibility checklist

- [ ] Keyboard reaches every visible action in DOM order.
- [ ] Focus is visible and never hidden by sticky navigation or banners.
- [ ] Approval dialogs focus their heading and return focus to their opener.
- [ ] Failed submit focuses one linked error summary; inline field errors remain associated.
- [ ] Status uses a word and icon and remains distinguishable in grayscale.
- [ ] Polling and fixture changes use one contextual status announcement instead of announcing every badge.
- [ ] Native video controls work without a pointer and media does not auto-play.
- [ ] Reduced motion removes all non-essential transitions.
- [ ] Dark and light text, muted text, accents, and statuses meet the documented contrast ratios.
- [ ] Heading levels, labels, descriptions, and table-to-record semantics stay meaningful at every width.
- [ ] No control promises cancel, persisted reject, publish, or a paid provider.

## Visual review matrix

Capture Jobs, New Job invalid, Overview running, Script blocked, Review QA failed, Queue, Health blocked, and Logs failed. Review each at 1280 and 390 px in both themes. Add 900 px checks for Overview, Script, and Review because those pages switch layout there.

## Tooling

Build the prototype as static HTML and ES modules that can be opened without a pipeline. Use the browser already available on the machine. If browser automation cannot start, record that limitation and use manual Chrome review. Do not install Playwright to produce the prototype.

## Exit criterion

A reviewer who has not read the source can distinguish draft, running, blocked, failed, stale, rendered, checked, approved, and exported, and can point to the next safe action for each fixture. The layout-stress fixture passes both checklists, and no prototype interaction reaches the CLI or workspace.
