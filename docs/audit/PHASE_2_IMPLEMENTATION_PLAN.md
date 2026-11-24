# Phase 2 implementation plan

Baseline: `849ea6a`, isolated branch `feat/phase2-foundation`. Ownership and available agents: `PHASE_2_AGENT_INVENTORY.json`. The original checkout is not an integration target. Do not edit another lane's files; hand off patches for primary review, then use an independent reviewer for acceptance.

| Order | Work / primary file ownership | Exit evidence |
|---|---|---|
| 1 | Production identity preflight, PF-22 slice: `contentos/pipeline.py`, `tests/test_export_security.py`. Runtime/reliability work can proceed independently. | No digest from incomplete compositions; valid prior digests unchanged. PF-22 stays open. |
| 2 | Stage local MPT material and inventory all inputs: `contentos/mpt.py`, `tests/test_mpt.py`; coordinate pipeline changes with step 1. | Approved staged SHA, mocked container receives only staged assets, no search-time substitution. Real MPT evidence reported separately. |
| 3 | PF-05: use `IMMUTABLE_RENDER_SNAPSHOT.md` to verify a confinement boundary and wire HyperFrames first. Own `pipeline.py`, `track_b.py`, renderer and ledger paths sequentially. | A real confined render and negative tests for asset, snapshot and output mutations. Do not call a mutable copy immutable. |
| 4 | Complete PF-22 for all renderer inputs; then migrate PF-02 per the approved `APPROVAL_POLICY.md`. PF-03/PF-07 follow. | CLI/API/Studio accept the same sealed reviewed subject atomically; private automation is authenticated, scoped, content-bound and attributable. No publishing. |
| 5 | Reliability: optional Hindi ASR prerequisite fix, CI-equivalent fresh checkout, G-05 quality gates (no gate change without authorization), G-06 honest backend probes, G-07 log/env scrubbing, three-job concurrency and recovery. | Clean tree check, full Python and Node suites, preserved first failures, controlled job receipts and independent review. |
| 6 | Runtime/multilingual audit and research; creative preparation only until Phase 2A and accepted owner decisions. | Versioned executable/path evidence, comparable Hindi benchmarks, listener/critic sign-off, no paid invocation. |

Creative discovery found the exact original D3 in `docs/P1-1_LOOK_PROPOSAL.md`: include the `figure` and `ticks` primitives in this milestone or defer to a following one. The proposal recommends holding M3/M4 for that decision and visual review. Do not reinterpret D3 as a renderer or palette choice. M2 implementation stays gated under the Phase 2 mandate.
