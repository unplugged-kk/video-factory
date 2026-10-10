# Motion Director M2 report: the video-director and a dry-run storyboard

Status: M2 complete, stopped for review. Nothing rendered, committed or pushed. Date: 2026-10-11.

## 1. Summary
M2 adds a project-local `video-director` skill, a short motion-intent reference, a small pure-Python planning module (`director.py`) with a CLI, 40 new tests, and one complete dry run for "What Happens When an AI Agent Uses a Tool?". The dry-run plan passes the M1 validator, the story-coherence checks and the anchor check. No `sceneplan/` version change was needed. Validation proves structure, not beauty: the plan has not been rendered or reviewed visually.

## 2. M1 verification (before building on it)
| Check | Result |
|---|---|
| Registry parses and validates | `direction registry` reported 88 installed, 2 available, 1 candidate, 2 unavailable; no problems |
| Status spot-check | p5.brush `candidate`; vibe filter and Motion AI Kit `unavailable`; MoneyPrinterTurbo lane `available` (whole-video, opt-in); nothing paid |
| Status meanings | Unchanged |
| M1 direction tests | 36 passed (before and after the M2 validator additions) |
| Full suite, Python 3.12.15 | **139 passed, 2 skipped, 1 failed** (142 tests) |
| `test_core.py::test_local_beats_paid_even_when_both_healthy` | **Reproduces**, identical to M1 (`'paid_api' != 'paid_api'`). Not touched; cause not investigated; provider code left alone |
| Verified mistakes corrected | None in the registry. One M1 module change: `direction.py` gained three optional fields (section 4) |

Presence versus runtime evidence ("installed" means file present, lock-verified and referenced; it is not a render test):
| Capability | Evidence |
|---|---|
| `hf.native:html-svg-css`, `hf.rule:svg-path-draw` (the only two the dry run selects) | Files present and lock-verified. Not render-tested in M2 |
| HyperFrames CLI | Executed in M2 (version printed); `lint` executed on a scratch copy of the Pilot landscape project, outside the repo |
| Registry loading, validator, director | Covered by tests (M1 36 + M2 40) |
| `tool:preview` | No test; presence only |
| `treatment:handdrawn-p5brush` | Candidate; experiment exists, no promotion |

## 3. Files added or modified
Added:
- `.claude/skills/video-director/SKILL.md`, `.claude/skills/video-director/references/motion-intent.md`
- `contentos/production/director.py`
- `tests/test_director.py`, `tests/fixtures/m2-dryrun-scene-plan.json`, `tests/fixtures/m2-dryrun-script.txt`
- `workspace/experiments/m2-director-dryrun-001/` (section 7)
- `docs/factory-v2/12-motion-director-m2-report.md` (this file)

Modified:
- `contentos/production/direction.py`: optional `reframe`, `verify`, `substituted_from`; `why` is now also required for secondary motion and for substitutions. Plans without these fields validate as before.

Not modified: ContentOS builder, `sceneplan.py`, HyperFrames, the default renderer, `config/capabilities.json`, Pilot 001, ep2, other experiments, global skills or symlinks.

Provenance: the skill files live under `.claude/`, which the file bridge refuses to write. I wrote them through a staging folder inside the experiment directory and moved them with the device shell. An empty `_stage/` folder is left there; deleting it needs your approval (see section 9).

## 4. Why the schema extension
`sceneplan/1` already carries free-text scene fields, so no new version was needed. The three direction fields were the smallest additions that made the required per-scene content machine-checkable: `reframe` (16:9 and 9:16 notes, both required), `verify` (claims still to be checked), `substituted_from` (a preferred, non-installed capability that was replaced). All optional, tested, and rejected if malformed. Plans with no direction block are unaffected (Pilot 001 fixture still validates).

## 5. Skill activation and usage
- Location and name: `.claude/skills/video-director/SKILL.md`, name `video-director`; the description starts with "Use when planning a new Video Factory explainer from a topic" and says "Planning only".
- It activates for a new explainer from a topic and writes into one experiment directory. It does not render, edit the builder or install anything.
- Defaults when only a topic is given: general learners, 45-60 s, `calm-precise`, both aspects.
- Workflow: registry first, brief, script, scenes, treatment with a simpler-alternative test, capability selection, motion intent, two formats, verification list, then `director check`.
- Not tested: automatic skill triggering (needs a fresh Claude session; the project skill was not loaded in this one).

## 6. Motion intent and precedence
`references/motion-intent.md` is advisory and written fresh: intent first, one personality per video, one focal point, primary/secondary/ambient, counter-motion only when it explains, timing follows narration, static is valid, camera default `hold`, a failure vocabulary. Its method is paraphrased from the approved audit; nothing is copied from LottieFiles or Motion AI Kit. Numbers marked provisional are this project's own.

Precedence (higher wins): brief and owner decisions; `hyperframes-core`; `explainer-motion-craft` R1-R6; `video-director`; official `hyperframes-animation`/`-keyframes`; the motion-intent reference; `explainer-visual-qa` after rendering. House rules preserved: no camera drift, no ambient motion, no default overshoot, no staggers that fight narration cues, no motion for its own sake.

## 7. Capability selection behaviour
Implemented in `director.select_capability` / `usable`, tested:
- Only ids in `config/capabilities.json`; the kind must be a scene technique (a lane is not).
- `installed` is usable if its file exists; `available` only with `opt_in`; `candidate` only in experimental mode and an experimental scene; `unavailable` never; paid needs explicit approval.
- If the first preference is unusable, the result is the first usable of: other preferences, the explicit fallback, the registry fallback, `hf.native:html-svg-css`. The substitution and its reason are recorded. If nothing is usable, the result is `needs_review` with no choice.
- The dry run substitutes once: scene `menu` preferred the p5.brush candidate and uses native SVG. That is a deliberate preference that exercises the recorded-substitution path, not an accident.

## 8. Dry-run artifacts (all in `workspace/experiments/m2-director-dryrun-001/`)
`README.md`, `brief.md`, `script.txt`, `storyboard.md`, `scene-plan.json`, `decision-log.md`, `capability-report.md`, `capability-report.json`, `storyboard.estimated.md`, `validation.txt`.

Result: 7 scenes (hook, menu, request, run, result, loop, next); 140 words, about 56.0 s estimated (words at 2.5 per second, not a measurement); capabilities used: `hf.native:html-svg-css`, `hf.rule:svg-path-draw`, both installed; none paid, none non-installed; static scenes: menu and next; no camera moves, no ambient motion. The M1 validator reports 0 issues and `director check` exits 0.

Caveats:
- The title equals Pilot 001's. The plan and script are independent; the Pilot was not read from or written to.
- Facts: the request/result flow was checked on 2026-10-11 against Anthropic's tool-use overview. Still open in `direction.verify`: loop repetition, a possible caveat for provider-hosted tools, the wording "request", and 9:16 platform-UI overlap.

## 9. Test results
- `tests/test_director.py` (40 tests) plus `tests/test_direction.py` (36): 76 passed.
- Full suite under Python 3.12.15: 139 passed, 2 skipped (layout tests need ffmpeg, node and HyperFrames Chrome), 1 failed (the pre-existing `test_core` case above).
- The new tests cover: selection (usable, opt-in, candidate, unavailable, paid, lane, missing file, nothing usable); report determinism; coherence on good and bad plans; anchors and duration; the dry-run plan passing the validator and `check`; every capability in the registry; static scenes present; ambient and camera quiet; the new fields; Pilot plan still valid; planning does not mutate the plan, registry or on-disk files. No test judges visual quality.
- Not run: your own `~/.contentos/venv` (not reachable); please run `python -m pytest tests -q` there.

Integrity: files under Pilot 001, ep2, motion-ab-001, p5brush-001, upstream-animation-map and motion-audit-001 have no modification time later than my pre-M2 baseline; motion-ab, p5brush, upstream-animation-map, motion-audit and both `explainer-*` skills reproduce their baseline hashes exactly. For Pilot 001 and ep2 my re-hash did not reproduce the baseline value, although no file in them is newer than the baseline; I cannot rule out a difference in the baseline method (for example which files it included), so please run `git status workspace` or your own checksum if this matters. `git status` differs from the pre-M2 listing only by the two new untracked files `director.py` and `test_director.py` (plus the skill and workspace additions in untracked directories).

## 10. Limitations
- The dry run is unrendered; the storyboard times are estimates; layout, legibility and the 9:16 safe zone are unproven.
- `installed` still means presence, not a render test; the two capabilities selected have not been rendered in this plan.
- The skill has not yet been exercised by a fresh agent session; whether its description triggers reliably is untested.
- `director.py` is not wired to the builder, by design; the plan is read by nothing downstream yet.
- Coherence rules (hook first, recap or cta last, not every scene animated) are structural heuristics, not creative judgment.
- Takeaway length and personality timings remain provisional.

## 11. Recommended next milestone (M3)
Run the plan through a real build, in a new project directory, without touching the production builder: voice, alignment against the real word times (re-run `director check` with measured timings), then a HyperFrames composition authored from this plan, lint, one 16:9 render and one 9:16 render, and `explainer-visual-qa`. That answers the open questions (legibility, cue sync, the p5.brush substitution) with evidence. Builder integration should wait until that build succeeds.

## 12. Commands
```
python -m contentos.production.direction validate workspace/experiments/m2-director-dryrun-001/scene-plan.json
python -m contentos.production.director check workspace/experiments/m2-director-dryrun-001/scene-plan.json --script workspace/experiments/m2-director-dryrun-001/script.txt
python -m contentos.production.director report workspace/experiments/m2-director-dryrun-001/scene-plan.json --script workspace/experiments/m2-director-dryrun-001/script.txt --out /tmp/m2-report-check
python -m pytest -q tests/test_director.py tests/test_direction.py
python -m pytest -q tests
```
