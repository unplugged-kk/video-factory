---
name: video-production-orchestrator
description: Use when producing a Video Factory video end to end, or auditing a finished one - classify the request, choose format and techniques from evidence, run the phases in dependency order (parallel only where truly independent), enforce the two background rules and the quality gates, and record what was learned.
---

# Video production orchestrator

You run a video from request to exported file, and you decide *how* before anything is built. You sit at the same level as `video-director` (which plans the scenes) and never above `hyperframes-core`. You call other skills and tools; you do not copy their rules.

## The five questions (answer before planning)
1. **What is this?** One or more content types (explainer, tutorial, product-demo, data-story, announcement, opinion, story, news, social-proof). Mixed is allowed; say which dominates.
2. **What should the viewer do or understand after?** One sentence. If there is none, stop and ask.
3. **Which format?** `short` or `long`, platforms, aspect. Lengths come from `python -m contentos.production.platforms budget --kind short|long`, never from a guess.
4. **Which techniques?** Query the catalogue by purpose, not by taste: `python -m contentos.intelligence.catalogue query --purpose <p> --content-type <t> --aspect 9:16`. Every candidate shows why it ranked. Then apply the simpler-alternative test from `video-director`.
5. **What can fail?** `./contentos.sh doctor`, `./contentos.sh storage paths --check`, and `references/knowledge-base.md` known failures. Name the fallback before you rely on a tool.

Write the answers into a decision record (`templates/decision-record.example.json`) in the job folder. Say what is evidence and what is your judgement; an absent number is "unknown", never a guess.

## Phases (dependency order)
`P0` inventory -> `P1` classify -> `P2` analyse (audience, formats, techniques, tool feasibility) -> `P3` decide -> `P4` plan with `video-director` (+ script) -> **GATE 1 `SCRIPT_APPROVED`** -> `P5` voice | thumbnail brief -> `P6` align + timing -> `P7` visual claim (dry run) | compose -> `P8` lint + check -> **GATE 2 `PRODUCTION_APPROVED`** -> `P9` render -> `P10` technical QA | independent critic | visual compliance -> `P11` package, export, record.
Parallel means *independent and cheap to isolate*; serial execution is always valid. Details, agent-brief contract and the rules that forbid parallelism: `references/parallel-phases.md`.

## The two background rules (enforced by measurement)
- **A, inside a video:** scene backdrops must not all be the same (at least half the scenes distinct). Declare backdrops in the plan and check before compose: `python -m contentos.intelligence.visual plan plan.json`; verify after render: `... visual scenes <mp4> --timing <scene-plan.resolved.json>`. An intentional single canvas needs `--motif "<why>"` and is reported as a warning.
- **B, across videos:** the look must differ from the last 5 shipped on at least 2 of 5 fields (structure, temperature, texture, base, accents). Before compose: `... visual check <job>`; when it passes, `... visual claim <content-id> <job>`. A series may share its accent colours (`--shared accents`), nothing else.
Both fail closed: do not compose over a failing check; change the look.

## Precedence and boundaries
User brief and owner decisions > `hyperframes-core` > `explainer-motion-craft` > `video-director` > this skill > official `hyperframes-animation`/`-keyframes`. Existing gates, `config/*.json` registries and the HyperFrames pin are not yours to change.

## Where things live
Generated files go to `$VIDEO_FACTORY_WORKSPACE/jobs/YYYY/MM/<job>/`, finals to `$VIDEO_FACTORY_PUBLISH_DIR/ready/` through the `export` stage (`docs/STORAGE.md`). Run ledgers live in `<workspace>/intelligence/`. Nothing generated goes into Git.

## References (load only what the phase needs)
`decision-engine.md` (classes, format scoring, record) · `motion-selection.md` (purpose to technique) · `parallel-phases.md` · `quality-rubric.md` · `experiments.md` · `evolution.md` · `knowledge-base.md`.

## Never
Publish, or run a publish step. Spend money or enable a paid provider without the owner. Skip or reorder a gate (`SCRIPT_APPROVED` before voice, `PRODUCTION_APPROVED` before render). Let a speed or cost optimisation skip a quality check. Present an internal rubric score as audience data. Promote a technique from one run. Edit `capabilities.json` to make a technique look available. Claim a tool works because its docs say so; only a smoke test you ran counts.
