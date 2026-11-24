# Agent Handoff - Phase 2 foundation

- **Checkpoint:** ITER-2026-11-24-003
- **Generated:** 2026-11-24 14:31 IST (UTC+0530)
- **Root and repo:** `~/git/video-factory-phase2-foundation`, `https://github.com/unplugged-kk/video-factory.git`
- **Branch / code commit:** `feat/phase2-foundation` / `46f8e78` (before the docs-only parking commit).

## Parking point

The owner authorised a branch push and is switching focus to UI design and prototyping. Keep the Phase 2 implementation on `feat/phase2-foundation` for later review; do not merge it into `main` as part of the pause. Use a separate worktree off `main` for independent prototypes. The following sections describe resuming Phase 2, not work to start during the pause. `46f8e78` is the tested code baseline; the parking commit contains only documentation.

## Objective and boundaries

Kishore's objective is one local-first, reliable, creative, multilingual factory. For the next iteration, prove one genuinely confined snapshot lane; the PF-23 local adapter slice is already tested. Do not start look-to-render wiring while integrity is open. The original `/Users/kishore/git/video-factory` remains on `feat/p1-1-lookmap @ 849ea6a`, 2 ahead of local `origin/main`, with its historical Phase 1 report and checkpoint untouched. Work only in the new worktree; give additional lanes isolated ownership and have the primary integrate. No push, publishing, spend, paid provider, protected config/gates/pin/vendor/skills, scheduler claims, publishing approval files, account credentials, or generated media in Git. Owner authorized PF-02 migration after the immutable, complete production subject work. New local focused commits are allowed after verification.

## Relevant architecture and fixed baseline

1. Track A goes `spec -> script gate -> voice -> compose -> production gate -> render -> attest -> export`. Track B agent-authored render uses the same digests, while `job register` binds finished media only. `ledger.renders` is authoritative for export attestation. Studio already passes `seenDigest`, CLI supports optional `--expect`.
2. `contentos/pipeline.py:production_digest` binds the composition tree and selected audio; it does not see arbitrary document references. `d9c1d8e` rejects a missing symlink target or failed directory walk; evidence `VF2-WALK-RED`, `VF2-SECURITY`, `EV-20261124-135640` (116 passed). Do not redo this slice.
3. `46f8e78` stages local MPT clips and joined narration under `project/mpt-assets/`. The request binds hashes, origins, rights labels, normalized MPT inputs and ordering. Production digest and Docker argv both validate the staged files; Docker must see matching bytes at preflight. Remote stock and legacy requests fail closed. 160 focused passed; full Python 1,224 passed / 17 skipped; Node 66 passed. Actual MPT consumption, acquisition with verified stock metadata, and concurrent mutation on its live mount are not solved.
4. `cce972d` fixes language test assumptions; missing-binary targeted skip, fallback command targeted pass, full fresh worktree `1211 passed, 17 skipped`. JS `66 passed`. Initial full failure and unavailable offline npm package are preserved. The two code commits follow `849ea6a` (ledger-export integrity) and `c391db0` (lookmap compile-only).
5. Runtime English Kokoro and Hindi Chatterbox each produced a new WAV offline; no human quality result. Three existing technology fixtures rendered under private sandbox test roots, 3 passed, with isolated scratch export only and `DRY_RUN` publish. Contact sheets show repeated text-card compositions. Not an independently accepted creative benchmark.

## Files to read first

`AGENTS.md` for protections; `CURRENT_STATE.md` and `OPEN_ITEMS.md` in this directory for evidence; `docs/audit/MASTER_GAP_REGISTER.md` for attested gaps; `docs/audit/DEPENDENCY_INTEGRITY_DESIGN.md` and `IMMUTABLE_RENDER_SNAPSHOT.md` for work sequence; `APPROVAL_POLICY.md` for the owner decision. Use `graft` for the `mpt.compose`, `mpt.render`, `production_digest` and `render_subjects` blast radius before source edits. No approved native Pi subagent was available; inspect capability inventory for the model/session constraint before reassigning.

## Next deliverable and checks

- Own the first PF-05 lane. A local `node:22-bookworm` process probe showed a no-mount network-disabled worker can read root-sealed staged bytes while a replaced host source is invisible. See `docs/audit/IMMUTABLE_RENDER_SNAPSHOT.md` and the PF-23 evidence directory. Build a real renderer proof with isolated output and ledger attestation, then cover remaining lanes before PF-22/PF-02 acceptance.
- Verify in isolated roots with `~/.contentos/venv/bin/python -m pytest tests/test_mpt.py tests/test_export_security.py -q -rs`, then `~/.contentos/venv/bin/python -m pytest tests -q -rs` and `node --test contentos/adapters/v1/*.test.mjs`. Compare with local bootstrap in `docs/audit/LOCAL_TEST_BOOTSTRAP.md`. Preserve all failures. For a real existing HyperFrames regression fixture use `CONTENTOS_E2E=1 ~/.contentos/venv/bin/python -m pytest tests/test_e2e_features.py -q -rs -k 'hf-' --basetemp <new-outside-Git-dir>`, and check the actual MP4 and `qa.json`.
- The owner approved PF-02. After PF-05/PF-22, add mandatory shared confirmation tests and migrate CLI/API/Studio together. Authenticate and scope private automation separately; compare and grant atomically against the sealed subject revision. G-06 doctor and G-07 env/log audit can proceed independently. Independent security and visual review remain required for acceptance, along with successful multilingual listening and three genuinely different niches.

Raw fixture paths and evidence are under `/Users/kishore/.contentos/checkpoints/video-factory-phase2-20261124/`, with test results indexed in `VERIFICATION_EVIDENCE.md`. Append one new execution checkpoint per meaningful iteration. Do not modify the original 2026-11-21 checkpoint in its checkout.
