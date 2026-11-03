---
name: creative-skill-router
description: Use when a request names a creative video format or style (lyric video, comic reel, podcast explainer, talking-head edit, kids story, blueprint or news explainer, a numbered skill like "#20") or asks which format suits a script. Finds the right recipe in the 79-skill creative catalogue, says what inputs and capabilities it needs and what is missing, and for the runnable ones writes a Track A spec. Routing and planning only; never renders, publishes or installs.
---

# Creative skill router

The 79 creative recipes and 7 core workflow skills of the Video Factory Skills Bundle are vendored, hash-verified, in `contentos/skills/library/` and indexed in `config/creative-skills.json`. They are deliberately **not** under `.claude/skills/` (86 more auto-loaded descriptions would bloat every session and collide with `video-director`). This skill is the single entry point.

## Precedence
Owner brief > repo `AGENTS.md` > `hyperframes-core` > `explainer-motion-craft` > `video-director` > a creative recipe from the library. A recipe is a creative brief, not a stack: its "canvas in headless Chrome", "torchaudio MMS_FA" or "Remotion" lines are candidate implementation details. HyperFrames is the only renderer.

## Commands (all read-only; run from the repo root with the venv python)
```
python -m contentos.skills route "<request>" --have song,lyrics,footage,script   # ranked candidates, missing inputs, fallbacks
python -m contentos.skills route 20                                              # numbered request, resolved from the catalogue
python -m contentos.skills show <name|id>      deps <name|id>                    # contract, requirements, blockers, limitations
python -m contentos.skills compat <skill> <skill> ...                            # can these combine (rule check, not a render test)
python -m contentos.skills plan --skill <name> --script SPEC.yaml --content-id sample-x --out OUT.yaml   # Track A only
python -m contentos.skills analyze-reference VIDEO --out DIR                     # local reference video: cuts, pacing, loudness, palette
python -m contentos.skills probe | list | ledger | verify
```

## How to use it
1. `route` the request with the inputs the user actually has. Never guess a number; resolve it.
2. Read the status honestly: `readiness` is `ready-to-run` (script/topic only), `needs-user-media` (song, lyrics, footage, photos: ask for them), or `blocked`. `execution` is `track-a-scenekit` (a spec can be generated) or `track-b-agent-authored` (you read the recipe's `SKILL.md` and author a HyperFrames composition with `hyperframes-*` and `explainer-motion-craft`).
3. **Recommend, then wait.** Give the owner the candidate, why, what is missing, and the fallback. No render before script approval (gate 1).
4. Track A: `plan` writes `visual_style` + `creative_skill`, then `./contentos.sh pipeline run` as usual. Gates and `--approve-private` rules in AGENTS.md apply unchanged.
5. Track B: follow the recipe, but timing comes from `production/align.py`, never invented. English-only ASR is installed; Hindi/Odia line timing is author-supplied and must be labelled unverified.

## Hard rules
- Recipes naming a copyrighted work or living creator (`ip_sensitive` in the registry) need original characters and assets.
- Footage, songs and voices you did not make need a recorded rights status (`production/supplied_audio.py`).
- Do not download third-party video (the installed `yt-dlp` is broken and the rights gate applies), install a dependency, or use a paid service without owner approval. Say what is missing and offer the fallback.
- Run the existing gates (`qa`, `visual check`, critic, `variety-report.json`). Do not add a second QA system.
- After changing the library or installing a dependency: `python -m contentos.skills build`, then `verify`.
