# AGENTS.md — video-factory

Contract for any coding agent working in this repo (Cursor, Claude Code, Codex, Command Code). Read this
file first. It stays short on purpose; the deeper truth lives in the documents it points at (section 9).

`contentos` is a local-first video pipeline on this Apple Silicon Mac: a topic or a script goes in, a
captioned and QA-checked MP4 comes out, with human approval gates on the way. Python CLI through
`./contentos.sh`, no server, no account, nothing that costs money.

## 1. Non-negotiables

- **Never publish.** The `publish` stage is a dry run: `config/youtube.yaml` sets `publish.enabled: false`
  and no upload adapter exists. Do not change either.
- **Never spend money.** No paid APIs, providers, stock sources or hosted services. `--allow-paid` and the
  paid MoneyPrinterTurbo sources stay off unless the owner explicitly asks.
- **Never edit** `config/*.yaml`, the approval gates, or the pinned HyperFrames version (`package.json` =
  0.8.114) unless the owner asks for it.
- **Never write media into the repo.** Everything generated goes to `$VIDEO_FACTORY_WORKSPACE`. The code
  refuses an in-repo workspace root on purpose; do not work around it.
- **Never touch git history** — no commit, push, stash, reset, or branch surgery unless asked.
- **Never modify** `vendor/` (upstream code), `.claude/skills/hyperframes-*` (generated and hash-verified),
  `*.publish.json` sidecars, or `.state/claims/` (a scheduler owns those). Never delete files to free
  space, and never print anything from `~/.contentos/secrets/`.

## 2. Gates — hard stops, never skipped or reordered

| Gate | Blocks | Granted with |
|---|---|---|
| `SCRIPT_APPROVED` | the `voice` stage | `./contentos.sh approve <content_id> SCRIPT_APPROVED` |
| `PRODUCTION_APPROVED` | the `render` stage | `./contentos.sh approve <content_id> PRODUCTION_APPROVED` |
| `PUBLISH_APPROVED` | `publish`, which is disabled anyway | as above |

Show the script and title, then **wait** at gate 1. Show the composed project, then **wait** at gate 2.
`--approve-private` grants the research, script and production gates in one call: use it only after the
owner has approved, or when they explicitly ask for an unattended run. Gates are keyed by `content_id`
alone, so a previously approved script that you then change needs a fresh approval.

## 3. Producing a video

Skill-first: read `.claude/skills/video-production-orchestrator/SKILL.md` and follow its phases. The loop:

1. `./contentos.sh doctor` — stop and report anything the plan needs that is `NOT_INSTALLED`.
2. `./contentos.sh storage paths --check` — workspace and publishing library must exist and be writable.
3. Length budget from the registry, never guessed: `python -m contentos.production.platforms budget --kind short`.
4. Research when the topic needs facts: `./contentos.sh research "<topic>"` (Reddit + HN, keyless). Every
   claim gets a source; unverifiable material stays out of the video or is labelled illustrative.
5. Plan with the `video-director` skill, then validate the plan:
   `python -m contentos.production.direction validate PLAN.json` and
   `python -m contentos.production.director check PLAN.json --script SCRIPT.txt --kind short`.
6. Write the spec (Track A) or go on to the composition (Track B). Spec template: `docs/AGENT_BRIEF.md`
   section 4; worked examples in `examples/`. Narration runs about 2.5 words per second.
7. **GATE 1** — script and title to the owner, then wait.
8. Voice, align, compose, lint. `./contentos.sh pipeline run SPEC.yaml` stops at the gates by itself.
9. **GATE 2** — then render.
10. QA and review: `./contentos.sh qa <video>`, `./contentos.sh preview <video> --at 2,10,30 --out DIR --sheet`,
    then the `explainer-visual-qa` skill with an **independent** critic
    (`python -m contentos.production.critic report.json` — a builder never grades its own video).
11. Export only validated finals and stop before publish, then report (section 8).

**Two tracks, and the difference matters.**

- **Track A — template pipeline, automated.** A spec YAML goes in; `contentos` builds one scene per script
  line with word-highlight captions. This is what `pipeline run`, the queue and the ContentForge worker run.
- **Track B — director-led explainer, agent-built.** Plan, validated `sceneplan/1`, voice, word alignment,
  then a hand-authored HyperFrames composition, render, independent visual QA. The builder does not consume
  scene plans yet, so an agent writes the composition with the HyperFrames skills.

Render lanes are chosen by `render:` in the spec, and only two exist in code: `hyperframes` (default) and
`mpt`. OpenMontage is a manual handoff, not a lane.

## 4. Commands worth knowing

```
./contentos.sh doctor                                   # PASS / NOT_INSTALLED / OPTIONAL, with fix commands
./contentos.sh pipeline run SPEC.yaml                   # stops at the gates
./contentos.sh pipeline run SPEC.yaml --approve-private # grants research+script+production, never publish
./contentos.sh approve <content_id> SCRIPT_APPROVED      # (or PRODUCTION_APPROVED, --note "...")
./contentos.sh qa VIDEO.mp4                             # 9 ffprobe/ffmpeg checks
./contentos.sh preview VIDEO --at 2,10,30 --out DIR --sheet
./contentos.sh status                                   # recent ledger rows
./contentos.sh queue add SPEC.yaml | queue list | queue requeue <id>
./contentos.sh worker --concurrency 2 [--once]
./contentos.sh factory-worker                           # ContentForge exchange worker (README)
./contentos.sh storage paths --check | inventory | export <id> | ready | recover
./contentos.sh research "<topic>" | competitor <youtube-url...>
```

Verification before you claim anything works:

```
~/.contentos/venv/bin/python -m pytest tests             # never a bare `pytest`: vendor/ adds ~182 unrelated tests
node --test contentos/adapters/v1/*.test.mjs             # the ContentForge worker
```

`contentos.sh` puts `/opt/homebrew/bin` first because the `/usr/local/bin` ffmpeg and `timeout` are x86_64
and die with "bad CPU type". Run commands through the wrapper rather than calling `python` directly.

## 5. Skills (auto-loaded — do not copy them)

Cursor and Claude Code both discover `.claude/skills/*/SKILL.md` by frontmatter, so a skill needs no
registration. Factory-owned: `video-production-orchestrator` (start here for any whole video), `video-director`
(planning only), `explainer-motion-craft` (motion rules R1–R6, authoritative), `explainer-visual-qa`
(post-render review). Pinned upstream: `hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes`
— gitignored and hash-verified, restored with `python scripts/upstream_skills.py sync`, verified with
`verify`, never edited in place.

When guidance conflicts, precedence is: the owner's brief, then `hyperframes-core`, then
`explainer-motion-craft`, then `video-director`, then the orchestrator, then upstream animation skills,
with `explainer-visual-qa` applied after rendering. Never auto-load skill text from outside this repo; new
third-party skills arrive through `scripts/upstream_skills.py` with a commit pin and tree hash, after review.

## 6. Intelligence layer

Techniques and looks are chosen from registries, not taste:

```
python -m contentos.intelligence.catalogue query --purpose <purpose> --content-type <type> --aspect 9:16
python -m contentos.intelligence.catalogue show <technique-id>
python -m contentos.intelligence.designs recommend --topic <topic> --mood <mood> --register dark --aspect 9:16
python -m contentos.intelligence.visual plan plan.json          # declared backdrop check, before composing
python -m contentos.intelligence.visual scenes VIDEO --timing timing.json   # measured, after render
python -m contentos.intelligence.visual check <job-id|dir>      # Rule B against the last 5 shipped videos
python -m contentos.intelligence.visual claim <content-id> <job-id>
```

The two background rules fail closed: **Rule A** requires at least half the scenes to use distinct backdrops,
**Rule B** requires a new video to differ from each of the last five shipped videos on at least two of five
signature fields. Do not compose over a failing check — change the look. An intentional single canvas needs a
`--motif "<why>"` and is reported, never hidden.

## 7. Storage and identity

Generated work lives **outside Git** (see `docs/STORAGE.md`): intermediates in
`$VIDEO_FACTORY_WORKSPACE/jobs/YYYY/MM/DD/<job-id>/` (default `~/Desktop/VideoFactory-Workspace`), validated
finals in `$VIDEO_FACTORY_PUBLISH_DIR/ready/<project>/YYYY/MM/<content>__<job>.mp4` plus a
`.publish.json` sidecar written last (default `~/Desktop/Video-Publishing`). The job id is the spec's
`content_id`, which must match `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. A folder that is missing or unwritable
stops the run — report it, never fall back into the repo. Optional spec fields feed the sidecar and are
never guessed when absent: `project`, `project_name`, `content`, `topic`, `description`, `tags`,
`platform_targets`, `language`, `kind` (`short`|`long`), `require_audio`.

The repo-root folders `workspace/ queue/ work/ done/ failed/ building/ output/ state/ thumbs/` are legacy
and gitignored; the live exchange root is `~/.contentos/exchange`. Migrate rather than resurrect.

## 8. Evidence and reporting

Facts are not invented: cite sources for claims, label illustrative data as illustrative, and distinguish
what you read or measured from what you inferred. Prefer a fresh measurement over a remembered figure.

When you finish, report the absolute path to `video.mp4`, the QA table, the visual-review verdict, the
verification you ran, anything you were unsure about, and any decision you could not make alone. Do not
claim completion before the artifacts exist and the checks pass.

## 9. Which document answers which question

| Question | Read |
|---|---|
| How does the factory work end to end, and what is built vs. planned? | `docs/HOW_IT_WORKS.md` |
| What must an agent do, step by step, with the copy-paste prompt? | `docs/AGENT_BRIEF.md` |
| Storage, export, sidecar, scheduler contract | `docs/STORAGE.md` |
| Command reference and current status table | `README.md` |
| How to drive all of this from Cursor | `docs/CURSOR.md` |
| Skill design, known failures KF-001…KF-006, evidence | `docs/video-intelligence/` |
| Program history, audits, licensing, platform limits | `docs/factory-v2/` |
| Current uncommitted work on this branch | `git status` and `docs/video-intelligence/04-visual-reliability-gate.md` |

## 10. Known limits (verified 2026-10-11)

Not built: a YouTube uploader and OAuth, multi-platform publishing, niche discovery, analytics ingestion,
thumbnail images, Odia/Hindi voices. OpenMontage has no adapter — manual handoff only. Pexels/Pixabay/Coverr
stock needs a free key in `vendor/MoneyPrinterTurbo/config.toml` and is untested. A `frozen_frames` WARN on
text slides is expected, not a defect. `contentos/production/sheet.py` (labelled contact sheets) and
`timeline.py` are new and in shadow mode: usable as `python -m contentos.production.sheet` but not wired
into `contentos.sh` or the pipeline. The labelled sheet needs an ffmpeg built with `drawtext`; the
`/opt/homebrew` build on this Mac has no freetype, so on this machine it fails closed by design — use
`./contentos.sh preview <video> --at ... --out DIR --sheet` instead of passing `--allow-unlabelled`, which
produces an unlabelled sheet and is not the same artifact. Wire `sheet.py` into the QA workflow only after a
labelled sheet has been generated successfully on this Mac and its labels inspected. `docs/HOW_IT_WORKS.md` section 10 holds the longer list.
