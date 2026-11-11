# Skills inventory

Verified against the filesystem on 2026-11-11. Counts are measured, not copied from older docs. A skill is
listed as usable only when its `SKILL.md` exists and its dependencies were checked; "installed" never means
"render-tested".

## 1. Where skills live

| Location | Count | Role |
|---|---|---|
| `.claude/skills/` | 14 dirs: 10 factory-owned + 3 pinned upstream + `_upstream` | **canonical project skills** |
| `.agents/skills/` | 13 dirs: a stale mirror + 4 generated `source-command-*`; missing the 5 universal-entry skills | per-agent mirror, gitignored; regenerate, never edit as source |
| `.commandcode/skills/` | 16 | Command Code-specific pack, including `hyperframes-creative`, `hyperframes-registry`, `media-use`; invisible to Claude Code |
| `~/.claude/skills/` | 633 | global personal pack |
| `~/.agents/skills/` | 633 | same personal pack, mirrored for other agents |
| `~/.commandcode/skills/` | many, including `wayfinder`, `writing-plans`, `executing-plans`, `using-superpowers` | global Command Code pack |
| `contentos/skills/library/` | 79 creative recipes + 7 core workflow skills | vendored, hash-verified, indexed by `config/creative-skills.json` |
| `.cursor/commands/` | 4 command templates | source for the generated `source-command-*` wrappers |

`.agents/` is now gitignored. The canonical copies are `.claude/skills/` and `.cursor/commands/`.

## 2. Factory-owned skills (`.claude/skills/`)

| Skill | Purpose | When to use | Dependencies | Tested? |
|---|---|---|---|---|
| `video-production-orchestrator` | Runs a whole video through phases P0-P11, gates and Rules A/B | Any complete video, or auditing a finished one | `contentos.sh`, `config/*.json`, ffmpeg | Gates are mechanized; its rubric is labelled provisional |
| `video-director` | Creative direction: audience, hook, arc, scene plan | Planning a Track B explainer before composing | `config/capabilities.json`, `director check`, `platforms budget` | Validator exists; structure only, not taste |
| `explainer-motion-craft` | House motion rules R1-R6 | Authoring or revising HyperFrames motion | `hyperframes-core`, GSAP, `motion_compare.py` | A/B checked on Pilot 001; the only rules with evidence |
| `explainer-visual-qa` | Post-render review, phone-size frames, independent critic | After every render, before calling it ready | `visual_gate`, ffmpeg, `preview`, `critic` | Partly calibrated; critic thresholds provisional |
| `creative-skill-router` | Single entry to the 86-skill creative catalogue | A named format/style, or "which format fits?" | `python -m contentos.skills route|show|deps|compat|plan` | `compat` is a rule check, not a render |
| `create-video` | Universal entry for any video request | Topic, script, audio, song, images, data, edit, lyric, repurpose, asset search | `contentos.sh videojob`, `video-production-orchestrator` | Selector and presets tested; end-to-end render not produced by this entry yet |
| `edit-video` | Thin shortcut: intent `edit` | Editing a supplied recording | `create-video/SKILL.md` | Same as `create-video` |
| `make-lyric-video` | Thin shortcut: intent `lyric` | Song + lyrics | `create-video/SKILL.md` | Same; note the vendored recipe named `lyric-video` is a different artifact |
| `repurpose-video` | Thin shortcut: intent `repurpose` | Long video -> short clips | `create-video/SKILL.md` | Same |
| `video-assets` | Thin shortcut: intent `assets` | Index/search local B-roll | `contentos/production/assets.py` | Asset tests pass; no real footage used |

## 3. Pinned upstream skills

`hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes` are gitignored, hash-verified and
restored by `python scripts/upstream_skills.py sync`; `verify` checks them. Never edit them in place. They carry
the composition contract, 40+ animation rules/blueprints/transitions, and camera/keyframe patterns.
`hyperframes-creative` and `hyperframes-registry` live in `.commandcode/skills/` and are not visible to Claude
Code; use them only from a harness that loads that directory.

## 4. Creative library

`contentos/skills/library/` holds 79 creative recipes and 7 core workflow skills, hash-verified and indexed in
`config/creative-skills.json` (86 entries). Read `readiness` and `blockers` before promising a format; several
need user-supplied media, `torchaudio`/MMS alignment, face detection, or a beat detector that is not installed.
Route with:

```bash
python -m contentos.skills route "a lyric video for this song"
python -m contentos.skills show lyric-video
python -m contentos.skills deps youtube-clips
python -m contentos.skills compat lyric-video kids-story
```

The 7 core skills duplicate names that also exist globally: `video-director`, `script-to-storyboard`,
`style-architect`, `reference-video-analyzer`, `factory-skill-integrator`, `video-qa-critic`,
`publishing-packager`. The vendored copy is the one this repo tests.

## 5. Global skills worth using

| Need | Use | Location | Notes |
|---|---|---|---|
| Repository discovery | `repo-mapper` subagent, `graft`, `codegraph` | tools / global | read-only |
| Planning a large effort | `wayfinder` + `grilling` + `domain-modeling` | `~/.claude/skills/` | Wayfinder needs a tracker; see §7 |
| Writing a code plan | `writing-plans` | global | model-invocable |
| Executing a plan | `executing-plans`, `subagent-driven-development` | global | review checkpoints |
| Brainstorming a spec | `brainstorming` | global | starts a local visual companion |
| Debugging | `systematic-debugging` | global | root cause before fixes |
| TDD | `test-driven-development` | global | tests first |
| Verification | `verification-before-completion` | global | evidence before "done" |
| Reference analysis | `reference-video-analyzer` + `python -m contentos.skills analyze-reference` | global + repo | local file only |
| Generic QA second opinion | `video-qa-critic` | global | do not add a second QA system; `explainer-visual-qa` is the house one |
| Storyboard | `script-to-storyboard` | global | prompt-only; `video-director` is validated |
| Style cards | `style-architect` | global | overlaps `config/design-library.json` |
| Packaging copy | `publishing-packager` | global | never publishes |
| Motion vocabulary | `animation-vocabulary` | global | naming only |

## 6. Use these, not those

- **Whole video:** `video-production-orchestrator` (entered through `create-video`), not a new topic skill.
- **Planning:** `video-director` for scene plans; `writing-plans` for code. Not `script-to-storyboard` when a
  validated plan is needed.
- **Motion:** `explainer-motion-craft` R1-R6, then `hyperframes-animation` (2-4 relevant rules), then
  `hyperframes-keyframes` for camera. Not web-UI motion skills (`review-animations`, `improve-animations`) for
  HyperFrames work.
- **QA:** `contentos.qa` -> `hyperframes lint` -> `visual_gate` -> `preview --sheet` -> independent
  `explainer-visual-qa`. Do not self-grade.
- **Reference:** local `analyze-reference` for structure; `competitor` for metadata/hook. Do not claim a
  download/transcribe/recreate workflow that does not exist.
- **Packaging:** the `export` stage plus `publishing-packager` for copy. Never let a skill publish.

## 7. Wayfinder and the tracker

Wayfinder exists (`~/.claude/skills/wayfinder/SKILL.md`, also in `~/.commandcode/skills/`) but requires an
issue tracker and is `disable-model-invocation: true`. No tracker is configured in this repo: there is no
`docs/agents/issue-tracker.md`, no `.scratch/`, and GitHub issues are empty. Its local-markdown fallback
(`.scratch/<effort>/map.md`) is a template only and was **not** instantiated, because creating a second
planning system would compete with the existing docs. The single authoritative roadmap is
[`ROADMAP.md`](ROADMAP.md). If the owner wants Wayfinder later, run `/setup-matt-pocock-skills`, choose the
tracker, and migrate the roadmap tickets into it.

## 8. Present but not usable as-is

1. **`~/.claude/skills` and `~/.agents/skills` both load 633 skills**, including all 79 recipes the router says
   are deliberately not in `.claude/skills`. That contradiction is real; decide whether the global recipe pack
   is intentional. The repo's own guard test only forbids recipe names inside the repo.
2. **`.agents/skills` is a mirror, not a source.** Its `creative-skill-router` and `explainer-motion-craft`
   copies contain a broken `.Codex/skills/...` path. Edit the canonical `.claude` copy, then regenerate.
3. **`hyperframes-creative`, `hyperframes-registry`, `media-use`** are in `.commandcode/skills/` and are
   unreachable from Claude Code. Do not assume they are active.
4. **`yt-dlp` is broken on this Mac** (x86 binary in `/usr/local/bin`). Reference download and `youtube-clips`
   are blocked until `brew install yt-dlp`.
5. **Forced alignment (`torchaudio` MMS) is not installed**; any recipe that needs it must label line timing
   as unverified.
6. **Global quarantine** (`~/.agents/skill-quarantine/`) holds at least one blocked skill; do not load it.
7. **`poteto-mode` / `poteto-help`** exist but are `disable-model-invocation`. There is no `mad-poke` or
   `potato-agent` skill installed.

## 9. Adding or changing a skill

- A new **format** is configuration (`look/1` JSON in `config/presets/`), not a new skill.
- A new **workflow** is a thin skill that defers to `create-video` and names only capabilities that exist in
  `contentos/videojob.py`.
- A new **third-party skill** arrives through `scripts/upstream_skills.py` with a commit pin and tree hash,
  after review. Never copy a global skill into the repo ad hoc.
- Every skill needs: purpose, inputs, outputs, dependencies, examples, validation criteria, and an honest
  tested/untested statement.
- The guard test `tests/test_creative_skills.py` rejects recipe names dropped into `.claude/skills`; keep the
  universal entry and the 79 recipes separate.
