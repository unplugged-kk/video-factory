# 08 - Motion-skills implementation report

Date: 2026-10-10. Companion to `07-motion-graphics-skills-audit.md`. Nothing here is committed; all changes are in the working tree of `~/git/video-factory`.

## Test results
- `~/.contentos/venv/bin/python -m pytest tests -q` -> **66 passed in 4.34 s** (run after the last change). Milestone A baseline was 39; the working tree adds 27 (6 align/sceneplan from the earlier phase, plus 8 + 7 + 6 from this task), none removed. Per file: align/sceneplan 6, core 5, critic 7, layout 2, loops 5, motion_audit 8, mpt 6, production smoke 21, upstream_skills 6.
- Use `pytest tests`, not bare `pytest` (bare run also collects tests under `vendor/`, which fail for unrelated reasons).
- `python scripts/upstream_skills.py verify` -> "OK: installed skills match the lock".
- `python -m contentos.production.critic .claude/skills/explainer-visual-qa/templates/critic-output.example.json` -> well-formed, computed verdict `revise` (the example is deliberately a revise case).
- SKILL.md frontmatter (name, description) checked for all five skills.
- **Pilot 001 unchanged:** tree hash compared before and after all experiments: 283 files identical. Nothing published; `PUBLISH_APPROVED` not granted.
- **Not tested:** that Claude Code on the Mac loads the project-scoped skills (global dangling-symlink finding in audit section 12); calibration of the critic thresholds; any Remotion or Motion Canvas render.

## Files added (new, untracked)
| File | Lines | Purpose |
|---|---|---|
| `contentos/production/motion_audit.py` | 96 | `ease_inventory`, `parse_ydif`, `motion_stats`, `video_ydif` (ffmpeg `signalstats`), `compare` |
| `tests/test_motion_audit.py` | 62 | 8 tests for the above |
| `contentos/production/critic.py` | 90 | Validates an independent critic's JSON report; computes verdict from scores and hard failures; CLI via `python -m` |
| `tests/test_critic.py` | 55 | 7 tests |
| `contentos/upstream_skills.py` | 129 | `sync` / `verify` / `remove` for pinned third-party skills with commit check and per-skill SHA-256 |
| `tests/test_upstream_skills.py` | 109 | 6 tests (local fixtures; no network) |
| `scripts/upstream_skills.py` | 49 | CLI wrapper: `sync [--record] | verify | remove` |
| `scripts/motion_compare.py` | 193 | A/B harness: `prepare`, `build`, `render`, `measure`, `frames`, `report` |
| `config/upstream-skills.lock.json` | - | Pin: hyperframes tag `v0.8.114`, commit `01c6f6004a00ecfa6e77ab4025b47a46a5e925fc`, Apache-2.0, accessed 2026-10-10, 3 skills with tree SHA-256 |
| `.claude/skills/explainer-motion-craft/SKILL.md` | 37 | Factory skill: motion rules R1-R6 |
| `.claude/skills/explainer-visual-qa/SKILL.md` | 39 | Factory skill: gates, inspection, independent critic, A/B discipline |
| `.claude/skills/explainer-visual-qa/references/critic-rubric.md` | 24 | Critic dimensions and hard failures |
| `.claude/skills/explainer-visual-qa/templates/critic-output.example.json` | 19 | Example report |
| `.claude/skills/hyperframes-core/`, `hyperframes-animation/`, `hyperframes-keyframes/`, `_upstream/` | 136 files | Vendored copy of the three official skills at the pinned commit plus `_upstream/hyperframes.LICENSE` and `hyperframes.PROVENANCE.md`. **Gitignored** (reproducible from the lock) |
| `docs/factory-v2/07-motion-graphics-skills-audit.md`, `08-motion-skills-implementation-report.md` | - | These documents |

`.claude/` holds 140 files in total: 4 factory-skill files that should be committed and 136 vendored.

## Files modified
| File | Change |
|---|---|
| `.gitignore` | Added a comment and two ignore lines: `.claude/skills/hyperframes-*/`, `.claude/skills/_upstream/` |
| `docs/factory-v2/05-architecture.md` | Added "Motion skills and quality gates" section |
| `docs/factory-v2/01-inventory.md` | Added "Skill inventory (project-scoped)" section |

## Pre-existing uncommitted work that this task did NOT change
`contentos/cli.py` (the `preview` subcommand), `contentos/production/{align,sceneplan,preview}.py`, `tests/test_align_sceneplan.py` and docs `01`-`07-guides-vs-implementation` belong to the earlier Milestone A / Pilot phases. They are listed so that nobody mistakes them for part of this integration.

## Experiments (gitignored, safe to delete)
`workspace/experiments/motion-ab-001/` (arms, results, frames, animation-map logs), `workspace/experiments/upstream-animation-map/` (three upstream scripts with matching SHA-256), `workspace/experiments/motion-audit-001/` (earlier manual copy).

## Verify and reproduce
```
python scripts/upstream_skills.py verify
~/.contentos/venv/bin/python -m pytest tests -q
python scripts/motion_compare.py prepare|build|render|measure|frames|report   # see audit 10.5
```

## Rollback
See audit section 11.4. Removing the integration leaves the Pilot, gates and pipeline untouched.

## Known limits (repeated so they are not lost)
Single render per arm; "looks better" unproven; variant B has more static time and dead zones that still need reveal timing; animation-map collision flags unreviewed; critic thresholds provisional; 9:16 platform UI safe zones unverified; the contentos builder itself has not been changed yet.
