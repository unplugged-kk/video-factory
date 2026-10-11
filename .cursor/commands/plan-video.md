Plan a video without producing it. Cheap, text-only, no voice and no render — this is the step before
`/make-video`, for seeing the idea before it costs anything.

Read `AGENTS.md` first. Then treat the text I typed after the command as the topic (if I typed nothing, ask
for the topic, the format and the target length, then wait).

Do this:

1. `./contentos.sh doctor` — note only what the plan would need.
2. Length budget from the registry, never guessed:
   `python -m contentos.production.platforms budget --kind short` (or `--kind long`).
3. Research if the topic needs facts: `./contentos.sh research "<topic>"`, and cite a source for every claim
   you intend to put on screen.
4. Use the `video-director` skill: audience, the single takeaway, the hook, the narrative arc, tone, and a
   scene-by-scene treatment that names only capabilities that exist in `config/capabilities.json`.
5. Choose techniques and the look from the registries
   (`contentos.intelligence.catalogue query`, `contentos.intelligence.designs recommend`) and say why the
   pick fits this topic.
6. Write the planning artifacts as text into an experiment folder under
   `$VIDEO_FACTORY_WORKSPACE/experiments/<slug>/` — **not** into the repo: `brief.md`, `script.txt`,
   `scene-plan.json`, `decision-log.md`.
7. Validate before you show me anything:
   `python -m contentos.production.direction validate PLAN.json` and
   `python -m contentos.production.director check PLAN.json --script SCRIPT.txt --kind short`. Fix what
   fails rather than reporting it as a limitation.
8. Run the two background rules as a declared check (Rule A backdrops, Rule B against the last five shipped
   videos) and report the result.

Then report: the title, the full script with word count and estimated duration against the budget, the
scene list with the technique id and evidence level for each, the validation output, what you were unsure
about, and what you would need approved next.

Do not render, do not grant any gate, do not write media into the repo, and do not claim the plan is
approved — I approve it.
