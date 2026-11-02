# Design system (Phase 6)

Starting point is `contentos/dashboard.html` (verified): CSS variables `--bg --panel --line --tx --mut --ok --run --fail --blk --pend --acc`, dark by default with a `prefers-color-scheme: light` override, system font stack (`-apple-system, "SF Pro Text", system-ui`), 14 px / 1.45 base, 14 px panel radius, sticky header, max width 1180 px. Keep these names so the migration is additive.

## Tokens
| Token | Dark | Light | Use |
|---|---|---|---|
| `--bg` | #0b0d12 | #f5f6f9 | page |
| `--panel` | #12151c | #ffffff | cards, tables |
| `--line` | #232836 | #dfe3ec | borders |
| `--tx` | #e6e9f0 | #171a23 | text |
| `--mut` | #8b93a7 | #667089 | secondary text (check contrast >= 4.5:1 on `--panel`; verify in the a11y tier) |
| `--ok` `--run` `--fail` `--blk` `--pend` | #34d399 #fbbf24 #f87171 #fb923c #3a4156 | same hues, darkened until 3:1 against `--panel` for non-text and 4.5:1 for text | status only |
| `--acc` | #818cf8 | darker variant for 4.5:1 | links, primary buttons, focus ring |
Rule: status colours never decorate; every status also has an icon shape and a word (OK, Running, Failed, Blocked, Stale, Pending).

Type: system sans for UI; `ui-monospace, "SF Mono"` for ids, paths, commands and logs. Scale 12 / 14 / 16 / 20 / 28 px; headings 600 weight; 12 px uppercase only for section labels as today.
Spacing: 4 px base; 8/12/16/24/32. Radius 8 (controls), 14 (panels). Shadows: none; borders carry elevation.

## Components
- **Stage chip / timeline**: 9 fixed positions in pipeline order, icon + label + duration; BLOCKED uses the gate name ("Waiting: SCRIPT_APPROVED"), not the word failed.
- **Next-action card**: one sentence, one primary button, one secondary link. Appears at the top of Job detail; it is the only place the primary accent button is used on that page.
- **Table**: sticky header, 40 px rows, row is a link, columns: title, id (mono), state, stages (9 mini chips), updated. Sort by updated.
- **Form**: label above field, helper text below, error text replaces helper, `aria-describedby` wiring; live validation on blur.
- **Dialog**: native `<dialog>`; destructive or gate-granting actions require reading a one-line consequence; typed confirmation only for `--approve-private` and `--force`.
- **Toast**: used only for completed background actions; errors that need action stay inline.
- **Log viewer**: monospace, wrap toggle, tail follow toggle, copy, download; escaped text only.
- **Banner**: page-level (Health failure, server unreachable); not dismissible while the condition holds.
- **Empty state**: says what is missing and the next action, including the CLI equivalent in a code block.

## Behaviour
- Motion: 120 ms opacity/transform only; none when `prefers-reduced-motion`.
- Focus: 2 px `--acc` outline, 2 px offset, never removed.
- Keyboard: `g j` Jobs, `g h` Health, `?` shortcuts; all actions reachable by Tab.
- Notifications: none outside the page in v1 (no push, no sound).
- Dates: local time with ISO on hover; durations as `1m 12s`.
- Responsive: see ui-concepts.md.
