# Decision log

**Research date:** 2026-11-24. **Scope:** design decisions only. **Evidence / sources:** owner assignment, [requirements](01-PRODUCT-REQUIREMENTS.md), [capabilities](00-RECONCILIATION.md), [tech recommendation](09-TECHNICAL-DECISION.md). **Verified:** owner constraints are distinct from author recommendations; independent findings below verified against `origin/main` at `8709b0b`.

| Topic | Design branch recommendation | ChatGPT recommendation | Evidence | Resolution / owner approval |
|---|---|---|---|---|
| Audience and ownership | Single operator, one local machine; logical workspace IDs for future | Pending | Owner brief + existing local API | Owner decided, no authentication/fleet build |
| Batch and campaigns | Independent row receipts plus versioned campaign defaults | Pending | [Journeys](03-USER-JOURNEYS.md), queue primitive | Product direction approved; detailed contracts proposed |
| Stack | Keep vanilla ES modules; only isolate later if measured need | Pending | [Stack decision](09-TECHNICAL-DECISION.md) | Owner to ratify |
| Look and feel | Cutting Room, expressive via media and typography rather than heavy animations | Pending | [Design system](06-VISUAL-DESIGN-SYSTEM.md) | Owner visual preference pending |
| Technical vs creative gate | Separate statuses; don't add export gate without approval | Pending | Existing QA evidence and fixture creative revise | Open whether creative review blocks export |
| Scope progression | Read-only and inert prototype first; expanded mutating surfaces only after required integrity work | Pending | [Roadmap](10-IMPLEMENTATION-ROADMAP.md) | Owner to authorize phase after review |

## Independent review dispositions

Source: [complete ChatGPT review at `10ae59f`](https://github.com/unplugged-kk/video-factory/blob/10ae59f5076e10c74266b3aeb2d7f19434051417/docs/ui-discovery/creator-studio-redesign/reviews/chatgpt-review-01.md). All changes are proposed unless labeled existing. The initial table preserves the pre-review state; this table supersedes its Pending entries where applicable.

| Finding / ChatGPT recommendation | Disposition and evidence | Resolution / owner status |
|---|---|---|
| P1 atomic sealed approval and legacy grants | **ACCEPT**. `ui_api.py:_approve` compares from `job_state` before a separate `ledger.approve` insert. `pipeline.py:_check_gate` warns and permits legacy-only `unbound`; `export.py:approval_refusal` already refuses unbound grants, including the case in `test_an_unbound_grant_does_not_satisfy_export`. `ledger.check_gate` accepts any matching historical digest and `revoke` deletes rows today. | [R3 contract](08-API-GAP-ANALYSIS.md): require fresh review, never backfill legacy grants. Use a sealed revision and a core compare-and-grant transaction; history remains evidence, not authority. PF-02 is approved, not implemented. |
| P1 honest attribution | **PARTIALLY ACCEPT**. `write_authorized` checks local Host, Origin and token; `_approve` writes `creator-studio`, not an authenticated person. The review's session label is accurate, but existing [PF-02 policy](../../audit/APPROVAL_POLICY.md) explicitly asks for authenticated human attribution. A session label cannot fulfill that policy. | Use honest local actor labels in the baseline and fixture. Do not introduce accounts, silently weaken PF-02 or enable the redesigned live grant action pending owner clarification of the attribution bar. Keep authenticated private automation separate. |
| P1 inert prototype | **ACCEPT**. `contentos/ui/api.js` is a real client and `ui_api.py:dispatch` exposes writes; a disabled button cannot isolate them. | [R0](10-IMPLEMENTATION-ROADMAP.md) requires separate fixture build, no production connection and a browser deny-by-default test. Prototype authorization still pending. |
| P2 batch durability and drift | **ACCEPT**. `specs.save_spec` writes a file, while `queue.add` separately inserts rows and dedupes only active jobs; `claim/recover` cover worker execution, not admission recovery. `ui_state` health is cached. | [Protocol](08-API-GAP-ANALYSIS.md) uses durable row intents, stable queue keys and reconciles every partial write; independent batch before campaigns. No spec substitution on capability drift. |
| P2 campaign resolution and immutable shared assets | **ACCEPT**. No campaign entity in `ui_state`/API; `mpt.reviewed_request` provides lane-specific hash validation, not shared asset lifecycle. | [Domain](04-DOMAIN-MODEL.md) adds field provenance, exact asset pinning, explicit rebase and missing-asset handling. |
| P2 import threat and budget | **ACCEPT**. `production/assets.py` indexes existing local paths; `dashboard.py`/`ui_api.py` have no managed import endpoint. A local file can still be malformed or exhaust disk and decoder resources. | [API](08-API-GAP-ANALYSIS.md) defines a conservative, proposed budget and isolation; initial families and effective limit measurements pending. |
| P2 creative verdict and export | **NEEDS OWNER DECISION**. `ui_api.py:_export_preview` exposes technical eligibility and `publishEnabled: false`; `export.py` checks attestation and grants, not creative sign-off. | Keep four separate creative verdicts advisory in the blueprint and fixture, not an export gate. An owner-approved future gate would need its own versioned identity and invalidation policy. |
| P2 accessibility validation | **ACCEPT**. `ui/styles.css` and the prior fixture tests apply to current Studio, not Cutting Room; this branch has only Markdown. | [Design acceptance](06-VISUAL-DESIGN-SYSTEM.md) requires numeric contrast and manual browser/keyboard/locale checks. No claim of conformance. |
| Screen and workflow refinements | **ACCEPT**. `ui_state` caches readiness and provides job detail; selector/planner and lookmap are separate from actual render; UI routes and queue support no live agent engine. | [Screens](05-SCREEN-SPECIFICATIONS.md) and [R0](10-IMPLEMENTATION-ROADMAP.md) add freshness, independent filters, evidence chips, mixed rows and drift fixtures. Existing job deep links and current actions remain untouched. |
| Vanilla recommendation and next sequence | **ACCEPT**. Current `contentos/ui` uses same-origin ES modules; no new dependency fixes integrity or persistence. | Keep [vanilla-first](09-TECHNICAL-DECISION.md); owner ratifies visual direction and prototype scope before any code. |

## Review 02 dispositions

[Review 01](https://github.com/unplugged-kk/video-factory/blob/10ae59f5076e10c74266b3aeb2d7f19434051417/docs/ui-discovery/creator-studio-redesign/reviews/chatgpt-review-01.md) remains the historical findings record. [Review 02](https://github.com/unplugged-kk/video-factory/blob/abf2c524893a03af1a0eff9070e1229d37dd421d/docs/ui-discovery/creator-studio-redesign/reviews/chatgpt-review-02.md) reviewed `30dc041` and reported no new P1 blockers **in the documents**. The source baseline remains `8709b0b`. Neither review is implementation verification.

| Recommendation or follow-up | Disposition and rationale | Document / section |
|---|---|---|
| Keep review bytes immutable and identical to the digest subject; no legacy backfill | **Accepted.** Transaction serialization covers pointers and grants, not mutable files. Legacy rows remain history, not sealed authority. | [API: sealed approval](08-API-GAP-ANALYSIS.md#sealed-approval-and-attestation-proposed-r3-contract) |
| Keep redesigned live approvals read-only until trusted attribution satisfies PF-02 | **Needs owner decision.** Baseline local token/channel is not authenticated human identity. Retain the existing requirement and read-only default; no change to today's Studio. | [API: sealed approval](08-API-GAP-ANALYSIS.md#sealed-approval-and-attestation-proposed-r3-contract), proposal D1 |
| Preserve fully isolated R0 and separately authorize R1 | **Accepted** as a scope boundary, not permission. A shared client or proxy reintroduces live access even without mutation buttons. | [R0: isolation](R0-PROTOTYPE-SPEC.md#isolation-contract), [roadmap](10-IMPLEMENTATION-ROADMAP.md) |
| Authorize only the fixture prototype | **Needs owner decision.** A spec can be ready without authorizing any code or server startup. | [R0: scope](R0-PROTOTYPE-SPEC.md#scope-and-non-goals), proposal D6 |
| Prove crash recovery across fsync, queue transaction and receipt delivery; retain exact specs on drift | **Accepted.** Existing queue recovery is not durable admission; a dropped response must not create another job. | [API: independent batch admission](08-API-GAP-ANALYSIS.md#independent-batch-admission-proposed-r4-contract) |
| Keep explicit campaign field provenance, rebase and pinned assets | **Accepted.** Defaults updates cannot change existing reviewed subjects; a missing digest must block rather than substitute. | [Domain: resolution and example](04-DOMAIN-MODEL.md), [R0: journeys](R0-PROTOTYPE-SPEC.md#journeys-and-interaction-rules) |
| Enforce probe budgets or leave managed import disabled | **Accepted.** A timeout or a documented memory target alone is not enforcement; manual handoff is not an import bypass. | [API: managed asset import](08-API-GAP-ANALYSIS.md#managed-asset-import-proposed-not-r0r1) |
| Prioritize PNG/JPEG and WAV, defer video import | **Needs owner decision.** Stills/audio are useful for briefs without committing to video ingest; existing named video review and managed video import are different capabilities. | [API: managed asset import](08-API-GAP-ANALYSIS.md#managed-asset-import-proposed-not-r0r1), proposal D3 |
| Keep creative verdict advisory initially | **Needs owner decision.** Preserve four distinct axes: QA, human grant, creative verdict and export eligibility. No gate added by default. | [Interaction design](07-INTERACTION-DESIGN.md), proposal D2 |
| Retain accessibility criteria and screen/readiness refinements | **Accepted.** Require numerical and manual checks; readiness and activity stay provenance- and timestamp-based. | [Visual system](06-VISUAL-DESIGN-SYSTEM.md), [R0: browser and manual validation](R0-PROTOTYPE-SPEC.md#browser-and-manual-validation) |
| Try Cutting Room, not a final visual commitment | **Needs owner decision.** Compare task completion and wrong actions against Precision Workbench, not just aesthetics. | [R0: visual and responsive contract](R0-PROTOTYPE-SPEC.md#visual-and-responsive-contract), proposal D4 |
| Ratify vanilla rather than React | **Needs owner decision.** No measured framework need; reuse the platform, not the live Studio client. First release needs separate authorization. | [Technical decision](09-TECHNICAL-DECISION.md), proposal D5 |
| Update PR landing page; keep draft and unmerged | **Accepted.** The PR still described the first draft as awaiting independent review. Both reviews and open decisions belong on the landing page. | [Research status](RESEARCH-STATUS.md), [draft PR #6](https://github.com/unplugged-kk/video-factory/pull/6) |

## Owner decision proposals

The table below preserves the proposals as reviewed. See the subsequent owner authorization for their disposition. They do not supersede approval or storage policies. No remaining technical disagreement with Review 02 is recorded.

| ID / topic | Recommended default | Current status | Risk if unresolved | Owner action required |
|---|---|---|---|---|
| D1 / PF-02 attribution | Keep redesigned live approval read-only until a trusted human identity mechanism satisfies PF-02 | Existing PF-02 requirement stands; rollout mechanism unapproved | Operator/channel could be misrepresented as an authenticated person | Authorize the eventual identity mechanism and live rollout after evidence, or explicitly amend policy separately |
| D2 / Creative review | Advisory initially, not export-blocking | Proposed; fixture demonstrates independent states | UI may signal approval or wrongly block technically eligible work | Ratify advisory or commission a separate, version-bound gate with invalidation policy |
| D3 / Import families | PNG/JPEG and WAV first; defer video until safe probing/resource enforcement is validated | Proposed, no managed import enabled | Expanding ingest prematurely increases parser and resource exposure | Choose first families; authorize managed import only after measured safety tests |
| D4 / Visual direction | Test Cutting Room in R0 only | Proposed, not final direction | Subjective styling could eclipse operator clarity | Authorize experiment; choose final direction after task comparison |
| D5 / Frontend | Vanilla ES modules for R0 and initial release | Recommended, not ratified | Unnecessary framework/build split or unresolved ownership | Ratify stack, not release authorization |
| D6 / Authorization | Consider standalone fixture-only R0 as a separate decision; R1 and production unauthorized | Spec ready for owner review; **R0 not authorized** | Prototype may acquire live API integration by scope drift | Explicitly authorize R0 only; R1/live requires separate security review and permission |

**Assumptions:** this branch remains docs-only and draft. **Open questions:** owner choices above and prototype test participants. Record actual owner decisions as new entries instead of rewriting either review.

## Owner authorization (D1–D6)

Date: 2026-11-24. Source: owner instruction “Video Factory Creator Studio — Owner Authorization and R0 Execution”. The historical proposal table above is superseded for these decisions.

| Decision | Owner resolution |
|---|---|
| D1 | Approved: PF-02 remains mandatory. Redesigned live approvals remain read-only until trusted human attribution satisfies the policy. |
| D2 | Approved: creative review is advisory initially, separate from technical export eligibility. |
| D3 | Approved: PNG/JPEG and WAV first. Video import deferred until safe probing and resource isolation are validated. No import implementation in R0. |
| D4 | Approved: Cutting Room for R0 experimentation only, not final direction. |
| D5 | Approved: vanilla ES modules for R0 and initial frontend direction. |
| D6 | Owner authorized implementation of isolated fixture-only R0. Authorization does not extend to R1, production code, live APIs, approval systems, publishing or pipeline changes. |
