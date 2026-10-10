# 11 - Motion Director M1 implementation report

Date: 2026-10-11. Implements milestone M1 of `10-motion-director-integration-audit.md`: a capability registry, a read-only direction validator and tests. Nothing renders, no renderer, dependency, global skill or Pilot file was touched, and nothing was committed.

## 1. Files created or changed

| File | Status | Purpose |
|---|---|---|
| `config/capabilities.json` | new (untracked) | Capability registry, schema `capabilities/1`, 93 entries |
| `contentos/production/direction.py` | new (untracked) | Registry loader and checker, scene-plan/direction validator, small CLI. Standard library only |
| `tests/test_direction.py` | new (untracked) | 36 tests |
| `tests/fixtures/pilot-001-scene-plan.json` | new (untracked) | Byte-identical read-only copy of Pilot 001's `src/scene-plan.json` |
| `docs/factory-v2/11-motion-director-m1-report.md` | new | This report |
| `docs/factory-v2/10-motion-director-integration-audit.md` | appended | Short "Implementation progress" section; original findings untouched |

No tracked file changed. `git status --short` before: 17 entries. After: the same 17 plus `config/capabilities.json`, `contentos/production/direction.py`, `tests/fixtures/`, `tests/test_direction.py` (`docs/factory-v2/` was already an untracked directory). `git diff --stat` still shows only the pre-existing `.gitignore` (+4) and `contentos/cli.py` (+15). `sceneplan.py` is unchanged.

## 2. Registry reference

### 2.1 Schema (`capabilities/1`)
Top level: `schema`, `note`, `verified` (`date`, `hyperframes` pin, `upstream_lock` path), `capabilities` (list).

Each entry has exactly these fields (unknown fields are rejected):

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable id, `namespace:name`, unique (e.g. `hf.rule:svg-path-draw`, `craft:R1`) |
| `name` | string | Human-readable name |
| `kind` | enum | `renderer`, `skill`, `house-rule`, `rule`, `blueprint`, `native`, `treatment`, `lane`, `tool`, `ref` |
| `status` | enum | `installed`, `available`, `candidate`, `unavailable` (section 2.2) |
| `purpose` | string | What it is for (taken from the project's own index or file, not written from memory) |
| `path` | string or null | Repository-relative file that evidences it; null only when nothing exists to point at |
| `context` | list of enum | `hyperframes`, `pre-render`, `post-render`, `alternate-renderer`, `reference` |
| `requires` | list of ids | Other capabilities it depends on (must exist; an installed entry may only require installed ones) |
| `offline` | bool | Works with no network |
| `paid` | bool | Needs a paid service |
| `limitations` | list of strings | Known limits, each taken from a project document or file |
| `fallback` | id or null | Installed capability to use instead |
| `status_reason` | string | Required for every status except `installed`: the prerequisite or the reason |
| `roles` | list (optional) | Blueprints only: the roles listed in `blueprints-index.md` |

### 2.2 Status meanings
| Status | Meaning | Production use |
|---|---|---|
| `installed` | File present, safe path inside the repo, tied to the pinned/lock-verified skills or project modules | Allowed |
| `available` | Known and usable after a documented prerequisite (`status_reason`) | Allowed only if the plan lists the id in `brief.opt_in`; needs a fallback |
| `candidate` | Experimental, not approved | Rejected in production. Allowed only in `mode="experimental"` on a scene with `direction.experimental: true`; needs a fallback |
| `unavailable` | Known but absent or blocked | Always rejected |

### 2.3 Contents (counts by status: **88 installed, 2 available, 1 candidate, 2 unavailable**)
| Group | Entries | Status |
|---|---|---|
| `hf.rule:*` | 48 | installed |
| `hf.blueprint:*` | 22 | installed |
| `renderer:hyperframes`, `hf.native:html-svg-css` | 2 | installed |
| `hf.skill:core/animation/keyframes`, `skill:explainer-motion-craft`, `skill:explainer-visual-qa` | 5 | installed |
| `craft:R1`..`craft:R6` | 6 | installed |
| `tool:align`, `tool:sceneplan`, `tool:preview`, `tool:motion-audit`, `tool:critic` | 5 | installed |
| `tool:animation-map` | 1 | available (installing its dependencies is an opt-in step in `explainer-motion-craft`) |
| `lane:mpt-stock` | 1 | available (needs the `moneyprinterturbo-api` container and free stock API keys; network) |
| `treatment:handdrawn-p5brush` | 1 | candidate (KEEP EXPERIMENTAL per `09`) |
| `treatment:vibe-filter` | 1 | unavailable (no implementation found) |
| `ref:motion-ai-kit` | 1 | unavailable (reference-only; hosted/paid parts; no LICENSE file) |

### 2.4 How it was verified (2026-10-11)
- Rules: the 48 unique `rules/*.md` paths in `rules-index.md` equal the 48 files on disk (asserted, not assumed). Two of them, `css-marker-patterns.md` and `gsap-effects.md`, have no YAML frontmatter, so purposes for all rules come from the index, which lists every file.
- Blueprints: the 22 ids in `blueprints-index.md` equal the 22 files; purpose is the first clause of each file's `intent`; `roles` come from the index.
- House rules: parsed from `- **R1 ...` through `R6` lines in `explainer-motion-craft/SKILL.md`; limitations quoted from those lines.
- Tools and skills: every `path` was asserted to exist when the file was generated; `python3 scripts/upstream_skills.py verify` printed "OK: installed skills match the lock"; `node_modules/hyperframes/package.json` is 0.8.114.
- Determinism: the registry was generated by a one-off script (not added to the repo) that sorts files and writes fixed key order; running it a second time produced a byte-identical file. In the repo, `python -m contentos.production.direction registry` re-checks paths and compares the rules, blueprints and house rules on disk with the registry, so drift is reported.
- "Installed" means present, hash-locked and referenced by the project's own docs. It does not mean render-tested in this milestone.

### 2.5 Deviations from the audit's seed table (10, section 8.1)
- `hf.native:text-card`, `svg-diagram`, `stat-card` collapsed into one `hf.native:html-svg-css`: no card templates exist in the repository (`contentos/templates/` holds only `gsap.min.js`), so three ids would have implied tools that are not there.
- `lane:mpt-stock` has kind `lane`, which is not allowed as a scene `technique`. It renders a whole video; per-scene use is not integrated.
- `tool:animation-map` is `available`, not installed: its dependency bootstrap fetches packages and is opt-in.
- Note: `registry/capabilities.yaml` already exists and describes provider capabilities (tts and similar). The new `config/capabilities.json` is a different registry (creative-direction techniques). The names are close; consider renaming one before M2 if this confuses.

## 3. Validator

### 3.1 API (`contentos/production/direction.py`)
```python
from contentos.production import direction as dr
reg = dr.load_registry()                       # config/capabilities.json; raises RegistryError(.problems) listing every problem
dr.check_registry(reg)                         # [] when paths exist and registry matches the files on disk
plan = dr.load_plan("path/to/scene-plan.json") # read-only
issues = dr.validate_plan(plan, reg, mode="production")   # or mode="experimental"; list[Issue(scene, field, value, message)]
```
`validate_plan` never modifies the plan or registry and never calls the resolver. `load_registry(path)` derives the repository root from the registry's location (`<root>/config/capabilities.json`).

### 3.2 CLI (exit 0 ok, 1 problems, 2 unreadable file)
```
python -m contentos.production.direction registry
python -m contentos.production.direction validate PLAN.json [--mode production|experimental] [--registry PATH]
```
Example message: `scene s: direction.technique[0]: unknown capability id; did you mean ['hf.rule:svg-path-draw']? (ids come from config/capabilities.json) (got 'hf.rule:svg-path-drawn')`

### 3.3 What is checked
- Plan: `schema` must be `sceneplan/1`; `scenes` non-empty; each scene has a unique non-empty `id` and a valid `starts_at` (word index >= 0 or non-empty phrase); consecutive word-index anchors increase; `title` a string if present. Other scene keys (`visual`, `transition`, ...) and top-level keys are ignored, so existing plans pass unchanged.
- `brief` (optional): known keys only; `personality` enum; `renderer` must be `hyperframes`; `arc` from the purpose enum; `opt_in` ids must exist and be `available` or `candidate`; `allow_ambient` boolean.
- `direction` (optional per scene): required `purpose`, `takeaway` (<= 20 words), `treatment`, `technique`; optional `focal`, `why`, `motion`, `cues`, `camera`, `exit`, `text_zone`, `assets`, `fallback`, `checks`, `experimental`; unknown keys rejected. `why` is required for experimental scenes and for `handdrawn`/`footage`. `ambient` must be `none` unless `brief.allow_ambient` is true (house rule R4). Assets need `ref`, `source`, `license`; `unknown` licences are rejected.
- Capability references (`technique`, `fallback`, `opt_in`): unknown ids rejected with close-match hints; only kinds `rule`, `blueprint`, `native`, `treatment` may be techniques; `unavailable` always rejected; `candidate` per table 2.2; `available` needs `opt_in`; `installed` entries whose file is missing or whose path resolves outside the repo (including via symlink) are rejected with the `sync` hint, but only if the plan references them. A fallback must be installed.
- Registry: structure, enums, duplicate ids, dangling or self `requires`/`fallback`, non-installed fallback, installed-requires-non-installed, unsafe paths (absolute, `..`, backslash), missing `status_reason`.

### 3.4 Not checked in M1
Cue phrases are not matched against real narration (needs aligned words), easing and overshoot are not inspected (needs built HTML), `checks` strings are free text, and `sceneplan/1.resolved` (the derived file the resolver writes, e.g. `storyboard/scene-plan.resolved.json`) is deliberately rejected as a different schema.

## 4. Tests

`tests/test_direction.py`: 36 tests (4 of them skip automatically when the gitignored Pilot workspace or the vendored skills are absent, so a fresh checkout still runs the other 32).

| Required case | Tests |
|---|---|
| 1 existing plan without direction | `test_plan_without_direction_or_brief_validates`, `test_wrong_schema_and_bad_scene_basics_are_reported` |
| 2 valid direction | `test_valid_direction_and_brief_validate` |
| 3 unknown ids | `test_unknown_capability_is_rejected_with_a_suggestion`, `..._fallback_and_opt_in_ids...`, `test_only_technique_kinds_can_be_techniques` |
| 4 unavailable | `test_unavailable_capability_is_rejected_in_every_mode` (both modes) |
| 5 candidate gating | production rejection, flag required in experimental mode, allowed with both, fallback required, `available` needs `opt_in`, opt-in of installed rejected |
| 6 missing fields / invalid values | `test_missing_required_fields_and_bad_values_are_actionable`, ambient, why, brief checks, registry invalid status |
| 7 no mutation | `test_validator_does_not_mutate_plan_or_registry`, `test_load_plan_and_cli_do_not_modify_the_file` (bytes and mtime) |
| 8 Pilot 001 | fixture validates; fixture equals the real plan when the workspace exists; the resolver passes `direction` through unchanged and does not mutate the plan; resolved file is reported as a different schema |
| 9 malformed registry | missing file, invalid JSON, wrong schema, empty list, non-object, 12+ simultaneous problems, installed-requires-candidate |
| 10 safe deterministic paths | unsafe path rejection, symlink escaping the repo, missing file reported only when referenced, `check_registry` output sorted, identical across runs and detecting drift |
| Real registry | counts, conservative statuses (p5.brush candidate, vibe unavailable, Motion kit unavailable, nothing paid), matches files on disk, accepts a real direction and rejects the reference-only kit |

### 4.1 Results
- `tests/test_direction.py`: **36 passed**.
- Whole suite, `pytest tests -q`: **99 passed, 2 skipped, 1 failed** (102 tests = the earlier 66 plus 36 new).
  - 2 skipped: `test_layout.py`, which needs ffmpeg, node and the HyperFrames Chrome (not available in the VM).
  - 1 failed: `tests/test_core.py::test_local_beats_paid_even_when_both_healthy` (provider routing picks a `paid_api` first). It fails identically on a copy of the repo with all M1 files removed, so it is not caused by M1. I did not investigate its cause; it appears to depend on which local providers are installed on the machine.
- Real-repo CLI runs: `registry` printed "88 installed, 2 available, 1 candidate, 2 unavailable" (exit 0); `validate` on both the fixture and the real Pilot 001 plan printed "OK: 0 issue(s)" (exit 0).

### 4.2 Environment note
The sandbox had Python 3.10 without pytest, and the repository needs 3.12 (`pipeline.py` uses nested f-string quotes). I created throwaway environments under the sandbox home, outside the repository (a 3.12.15 interpreter via `uv`, with pytest and pyyaml). Nothing was added to `package.json`, `requirements`, or the repository, and your own `~/.contentos/venv` was not used or reachable, so please run the suite once there.

## 5. Verification that nothing else moved
- Pilot 001 (`workspace/projects/pilot-001-agent-tool-use`) and `workspace/experiments/{motion-ab-001,p5brush-001,upstream-animation-map,motion-audit-001}`: file-tree SHA-256 recorded before and after; **all identical**.
- `~/.claude/skills` and `~/.agents/skills`: not touched (neither exists in the sandbox).
- `direction.py` imports only `argparse, difflib, json, re, sys, dataclasses, pathlib`: no renderer, no network, no new dependency, nothing paid.
- The existing pipeline path `sceneplan.resolve()` still processes plans with and without a `direction` block (tested).

## 6. Limitations
- "Installed" is evidence of presence and lock-verification, not a render test.
- Vendored skills (`hyperframes-*`) are gitignored, so on a fresh checkout every `hf.*` reference is rejected until `python scripts/upstream_skills.py sync` runs; the message says so.
- The registry has no generator in the repository; adding a rule or blueprint upstream means editing the JSON by hand, and `registry` reports what is missing.
- Takeaway length (20 words) and enum lists are first guesses, not calibrated.
- The Pilot fixture must be refreshed if its plan ever changes; a test flags drift when the workspace is present.

## 7. M2 should implement next
1. The `video-director` skill (`SKILL.md` workflow plus `references/motion-intent.md`, adapted from the LottieFiles method with an MIT attribution line), with no renderer change.
2. A dry-run direction for one new topic: a `scene-plan.json` containing `brief` and `direction`, validated with this module, plus the storyboard table with treatment and technique columns. No render.
3. Optional: validate `cues[].at` phrases against aligned words (reuse `sceneplan._find_phrase`), and decide whether to commit a small registry generator and whether to rename one of the two `capabilities` registries.
