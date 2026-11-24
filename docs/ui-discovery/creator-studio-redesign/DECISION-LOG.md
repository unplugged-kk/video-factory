# Decision log

**Research date:** 2026-11-24. **Scope:** design decisions only. **Evidence / sources:** owner assignment, [requirements](01-PRODUCT-REQUIREMENTS.md), [capabilities](00-RECONCILIATION.md), [tech recommendation](09-TECHNICAL-DECISION.md). **Verified:** owner constraints are distinct from author recommendations; no independent review received yet.

| Topic | Design branch recommendation | ChatGPT recommendation | Evidence | Resolution / owner approval |
|---|---|---|---|---|
| Audience and ownership | Single operator, one local machine; logical workspace IDs for future | Pending | Owner brief + existing local API | Owner decided, no authentication/fleet build |
| Batch and campaigns | Independent row receipts plus versioned campaign defaults | Pending | [Journeys](03-USER-JOURNEYS.md), queue primitive | Product direction approved; detailed contracts proposed |
| Stack | Keep vanilla ES modules; only isolate later if measured need | Pending | [Stack decision](09-TECHNICAL-DECISION.md) | Owner to ratify |
| Look and feel | Cutting Room, expressive via media and typography rather than heavy animations | Pending | [Design system](06-VISUAL-DESIGN-SYSTEM.md) | Owner visual preference pending |
| Technical vs creative gate | Separate statuses; don't add export gate without approval | Pending | Existing QA evidence and fixture creative revise | Open whether creative review blocks export |
| Scope progression | Read-only and inert prototype first; expanded mutating surfaces only after required integrity work | Pending | [Roadmap](10-IMPLEMENTATION-ROADMAP.md) | Owner to authorize phase after review |

**Assumptions:** no PR merge or implementation on this branch. **Open questions:** ordering of asset families, gate policy and stack sign-off. Add review quote/link and disposition per comment once ChatGPT submits; disagreement is recorded, not silently resolved.
