# Phase 2A security results - first increment

Status: TESTED in the focused suite, not independently verified or production-ready. Baseline `849ea6a`; focused run includes the production walk patch and two new cases. No renderer, gate definition, publishing setting or human approval contract changed.

| Finding | Evidence and status | What remains |
|---|---|---|
| PF-22 (Medium), incomplete local composition subset | `production_digest` previously hashed a dangling link as a placeholder and `os.walk` could silently omit an unreadable directory. Two Studio approval handler regressions observed `DIGEST_MISMATCH` (a digest was still offered) instead of `ARTIFACT_NOT_READY` on both cases. `contentos/pipeline.py:_tree_parts` now refuses failed directory walks and dangling links. `tests/test_export_security.py::test_production_does_not_offer_a_digest_for_an_incomplete_project` checks both. | PF-22 OPEN: arbitrary out-of-root and remote resource references, provenance, fonts and renderer confinement not covered. Legacy CLI unbound grants are not changed by this patch. |
| PF-23 (Medium) | INSPECTED: `contentos/mpt.py` request records paths/terms, not material hashes; remote selection occurs at render. | Stage actual B-roll before approval, verify effective container inputs and no substitution. MPT endpoint unavailable for real verification. |
| PF-05 (Medium) | INSPECTED: pre/post checks still operate on mutable paths, so there is no sealed lane. | Apply the snapshot design and prove immutable inputs/output attestation in all render lanes. |
| PF-02 (High), PF-03 (Medium), PF-07 (Low) | INSPECTED / PLANNED: see `APPROVAL_POLICY.md`; the mandatory confirmation migration is unapproved. | No semantic changes; independent review pending. |

## Focused verification

ARM64, Python 3.12.16, explicit Homebrew-first PATH, baseline `849ea6a` plus worktree changes:

- `python -m pytest tests/test_export_security.py -q -k incomplete_project` (13:47:45 to 13:47:49 IST, exit 1): 2 failed, 51 deselected. Both failed with `DIGEST_MISMATCH` when `ARTIFACT_NOT_READY` was expected. Log: `/tmp/video-factory-phase2-baseline.Nl2Zuoid/incomplete-project-red.log`.
- `python -m pytest tests/test_export_security.py tests/test_ui_api.py tests/test_track_b.py tests/test_mpt.py -q -rs` (see exact start/end in log, exit 0): 96 passed, 1 optional real Track B render skipped. Log: `/tmp/video-factory-phase2-baseline.Nl2Zuoid/security-focused.log`.

No independent agent signed off on this increment. This hardening does not close PF-22 or change the Phase 1 readiness verdict.
