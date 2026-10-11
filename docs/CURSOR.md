# Driving the video factory from Cursor

Status as of 2026-10-11. The contract every agent follows is [`../AGENTS.md`](../AGENTS.md); how the factory
works end to end is [`HOW_IT_WORKS.md`](HOW_IT_WORKS.md); the rules an agent must obey step by step are
[`AGENT_BRIEF.md`](AGENT_BRIEF.md). This page only covers Cursor.

## 1. What Cursor picks up by itself

Nothing below needs installing, and there is no MCP server, account or API key involved.

| Path | What it is | When it applies |
|---|---|---|
| `AGENTS.md` (repo root) | the contract: gates, hard stops, the production loop, the doc map | every session |
| `.cursor/rules/video-factory.mdc` | the hard stops, short | every session |
| `.cursor/rules/factory-code.mdc` | Python, test and config guardrails | when `contentos/`, `tests/`, `scripts/` or `config/` files are in play |
| `.cursor/rules/skills-and-intelligence.mdc` | skill map, guidance precedence, the registries | when skills, `intelligence/` or `production/` files are in play |
| `.cursor/rules/docs-and-evidence.mdc` | evidence and documentation conventions | when docs or `README.md`/`AGENTS.md` are in play |
| `.claude/skills/*/SKILL.md` | the seven skills (four factory-owned, three pinned HyperFrames) | discovered at startup; Cursor reads `.claude/skills/` for compatibility |
| `~/.claude/skills/yt-*` | your global YouTube Agent Skills | discovered at startup |
| `.cursor/commands/*.md` | the four prompts in section 2 | when you type `/` in Agent chat |

Check the first two in **Customize → Rules**, and the skills in **Customize → Skills**. If a skill is
missing from that list, the file is missing on disk: the three `hyperframes-*` skills are gitignored and are
restored with `python scripts/upstream_skills.py sync`.

## 2. The four prompts

| Type this | What it does | What it costs |
|---|---|---|
| `/factory-status` | read-only health snapshot: doctor, storage, ledger, queue, ready videos, worker heartbeat, git state | seconds |
| `/plan-video` | plans the video in text only: brief, script, scene plan, validated `director check`, registries consulted | minutes, no audio, no render |
| `/make-video` | the whole thing: plan, research, spec, **gate 1**, voice, compose, **gate 2**, render, QA, review, export | the real run |
| `/audit-video` | read-only audit of a finished render: QA, contact sheet, labelled tiles, rendered-frame gate, independent critic | minutes |

Type the topic after the command (`/make-video how a small team ships a podcast`) or type the command alone
and the agent asks for topic, format, length and whether you supply the script.

The natural order is `/factory-status` → `/plan-video` → (read the script) → `/make-video` → `/audit-video`.
`/make-video` does not need `/plan-video` first; it plans on its own. Skipping to `/make-video` is fine when
the topic is already settled.

## 3. One-paragraph prompt, for pasting anywhere

If you would rather paste than use a command — or you are driving a different agent — this is the whole
thing:

> You are operating my local video factory at `~/git/video-factory` (contentos). Read `AGENTS.md`, then
> follow the workflow in `docs/AGENT_BRIEF.md` and the phases in
> `.claude/skills/video-production-orchestrator/SKILL.md`. Make one video about: **<TOPIC>**. Format:
> <9:16 short | 16:9>. Length: <~45 s>. Language: <English>. Tone: <calm-precise>. Script: <"write it
> yourself" | paste my script below>. Stop at every approval gate and ask me. Never publish, never spend
> money. When done, give me the path to `video.mp4`, the QA result, and anything you were unsure about.

## 4. Practical notes

- **Run it on this Mac, not in a Cloud Agent.** Kokoro, whisper.cpp, ffmpeg and the pinned
  `node_modules/hyperframes` 0.8.114 all live here, and the generated work sits outside the repo in
  `~/Desktop/VideoFactory-Workspace`. A cloud or remote session has none of that.
- **Let the agent run commands, with approval on.** Almost everything it needs is a `./contentos.sh …` call.
  Keep command approval enabled rather than full auto-run: the pipeline writes outside the repo and a render
  can take minutes.
- **Approve file access outside the project.** The workspace and the publishing library are outside the repo
  root. When Cursor asks for that access, allow it — otherwise the agent cannot open the audio, the render or
  the QA report it is supposed to check.
- **The two gates are stops, not suggestions.** Cursor will show you the script and wait, then show you the
  composed project and wait. Answer them in chat; the gates are recorded against the `content_id`, so a
  script you approve and then change needs approving again. If you want it unattended, say so explicitly and
  accept `--approve-private` for that run.
- **Renders are not instant.** Quote roughly: a short renders in seconds once the voice exists, but the voice
  and alignment stages are the slow part. Do not interrupt a run mid-stage — a killed stage deletes its own
  artifact and the next run redoes it.
- **Ask for evidence, not adjectives.** The house style is a path, a measured number and a labelled
  uncertainty. If a reply claims a video is good without pointing at frames and numbers, ask it to run
  `/audit-video` on its own output.

## 5. Commands the agent will run

```
./contentos.sh doctor                                    # tool readiness, with fix commands
./contentos.sh storage paths --check                     # workspace + publishing library writable
./contentos.sh research "<topic>"                        # Reddit + HN dossier, keyless
python -m contentos.production.platforms budget --kind short
python -m contentos.production.direction validate PLAN.json
python -m contentos.production.director check PLAN.json --script SCRIPT.txt --kind short
python -m contentos.intelligence.catalogue query --purpose <purpose> --content-type <type> --aspect 9:16
python -m contentos.intelligence.designs recommend --topic <topic> --mood <mood> --register dark --aspect 9:16
./contentos.sh approve <content_id> SCRIPT_APPROVED      # or PRODUCTION_APPROVED
./contentos.sh pipeline run SPEC.yaml                    # stops at the gates
./contentos.sh qa VIDEO.mp4                              # 9 ffprobe/ffmpeg checks
./contentos.sh preview VIDEO --at 2,10,30 --out DIR --sheet
python -m contentos.production.sheet VIDEO TIMELINE.json -o DIR
python -m contentos.production.critic report.json        # validates the independent critic's report
./contentos.sh storage ready                             # what has actually shipped
```

## 6. Troubleshooting

| Symptom | What is happening |
|---|---|
| A rule is not applied | Check **Customize → Rules**. `alwaysApply: true` rules always load; the others attach by `globs` or because the agent read the description. A plain `.md` file in `.cursor/rules` is ignored — it must be `.mdc`. |
| A skill is missing from **Customize → Skills** | The folder needs a `SKILL.md` with `name` matching the folder. Run `python scripts/upstream_skills.py verify` for the three pinned ones. |
| The agent says `NOT_INSTALLED` | `./contentos.sh doctor` prints the fix command per provider. Do not let it substitute a paid provider. |
| `bad CPU type in executable` | The `/usr/local/bin` ffmpeg or `timeout` is x86_64. Always go through `./contentos.sh`, which puts `/opt/homebrew/bin` first. |
| The agent wants to "fix" the quality thresholds | That is a gate it may not touch. `config/quality.yaml` and `config/*.yaml` change only when you ask. |
| Labelled sheet exits with "cannot draw labels" | The ffmpeg here has no `drawtext` (homebrew 9.0.2 was built without freetype), so `sheet.py` fails closed by design. Fall back to `./contentos.sh preview … --sheet`; it is not a bug to defeat with `--allow-unlabelled`. |
| It is about to commit | Stop it. No commits, pushes, stashes or resets here unless you ask for them. |

## 7. What is deliberately not available

No uploader and no OAuth — `publish` is a dry run and stays that way. No multi-platform export, no thumbnail
images, no analytics ingestion, no Odia/Hindi voices. OpenMontage has no adapter: cinematic and avatar work
is a manual handoff, not something Cursor can trigger. `contentos/production/sheet.py` (labelled contact
sheets) and `timeline.py` are new and in shadow mode, so the agent calls them as `python -m …` rather than
through `contentos.sh`. The longer list is in `HOW_IT_WORKS.md` section 10 and `AGENTS.md` section 10.

## References

- Rules (project rules and `AGENTS.md`): <https://cursor.com/docs/rules>
- Agent Skills (`.cursor/skills/`, `.claude/skills/` compatibility): <https://cursor.com/docs/skills>
