# Decision B dossier - CEH capability consumption in Video Factory

Prepared 2026-11-11. DECISION SUPPORT ONLY. Nothing here is approved, implemented, merged, installed, activated or published.
Supersedes the draft `CEH_DECISION_B_PROPOSAL.md` (kept for history). Decision A is recorded in
`~/git/creative-engineering-hub/reports/acceptance/2026-11-11/decision-a-approval-record.md`.

## 0. Read first: three blockers and what B can honestly cover

1. **No final catalog entry exists.** Decision A approved `kinetic-type-planning` 0.1.0 but kept parent CEH-0018 as CANDIDATE.
   CEH's exporter publishes skills only through a PRODUCTION parent, so the real catalog is still empty
   (`catalog-v2.json`, 0 entries, digest `11ef9402...9cc9da`, verified live). Final entry and catalog fingerprints therefore do not exist.
   Needs separate decision **A2** (CEH skill-level approval path, section F). Without A2, B2 can be built and tested on fixtures
   only; it cannot be run against a real approved release.
2. **Metadata discovery is not artifact consumption.** Merged `b1befad` returns digest references and never opens the bundle.
3. **Licence wording conflict.** `proposed-skill-metadata.yaml` assigns a LicenseRef; the owner said the guidance licence stays
   unassigned. This dossier assumes the approved bytes are the CURRENT bundle `942d06fc...` (not the `addfcc1b...` preview). Owner confirms (Q1).

Decision B is split so the owner can approve parts independently:
- **B1** merge the metadata consumer (disabled by default).
- **B2** add artifact verification (`verify_artifact`), adapter-only.
- **B3** (not proposed now) core pipeline/manifest integration. Out of scope; would need its own decision.

## A. Exact integration scope

### Repositories and commits (re-verified 2026-11-11, not assumed)

| Item | Value |
|---|---|
| VF repo | `unplugged-kk/video-factory`, local `~/git/video-factory` |
| VF `main` / `origin/main` | `a0f60cdf99c66df2733ad1e3d3787e35270a3e3c`; tracked tree clean; untracked: `AGENT_HANDOVER.md`, `SESSION_LOG.md`, `docs/integrations/` (documentation only) |
| Consumer branch | `origin/codex/ceh-catalog-consumer` = `b1befad73b4285ce461eb48861e5559c069d2776`, merge-base with main `36bb558` |
| Consumer diff | 5 files, all status `A`, 551 insertions, 0 deletions: `contentos/ceh_catalog.py` (50), `contentos/ceh_contract.py` (275), `docs/integrations/CEH.md` (29), `tests/test_ceh_catalog_provider.py` (40), `tests/test_ceh_contract.py` (157) |
| Merge into current main | `git merge-tree --write-tree` clean, result tree `4b8db944565cd5943282690666c14b0e950dfcac` |
| Consumer tests | exported `b1befad` to scratch and ran the two files: **71 passed** |
| CEH repo | `unplugged-kk/creative-engineering-hub`, main `ad1e1333df230df8dfbef190d90359be832e5667` = origin; 104 tests pass; `ceh validate` ok (48 resources, 3 skills) |
| Worktree note | `/tmp/ceh-vf-consumer` no longer exists; the origin branch is the source of truth |

### Exact artifact and approved version

| Field | Value |
|---|---|
| Skill / version | `kinetic-type-planning` 0.1.0 (instruction-only; 8 files; no executables, no exec bits, no scripts beyond a README note) |
| Bundle SHA-256 (recomputed with `ceh.catalog_publish.skill_digest`) | `942d06fc400fdf44beb9767d0300f6313cf8366372190325ad6c87799410c679` |
| Prospective `addfcc1b...b0` | recomputed OK, but NOT recommended (licence conflict above) |
| Final entry digest, final catalog digest | do not exist; blocked on A2 |
| Provenance (must be in the entry) | CEH-0018 `f9a8a041b85185ee4881b3471d3415e939aac772` MIT; CEH-0002 `229022ebca76972e119e36ada23a1648d51665ab` MIT |
| Licence metadata (entry) | usage grant only: internal commercial planning/production, no redistribution/sublicensing. Entry schema forbids an `spdx` of "unassigned/NONE/unknown", so it needs a `LicenseRef-...` label that denotes the usage grant, with `restrictions` saying no guidance licence is granted (Q2) |

### Files to change (proposed, nothing created yet)

Branch: `feat/ceh-artifact-verify` cut from `origin/main` (a0f60cd). Never on the dirty user checkout; a separate worktree or fresh clone.

| Step | File | Change |
|---|---|---|
| B1 | the 5 files above | `git merge --no-ff b1befad` (or cherry-pick); no edits |
| B2 | `contentos/ceh_artifact.py` | NEW, about 130 lines: `skill_digest()` conformant with CEH, `verify_artifact()` |
| B2 | `contentos/ceh_catalog.py` | edit: optional `--skill-dir` and `--record-to`; `recommend()` gains optional `skill_dirs` param; default behavior unchanged |
| B2 | `tests/test_ceh_artifact.py` | NEW: matrix in section D |
| B2 | `tests/fixtures/ceh_skill_bundle/` | NEW tiny bundle + `expected_digest.txt` generated once by CEH `skill_digest` (conformance vector) |
| B2 | `tests/test_ceh_isolation.py` | NEW: AST scan proving no module outside `contentos/ceh_*.py` imports `ceh_*` or `ceh`; no `subprocess`/`importlib`/`exec`/`eval`/`os.system` in `contentos/ceh_*.py` |
| B2 | `docs/integrations/CEH.md` | edit: artifact mode, config, rollback |
| none | pipeline, CLI, config, gates, renderers, ContentForge, HyperFrames pin, `contentos.sh` | NOT touched |

### Feature flags / opt-in (unchanged model, one addition)

- Disabled by default. Per-invocation `--enable`, plus `--trusted-digest` taken from an owner-reviewed final catalog.
- Artifact verification additionally requires an explicit absolute `--skill-dir` (CEH canonical checkout path). No env guessing, no
  search of `~/.agents`, no home scan. Absent flag means metadata only, as today.
- No persistent config, no auto-enable, no default path.

## B. Artifact verification (how it works)

`verify_artifact(entry, skill_dir, *, catalog_digest) -> dict`, adapter module only, fails closed:

1. **Locate.** Path comes only from the explicit `--skill-dir`. Directory name must equal `entry.skills[0].name`. Missing directory or
   no flag: result `verified: false, reason: "artifact unavailable"`, fallback standalone routing. Not an exception.
2. **Resolve exact version.** `entry.skills` must contain exactly one item with `name`, `version`, `digest`. Request is by exact
   `id` + exact `version`; no ranges, no "latest". Wrong version: not selected (existing selector) and also rejected here.
3. **Fingerprint.** Re-implement CEH's `skill_digest` exactly: sorted `rglob("*")` regular files; per-file sha256 of bytes; top-level
   `skill.yaml` parsed with `yaml.safe_load`, `catalog_release` and `approval` keys removed, re-serialised with
   `json.dumps(sort_keys=True, separators=(",",":"))` (CEH keeps default `ensure_ascii=True`; VF must too), then the list of
   `[relpath, sha256]` hashed. Compare with the entry digest using `hmac.compare_digest`. PyYAML 6.0.3 exists in `~/.contentos/venv`
   (verified); adding it as a hard dependency of the VF repo is NOT assumed (Q5).
4. **Reject modified or unexpected files.** Any added, removed or changed file changes the digest, so the bundle fails. Digest cannot say
   which file; the error reports mismatch plus the observed digest and file count, and lists per-file sha256 so the owner can diff.
   Also reject symlinks (root or inside), non-regular files, files with any exec bit, extensions outside `{.md,.yaml,.json}`, more than
   64 files, any file over 256 KiB. These are stricter than CEH and are checked BEFORE hashing.
5. **Provenance and licence.** Cross-check bundle `skill.yaml` `sources[]` (`ceh_id`, `url`, `commit`) against `entry.resources[]`
   (`id`, `url`, `pinned_commit`): must match exactly. Check `skill.yaml` `version`, `name`, `execution == "instructions-only"`,
   `requires.runtime == []`, `requires.bins == []`, `licence.third_party_code is false`. Entry licence block must pass the
   existing `validate_catalog` rules (commercial true, non-restricted spdx, restrictions, evidence). Missing licence info: reject.
6. **Missing, incompatible, unapproved.** Entry must be `APPROVED` with actor/time/evidence (existing validator). A catalog that is empty,
   absent, digest-mismatched, or lists the skill under another status: nothing selected, standalone proceeds, reason printed.
7. **No execution.** The module has no subprocess, import, eval, exec, network, package manager. Enforced by test 11 in section D.
   Bundle `scripts/` holds only a README; `.py/.sh/.js` files cause rejection via the extension allowlist.
8. **Single read.** Each file is read once into memory; the digest is computed from those bytes and the returned guidance text comes
   from those same bytes. This closes the verify-then-read race (TOCTOU) that "return a path" would reopen.

### How instructions reach the production workflow (stated plainly)

Metadata discovery does not run or load anything. The handoff is explicit and manual-gated:

1. `python -m contentos.ceh_catalog --enable --catalog C --trusted-digest D --task "kinetic typography" --skill-dir S --environment E`
   emits JSON: selected capability, verification record, and `guidance` (`{"SKILL.md": "...", "references/...": "..."}` verified text).
2. A deliberately authorized planner (an operator or agent in a normal gated VF job) receives that text as input material for its
   plan. It is guidance, never executed by VF. The plan output (`kinetic-type-plan.json`) goes through the existing VF direction
   validators, script/production approvals, QA and critic. Nothing about this bypasses a gate.
3. VF does not invoke any agent by itself. Whether to make the planner step automatic is B3, not proposed.

### Recording which capability version produced a video

B2 writes a sidecar only when the caller passes `--record-to <job_dir>`: `ceh-usage.json` with capability id, version, bundle digest,
entry digest, catalog digest, verified timestamp, mode `ceh-enhanced`. It does NOT edit `manifest.json` or any core file.
Native (standalone) jobs produce no such file. Writing the id into `manifest.json` or the QA report is B3 (core change) and needs its own approval (Q6).

## C. Architecture boundaries (how each is kept)

| Principle | Mechanism | Test |
|---|---|---|
| CEH is canonical registry and authority | VF never holds a catalog copy; it reads the CEH export at an explicit path and the CEH bundle at an explicit path, both digest-bound. No VF-side registry, no cached skills | test: tree scan finds no `library/skills/` or catalog copy in VF |
| VF independent | All CEH code in `contentos/ceh_catalog.py`, `ceh_contract.py`, `ceh_artifact.py`. No imports from the CEH Python package; contract is a reviewed snapshot with conformance fixtures | isolation test |
| CEH optional, standalone works | Core never imports adapter modules | standalone test, section D |
| Disable or disconnect is harmless | No flag means disabled fallback; absent path means "unavailable", exit 0 for metadata, exit 1 only when `--enable` was explicitly requested and failed | tests 6-9 |
| No duplicate registry | VF stores only `ceh-usage.json` evidence (ids/digests), never skill content | review + tree scan |

## D. Compatibility and test matrix

All new tests are offline, use `tmp_path`, never touch the real CEH checkout unless an env var points to it for the optional live conformance case.

| # | Case | Expected |
|---|---|---|
| 1 | Valid approved artifact (fixture entry + matching bundle) | `verified: true`, guidance texts equal file bytes, usage record correct |
| 2 | Fingerprint mismatch (one byte changed) | `verified: false`, no guidance returned |
| 2b | Extra file added / file removed / file renamed | mismatch, rejected |
| 2c | Symlink, exec bit, `.py` file, oversize file | rejected before hashing |
| 3 | Missing artifact directory | `verified: false` "artifact unavailable", standalone fallback, no exception |
| 4 | Unapproved candidate (entry status not APPROVED, or skill not in catalog) | not selected |
| 5 | Wrong version (request 0.2.0, catalog has 0.1.0; or bundle yaml version differs) | rejected |
| 5b | Provenance mismatch (commit differs from entry) | rejected |
| 6 | Missing or restricted licence info in entry | rejected by validator |
| 7 | CEH unavailable (catalog path missing, unreadable, invalid JSON, oversize) | disabled-style fallback JSON, exit 0 unless `--enable` |
| 8 | Empty catalog (`entries: []`, the real state today) | `selected: []`, standalone message |
| 9 | Integration disabled (no `--enable`) | disabled fallback, no file read at all (assert by patching `open`/`Path.read_*`) |
| 10 | Conformance vector: VF `skill_digest` equals CEH `skill_digest` on the fixture bundle; optional live case on the real `942d06fc...` when `CEH_ROOT` is set | equal |
| 11 | Isolation: AST scan, no core import of adapters; adapter has no subprocess/importlib/eval/exec/socket | pass |
| 12 | Standalone video creation with CEH disconnected: run the existing example-spec pipeline with CEH paths absent, adapter modules removed from the tree (temp copy), result equals baseline | outputs and QA identical to baseline |
| 13 | Existing regression: `~/.contentos/venv/bin/python -m pytest tests` and `node --test contentos/adapters/v1/*.test.mjs` on the merged tree | same pass/skip set as main plus the new tests |
| 14 | Existing `./contentos.sh qa` on a baseline sample | unchanged |

Baselines recorded earlier (not rerun by this dossier, to be rerun at implementation): live original VF 1023 passed, 8 skipped;
isolated consumer VF 1080 passed, 17 skipped; Node 66 pass. Counts differ because of user WIP tests. Re-verify on the real target.

## E. Rollback

Implementation is additive files only (B1 five new files, B2 three new files plus two small edits to CEH adapter modules and one doc).

| Situation | Step | Effect on standalone |
|---|---|---|
| Stop using CEH any time | Omit `--enable` (and `--skill-dir`) | none; nothing else reads it |
| Disable artifact mode only | Omit `--skill-dir` | metadata mode as in B1 |
| Withdraw a release | CEH: `uv run ceh withdraw CEH-0018 --note ...`, re-export, accept new digest | VF rejects old digest automatically |
| Before merge | Delete feature branch `feat/ceh-artifact-verify` (local and origin) | nothing on main changed |
| After merge | `git revert -m 1 <merge-commit>` on a clean target, only with explicit owner authorization | main returns to a0f60cd tree content for these paths |
| Never | `reset --hard`, `clean`, stash user WIP, force-push, change pins | |

Demonstration that standalone is unaffected: (a) verified today that `b1befad` adds 5 files and modifies none, and that no `contentos`
module references CEH (`grep` finds only an unrelated `Search` substring in `jobs.js`); (b) at implementation, tests 11-14 run on the
merged tree AND on the same tree with the `contentos/ceh_*.py` files deleted, and both must give the same results. The second run is the
rollback proof, executed on a scratch copy, not on the user's checkout.

## F. Authorization plan (nothing executed)

0. **A2 (CEH, separate):** authorize a skill-level approval path so a real entry can exist while CEH-0018 stays CANDIDATE
   (design in the Decision A record). Without it there is nothing real to verify against.
1. Owner reviews this dossier; answers Q1-Q7.
2. Explicit **Decision B** approval, naming B1 and/or B2 scope.
3. Separate **implementation authorization** (branch, files, worktree location).
4. Implement on `feat/ceh-artifact-verify` in a clean worktree off `origin/main`; never touch the dirty checkout.
5. Run section D in standalone and CEH-enhanced modes.
6. Present exact commits and `git diff origin/main...feat/ceh-artifact-verify`.
7. Request explicit **merge/activation** authorization. Then, separately, a first real gated job.

Neither A, B nor A2 grants any job gate, publishing permission or spend.

## G. Open questions for the owner

| Q | Question | My recommendation |
|---|---|---|
| Q1 | Approved bytes are the current bundle `942d06fc...`, and `proposed-skill-metadata.yaml` (LicenseRef, `status: active`) is NOT applied? | Yes |
| Q2 | Entry `licence.spdx` needs a LicenseRef label for the usage grant. OK with e.g. `LicenseRef-CEH-Owner-Internal-Use` plus restrictions "no guidance licence granted, no redistribution"? | Yes |
| Q3 | Authorize A2 (CEH skill-level approval path) as the way to get a real entry, rather than approving CEH-0018? | Yes |
| Q4 | B scope: B1 only, or B1 + B2? | B1 + B2 in one branch, merged only after section D passes |
| Q5 | Accept PyYAML as an adapter dependency (already in the venv), or require a pure-JSON conformance subset? | Accept; document it |
| Q6 | Is a `ceh-usage.json` sidecar enough for "which version made this video", or do you want `manifest.json` touched (B3)? | Sidecar now, B3 later |
| Q7 | Skill dir given as canonical path only (symlink rejected), or resolve symlinks installed for agents? | Canonical only |

## H. Unverified assumptions

- That the owner's Decision A text means current bundle bytes (Q1) and a usage-grant label (Q2). Not confirmed.
- That A2 is acceptable; it changes CEH code and tests and has not been designed in detail or reviewed.
- That PyYAML in `~/.contentos/venv` is stable for the real run environment.
- That the VF digest re-implementation will match CEH on non-ASCII YAML content; test 10 must cover non-ASCII; current bundle files' ASCII-ness not audited.
- Timestamp and identity of the owner's Decision A message were not captured; no signature.
- No real agent has ever consumed the verified guidance; interoperability UNVERIFIED. English, 1 phrase, 1 canvas only; Hindi/brand/narration not covered.
- Full VF suite not rerun in this dossier; only the 71 consumer tests (pass) and CEH 104 tests (pass).
- The consumer's catalog validator treats the `spdx` text with a regex; behavior with a real LicenseRef string is untested.
- Whether `git merge` onto a user-dirty `main` checkout would conflict was not tested; only `merge-tree` against committed main.

## I. Authorization request

Please answer Q1-Q7 and state one of: **approve B1 only / approve B1+B2 / defer / reject**, and whether to authorize **A2** in CEH.
Until then: no branch is created, no file in either repo's code changes, nothing is merged or enabled.
