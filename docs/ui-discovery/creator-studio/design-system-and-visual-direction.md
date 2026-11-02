# Design system and visual direction

UI/UX Pro Max v2.15.0 was queried on 2026-10-20. The generated systems are recommendations, not repository truth. No result was persisted.

## Directions evaluated

| Direction | Skill result | Strengths | Rejection or selection |
|---|---|---|---|
| Creator workbench | Minimalism and Swiss Style; variance 3, motion 2, density 6 | Strong hierarchy, low implementation cost, accessible in both themes, and enough density for Jobs | **Selected.** It keeps review and the next safe action above operational chrome |
| Production console | Flat Design; variance 4, motion 2, density 8 | Efficient tables and diagnostics | Rejected as the product-wide direction. It optimizes Queue and logs, makes touch targets and error wrapping harder, and turns review into a secondary task |
| Editorial review | Bento Box Grid; variance 6, motion 3, density 4 | Large video surface and visual distinction | Rejected as the global structure. Asymmetric cards reorder poorly on narrow screens and create page-specific span rules. The large review surface is retained inside the Review tab |

The skill's generated commerce patterns (ratings, purchase CTAs, and funnel steps), amber palette, Playfair body type, and GSAP scroll reveals were rejected as off-topic. Creator Studio is an authenticated workbench, not a conversion page. The console's blue palette was usable, but changing the established indigo accent did not improve state comprehension. Inter was accepted conceptually; the implementation keeps the local system stack to avoid a font download.

## Chosen direction: Precision Workbench

The Studio feels like a professional editing bench with the restraint of a developer tool:

- quiet, full-width work surfaces instead of a card mosaic
- one dominant next action per page
- large media only where review is the task
- compact operational rows with 44 px minimum interactive targets
- borders for structure and no decorative shadows, gradients, charts, or scroll reveals
- 150–200 ms color and opacity feedback; no layout animation

## Tokens

Keep the existing dashboard token names. Components use tokens and never raw colors.

| Token | Dark | Light | Purpose |
|---|---|---|---|
| `--bg` | `#0b0d12` | `#f5f6f9` | Page canvas |
| `--panel` | `#12151c` | `#ffffff` | Work surfaces |
| `--line` | `#2b3140` | `#d7dce6` | Borders and separators |
| `--tx` | `#f1f3f7` | `#171a23` | Primary text |
| `--mut` | `#a0a8ba` | `#59637a` | Secondary text |
| `--acc` | `#8b93ff` | `#4338ca` | Primary action, link, focus |
| `--ok` | `#34d399` | `#047857` | Completed |
| `--run` | `#fbbf24` | `#854d0e` | Running |
| `--fail` | `#fb7185` | `#be123c` | Failed |
| `--blk` | `#fb923c` | `#c2410c` | Waiting on a gate |
| `--stale` | `#c084fc` | `#7e22ce` | Stale |
| `--pend` | `#94a3b8` | `#475569` | Pending and not run |

Measured against `--panel`, every text/status token above exceeds 4.5:1 in both themes. Status still uses a word and icon because color never carries meaning alone.

- Type: `-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif`; `ui-monospace, "SF Mono", monospace` for ids, paths, commands, and logs.
- Scale: 12 px metadata only; 14 px compact controls; 16 px body; 20 px section; 28 px page title. Body line height is 1.5.
- Spacing: 4 px base with 8, 12, 16, 24, and 32 px steps.
- Radius: 8 px controls, 12 px panels, and a full pill only for short statuses.
- Elevation: borders by default; one subtle overlay shadow for dialogs.
- Focus: 2 px `--acc` outline with 2 px offset and 3:1 state contrast. Sticky headers use `scroll-padding-top` so focus is not obscured.

## Search evidence accepted

| Query | Top verified result | Applied rule |
|---|---|---|
| `badge chip label wraps` | Compact Label Overflow | Keep one status on one line; truncate only unpredictable values and provide operable full-text disclosure |
| `focus not obscured` | Focus Not Obscured | Offset sticky UI and keep focused controls visible |
| `error summary validation` | Focusable Error Summary | Focus a linked summary after failed submit while retaining inline errors |
| `empty state next action` | Empty States | Explain what is absent and provide one next action |
| `dense data table responsive` | Table Handling | Use a card list on narrow screens; reserve horizontal scroll for logs and path data |

The `html-tailwind` compact-label result was translated to plain CSS: a collection may wrap; one pill uses `white-space: nowrap`, a shrinkable text span, and a non-shrinking icon. Tailwind is not introduced.

## Visual rules

- Long job ids use monospace and middle truncation in a row; focus, click, or a copy control reveals the full value.
- Status labels stay whole. Collections of labels wrap with an 8 px gap.
- Multiline errors wrap normally, preserve line breaks, and never increase a table row without an explicit Details region.
- Tables use stable column widths at desktop. Below 720 px, each row becomes a labelled record rather than a squeezed table.
- Video containers reserve 9:16 or 16:9 space before media loads to prevent layout shift.
- Empty states contain a heading, one explanatory sentence, and one action. They do not use decorative illustrations as a substitute for instructions.

## Components that carry the product

| Component | Responsibility |
|---|---|
| `NextActionCard` | One sentence, one primary button, and one secondary link |
| `StageTimeline` | Nine fixed stages, duration, provider, and gate or error text |
| `GateApprovalPanel` | Shows the artifact being approved and explains the digest binding |
| `VideoReviewPanel` | Playback, duration, dimensions, frames, and QA provenance |
| `HealthCapabilityRow` | Live provider state plus the existing remediation text |
| `LogViewer` | Escaped text, wrap, copy, and download |
| `JobTable`, `QueueTable` | Shared status, empty state, and row navigation |
| `ConfirmationDialog` | Native `<dialog>` stating the consequence before a grant or replacement |

Forms use a visible label, helper text, and `aria-describedby`. Failed submit focuses a summary whose links move to each invalid field; inline errors remain. Focus moves into a dialog and returns to the control that opened it. Motion is limited to 150–200 ms opacity or color and is removed under `prefers-reduced-motion`.

## Accessibility acceptance

- Every action is reachable by keyboard and shows a 2 px accent outline.
- Interactive targets are at least 44 by 44 px with 8 px separation.
- Inputs have labels and errors that name the field.
- Heading levels follow the page hierarchy.
- Polling uses one contextual `role="status"` announcement only when the job state changes, not for each chip or 2-second refresh.
- Focus remains visible below sticky navigation and banners.
- Reduced motion, contrast, label wrapping, and focus are checked in both themes at 1280, 900, and 390 px.

## Prototype versus product

Prototype screens may use the same tokens and components, but every fixture carries a visible "Sample data" label. A prototype control must not call `./contentos.sh`.
