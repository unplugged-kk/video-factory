# P0 verification dossiers

> **Current status (2026-11-19, reconciled):** the authoritative status of every finding is
> `MASTER_GAP_REGISTER.md`. This file keeps the dossiers as they were written, including statuses later superseded;
> superseded statuses are marked as such, never deleted. P0-A, P0-B and P0-C were reworked by **P0-1b** (bottom of
> this file): export now trusts a ledger render attestation instead of `manifest.json`, so the
> `gate_refusal` / `render_integrity_refusal` / `final_video_sha256` mechanism described below no longer exists.

Governance rule applied: **no security claim is verified by an error message.** Every assertion below is on a
state transition, a content digest, an approval binding, or the absence/presence of a published artifact.

Demonstrations were run in an **isolated worktree at HEAD** (`git worktree add --detach /tmp/vf-p0-verify HEAD`),
so "the test fails before the fix" is measured against the real unfixed code, not asserted. The worktree was
removed afterwards (`git worktree list` confirms no residue).

---

## P0-A / G-01 — Track A reached `ready/` with no approval gate

**Severity:** P0. **Status:** FIXED, verified. **Rule 4 rung: TESTED** (not PRODUCTION-READY; see the caveat at
the end).

### Reproduction (as an operator, before the fix)

```
$ VIDEO_FACTORY_PUBLISH_DIR=/tmp/vf-repro-pub ./contentos.sh storage export sample-kafka-events-kinetic
exported: ready/unassigned/2026/11/how-kafka-moves-events__sample-kafka-events-kinetic.mp4
  sidecar: ready/unassigned/2026/11/how-kafka-moves-events__sample-kafka-events-kinetic.publish.json
$ echo $?
0
```
Observed 2026-11-18: a `.mp4` and its `.publish.json` "ready" marker appeared in a publishing library. It had all
three approvals, so no gate was violated *for that job* — which is exactly why it is a P0: the job needed none.
A job with zero approvals took the same path.

### Failing test before the fix

```
$ cd /tmp/vf-p0-verify && pytest tests/test_export.py -k "both_gates"
E  Failed: DID NOT RAISE ExportRefused
1 failed
```
The unfixed `export_job` returned normally for a job with no grants at all.

### Root cause

`contentos/export.py:117` (HEAD):

```python
if m.get("track") == "B":          # only hand-built jobs were gated
    missing = [g for g in ("SCRIPT_APPROVED", "PRODUCTION_APPROVED") if not ledger.approved(job_id, g)]
```

A pipeline job has **no `track` key** (`contentos/ui_state.py:390` reads `"B" if manifest.get("track") == "B"
else "A"`), so the branch never fired. The gates *were* enforced — but only at the `voice` and `render` stages
(`pipeline.py:418` `GATE_OF`). Every route that skips those stages reaches `ready/` unguarded:
`contentos.sh storage export <id>` (`storage_cli.py:57`), `pipeline run --only export` (`pipeline.py:608`), and
the Studio export button (`ui_api.py:257`). Export is the single choke point all four share, and it was the one
place the check was missing.

### Code change

`contentos/export.py` — the branch is gone; both tracks go through one function:

```python
refusal = gate_refusal(job_id, d, m)
if refusal:
    raise ExportRefused(refusal)
```
(Full diff: `git diff contentos/export.py` in the working tree.)

### Regression test

`tests/test_export.py::test_export_requires_both_gates_on_every_path` — asserts **state**, in order:

| Assertion | What it proves |
|---|---|
| `tree(pub) == before` | the publishing library is byte-identical after the refusal |
| `ready/**/*.mp4 == []` and `ready/**/*.publish.json == []` | no artifact **and** no "ready" marker |
| `read_manifest(d).get("export") is None` | no export record was written |
| `not (d / "export-result.json").exists()` | the export stage produced nothing |
| `manifest["status"] != "exported"` | the job did not transition to exported |
| after `approve(...)`: `status == "exported"` | the refusal is policy, not corruption |
| `sidecar["video_sha256"] == sha256_file(mp4)` | the sidecar binds the exact bytes published |

### Independent verification

`docs/audit/SECURITY_AND_RELIABILITY.md` S-01, produced by an agent that never saw this dossier, reached the same
`export.py` line independently and reproduced the same export-without-gate outcome from a separate temporary
`PUBLISH_DIR`.

---

## P0-B / G-02 — an approval was a grant on *existence*, not on content

**Severity:** P0. **Status:** FIXED, then found BYPASSABLE by an adversary, then re-fixed. **Rung: TESTED.**

> **This dossier's first version was wrong.** It said "FIXED, verified" after one round of tests. The adversary
> (`POTATO_CHALLENGE.md` §A) found that 8 of 12 mutation scenarios still shipped, because `gate_refusal` fell back
> to the existence check whenever the spec or a digest was unavailable. Deleting the recorded spec after approval
> was enough to ship edited content. That fallback is now closed and the deleted/empty/unparseable-spec cases are
> refused, but **the history is kept here on purpose**: a fix that passes its own tests is not a verified fix.

### Reproduction

1. Job `edited`, spec on disk, `source_spec` recorded in the manifest.
2. `ledger.approve(cid, "SCRIPT_APPROVED", subject_sha256=script_digest(spec))`.
3. Export once → succeeds, `ready/` holds the reviewed render.
4. Edit the spec's script text so `script_digest` changes.
5. Export again with `--force` → **succeeded on unfixed code**, replacing the published artifact with a render of
   content no human approved.

### Failing test before the fix

```
$ cd /tmp/vf-p0-verify && pytest tests/test_export.py -k "edited_content"
E  Failed: DID NOT RAISE ExportRefused
1 failed
```

### Root cause

Two facts that compose into a hole:

1. `ledger.approved()` (`ledger.py:82`) is `SELECT 1 FROM approvals WHERE content_id=? AND gate=?` — it ignores
   `subject_sha256` entirely.
2. The digest machinery already existed and already returned the right answer: `ledger.check_gate()` reports
   `"mismatch"` when digest-bound grants exist but none covers the current content (`ledger.py:68-78`). It was
   called only from `pipeline.py:450`, i.e. from the stages that `storage export` skips.

So the capability to detect the replay existed and was never consulted at the last gate.

### Code change

`contentos/export.py::gate_refusal` calls `ledger.check_gate` against the live digest from
`pipeline.gate_digest` (`SCRIPT_APPROVED` → `script_digest(spec)`, `PRODUCTION_APPROVED` →
`production_digest(d, spec)`), reading the spec from `manifest["source_spec"]`. `mismatch` is a refusal;
`unbound` (legacy grants without a digest) stays valid so existing jobs are not stranded. If the spec file or the
composition is gone, it falls back to the existence check rather than inventing a digest.

### Regression test

`tests/test_export.py::test_export_refuses_an_approval_granted_for_edited_content` — asserts:

| Assertion | What it proves |
|---|---|
| `check_gate(..., approved_digest)[0] == "ok"` | the binding holds for the reviewed content |
| sidecar sha == published sha | the first export bound the real bytes |
| `current_digest != approved_digest` | the edit really moved the digest |
| `check_gate(..., current_digest)[0] == "mismatch"` | **the binding fires** - a state, not a message |
| `approved(...) is True` | a row still exists, which is precisely why existence checks shipped the edit |
| `pytest.raises(ExportRefused)` on the edited content | the replay is refused |
| published sha unchanged, still exactly one mp4 | the refusal did not replace the reviewed render |
| re-approval with the new digest → no refusal | the documented remedy works |

### Independent verification

`SECURITY_AND_RELIABILITY.md` S-01 flagged this as the P0 my first fix did **not** close, and named
`check_gate` as the fix. That is an adverse finding against the orchestrator, independently derived.

---

## P0-C / G-03 — no approval binds to `video.mp4`

**Severity:** P0. **Status history:** OPEN, no fix attempted (2026-11-18, superseded) -> Option D implemented,
TESTED (2026-11-18, superseded) -> **reworked by P0-1b: render attestation in the ledger, see the P0-1b dossier
below and `MASTER_GAP_REGISTER.md` G-03** (2026-11-19). The original "OPEN" text is kept below as written.

### Reproduction

1. Complete a job to `exported` with both gates granted.
2. Replace `<job>/video.mp4` with a different render (any other mp4 of the right resolution).
3. `contentos storage export <id> --force`.

Expected: refusal. Actual: **succeeds.** Every gate is still satisfied because no digest covers the render.

### Root cause

`pipeline.production_digest` (`pipeline.py:435-443`) hashes the composition HTML plus `audio/*.wav`. The video's
sha is first computed *at export* (`export.py`, in `_export_locked`) — after review. The one artifact that gets
published is the one no approval binds to.

### Why no fix was attempted

The fix is a schema decision with consequences outside the code:

- **Option A** — add the reviewed render's sha to the `PRODUCTION_APPROVED` grant. Needs a new approval step
  after `render`, which changes the operator workflow and every existing job's approval state.
- **Option B** — bind the render into `production_digest`. Makes `PRODUCTION_APPROVED` impossible to grant before
  a render exists, which inverts the current gate order (gate before render).
- **Option C** — accept the render as derived output and rely on the composition+audio digest. Defensible, since
  a re-render from the same composition and audio is deterministic — but only if HyperFrames determinism is
  actually proven, which nobody has measured.

Choosing between these silently would be worse than leaving it open. Recommended: **Option C plus a determinism
test**, because it preserves the gate order; fall back to A if HyperFrames re-renders are not byte-stable.

### Resolution — adopted Option D, not the Option C this dossier recommended

The adversary (§D) showed Option C was **wrong on its own premise**: `export_job` copies whatever `video.mp4` is on
disk and never re-renders, so render determinism is irrelevant to whether a swapped file ships.

Implemented instead, as a *separate integrity check* (not an approval):

1. `pipeline._note_stage` records `final_video_sha256` after the render stage and its audio hook
   (`pipeline.py:545`). This is the one place the manifest gates anything, and its docstring now says so.
2. `export.render_integrity_refusal` compares that record against the file at export and refuses on mismatch.
   A legitimate re-render updates the record, so re-rendering is not blocked.

Regression test: `tests/test_export.py::test_export_refuses_a_swapped_render` — verified to **fail at HEAD**
(`DID NOT RAISE ExportRefused`) and pass after.

**Still open** (adversary §A, not closed): removing `source_spec` from the manifest entirely, and repointing
`source_spec` at a pristine copy of the spec, both still degrade to the existence check. Both require the operator
to edit the manifest by hand, and both are listed in `IMPLEMENTATION_PLAN.md` as P0-1b.

### Rung discipline (rule 4)

The export gate is **TESTED** — reproduced, failing test, fix, regression test, adversarial attempt. It is **not
PRODUCTION-READY**: two manifest-level bypasses remain, and G-03's integrity fix covers the render file but not
the approvals' relationship to it.

---

## P0-1b - export trusted an editable manifest (2026-11-19)

**Severity:** P0. **Status:** IMPLEMENTED, TESTED; the two named bypasses are independently VERIFIED closed
(`POTATO_FINAL_SECURITY_REVIEW.md` section 7.6). Residual risks are in `MASTER_GAP_REGISTER.md`, current-status table.

### Reproduction (before)

`/tmp/attack_ab.py` (kept outside the repo) builds an approved, rendered Track A job in a `/tmp` workspace, then:
- **Attack A** - replaces the spec with an unapproved one and `video.mp4` with an unapproved render, deletes
  `source_spec` from `manifest.json` and rewrites `final_video_sha256` to the new video;
- **Attack B** - the same, but repoints `source_spec` at a pristine copy of the approved spec.

Run against the checkpoint tree (HEAD `86eeaa2` + the 21:42 working tree, rebuilt in a throwaway worktree from
`~/.contentos/checkpoints/phase1-20261119-2142/`):

```
attack-a: EXPORTED (bypass)
attack-b: EXPORTED (bypass)
```

### Root cause

Every fact export used to decide came from `manifest.json`: which spec to digest (`source_spec`) and which video
sha is the render (`final_video_sha256`). Anyone who can edit the job folder can edit both, so the check reduced to
"some approval row exists".

### Fix

Export no longer reads the manifest to make a trust decision.
- `ledger.renders` (new table, `ledger.attest_render` / `render_record`): one row per render, written only by the
  pipeline render stage (`pipeline._stages`), `track_b.render` and `contentos job register`. It records the video
  sha, the source (`pipeline`, `track-b`, `register`), the spec path the run used, and the gate digests the render
  was made under, taken before rendering and re-checked after it (a mismatch drops the render, PF-05).
- `export.approval_refusal` (both tracks, every route: pipeline export stage, `storage export`, Studio API) requires:
  the bytes on disk are an attested render of this job; both gates hold a digest-bound grant equal to the digests
  in that attestation (unbound grants do not count); and the content behind those digests is unchanged now. The
  bytes checked are pinned through the copy (`_export_locked` re-verifies the sha inside the lock).
- `pipeline.production_digest` binds every file under the composition root (following directory symlinks,
  loop-safe; a FIFO or device makes it unbindable), plus reviewed audio takes. `audio/ambient_bed.wav` is excluded
  as a render output. Only `project_remotion/node_modules` is bound by link target alone (accepted toolchain risk).
- A hand-built render (`job register`) binds PRODUCTION_APPROVED to the video bytes themselves
  (`pipeline.video_digest`), so swapping it and re-registering needs a fresh approval.
- `contentos approve` prints what it binds before recording; `--show` records nothing; `--expect DIGEST` grants
  only if the content still has the digest the approver saw.
- Also closed on the way: manifest `job_id` must match the requested job (PF-04); a forged export record cannot
  aim `--force` outside `ready/` (PF-20); Track B render requires SCRIPT_APPROVED too (PF-10).

### Evidence (after)

```
attack-a: REFUSED - attack-a: not exported, video.mp4 (sha c70ec23368f7) is not a render the factory recorded
attack-b: REFUSED - attack-b: not exported, video.mp4 (sha c70ec23368f7) is not a render the factory recorded
```

`tests/test_export_security.py` (49 tests) covers the attack list of the Phase 1 mandate: delete and repoint
`source_spec`, spec edited / replaced by another valid spec / deleted, approval metadata forged in the manifest,
ledger digest tampered, unbound grants, a replayed approval from a previous version, a grant for another job, a
replaced video (also with the manifest vouching for it), a replaced manifest, a swap during export, a missing
attestation, a lost ledger, every export route (API, CLI, Studio, pipeline stage), and the Track B equivalents.
Each test asserts that `ready/` is byte-for-byte unchanged, not only the message.

A real HyperFrames render (`/tmp/vf-smoke`, 2026-11-19 22:17): gates stop the run twice, the approved render
exports, a swapped video and an edited spec are refused by `storage export --force`, and an edited project file
blocks the re-render at the PRODUCTION gate.

### Rung discipline

TESTED and independently VERIFIED for the two named bypasses. **Not production-ready**: see the open PF rows in
`MASTER_GAP_REGISTER.md` (PF-02 default approve binding, PF-05 render-window swaps, PF-22 out-of-root assets,
PF-23 MPT materials).
