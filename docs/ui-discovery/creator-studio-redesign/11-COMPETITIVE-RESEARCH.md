# 11 / Competitive and workflow research

**Research date:** 2026-11-24. **Scope:** official public docs, not product trials or market claims. **Evidence / sources:** linked pages retrieved without authentication, unless limitation noted. **Verified findings:** products document the affordances below; proposed adaptations are hypotheses, not copied interfaces.

| Source and observed pattern | Transfer to Studio | Deliberately omit / test |
|---|---|---|
| [Resolve](https://www.blackmagicdesign.com/products/davinciresolve): separate cut, edit, color, audio and deliver workspaces | Dedicated stage workspace around a shared artifact, with evidence pane, predictable actions and media-first hierarchy | Don't build an NLE or model clips before having stable artifacts |
| [Premiere](https://www.adobe.com/products/premiere.html): edit, trim, audio and postproduction context | Active media stays central; scoped tools and outputs on edges | No transport controls without media; don't copy timeline gestures |
| [Frame.io](https://frame.io/): central assets, feedback and versions | Bring evidence and exact subject revision into one review surface | No collaboration accounts or public proof links; temporal notes only if separate from grants |
| [Runway Gen-4](https://runway.com/research/introducing-runway-gen-4): reference-driven consistency as generation input | Distinguish reference analysis, plan, and generation readiness; keep intent reusable | No claim of model parity or generation; support guide returned 403 |
| [Descript](https://www.descript.com/video-editing): edit by editing text | Caption and script review beside relevant media when alignment evidence exists | No claim that script edit changes rendered frames in place |
| [Canva developer autofill](https://www.canva.dev/docs/connect/api-reference/autofills/create-design-autofill-job/): template-plus-fields producing asynchronous work | Show effective template/brand field mapping before submit; receipt instead of waiting on form | Tutorials returned 403; cannot claim interactive Bulk Create tested. No external Canva or plan dependency |
| [Notion](https://www.notion.com/help/views-filters-and-sorts): alternate views of a single database | Campaign grid/list are views of same episodes; consistent filters and identities | Don't create a generic workspace builder |
| [Linear Triage](https://linear.app/docs/triage): operator inbox separates actionable work | Prioritize exact approval and failure next actions, not KPI counts | No invented priorities or urgency from uncontrolled queue age |
| [Airflow](https://airflow.apache.org/docs/apache-airflow/stable/ui.html): grid, graph and task-log views | Show stage attempts and controlled retry scope; job details link to real logs | No editable DAG, success inference or stage-percent approximations |
| [Temporal Web UI](https://docs.temporal.io/web-ui): execution-centric visibility | Run history grouped by job and discrete events; stable IDs when recovering | Do not introduce Temporal or a distributed worker bus |
| [OpenAI Agents tracing](https://openai.github.io/openai-agents-python/tracing/): receipts for handoffs and actual tool activity | Show provenance for real tasks and manual handoff completion | No fabricated live stream, hidden model reasoning, secret-bearing trace payloads or agent power to grant approvals |

**Assumptions:** imported patterns solve existing user tasks without increasing the app's execution authority. **Open questions:** compare task completion in fixture prototype, not visual preference alone. [Screen rationale](05-SCREEN-SPECIFICATIONS.md) · [Motion/component audit](12-REACTBITS-MOTIONSITES-AUDIT.md).
