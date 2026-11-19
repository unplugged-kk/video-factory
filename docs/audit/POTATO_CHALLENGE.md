# Adversarial challenge to P0_VERIFICATION.md

Reviewer role: read-only. Nothing in the repo was edited. All experiments ran in a throwaway
`VIDEO_FACTORY_WORKSPACE`/`VIDEO_FACTORY_PUBLISH_DIR` under `$TMPDIR` (deleted afterwards); the real
`ledger.db` mtime was checked before and after (`Nov 14 12:38`, unchanged). Reproduction scripts, outside the repo:
`/tmp/potato/attack.py` (scenarios), `/tmp/potato/mut.py`, `/tmp/potato/mut2.py` (mutations).

| | Finding | Verdict |
|---|---|---|
| A | P0-B "FIXED": approval cannot be replayed onto other content | **OVERSTATED** |
| B | Regression tests prove what the dossier claims | **UPHELD for the script gate; WRONG for the production gate** |
| C | Every route skipping voice/render reached `ready/` through `export_job` | **UPHELD**, with one unclaimed hole |
| D | Option C is preferable for G-03 | **WRONG** (it is the status quo, not a fix) |
| E | Capability-matrix rungs | **WRONG on 6 rows, count inconsistent** |

---

## A. P0-B fix bypassable — OVERSTATED

`gate_refusal` (`export.py:131-135`) only compares digests when a spec loads **and** a digest comes back; otherwise it
degrades to `ledger.approved()` — the existence check the dossier says was the root cause. Each scenario is a fresh
job: spec + composition + wav on disk, both grants **bound** to the real digests, then one mutation, then
`export.export_job(id)`.

| # | Mutation after approval | Result | Ships? |
|---|---|---|---|
| S0 | none (baseline) | exported | yes (correct) |
| S0b | spec script text edited | **REFUSED** | no (fix works here, and only here) |
| A1 | spec file deleted, `video.mp4` swapped | exported | **yes** |
| A1b | spec truncated to 0 bytes (`yaml.safe_load("")` is `None`, falsy), video swapped | exported | **yes** |
| A1c | spec = invalid YAML | uncaught `yaml.ParserError` (not an `OSError`/`ValueError`, `export.py:129`) | no, but a traceback: CLI catches only `StorageError` (`storage_cli.py:59`), Studio only `ExportRefused`/`StorageError` (`ui_api.py:258-261`) |
| A2 | manifest `source_spec` repointed at a pristine copy while the real spec is edited | exported | **yes** |
| A3 | `project/index.html` deleted (`production_digest` returns `None`, `pipeline.py:439`), video swapped | exported | **yes** |
| A3b / A3c | composition / wav bytes altered | REFUSED | no (works) |
| A4 | grants recorded **unbound**, spec edited, video swapped | exported | **yes** — `state == "unbound"` is not a refusal and, unlike `pipeline._check_gate:459`, prints no warning |
| A5 | no `source_spec` (what `job register` produces), grants bound to `"0"*64` / `"f"*64` (garbage) | exported | **yes** — Track B registered jobs get *no* content binding at all; the dossier's "both tracks, on content" is false for them |
| A6 | `video.mp4` swapped, everything else pristine | exported; published sha == swapped video's sha | **yes** (this is G-03, still open, confirmed) |
| A7 | manifest `source_spec` removed, spec edited | exported | **yes** |

Threat-model honesty: A2/A7 require editing `manifest.json`, i.e. a local actor who could also write the ledger. A1,
A1b, A3, A4, A5 do **not** need an adversary — a cleaned-up `specs/` dir, a regenerated composition, or a CLI
`approve` run before the spec was recorded produces them by accident. Those are the ones that matter.

**Real data.** I replayed the new gate read-only (`sqlite mode=ro`) against all 16 sidecars in `~/Desktop/Video-Publishing/ready`:
- 5 `tech90-*`: both gates `ok` with matching digests — good, the fix passes the freshest real jobs.
- 10 October jobs (`ai-models-on-kubernetes-001`, `ep6-…`, …): **no `source_spec`**, both gates `fallback-ok`. For 10/16 of the
  published library the "content-bound" gate is the existence check.
- `m3-sample-01-hf-sketch`: `PRODUCTION_APPROVED` = **mismatch** → it would now be refused on re-export. Cause not investigated
  (composition edited since approval, or a false positive). Unverified; someone must look before anyone re-exports it.

**Smallest correction (verified).** Delete the existence fallback: always call `ledger.check_gate(job_id, gate, current)`,
passing `current=None` when no digest is computable. `check_gate` already returns `mismatch` for "bound grant exists, nothing to
compare" (`ledger.py:75-78`). Result with that single change: A1, A1b, A3, A5, A7 → REFUSED; baseline still exports. Still open:
A2 (pin `source_spec` once per job, don't re-read a mutable path), A4 (decide whether `unbound` may ever ship; at minimum warn),
A6 (G-03). Mutating the existing suite to that behaviour: 124 pass, 2 fail — both are `match="SCRIPT_APPROVED and PRODUCTION_APPROVED"`
on my stub's message text, not behaviour; not investigated further. Also catch `yaml.YAMLError`/`KeyError`/`AttributeError`
around `gate_digest` (`script_digest({})`→`KeyError`, `script_digest([])`→`AttributeError`, run by me) and refuse.

Also: `gate_refusal` runs before `file_lock` (`export.py:171-173`), so the check and the copy are not atomic. Low.

## B. Tests — UPHELD / WRONG

`ExportRefused` subclasses `StorageError` and is also raised for missing video, supplied-audio and archived/claimed
jobs (`export.py:~181-200`), so `pytest.raises(ExportRefused)` alone would not prove the gate fired. Mutation testing settles it
(monkeypatched `export.gate_refusal` / `ledger.check_gate`, then run the two tests):

| Mutation | `both_gates` | `edited_content` |
|---|---|---|
| gate removed (`→ None`) | FAIL | FAIL |
| existence-only (my first fix) | pass (expected; it tests presence) | **FAIL** |
| `mismatch` treated as ok | pass | **FAIL** |
| **`PRODUCTION_APPROVED` mismatch treated as ok** | pass | pass — and **all 126 tests across the 7 export-related files pass** |
| `GATES` reduced to script only | — | caught only by 3 *other* tests (`test_job_register`, `test_legacy_manifest`) |

- UPHELD: the script-gate binding is genuinely pinned; the tests are killed by the right mutants. The state assertions
  (`tree(pub) == before`, no sidecar, sha equality) are real.
- **WRONG for the production digest:** no test exercises `PRODUCTION_APPROVED` content-binding at export. The dossier's
  P0-B claim covers "the digest recorded with it has to match what would be published now" for both gates; only one is tested.
  A3b/A3c work (my script), but nothing in the repo would notice a regression.
- `both_gates` approves with **unbound** grants and no spec, so it passes via the fallback — it proves presence, not binding.
- None of the fallbacks in section A is tested. Missing tests: spec deleted, empty, malformed, no `source_spec`, composition removed.

## C. Is P0-A overstated — UPHELD, one addition

`graft`/grep of `export_job(`: exactly three callers — `pipeline.py:387` (`s_export`), `ui_api.py:257`, `storage_cli.py:57`.
All three now pass through `gate_refusal`. `handoff.py:178-179` only moves files that already carry a sidecar; `storage_admin.migrate`
copies workspace/jobs/ledger, not `ready/` (no `ready` write in `storage_admin.py`). No unguarded writer found.
- Not claimed by the dossier: the fix is **not retroactive**. Everything already in `ready/` is grandfathered (see A, real data).
- Same defect class remains in publish: `pipeline.py:403` `ledger.approved(id, "PUBLISH_APPROVED")` is an existence check,
  and `PUBLISH_APPROVED` is never digest-bound (`cli._subject_digest` returns `None` for it, `cli.py:132`). Publishing is disabled
  (`youtube.yaml`), so latent; fix before that flag is flipped.
- Dossier cites `pipeline.py:608` for `--only export`; the call is in `_stages` (`pipeline.py:~604`). Cosmetic.
- `ui_api._spec_path:62-75` falls back to `workspace/specs/<id>.yaml` when `source_spec` is absent; `gate_refusal` does not.
  Studio approvals can therefore be bound to a spec export never reads. Inconsistent, not exploitable by itself.

## D. Option C for G-03 — WRONG

Dossier: "a re-render from the same composition and audio is deterministic". Irrelevant: `export_job` never re-renders. It copies
whatever `video.mp4` is on disk (`_export_locked`). Option C binds the *inputs* (composition + wav, `pipeline.py:441-442`);
A6 above swaps the *output* with inputs pristine and ships. Determinism would only matter if export re-rendered and compared,
which nobody proposes. Option C is today's behaviour relabelled.
Opposite case, cheaper and with no workflow change: **Option D** — at render completion record `sha256(video.mp4)` in the manifest
(currently `_note_stage` stores only relative paths, `pipeline.py:545-552`; note the `audio_bed` hook mutates the mp4 after
render, `pipeline.py:326-327`, so the pin must be taken *after* it) and have export refuse on mismatch. That is integrity, not a
human approval; say so. The real G-03 gap is that `PRODUCTION_APPROVED` is granted *before* render, so no human ever approves the
rendered bytes. That is a workflow decision, correctly left to the owner; but "Option C" is not one of the options.

## E. Rung inflation (rule 4) — WRONG

| Row | Marked | Evidence cited | Defensible rung |
|---|---|---|---|
| HyperFrames render lane | PRODUCTION-READY | `doctor` PASS + 5 mp4 names | `doctor` PASS = INSTALLED/EXECUTABLE. No frame of those 5 was viewed in this audit; QUALITY-APPROVED absent. **RENDER-VERIFIED** at best |
| English TTS (Kokoro) | PRODUCTION-READY | `doctor` PASS (`python import kokoro_onnx`) | INSTALLED. No audio was listened to by the audit. Handover claim, not evidence |
| Track A pipeline | PRODUCTION-READY | "suite green" | contradicted by the audit's own open P0 (G-03) and G-05/G-07/G-08 → **TESTED** |
| Export + sidecar | PRODUCTION-READY | one choke point | contradicts `P0_VERIFICATION.md` ("TESTED… not PRODUCTION-READY") and section A → **TESTED** |
| Technical QA (9 checks) | PRODUCTION-READY | "re-run at export" | 9 checks do exist (`qa.py:36-65`); nothing run by the audit; Lane F can't fail → **TESTED** |
| Track B hand-built composition | **VISUALLY VERIFIED** | "`ready/` jobs + proposal doc" | No frame of a Track B job was inspected (the sheets viewed were scenekit Track A). 0 of the manifests on disk carry `"track": "B"`. **EXISTS** |
| Batch / concurrent jobs | TESTED | "file locks… not run as a real batch" | the row's own evidence admits no run; no test cited → **EXISTS** |
| Job queue + worker | TESTED | "`tests/` queue tests" | only `test_queue_production.py` exists; unnamed, not run by the audit → **UNVERIFIED** until a file is cited |

Counts section: says "Capabilities inventoried: 30" — table has **27** rows; says "6 PRODUCTION-READY… publishing-by-refusal" —
table has **5** rows so marked, and the publishing row itself says CONFIGURED. After the corrections above the honest PRODUCTION-READY
count is **0**. Scenekit `visual_style` (6 styles, frames inspected) is absent from the matrix though it is the best-evidenced creative
row (RENDER-VERIFIED, partly VISUALLY VERIFIED: 4/6 styles viewed).

## Net

P0-A: closed for the pipeline routes, TESTED. P0-B: closed for exactly one case; seven concrete fallbacks ship. Downgrade
"FIXED, verified" to **PARTIALLY FIXED** until the existence fallback is removed and the production-digest/fallback tests exist.
P0-C: open, and the proposed Option C does not address it.

**Not verified:** why `m3-sample-01-hf-sketch` mismatches; the 2 suite failures under the fail-closed stub; whether HyperFrames
re-renders are byte-stable; Studio export end-to-end through HTTP; any run through `pipeline.run(only="export")` (read, not run).
