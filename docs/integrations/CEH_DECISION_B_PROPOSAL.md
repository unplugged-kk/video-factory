> SUPERSEDED 2026-11-11 by CEH_DECISION_B_DOSSIER.md. Kept as the original draft; do not use it as the current plan.

# Decision B proposal (DRAFT, do not execute)

Prepared 2026-11-11. Blocked on Decision A. Final entry/catalog fingerprints do not exist until A is granted and CEH publishes;
the prospective values in the A dossier must not be used as trust anchors.

## What exists

- Branch `codex/ceh-catalog-consumer` (local and `origin`), commit `b1befad73b4285ce461eb48861e5559c069d2776`, base `36bb558`.
- 5 added files, 551 lines: `contentos/ceh_catalog.py`, `contentos/ceh_contract.py`, `docs/integrations/CEH.md`, two test files.
- No pipeline, CLI, config, gate, renderer or ContentForge change. Disabled by default. Not called by production code.
- `git merge-tree` of that branch into current `main` (`a0f60cd`): clean, no conflicts (checked 2026-11-11).
- The `/tmp/ceh-vf-consumer` checkout named in CEH docs no longer exists. The branch on origin is the source of truth.

## Metadata-only, stated plainly

The consumer validates catalog metadata and returns digest REFERENCES. It never opens, hashes, installs or invokes the skill
artifact. `ceh_contract.py` opens only the catalog file. So even after merge and opt-in, there is NO artifact consumption.
Do not report CEH integration as complete on metadata discovery alone.

## Proposed B scope (smallest safe)

B1 (metadata): merge `b1befad` into main by normal PR; rerun `tests/test_ceh_catalog_provider.py tests/test_ceh_contract.py` and the full suite
(`~/.contentos/venv/bin/python -m pytest tests`) on merged tree; keep disabled by default; opt-in only via `--enable` plus
`--trusted-digest` taken from the owner-reviewed final catalog.

B2 (artifact, separate decision): a small `verify_artifact(entry, skill_dir)` that, given an explicit local skill directory, recomputes the
bundle digest with the same algorithm as CEH `skill_digest` and fails closed on mismatch; returns paths of SKILL.md and references for a
deliberately authorized planner to read. Design constraints:

- Reference, never copy: VF reads the canonical dir in the CEH checkout (path from explicit config/arg). No second copy in VF.
- Symlinks: CEH installs agent links to canonical dirs; B2 must resolve and verify bytes, not trust the link. Portability across Macs
  is not assumed: path is configuration, absence means "CEH unavailable", not an error.
- Pin: version + bundle digest + entry digest from the trusted catalog. Dependencies: this skill has none (instruction-only).
- Result validation: planner output (`kinetic-type-plan.json`) checked by existing VF `direction` validators and QA, unchanged gates.

## Standalone guarantee (mandate)

Core engine must not import `ceh_*`. Integration stays an optional adapter. Test to add with B1: with CEH disabled, absent, empty or
digest-mismatched, `./contentos.sh pipeline run` on an example spec behaves identically. CEH-dependent commands print why unavailable.

## Rollback

Omit `--enable`. Withdrawn release: `uv run ceh withdraw CEH-0018 --note ...`, re-export, accept new digest. Post-merge revert of
`b1befad` needs owner approval and a clean target. Do not reset, clean or change pins.

## Test plan

Focused 71 tests; full VF suite; Node suite `node --test contentos/adapters/v1/*.test.mjs`; standalone-with-CEH-off pipeline check;
one disposable gated job in the workspace using the verified guidance; `./contentos.sh qa` and `explainer-visual-qa` with an independent critic.

## Expected production behavior after B1

Default: nothing changes. Opt-in: a metadata selection JSON. No job gate, publish or spend permission is granted by B.
