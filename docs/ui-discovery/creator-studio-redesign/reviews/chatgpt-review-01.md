# ChatGPT independent review — Creator Studio redesign

**Review date:** 2026-11-24  
**Reviewed PR:** [#6 — Creator Studio redesign](https://github.com/unplugged-kk/video-factory/pull/6)  
**Blueprint commit:** `c94ca8a765d73e77c6de9cf62d5d92ed1e9710f0`  
**Reviewed branch tip:** `7236b39ca11d4bb9b24ebefd963e3e4c0beeb48a`  
**Code baseline:** PR base `main` at `8709b0bebc13fdf15eb08f03c83984fab187cedb`  
**Review branch:** `chatgpt/creator-studio-review`

## 1. Executive assessment

**Recommendation: accept the blueprint as the basis for an inert prototype after the high-priority clarifications below. Do not begin production implementation yet.**

The research is unusually disciplined about capability truth. It does not confuse queue rows with batches, campaign intent with a campaign entity, a compiled look with renderer adoption, Track B plans with an automatic renderer, or export with publishing. The proposed product structure is coherent: Mission Control, Universal Create, Batch Studio, Video Library, Creative Library, Review Studio and Operations & Agents, with shared individual-job workspaces.

The strongest technical choice is to retain vanilla ES modules and the existing Python API. The blueprint correctly treats React as a measured exception rather than a design requirement. The Cutting Room direction is a credible way to make the Studio more creative without turning operational state into decoration.

The main concerns are not visual. They are the integrity boundary for approvals, the durable semantics of batch submission, and the separation between a fixture prototype and live production authority. These should be clarified before the prototype is treated as a reference implementation.

## 2. Findings requiring action

### [P1] Approval design must fail closed for legacy unbound grants and close the digest TOCTOU window

**Evidence:** `contentos/ui_api.py::_approve` reads the current digest from `job_state`, compares `seenDigest`, and then calls `ledger.approve`. In `contentos/ledger.py::check_gate`, legacy approvals with no `subject_sha256` are explicitly treated as `unbound`; the current gate checker can still consider that legacy state valid. `ledger.approve` inserts a digest after the API-level comparison, not as one atomic compare-and-grant operation.

**Why it matters:** the blueprint's future sealed-subject model promises that a grant is bound to the exact immutable subject reviewed. That promise is not met merely by adding a subject digest to the UI or recording a new digest. A legacy unbound grant can undermine fail-closed semantics, and the current read-then-insert sequence leaves a possible time-of-check/time-of-use race if the subject changes between the comparison and grant write.

**Required correction:** make the integrity prerequisite explicit in R3 and in the API contract:
1. Define a canonical, immutable approval subject that includes the exact artifact identity/digest, job/spec revision, gate and any relevant provenance.
2. Perform current-subject comparison and grant insertion under one transaction/lock or equivalent compare-and-swap boundary owned by the core, not by a UI preflight.
3. Define a migration/compatibility policy for legacy rows with NULL/empty subject digests. For a sealed gate, they must not silently satisfy the new policy; require fresh review or a deliberately documented owner-approved migration.
4. Define supersession/revocation and render-attestation behavior when an approved subject changes.
5. Add tests for concurrent subject mutation, legacy unbound grants, duplicate grants, stale digest, and a grant racing with rerun/invalidation.

Do not enable an exact-subject approval claim until these tests pass. This is a core integrity prerequisite, not a frontend enhancement.

### [P1] “Explicit principal” must not imply authentication that the local Studio does not have

**Evidence:** `contentos/ui_api.py::write_authorized` uses loopback Host/Origin checks and a session token. `_approve` currently records `by="creator-studio"`. The blueprint correctly says the session token is not multi-user authentication, but the proposed Approval entity/API also says “require explicit principal” and includes principal attribution.

**Why it matters:** in the owner-approved single-operator phase, there is no authenticated user principal. A token proves possession of a local session token; it does not prove a named human identity. UI text or audit records must not imply stronger attribution than the system has.

**Required correction:** for the single-operator release, define the actor honestly as something like `local-operator-session` / `creator-studio-local`, with an explicit note that it is session attribution rather than authenticated identity. Do not add login or multi-user authorization in this phase. Reserve a stable authenticated principal field for a future identity layer, and specify how it will be populated then.

### [P1] Keep the inert prototype technically incapable of invoking production mutations

**Evidence:** Roadmap R0 calls for an inert fixture-only prototype, including exact-subject review and 20 mixed rows. The current Studio API has real mutating operations for spec creation, run, approve, rerun, queue, Track B, QA and export.

**Why it matters:** a visual prototype that happens to use the real API can create jobs, grant approvals, rerun stages or export files even if the intent is “just a demo.” Disabled buttons alone are not a safety boundary.

**Required correction:** state that R0 must use fixture data and a stub/mock API adapter with no network path to `/api/v1`. The prototype should have no production token, no mutation-capable API client and no hidden action handlers. Label approval, batch submission and export interactions as simulated. Include a test that fails if the prototype attempts to call the production API. Browser validation should be against the isolated prototype only.

## 3. Important design clarifications

### [P2] Specify batch submission as a durable, recoverable protocol—not just an idempotency key

The batch contract is directionally good: stable row IDs, intent key, per-row receipts, replay handling and partial outcomes. But “persist one keyed receipt before writes” still leaves the key crash window between creating job/spec files, queue entries and ledger records.

Before implementation, define:
- The durable batch and row state machine, including `VALIDATING`, `SUBMITTING`, `PARTIAL`, `SUBMITTED` and recoverable interrupted states.
- The exact idempotency-key scope and canonical payload hash. Same key + same payload replays the same receipt; same key + different payload returns conflict.
- Whether a row becomes submitted only after both its job/spec and queue intent are durable.
- A reconciliation worker/command or transactional outbox strategy for crashes between filesystem and SQLite writes.
- Per-row retry and repair behavior without re-submitting already accepted rows.
- Whether batch validation snapshots registry/capability versions and what happens if capabilities change before submit.

The first implementation should be deliberately small: independent batch, stable rows, per-row receipts and no campaign inheritance. Do not ship both the campaign model and generic bulk engine as one inseparable change.

### [P2] Make the campaign effective-configuration contract more concrete

The precedence rule (episode override > immutable campaign defaults > job default) is good. Persisting the effective spec and source of each resolved field is also correct.

Add an example with a real field-level resolution record, including:
- Value.
- Source layer (episode, campaign revision, job default).
- Source revision/digest.
- Whether the value is inherited, explicitly overridden, or explicitly cleared.
- Whether a changed default requires a rebase.

Define how shared asset references behave when an asset is replaced, deleted or becomes unavailable. A campaign revision should refer to immutable asset identities/digests, not a mutable filename or “latest” pointer.

### [P2] Asset import needs an explicit local-file threat and resource model

The proposed bounded stream, media allowlist, local staging and no arbitrary path/URL fetch are good boundaries. The open questions are still too broad for implementation.

Specify:
- Maximum file size and aggregate workspace quota.
- Allowed extensions and probed media/container/codec policy (extension alone is not validation).
- Symlink and path traversal handling.
- Whether the import copies bytes into managed storage or retains a reference to the original file; how missing/moved sources are represented.
- Probe/transcode time and resource limits; malformed media must not hang or exhaust the local machine.
- Hashing, deduplication, cancellation and cleanup of partial imports.
- Rights/provenance metadata and the distinction between “operator asserts rights” and verified permission.

Keep asset import out of the first read-only slice. Do not accept arbitrary filesystem paths from browser payloads.

### [P2] Clarify export eligibility and the meaning of creative sign-off

The blueprint correctly separates technical QA, production approval, creative verdict and export. The unresolved owner question—whether creative sign-off blocks export—is real and should remain a decision, not be guessed by implementation.

Until decided, use a visible non-blocking state such as **Creative review: not requested / pending / accepted / changes requested**, and keep technical export eligibility independent. Do not use one generic “Approved” badge. If creative sign-off later becomes an export gate, define its exact subject and invalidation semantics separately from the existing production approval.

Also preserve the distinction between local export into the configured library and publishing/uploading. The current API's export preview reports `publishEnabled: false`; do not expose “Publish” as an action or imply that an exported file has been uploaded.

### [P2] Accessibility tokens are proposals, not certified contrast results

The visual system gives concrete dark/light tokens and sensible keyboard/motion rules, but explicitly says the palette has not been contrast-certified. Before the prototype is accepted:
- Calculate WCAG 2.2 contrast for every text/status/focus/boundary pairing actually used.
- Test status chips on both panel surfaces, focus on raised surfaces, disabled states, and text over media.
- Test Devanagari and long Odia/Hindi labels for wrapping even if Odia production is blocked.
- Test 320 px reflow, 200% zoom, forced-colors, reduced motion and keyboard focus visibility.
- Keep media letterboxed with aspect ratio visible; do not use a cropped poster as a proxy for actual video review.

A design-token table alone is not accessibility validation.

## 4. Screen and workflow review

| Area | Assessment | Recommendation |
|---|---|---|
| Mission Control | Good focus on actionable blockers instead of vanity KPIs. | Do not show an aggregate “production pulse” unless derived from real, timestamped job state. Distinguish stale snapshot from live state. |
| Universal Create | Correctly separates intent from capability and saved spec validation. | Keep “idea/topic” as a draft input until a real plan/spec exists; don't imply natural-language generation is currently available. |
| Batch Studio | Strong row-level readiness and failure isolation. | Prototype with 20 fixture rows including invalid, blocked, duplicate, running and stale-capability cases. |
| Campaign | Inheritance and explicit rebase are sound. | Keep campaigns as metadata/orchestration, not a parallel production engine. |
| Video Library | Sensible media grid/list split. | Preserve existing job IDs and deep links; make status axes independently filterable. |
| Creative Library | Useful, but capability/readiness can easily be overstated. | Mark “compiled”, “available in registry”, “used by builder” and “verified in rendered frames” as different evidence states. |
| Review Studio | Correctly makes exact subject and evidence central. | No approval action until core sealed-subject work is complete; fixture prototype only. |
| Operations & Agents | Good decision not to invent a general agent launcher. | Show only receipts, queue and health events that actually exist; no simulated streaming agent activity. |

The eight journeys cover the important product paths. The one additional scenario I would add to the prototype test matrix is **capability drift between validation and submission**: e.g. a renderer, voice or look becomes unavailable after a 20-row batch was validated. The UI must revalidate and show which rows changed readiness, without silently changing the saved specs.

## 5. Technical recommendation

I agree with **vanilla ES modules + existing Python API** for the initial release.

Reasons:
- Current shell and same-origin token/API boundary already exist.
- There is no demonstrated need for a React runtime.
- The proposed first hard interaction (20-row batch editor) can be built and tested with native controls, reducers and focused view models.
- React Bits' component model is React-dependent, and the audit identifies meaningful dependency, accessibility and licensing concerns.
- A React migration would not solve the domain integrity or batch transaction problems.

Use the prototype to measure interaction complexity, not to showcase animation. Consider a React island only if a specific isolated interaction has a clear user benefit and the measured maintenance/accessibility cost is lower than a native implementation. Do not port the whole app to React for visual consistency.

## 6. Recommended next sequence

1. **Claude response:** address the three P1 items and the P2 batch/campaign/asset contracts in the blueprint. Record each disposition in `DECISION-LOG.md`; disagreements remain explicit.
2. **Owner decision:** ratify Cutting Room as the prototype direction, decide whether creative review is advisory or an export gate (or defer the decision and keep it advisory), choose the first asset families, and authorize an inert prototype.
3. **Prototype only:** fixture-backed, no production API connection, desktop/tablet/mobile, both themes, 20-row batch interaction, one campaign inheritance example, one exact-subject review fixture, and one export-vs-publish explanation.
4. **Browser validation:** test keyboard, focus restoration, stale data, capability drift, 320 px reflow, 200% zoom, reduced motion and contrast. This is still prototype validation, not production integration.
5. **Separate implementation plan:** after owner approval, split core integrity, batch persistence and UI work into independently reviewable PRs. Do not make UI affordances available before their core contracts exist.

## 7. What I verified and what remains unverified

**Verified in this review**
- PR #6 is open, draft, unmerged and targets `main`.
- The branch tip is `7236b39ca11d4bb9b24ebefd963e3e4c0beeb48a`; the blueprint commit is recorded in the handoff.
- The reading guide, status, reconciliation, requirements, IA, journeys, domain model, screens, visual system, interaction design, API gaps, stack decision, roadmap, competitive research, component audit and decision log were read from the published branch.
- Current `main` source was inspected for `AGENTS.md`, `contentos/ui_api.py`, `contentos/ui/api.js` and `contentos/ledger.py`, including the approval and route dispatch logic.
- The review branch was created from `main`.

**Not verified**
- I did not run the repository test suite or a real browser session in this environment.
- I did not run a production job, renderer, export or asset import.
- I did not independently profile React Bits/MotionSites components or perform a legal review of third-party licenses.
- The reported 53 Python and 25 JavaScript test results are recorded as the author's results, not rerun by this reviewer.

## 8. Overall disposition

**Blueprint: positive, with required integrity clarifications before prototype authorization.**  
**Frontend choice: agree with vanilla ES modules.**  
**Visual direction: recommend testing Cutting Room in an inert prototype; owner approval still required.**  
**Production implementation: not authorized by this review.**  
**PR #6: keep draft; do not merge until the owner has reviewed the revised blueprint and decisions.**
