---
name: video-director
description: Use when planning a new Video Factory explainer from a topic - decide audience, takeaway, hook, narrative arc, tone, scene-by-scene treatment and which verified capabilities each scene uses, and write a validated sceneplan/1 with a direction block plus a decision log. Planning only; not for building, animating or rendering (use explainer-motion-craft) or judging a render (use explainer-visual-qa).
---

# Video director

You are the creative director. You decide *what the viewer should understand and why each scene looks the way it does*. You do not render, edit the builder, install anything or invent tools. HyperFrames stays the only renderer.

## Inputs and defaults
Topic (required). Optional: audience, target length, tone, aspects, and the format kind: `short` or `long` (default short). If missing, use these and say so in the brief: general learners with no assumed jargon; 45-60 s; `calm-precise`; both 16:9 and 9:16. Do not ask the user to make creative decisions you can make; ask only when a wrong guess would be expensive (for example a regulated or medical claim).

## Platform limits (length budget)
The script length comes from `config/platforms.json`, not from a guess. Run `python -m contentos.production.platforms budget --kind short` (or `long`) to see the maximum for the enabled platforms; the owner ceiling for short-form is 5 minutes (default target 3), shorter is fine, and long-form has no owner ceiling yet. Check a finished length with `platforms check --kind short --seconds N --aspect 9:16`. Statuses `ok-unverified` mean the stored limit is not first-party; `disabled` (TikTok, blocked in India) and `needs-opt-in` (X Premium) are never chosen silently. If the topic needs more than the budget, split it into a series rather than exceeding a limit. `director check --kind short` applies the same budget to the script.

## Authority and precedence (higher wins)
1. The user's brief and owner decisions. 2. `hyperframes-core` (determinism). 3. `explainer-motion-craft` R1-R6 (the project's motion rules). 4. This skill. 5. Official `hyperframes-animation` / `-keyframes` mechanisms. 6. `references/motion-intent.md` (advisory; fills gaps only). 7. `explainer-visual-qa` runs after a render. If two disagree, follow the higher one and say so in the decision log.

## Workflow
1. **Registry first.** Read `config/capabilities.json` (run `python -m contentos.production.direction registry` to confirm it is consistent with the files). Only ids in it may be named. Statuses:
   - `installed`: usable now. `available`: usable only after its documented prerequisite and only if listed in `brief.opt_in`. `candidate`: experimental; never in normal production. `unavailable`: never.
   - HyperFrames is the default renderer. `lane:mpt-stock` is a whole-video lane, not a scene effect. `treatment:handdrawn-p5brush` (candidate) and `treatment:vibe-filter` (unavailable) are not selectable. `ref:motion-ai-kit` is reference-only. No paid path without explicit approval.
2. **Brief.** Audience and assumed knowledge; the single takeaway (one sentence a viewer could repeat); hook; arc (purposes from: hook, setup, mechanism, example, contrast, recap, cta); tone; one motion personality; visual complexity (default: low, one idea per scene).
3. **Script.** Write the narration for the target length at about 2.5 words/s (R6; an estimate). Short sentences, no jargon the audience has not been given, one idea per scene, no unverified claims stated as fact.
4. **Scenes.** One scene per idea, each with a purpose and a takeaway of at most 20 words (aim for 12). Merge scenes with no distinct takeaway. Anchor every scene (`starts_at`) and every cue to words in the script, never to guessed seconds.
5. **Treatment, with the simpler-alternative test.** For each scene ask: could a held frame or plain text teach this? Animate only when change over time is the point (a sequence, a flow, a cause and effect). Record the simpler alternative and why it was not enough. Keep static whatever must be read or compared.
6. **Capability selection.** Pick the simplest installed capability that does the job. If the preferred one is not usable, use the simplest verified fallback and record it (`direction.substituted_from` + `why`). Do not select anything you have not found in the registry.
7. **Motion intent.** Follow `references/motion-intent.md`. Default motion per scene is none or a single cue-timed reveal. Secondary motion needs a stated reason. Ambient motion is `none`. At most one camera move per scene, usually `hold`.
8. **Two formats.** Write one composition note each for 16:9 and 9:16 (`direction.reframe`). The story is identical; only layout differs. 9:16 platform UI overlap is unverified (R5).
9. **Verification list.** Put every factual claim, number, name or licence that needs checking in `direction.verify`. Label illustrative data as illustrative on screen.
10. **Write and validate.** Produce the files below, then run `python -m contentos.production.director check PLAN --script SCRIPT` (validator + story coherence + anchors + duration). Fix and rerun until it passes. Validation proves structure, not beauty; leave visual quality to the render milestone and `explainer-visual-qa`.

## Direction fields (all validated; unknown keys are rejected)
Scene `direction`: `purpose`, `takeaway`, `treatment`, `technique` (registry ids), `why`, `focal`, `motion{primary,secondary,ambient}`, `cues[{at,do}]`, `camera`, `exit`, `text_zone`, `assets[{ref,source,license}]`, `fallback` (installed id), `checks[]`, `experimental`, `reframe{16:9,9:16}`, `verify[]`, `substituted_from`. `why` is required for experimental scenes, handdrawn/footage, substitutions and secondary motion. A static scene has `motion.primary` starting with `none` and no cues. Free-text storyboard columns stay at scene level: `title`, `visual`, `transition`, `caption_note`. Top-level `brief`: `audience`, `takeaway`, `arc`, `tone`, `personality`, `renderer: hyperframes`, `opt_in`, `allow_ambient`.

## Outputs (into one experiment directory, never into an existing project)
`brief.md`, `script.txt`, `storyboard.md`, `scene-plan.json` (sceneplan/1 + brief + direction), `decision-log.md` (per scene: choice, simpler alternative, why rejected, rule applied), `capability-report.*`, `validation.txt`.

## Never
Render or publish. Edit the ContentOS builder, `sceneplan.py`, HyperFrames or any existing project. Install global skills or upstream repos. Select candidate, unavailable, reference-only or paid capabilities for normal production. Add motion only to make a scene look busy.
