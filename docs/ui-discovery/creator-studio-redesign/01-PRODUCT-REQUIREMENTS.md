# 01 / Product requirements

**Research date:** 2026-11-24. **Scope:** Creative Production OS for one local operator, extensible to workspace ownership. **Evidence / sources:** owner brief; [current capabilities](00-RECONCILIATION.md); prior `docs/ui-discovery/creator-studio/product-and-user-journeys.md`. **Verified:** saved specs, stage visibility and human review enable an operator workbench today; there is no campaign or generic agent API.

| ID | Requirement | Release acceptance |
|---|---|---|
| P1 | Explain the path from brief to exported artifact, including readiness and manual handoffs | Topic, script, asset and reference entries disclose supported, conditional, manual and planned actions before submission. Blocked choices remain inspectable with reason and remedy. |
| P2 | Produce one job without accidental execution | Validate a saved draft, show canonical spec and required inputs, submit explicitly, stop at each real gate. Never imply that a topic alone is runnable. |
| P3 | Plan/submit 20 unrelated jobs | Import preview validates every row, isolates bad rows, shows effective config, lets the operator submit only selected ready rows. Replaying a confirmation creates no duplicates. No batch-wide approval. |
| P4 | Run a 20-episode campaign | Versioned brief and defaults; show each episode's inherited and overridden values; defaults changes create a new revision, do not edit previously reviewed episodes. |
| P5 | Make approval reviewable and recovery predictable | Preview exact subject/version and explicit per-job grant; show changed subject as stale. Offer scoped retry with invalidation preview and durable per-job outcome. |
| P6 | Separate technical QA, creative review and export | Each state and reviewer attribution displayed separately; missing QA is “not run.” Export requires core eligibility, no upload option. Partial bulk failures never imply global success. |
| P7 | Accessible, expressive production environment | Keyboard-only paths to creation, review and recovery; visible focus, reduced motion, no color-only status, no fake ETA or activity. |

Formats (Shorts, Reels, long-form) are target profiles: duration, framing and validation differ from integration availability. Educational, tech, faceless, documentary, business and character are creative intent, not engine names. Podcast/talking head, music/lyric, audio/image-led and reference creation use capability checks or explicit handoff, never inferred from intent. Language availability and human audio approval are separate. Preserve Track A spec-driven and Track B director-led pathways. No editor timeline, automatic publishing, multi-user auth, distributed execution or AI provider install in the first release.

**Assumptions:** independent batches and campaigns can coexist; no campaign grant inheritance. **Open questions:** bulk import starter columns, first supported import MIME families, whether creative sign-off blocks export or remains advisory (owner decision). [Navigation](02-INFORMATION-ARCHITECTURE.md) · [Journeys](03-USER-JOURNEYS.md).
