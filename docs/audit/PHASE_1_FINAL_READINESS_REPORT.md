# Phase 1 final readiness report

- **Generated:** 2026-11-20 01:30 IST
- **Repo / branch:** `/Users/kishore/git/video-factory`, `feat/p1-1-lookmap` (no upstream, not pushed)
- **Start checkpoint:** HEAD `86eeaa2` plus 29 uncommitted paths. Backup taken before any change:
  `~/.contentos/checkpoints/phase1-20261119-2142/` (`tracked.patch`, `untracked.tgz`, `sha256.txt`, `HEAD`)
- **Commits made (local only):**
  - `c391db0` feat(video): add P1-1 lookmap compilation
  - `849ea6a` fix(security): enforce content-bound export approvals
- **This file** is written after both commits so it can name them, and is left uncommitted.
- **Authoritative status of every finding:** `MASTER_GAP_REGISTER.md`, "Current status - authoritative".

## Decision

**Production readiness: NOT APPROVED.**

The two manifest bypasses are closed, and an independent reviewer verified that. But the full security property
("nothing reaches ready/ unless it is approved content, unchanged") still fails in four known ways:

- PF-02: by default, `approve` binds whatever is on disk.
- PF-05: content can be swapped and restored during a render.
- PF-22: assets loaded from outside the composition folder are not bound.
- PF-23: MPT b-roll materials are not bound.

Publishing is still disabled, so none of these can publish anything today.

## 1. Status by evidence level

| Item | Implemented | Tested | Independently verified | Production-ready |
|---|---|---|---|---|
| P0-1b bypass A: delete `source_spec` | yes | yes | **yes** (PF-12) | yes, for this attack |
| P0-1b bypass B: repoint `source_spec` | yes | yes | **yes** (PF-13) | yes, for this attack |
| G-01: gates on both tracks and every route | yes | yes | yes (PF-18) | yes |
| G-02: digest-bound grants; unbound and stale grants refused | yes | yes | yes (PF-15) | yes, but see PF-07 |
| G-03: approval bound to the rendered bytes (ledger attestation) | yes | yes | yes (PF-14, PF-17) | partial, see PF-05 |
| Whole-tree production digest (PF-01, PF-21, PF-27, PF-28) | yes | yes | yes | partial, see PF-22 |
| `approve --show / --expect` (PF-02 mitigation) | yes | yes | yes | no: optional, PF-02 open |
| PF-03: sidecar metadata unapproved | no | no | no | no |
| PF-05: render-window swap and restore | partial | partial | partial | no |
| PF-07: old approvals never superseded | no | no | no | no |
| PF-22: out-of-root and remote assets | no | no | no | no |
| PF-23: MPT materials | no | no | no | no |
| P1-1 M1 lookmap | yes | yes | no independent review | not wired: M2 |

## 2. Security findings and how each was closed

### The fix

Export trust moved from `manifest.json`, which anyone can edit, to the ledger.

- **The attestation.** `ledger.renders` is written only by:
  - the pipeline render stage;
  - `track_b.render`;
  - `contentos job register`.

  Each row records the video's sha and the gate digests the render was made under. Those digests are checked
  again after the render. If the content changed while rendering, the render is dropped.
- **The export check.** `export.approval_refusal` runs on all three routes: the CLI, the pipeline export stage and
  the Studio. It requires three things:
  1. the bytes on disk are an attested render of this job;
  2. both gates hold a digest-bound grant for that render's digests;
  3. the content behind those digests is unchanged now.

  The checked bytes are pinned through the copy.

### Before and after

Bypasses A and B were reproduced on the checkpoint tree and refused on the new code (`/tmp/attack_ab.py`):

```
== BEFORE (checkpoint 21:42 tree)
attack-a: EXPORTED (bypass)
attack-b: EXPORTED (bypass)
== AFTER (current tree)
attack-a: REFUSED - attack-a: not exported, video.mp4 (sha c70ec23368f7) is not a render the factory recorded
attack-b: REFUSED - attack-b: not exported, video.mp4 (sha c70ec23368f7) is not a render the factory recorded
```

### Mandate attack list: every attack is refused

All tests are in `tests/test_export_security.py`. Each one asserts that `ready/` is unchanged byte for byte.

| Attack | Test |
|---|---|
| Delete `source_spec` | `test_attack_a_*` (2) |
| Substitute `source_spec` | `test_attack_b_pointing_source_spec_at_a_pristine_copy_is_refused` |
| Spec modified after approval | `test_spec_edited_after_approval_and_before_render_blocks_the_render`, `test_spec_edited_after_render_is_refused` |
| Spec replaced by another valid spec | `test_spec_replaced_by_another_valid_spec_is_refused` |
| Approval metadata modified | `test_approval_metadata_in_the_manifest_grants_nothing`, `test_tampered_approval_digest_in_the_ledger_is_refused` |
| Approval replayed from a previous version | `test_replaying_an_approval_from_a_previous_version_is_refused`, `test_an_approval_for_another_job_does_not_transfer` |
| Rendered video modified | `test_a_replaced_video_is_refused_even_when_the_manifest_vouches_for_it`, `test_a_video_swapped_during_export_is_refused` |
| Manifest replaced after rendering | `test_a_manifest_replaced_after_rendering_changes_nothing` |
| Authoritative records missing | `test_no_render_attestation_is_refused`, `test_a_lost_ledger_is_refused`, `test_spec_deleted_after_render_is_refused` |
| Every export route | `test_every_export_route_refuses_the_same_attack` (API, `storage export`, Studio, pipeline stage) |
| Track B | `test_track_b_*` (4), `test_registering_a_factory_render_keeps_the_stronger_record` |

## 3. Independent review (Potato)

- **Who reviewed.** A fresh-context `security-auditor` agent was given no conclusions from the implementer.
- **How.** It worked in 3 rounds. It ran attacks in `/tmp` workspaces and mutation-checked the tests. It did not
  modify any repo code.
- **Report.** `docs/audit/POTATO_FINAL_SECURITY_REVIEW.md`. Its final table is in section 8.4.

**Final review statuses:**

| Status | Findings |
|---|---|
| VERIFIED | PF-01, 04, 06, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 25, 26, 27, 28, 29 |
| OPEN | PF-02 (High; mitigated, owner decision), PF-03 (Medium), PF-05 (Medium; partly fixed), PF-07 (Low), PF-22 (Medium), PF-23 (Medium) |
| ACCEPTED RISK | PF-08 (`--approve-private`), PF-09 (unauthenticated local ledger), PF-24 (Remotion toolchain link) |

**Test quality.** Removing any one of the new protections fails at least one test.

**Residual notes from the review.** Section 8.3 listed three minor items, and all three were fixed after round 3:
- a FIFO in `audio/` could hang approval;
- an empty `tts` was not shown;
- PRODUCTION `--show` did not list the files it binds.

The tests for these three fixes ran in the full suite. The reviewer did not re-review them.

## 4. Test results (all runs recorded, none hidden)

| Run | Code state | Result |
|---|---|---|
| Full pytest #1, 2026-11-19 | first P0-1b cut | **1 failed**, 1196 passed, 8 skipped. Application failure: `test_track_b.py::test_export_refuses_when_either_grant_is_absent` still expected the old message. The test was updated to the new contract. |
| Full pytest #2 | after review round 1 fixes | 1207 passed, 8 skipped, exit 0 |
| Full pytest #3 | after round 3 | **No result.** The process died at 23% with no output. Re-running `test_export.py` on its own: 22 passed. Treated as environmental; not counted. |
| Full pytest #4, 2026-11-20 01:15 | final code, identical to `849ea6a` (only docs changed afterwards) | **1218 passed, 8 skipped, exit 0** |
| `node --test contentos/adapters/v1/*.test.mjs` | final | 66 passed, 0 failed, exit 0 |
| `ruff check --select E9,F` on changed files | final | All checks passed |
| Full pytest at `c391db0` alone (fresh worktree) | commit 1 only | 1 failed, 1152 passed, 22 skipped. The failure is `test_lang.py::test_english_words_for_keeps_the_legacy_hyperframes_path...`. It fails the same way at `86eeaa2` in a fresh worktree, because it needs the repo-local `node_modules`. This is environmental and pre-existing, not caused by commit 1. The extra skips come from the same missing gitignored assets. |
| Checkpoint report (2026-11-19 21:40) | before this work | 1171 passed, 1 failed (whisper-cli relinked during the run), 8 skipped. The failing test passed on its own. Environmental. |

**Runtime smoke test.** A real HyperFrames render ran through `./contentos.sh` with workspace and library in `/tmp/vf-smoke`, on the final code. Log: `/tmp/vf-smoke/log3.txt`.

| Step | Result |
|---|---|
| Run 1 | stopped at SCRIPT_APPROVED |
| Run 2 | stopped at PRODUCTION_APPROVED |
| Run 3 | render OK (8.4s), export OK. Ledger row: `pipeline`, spec path recorded. The `ready/` sha `e242f93c...` equals the rendered file. |
| Video swapped, then `storage export --force` | refused |
| Spec edited after render | refused |
| Project file edited, then re-render | BLOCKED at the PRODUCTION gate |

Not run: Remotion and MPT renders, CI (no upstream), the opt-in Studio UI smoke.

## 5. Lookmap (P1-1 M1)

`python -m contentos.scenekit.lookmap report` exits 0. **17 of 30 looks compile; 13 are BLOCKED**, each with a
reason:
- 10 lack a texture primitive (rain, clean-outline, panel-border, marker-swipe, starry-backdrop, depth-blur,
  double-outline and pattern-fill, frosted-glass, curtain and smoke, paint-splat, line-art);
- 3 fail on contrast alone (corporate-docs 2.65, sketch-beside-motion 2.59, both below 3.0);
- 2 have both a texture blocker and a contrast blocker (aged-paper-rain 2.46, cream-kinetic-panel 1.83).

Every reason is a real capability gap or a legibility failure, not a mapping omission. The lookmap tests pass in
every full run above. The security work touched no scenekit file, so it caused no regression there.

## 6. Remaining work

**Security, before relying on the chain:**
1. PF-22: refuse out-of-root and remote asset references when approving and when rendering.
2. PF-05: render from a snapshot copy of the approved content.
3. PF-02: make `--expect` mandatory. **This needs an owner decision.**
4. PF-03: bind sidecar metadata, before any uploader or PUBLISH_APPROVED design.
5. PF-07: let a new grant supersede the old ones.
6. PF-23: bind MPT materials.

**Other gaps:**
- **G-05:** the Lane F gates cannot FAIL.
- **G-06:** `lang doctor` reports READY without probing the TTS backend.
- **G-07:** logs and the environment are not scrubbed. This blocks an ElevenLabs adapter.
- **G-09:** `look:` is still not consumed. That is P1-1 M2.
- **Not done by anyone:** visual and creative review, Studio UX review, Hindi listening, CI.
- **Test hermeticity:** `test_lang.py` depends on `node_modules` being installed. It fails in a fresh checkout.

**Principle to keep:** immutable content identity across the lifecycle (spec, then approval, then render, then
export). The ledger attestation provides it up to export. Publishing must extend it: PUBLISH_APPROVED should bind
the exact video sha plus the sidecar metadata, which is why PF-03 belongs in that design.

## 7. P1-1 M2

Hold M2 until PF-22 and PF-05 are closed and the owner has decided PF-02. M2 makes compositions richer: textures,
and likely external assets. That widens exactly the PF-22 surface, so building it first would add unbound inputs.

## 8. Owner decisions needed

1. **PF-02:** make `approve --expect` mandatory for SCRIPT and PRODUCTION. This changes the documented approval
   workflow and the Studio flow.
2. **Branch and push:** where the two commits go, and the review strategy.
3. **D3** (from P1-1), still open.

## 9. Side effects to know about

`git worktree prune` was run to remove a throwaway worktree. It also removed the stale metadata for two
worktrees whose directories were already gone: `/private/tmp/ceh-vf-consumer` and `vf-b1`. No branch or
directory was touched.
