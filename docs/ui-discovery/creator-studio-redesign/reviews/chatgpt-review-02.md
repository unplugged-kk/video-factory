# ChatGPT follow-up review — revised Creator Studio blueprint

**Review date:** 2026-11-24  
**Reviewed PR:** [#6 — Creator Studio redesign](https://github.com/unplugged-kk/video-factory/pull/6)  
**Revised blueprint commit:** `30dc04180cb9af28958a310b1f37a7c43eba42a7`  
**Code baseline:** `main` at `8709b0bebc13fdf15eb08f03c83984fab187cedb`  
**Prior review:** [ChatGPT review 01](chatgpt-review-01.md)

## 1. Verdict

**The revised blueprint addresses the substantive findings from review 01. No new P1 blocker was found in the revised documentation.**

The author did more than acknowledge comments: the revised documents contain concrete contracts for sealed approvals, batch crash recovery, campaign field provenance, asset pinning/import limits, and an isolated fixture prototype. The decision log records the dispositions and links them to source evidence.

I agree with the eight accepted findings and the partial acceptance on attribution. The remaining attribution question is correctly left with the owner because it is a policy conflict, not something the frontend design can solve.

This remains a documentation review. I did not run the code, browser, or test suites.

## 2. Follow-up against review 01

| Previous finding | Follow-up assessment |
|---|---|
| Atomic sealed approval and legacy unbound grants | **Addressed in the proposed contract.** Fresh review for sealed gates; no synthetic migration of legacy grants; core compare-and-grant; pointer changes serialized with grant invalidation; acceptance tests cover races and stale subjects. |
| Honest local attribution vs authenticated principal | **Correctly unresolved.** Local session/channel is not a human identity. Live redesigned approval remains read-only until PF-02's authenticated-human requirement is satisfied or the owner explicitly resolves the policy. Do not weaken PF-02 implicitly. |
| Inert prototype isolation | **Addressed.** Separate origin, fixture-only in-memory adapter, no production client/API/media connection, CSP restrictions, production server stopped during browser tests, and deny-by-default request assertions including reads. |
| Durable batch submission and drift | **Substantially addressed.** Stable row intents, canonical payload fingerprints, reserved IDs, filesystem/SQLite reconciliation, replay semantics, and fault-injection tests are specified. Capability drift blocks affected rows without rewriting saved specs. |
| Campaign inheritance and immutable assets | **Addressed at design level.** Field-level source/revision/mode is shown; explicit clear differs from absence; asset bytes are pinned by digest; rebase is explicit and creates new lineage. |
| Asset import threat/resource model | **Substantially addressed.** Concrete candidate byte/quota/headroom/time limits, type profiles, content probing, staging, path/symlink controls, probe resource limits, cancellation, hashing, rights assertions and partial-import cleanup are documented. Limits remain proposed until measured on the target Mac. |
| Creative review vs export | **Correctly unresolved.** Creative review is advisory in the design until owner decision; technical QA, production grant and creative verdict remain separate. |
| Accessibility | **Addressed as acceptance criteria, not falsely claimed as completed.** Contrast ratios, 320 CSS px reflow, 200% zoom, forced colors, reduced motion, focus, and Indic text wrapping are called out for actual prototype validation. |
| Screen/workflow refinements | **Addressed.** Freshness, capability drift, independent state axes and fixture scenarios are included. |
| Vanilla-first recommendation | **Agreed.** No evidence emerged that justifies React migration. |

## 3. Technical notes

### Approval contract

The revised contract is directionally sound. One implementation detail must remain explicit when this is eventually built: a database transaction alone cannot freeze an artifact file on disk. The proposal correctly recognizes this by requiring all pointer changes and grant invalidations to serialize on the same core boundary, and by requiring preview bytes to come from the sealed subject. Implementation must make the sealed subject immutable and ensure the bytes served for review are exactly the bytes whose digest is granted.

Do not treat the proposed schema/API contract as proof that PF-02 is implemented. The current UI route remains weaker than the future design.

### Batch recovery

The revised protocol correctly separates durable admission from worker execution. The recovery path for a spec file written before the queue transaction is clear, and stable row submission keys prevent duplicate enqueue after an ambiguous response.

During implementation, test process termination at every filesystem/SQLite boundary, including directory fsync, queue insert, row state update, and receipt readback. The batch must never report a row as submitted before the spec and queue intent are durable.

### Asset import

The candidate profile limits are reasonable as an initial constrained scope, but the 512 MiB probe memory target and 10-second timeout must be enforced, not merely documented. If the target Mac cannot enforce the resource boundary reliably, keep import disabled and use a manual local-file handoff.

### Prototype boundary

The R0 isolation contract is strong. Preserve the distinction between R0 and R1: R0 is fully fixture-only with no production API reads; R1 may later add read-only live data after separate authorization and security review. Do not let a shared API adapter or development proxy blur that boundary.

## 4. Remaining owner decisions

These are the decisions that genuinely need the owner. My recommended defaults are included to make the next step straightforward.

| Decision | Recommended default | Reason |
|---|---|---|
| PF-02 human attribution | **Keep live redesigned approval read-only until a trusted authenticated-human mechanism satisfies PF-02.** | A local session label is honest but insufficient. Do not weaken the existing policy just to unlock a UI action. |
| Creative review and export | **Keep creative review advisory initially.** | Technical eligibility and human creative judgment are different. Add a blocking creative gate only after experience with the review workflow and an explicit owner decision. |
| Initial asset families | **Start with still images (PNG/JPEG) and audio (WAV); defer video import until probe/resource handling is validated.** | Smaller initial surface, useful for creative briefs and audio-led planning, less complexity than general video ingest. This is a product choice, not a claim that video is unsupported by the pipeline. |
| Visual direction | **Approve Cutting Room for prototype testing, not as a final visual commitment.** | It brings media and creative work forward while retaining operational clarity. Compare it against the current Precision Workbench using task completion, not aesthetics alone. |
| Frontend stack | **Ratify vanilla ES modules for the prototype and first release.** | No demonstrated React requirement; avoids a new runtime/build chain. |
| Prototype authorization | **Authorize R0 only: isolated, inert, fixture-backed, no production API access.** | Produces evidence for the visual/workflow decision without creating production risk. R1 and all implementation phases remain separately gated. |

The asset-family recommendation is intentionally conservative. If you prefer the first experience to focus on complete video review rather than brief creation, video import may be a higher priority—but should remain disabled until resource isolation is proven.

## 5. Small process follow-up

The PR #6 description still reads as though the independent review is pending and refers to the original first-draft commit. The branch and `RESEARCH-STATUS.md` correctly identify the revised head and addressed review. Update the PR description before requesting final owner review so the PR landing page reflects the current state and the remaining owner decisions.

## 6. Final disposition

- **Revised blueprint:** accepted as a sound basis for an inert prototype.
- **Review 01 findings:** addressed in the documents, with attribution correctly left unresolved.
- **New P1 findings:** none.
- **Live approvals:** remain read-only pending PF-02 policy compliance.
- **Creative export gate:** advisory by default pending owner decision.
- **R0 prototype:** recommend authorizing only the isolated fixture-only phase.
- **R1 live read-only integration and production implementation:** not authorized by this review.
- **PR #6:** keep draft until owner decisions are recorded; do not merge based solely on this review.
