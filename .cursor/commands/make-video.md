You are operating my local video factory at `~/git/video-factory` (contentos) from Cursor. Read `AGENTS.md`
first, then the workflow in `docs/AGENT_BRIEF.md`, then follow the phases in
`.claude/skills/video-production-orchestrator/SKILL.md`.

Anything I typed after the command is the topic plus any constraints I gave. If I gave none, ask me for the
topic, the format (9:16 short or 16:9), the target length, and whether I supply the script or you write it —
then wait. Defaults when I stay silent: 9:16 short, English, at most 60 seconds, calm-precise tone, you
write the script.

Make one video, in this order:

1. `./contentos.sh doctor` and `./contentos.sh storage paths --check`. Report anything `NOT_INSTALLED` that
   the plan needs and stop rather than substituting a different tool.
2. Take the length from the registry, never from a guess:
   `python -m contentos.production.platforms budget --kind short`.
3. If the topic needs facts, `./contentos.sh research "<topic>"` (Reddit + HN, keyless) and give every claim
   a source. Unverifiable material stays out of the video or is labelled illustrative.
4. Plan with the `video-director` skill, then validate the plan with
   `python -m contentos.production.direction validate PLAN.json` and
   `python -m contentos.production.director check PLAN.json --script SCRIPT.txt --kind short`.
5. Choose the technique and the look from the registries, not from taste:
   `python -m contentos.intelligence.catalogue query --purpose <purpose> --content-type <type> --aspect 9:16`
   and `python -m contentos.intelligence.designs recommend --topic <topic> --mood <mood> --register dark --aspect 9:16`.
   Run the two background rules and do not compose over a failing check: change the look instead.
6. Write the spec YAML (Track A: `docs/AGENT_BRIEF.md` section 4 has the template, `examples/` has worked
   ones, narration is about 2.5 words per second). If the job needs a hand-built composition instead, say so
   and follow the HyperFrames skills — that is Track B and the builder does not read scene plans yet.
7. **GATE 1 — stop and wait.** Show me the title, the full script, the sources and the plan summary, then ask
   for `SCRIPT_APPROVED`. Do not run the voice stage before I answer.
8. After I approve: voice, alignment and compose. `./contentos.sh pipeline run SPEC.yaml` stops at the gates
   by itself, or drive the stages directly. Then **GATE 2 — stop and wait**: show me the composed project
   and ask for `PRODUCTION_APPROVED` before any render.
9. After I approve: render, then `./contentos.sh qa <video>`,
   `./contentos.sh preview <video> --at 2,10,30 --out <dir> --sheet`, and the `explainer-visual-qa` skill
   with an independent critic (`python -m contentos.production.critic report.json`). You did not build the
   motion, so review it as an outsider and look at the frames at phone size.
10. Export only a validated final, stop before `publish`, and report the absolute path to `video.mp4`, the
    QA table, the visual-review verdict, the commands you ran to verify, anything you were unsure about, and
    any decision you could not make alone.

Never publish, never spend money, never edit `config/*.yaml` or the pinned HyperFrames version, and keep
every generated file under `$VIDEO_FACTORY_WORKSPACE` — never inside the repo. Do not claim the video is
finished before the artifacts exist and the checks pass.
