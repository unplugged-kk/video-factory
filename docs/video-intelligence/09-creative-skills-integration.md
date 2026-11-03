# 09 - Creative skills integration (Video Factory Skills Bundle v1.0.0)

Date: **2026-11-03**. Evidence labels: **[ran]** executed and inspected, **[read]** read in source, **[not verified]**.
Related: `08-multi-style-system.md` (scenekit, the Track A engine this integration routes into), `docs/RENDERERS.md`, `AGENTS.md`.

## 1. Result in one paragraph

All 86 bundle skills (79 creative, 7 core workflow) now have a stable ID, a machine-readable contract, a live-probed status and a route into the factory, through one registry (`config/creative-skills.json`), one CLI (`python -m contentos.skills`) and one agent skill (`creative-skill-router`). **That is not the same as 86 working formats.** Three creative skills generate a real video through the existing pipeline (approximately: scenekit styles, not the full recipe). The other 76 are recipes an agent must author as HyperFrames compositions (Track B); 73 of them need media you have to supply (song, lyrics, talking-head clip, podcast audio, photos) and none of that is in the repo, so **no recipe was rendered end to end**. Three are blocked by a missing dependency. Zero creative skills are `integrated-and-tested` at full fidelity, and the registry refuses to say so.

## 2. Environment and baseline (before any change) [ran]

| Item | Finding |
|---|---|
| Repo / branch | `video-factory`, `main`; the working tree already held uncommitted scenekit work from the previous task, left untouched except as noted below |
| Bundle | `VIDEO_FACTORY_SKILLS_BUNDLE.zip` (349 KB, 104 files); all 103 MANIFEST hashes match; 79 unique catalog ids 1-79 matching 79 skill folders; 7 core skills; 9 prompts; style registry (10 styles) |
| Tests before | 933 passed, 8 skipped (after scenekit) |
| Renderer | HyperFrames 0.8.114 healthy; Track A legacy render of the sample script: 19.7-22 s |
| Installed | ffmpeg/ffprobe, whisper-cli with **`ggml-small.en` only**, kokoro-onnx, node, numpy/scipy, pyyaml |
| Not installed | torchaudio, librosa, demucs, mediapipe, cv2, rembg, Blender, `world-atlas`, a working `yt-dlp` (the x86 binary dies with "bad CPU type") |
| Conflicts with the repo | bundle `video-director` vs the factory's own (same name); bundle `config/style-registry.yaml` vs `design-library.json` + `config/styles` + scenekit styles (would be a fourth registry); bundle `AGENTS.md` vs the repo's (repo wins); bundle recipes name Remotion, torchaudio MMS_FA, "canvas in headless Chrome" |

## 3. Design decisions

| Decision | Why |
|---|---|
| Vendor the bundle **byte-for-byte** into `contentos/skills/library/` | Its own MANIFEST then verifies integrity (`verify` fails on any edit); updates are a replace-and-rebuild, not a merge |
| **Do not** install the 86 skills under `.claude/skills/` | Claude Code auto-loads every description there: 86 more would bloat every session, trigger on loose keywords, and the bundle `video-director` would collide with ours. One router skill is the single entry point |
| Registry is a **build product**: bundle catalog + SKILL.md text + live probe | Requirements and fallbacks come from each skill's own text; status comes from probe x requirements; nothing is hand-marked "works". `verify` fails if the checked-in registry is stale or a SKILL.md changed |
| Keep the bundle's numeric ids for creative skills, `core:<name>` for core | The bundle promises numbered requests stay stable; core skills must never renumber them |
| Reuse existing core capabilities, implement only what was missing | video-director, storyboard, style selection, QA critic are `already-supported`; only the integrator (registry/router) and a local reference analyzer were new |
| Map the bundle style registry **onto** scenekit styles and cards, not add it | One authoritative implementation per function; unmapped styles are listed with the reason |
| HyperFrames stays the only renderer | `render.remotion` is probed as intentionally unavailable; skills that name Remotion get a HyperFrames fallback |

## 4. What was added or changed

```
contentos/skills/library/        bundle, unmodified (104 files, hash-verified)
contentos/skills/probe.py        18 capability probes with evidence; no installs, no network, no downloads
contentos/skills/classify.py     inputs / requirements / fallbacks / blockers / readiness from each skill's text
contentos/skills/registry.py     build, validate, verify_library, route, compat, ledger; core-skill and style mappings
contentos/skills/analyze.py      local reference-video analysis (cuts, pacing, loudness, palette, contact sheet)
contentos/skills/__main__.py     CLI: build verify probe list show deps route compat plan ledger analyze-reference evidence
config/creative-skills.json      the registry (86 skills, 10 style mappings, probe snapshot)
config/creative-skills.evidence.json   render evidence recorded through the CLI
.claude/skills/creative-skill-router/SKILL.md   the single agent entry point
registry/capabilities.yaml       +1 line: creative_skill_routing
AGENTS.md                        +1 short section pointing at the catalogue (sections 1-2 untouched)
contentos/scenekit/compose.py    records the routing skill in visual-plan.json; numeral now labelled "scene N of M"
tests/test_creative_skills.py    26 tests
```

Not touched: `config/*.yaml`, gates, `config/capabilities.json`, vendor/, upstream skills, git history. Nothing committed or pushed.

## 5. Registry, routing, discovery

Every entry carries: id, name, category, `role` (format vs stackable effect), description, tags, path + sha256, `inputs_required`, `requires` (probe capability ids), `missing`, `execution` (`track-a-scenekit` | `track-b-agent-authored` | `existing-implementation`), renderer, `status`, `readiness`, `fallbacks`, `blockers`, `limitations`, `ip_sensitive`, `evidence`, `invoke`.

The agent can answer your five questions with commands:

| Question | Command |
|---|---|
| Which skills are available? | `python -m contentos.skills list [--status S] [--category C] [--core]`, `ledger` |
| Which suits this request? | `route "<request>" --have song,lyrics,footage,script` (ranked, with missing inputs and fallbacks; never auto-selects; `route 20` resolves numbered requests from the catalogue) |
| Which dependencies are required? | `deps <skill>`, `probe` |
| Which combine? | `compat <skill> <skill> ...` (one whole-video format per job; effects that fight over one layer conflict; at most 3 stacked; footage effects need a footage format; blocked never combine. A rule check, **not** a render test) |
| Which need a fallback or are unsupported? | `list --status adapted-with-fallback`, `list --status blocked-by-dependency` |

Routing is lexical (tags from names, descriptions and categories), deliberately simple and explainable. It will miss synonyms; that is why it returns reasons and never decides alone.

## 6. Status summary

| Status | Count | Meaning here |
|---|---|---|
| `integrated-and-tested` | 1 | `core:factory-skill-integrator` (this registry, probe, router; 26 tests). **No creative skill** |
| `already-supported` | 4 | core: video-director, script-to-storyboard, style-architect, video-qa-critic: existing implementations are authoritative |
| `adapted-with-fallback` | 78 | 76 creative + 2 core (reference-video-analyzer, publishing-packager): a required tool is replaced by an installed one (whisper.cpp for torchaudio MMS_FA, HyperFrames for Remotion, owner-supplied timing for beats/Hindi, no-matte layouts without segmentation). Includes the 3 scenekit-generated skills |
| `blocked-by-dependency` | 3 | watercolor-map (world-atlas), 3d-explainer (Blender, world-atlas), youtube-clips (yt-dlp, rights) |
| `integrated-but-not-fully-tested` | 0 | no creative skill reached this: every one needs at least one substituted capability |
| `blocked-by-incompatibility`, `not-integrated` | 0 | not used; the three blocked skills are blocked by a missing, installable dependency, not by incompatibility |

Readiness (creative, 79): **3 ready-to-run** (script or topic only: blueprint-explainer, personal-explainer, news-report), **73 needs-user-media** (36 need footage, 23 a song, 21 voice audio, many photos), **3 blocked**. 22 name a copyrighted work or a living creator (`ip_sensitive`): original characters and assets only.

Most-missing capabilities across the 79: forced alignment (45), face detection (32), beat detection (28), multilingual ASR (17, so every Hindi line is author-timed), person matte (9), world-atlas (2), Blender (1), working yt-dlp (1), Remotion (1, substituted).

## 7. Validation [ran]

**Tests.** 959 passed, 8 skipped (933 + 26 new; the 8 skips are unchanged). Mutation checks: making `route` surface blocked skills, disabling the compat conflict rules, letting a missing fallback pass, and dropping the "never rendered" limitation each fail a test.

**Original pipeline unchanged.** The legacy (no `visual_style`) job re-rendered after the integration is frame-identical to the pre-integration render (PSNR `inf`); QA unchanged (8 pass + the documented `frozen_frames` WARN).

**End-to-end through the new route** (skill -> `plan` -> `pipeline run` stages voice, compose, render, qa; same approved script, 9:16, 34 s each):

| Skill (id) | Style it routed to | Rule A | Rule B | QA | variety report | Render |
|---|---|---|---|---|---|---|
| blueprint-explainer (20) | blueprint-architecture | pass 3/6 | **FAIL** (too close to two shipped navy-grid videos) | 8 pass + frozen_frames WARN | PASS | 21 s |
| personal-explainer (13) | clean-explainer | pass 3/6 | pass | same | PASS | 21 s |
| news-report (6) | kinetic-type | pass 3/6 | pass | same | PASS | 27 s |

Contact sheets: `$VIDEO_FACTORY_WORKSPACE/experiments/style-evolution/render/skill-*/contact-sheet.png`. The three are visibly distinct (blueprint grid and monospace; light paper with dark caption pills; black with acid-yellow condensed type). Diversity vs the legacy render of the same script: content density 0.134 / 0.150 / 0.173 vs 0.104; within-video variation 0.133 / 0.166 / 0.237 vs 0.064 (coarse thumbnail metrics, see report 08). Each `visual-plan.json` records the routing skill.

**Fidelity caveat.** These are *approximations of three recipes*, not their full creative briefs: no sheet title block or live calculation tables (blueprint), no embedded real footage with credit (personal), no screenshot cards, memes or presenter (news). They are therefore `adapted-with-fallback`, with the missing parts written into `limitations`.

**Reference-video analyzer** (the bundle's reference-video-analyzer, local files only). Tested on a synthetic clip with a known cut (unit test) and on the three renders above, each with 5 known hard cuts: at the first default (0.3) it found **1/5, 0/5, 3/5**, so I measured thresholds, merged detections within 0.6 s and set the default to 0.1: **5/5 recall with 1 extra detection per video** on all three. It does not read text, identify typography, transcribe, or analyse URLs (yt-dlp is broken). Its output states those limits.

**Publishing.** `config/youtube.yaml` `publish.enabled` is still `false` (asserted in a test); no registry command can upload; all sample jobs were stopped before export and publish.

## 8. Dependencies, fallbacks, and what needs your approval

Nothing was installed or downloaded. Sizes and licences below are from general knowledge and are **[not verified here]**; vet before installing.

| Dependency | Needed by | Why | Licence (to verify) | Resource impact | No-install fallback today |
|---|---|---|---|---|---|
| multilingual whisper model (e.g. `ggml-small.bin`) | 17 Hindi/Indic skills | word timing for non-English audio | whisper.cpp MIT; model weights MIT | ~0.5 GB download | author-supplied timing, labelled unverified |
| `world-atlas` npm package | watercolor-map, 3d-explainer | real map boundaries | ISC / Natural Earth public domain | small | none (the skill forbids hand-drawn borders) |
| Blender | 3d-explainer | 3D shots | GPL | several hundred MB | none |
| arm64 `yt-dlp` | youtube-clips | fetching a source video | Unlicense | small | none; also a rights gate |
| mediapipe or rembg (+cv2) | depth-ui-reel, magazine-cover, hindi-pastel-reel-edit and 6 more; 32 face-safe checks | person matte, face zones | Apache-2.0 / MIT | hundreds of MB with models | no-matte layouts; fixed safe zones |
| librosa (or a wired numpy onset detector) | 28 beat-synced skills | beat times | ISC | large with numba | owner-supplied beat times or ASR word onsets |
| torchaudio | 45 skills name MMS_FA | forced alignment | BSD | multi-GB with torch | whisper.cpp (English), already used |
| ElevenLabs (named by kids-story, anime-reel) | optional voice | paid | not allowed | n/a | Kokoro (English) or user-supplied audio |

## 9. Remaining work, by impact

1. **Supply real media and render one recipe per category** (song + lyrics for a lyric video, a talking-head clip for an effect, a podcast clip for an explainer). Until then 73 statuses stay "unknown quality". This is the single biggest gap and needs your files and rights status.
2. **Install a multilingual whisper model** (approval): unlocks verified timing for 17 Hindi/Indic skills and the lyric formats you listed first.
3. **Beat detection** (small numpy/scipy onset module, no new dependency) and **lyric-line and word-reveal scene types** in scenekit: would move the 23 song-driven skills from "agent authors it" to a repeatable path.
4. **Person-matte decision**: approve mediapipe/rembg or accept no-matte layouts for the 9 behind-subject effects.
5. **Rule B awareness in the style recommender**, and a softer blueprint look (it fails Rule B against shipped videos).
6. Owner phone review and an independent critic run on the three skill renders (a builder does not grade its own video; none has been done).
7. Track B composition helpers (code panel, captions, safe zones) so agent-authored recipes share primitives with scenekit.
8. Thumbnail generation for the publishing packager (capabilities: planned).

## 10. Commands

```bash
cd ~/git/video-factory; export PATH=/opt/homebrew/bin:$PATH; P=~/.contentos/venv/bin/python
$P -m contentos.skills verify                                     # bundle hashes + registry schema + not stale
$P -m contentos.skills probe                                      # what is installed right now
$P -m contentos.skills route "narrated explainer about kafka" --have script
$P -m contentos.skills route 4 ; $P -m contentos.skills show lyric-video ; $P -m contentos.skills deps hindi-lyric-video
$P -m contentos.skills compat talking-head-edit cinema-scope
$P -m contentos.skills plan --skill blueprint-explainer --script my-script.yaml --content-id my-job-001 --out my-spec.yaml
./contentos.sh pipeline run my-spec.yaml                          # stops at the gates, as always
$P -m contentos.skills analyze-reference some-video.mp4 --out /tmp/refcheck
$P -m contentos.skills build                                      # after changing the library or installing a dependency
$P -m pytest tests/test_creative_skills.py tests/test_scenekit.py -q
```

Updating the bundle: replace `contentos/skills/library/` with the new release, run `build`, read `git diff config/creative-skills.json`, run `verify` and the tests. Roll back: delete `contentos/skills/`, `config/creative-skills*.json`, `.claude/skills/creative-skill-router/`, the AGENTS.md section and the capabilities line; nothing else depends on them.

## 11. Known limits

- Statuses depend on the probe snapshot stored in the registry; on another machine run `build` first.
- Requirements are inferred from skill text by regex (reviewed on the 79, not proven exhaustive). A skill may need something its text does not name.
- `adapted-with-fallback` means a substitute exists in this factory, **not** that the substitute was exercised for that skill. Only the three scenekit-routed skills have render evidence.
- The `plan` command only supports skills mapped to a scenekit style; it refuses the rest instead of pretending.
- Routing is keyword-based.
- `hyperframes inspect` warns `connector_orphan` / `connector_detached` on scenekit diagrams (SVG edges); in frames the edges are attached. Treated as a heuristic false positive, not blocking, not suppressed.
- The earlier scenekit sample jobs (editorial, kinetic, clean, cinematic, wide) predate the "scene N of M" numeral label; only the three skill jobs were re-rendered with it.

## 12. Production-readiness validation update (same day, after report sections 1-11)

Scope: verify the integration, fix what was fixable without weakening a gate, and say plainly what is still unproven. Evidence levels are kept apart on purpose.

### 12.1 What each check actually established

| Check | Registry validation | Routing | Planning | Render | Automated QA | Independent human/critic review | Full-fidelity creative validation |
|---|---|---|---|---|---|---|---|
| blueprint-explainer (20) | yes (`verify`) | yes (`route 20`, free text) | yes (`plan`) | yes, 9:16 English; also with Hindi script | yes: qa 8 pass + frozen_frames WARN, lint pass, Rule A and B pass | **no** (builder inspected frames only) | **no** (no sheet title block, no live calculation tables, 34 s not 3-10 min) |
| personal-explainer (13) | yes | yes | yes | yes | yes (Rule B pass) | **no** | **no** (no embedded footage with credit) |
| news-report (6) | yes | yes | yes | yes | yes (Rule B pass) | **no** | **no** (no screenshot cards, memes, presenter) |
| the other 76 creative skills | yes | yes | no (agent-authored recipes) | **no** | **no** | no | no |

"Independent" means a reviewer that did not build the video (AGENTS.md section 8). I cannot launch one here: no review of any render in this repository has been independent. What I did is a structured self-review (below); it is evidence for defects found, not a quality verdict, and `contentos.production.critic` has not been run on any of these videos.

### 12.2 Registry reconciled with the repository [ran]

`python -m contentos.skills verify` -> `ok: bundle verified, 86 skills, registry current`; the registry, the 79 catalog ids and 7 core skills, the vendored files' hashes and the status counts in this report agree. The multilingual work changed one fact: the 17 skills that involve Hindi/Indic text no longer lack multilingual word timing (`asr.word_timing_multilingual` is now a passing probe, `tts.hindi` is now a real probe of the Chatterbox stack). Their statuses did not change because each still substitutes forced alignment or beat detection; the statuses are `adapted-with-fallback` 78, `already-supported` 4, `blocked-by-dependency` 3, `integrated-and-tested` 1 (the integrator itself), unchanged. Language routing is documented in `docs/MULTILINGUAL.md`.

### 12.3 Blueprint style vs Rule B: fixed by changing the look, not the rule [ran]

v1 (dark navy, cyan and amber) differed from `ep6-how-llms-actually-work` on one field (texture) and from `m3-sample-01-hf-sketch` on one (structure); the rule needs two. v2 is a light engineering-drafting-paper look (pale ground, blue linework, red annotations, same monospace, grid, wipe and diagram-dominance) and bumps the style to `version: 2`, so a spec pinned to v1 fails loudly. Re-rendered through the router: **Rule B pass against all five shipped videos** (each differs on 2 to 4 fields), Rule A pass (3/6), qa 8 pass, lint pass. `visual.py` was not modified. A side effect found in frames: the plain-caption drop shadow made a muddy halo on a light ground; it is now disabled when the ground is light. Rule B measures `#root` CSS, which for scenekit is nearly "flat/none" for every style, so the rule currently separates scenekit styles mostly by base tier, hue and accents (KF-006 in `02-known-failures.md`); the look change is real, but the measurement is coarse.

### 12.4 frozen_frames: a genuine pacing property, not a defect in the render [ran]

On the new renders the segments longer than 3 s at the QA threshold (`freezedetect n=-60dB`) fall in the text-only scenes (for `personal-explainer`: 0.8-5.4 s and 30.2-34.0 s, exactly scenes 1 and 6). At a looser `-35 dB` freezes over 3 s also appear inside data scenes: after the entrance animation the diagram, steps or cards hold still while narration continues. The legacy template shows the same (3 segments at -60 dB). Nothing is blank, undecodable or desynchronised, so it is not a render failure, and AGENTS.md already classes it as expected on text slides. It is still a **weak spot for retention** (a static headline for 4-5 s with only the caption highlight moving). The gate stays a WARN and is not loosened. Minimal reversible fix, not applied: word-aligned focus cues (highlight the node or step named in the narration), which would add real motion tied to meaning and respect the house rule against idle "breathing" motion.

### 12.5 Structured self-review of the renders (builder, not independent) [ran, frames]

| Aspect | Observation |
|---|---|
| Phone-size readability | caption 58 px on 1080 wide (5.4% of width), headline 56-100 px, diagram labels 32-50 px; all legible on 360 px contact sheets. Lint WCAG-AA contrast: 103/103 text checks pass on the blueprint job |
| Pacing | scenes 4.5-7.3 s, follows narration (longest/shortest 1.6); text-only scenes feel slow (12.4) |
| Typography | consistent within each style; **defects found and fixed**: Devanagari in a monospace headline font (word gaps, letter-spacing breaking conjuncts) and missing `@font-face` declarations (caught by `hyperframes lint`); the numeral "05" now reads "scene 5 of 6" so it cannot be mistaken for a statistic |
| Captions | highlight follows ASR word timing (English match ratio 1.0 on all lines, Hindi 0.64-0.94, interpolated otherwise) |
| Transitions | slam, wipe sweep and edge-draw inspected mid-transition in report 08; no clip-path used (it did not animate visibly) |
| Audio sync | not measured by ear; caption timing derived from ASR; loudness -12 LUFS, peak -1.4 dBFS (QA pass) |
| Consistency | grounds rotate within one family (needed for Rule A); the cinematic style's teal/plum variants stray from its amber identity |
| Known weak | sparse text-only scenes (large empty areas); no real footage anywhere |

### 12.6 Real routing, planning, render, QA: combined request [ran]

`route "narrated blueprint explainer about kubernetes architecture in hindi" --have script` -> `blueprint-explainer` (20), `adapted-with-fallback`, `ready-to-run` -> `plan` with the Hindi script -> `pipeline run` stages voice (Chatterbox, 4 lines, one model load), compose, render, qa -> **ok**: Rule A 3/4, Rule B pass, qa 8 pass + frozen_frames WARN, variety PASS, `visual-plan.json` records skill 20, style `blueprint-architecture` v2, and `voice-languages.json` records the models. That exercises registry, router, planner, language routing, multilingual ASR, scenekit, renderer and QA in one path. A multi-**skill** combination cannot be rendered here: the only compatible multi-skill sets are footage formats plus effects (for example `talking-head-edit` + `cinema-scope`, which `compat` accepts as a rule check), and all of them need a talking-head clip that does not exist in the repo. Two Track A formats correctly conflict.

### 12.7 Coverage across the six categories

| Category (skills) | Rendered | Why not |
|---|---|---|
| explainers-and-motion-graphics (7) | blueprint-explainer, personal-explainer (approximate) | the other five need footage or blocked dependencies |
| spoken-content-and-editing (9) | news-report (approximate) | the rest need podcast or talking-head media |
| music-and-lyrics (34) | none | need a song and lyrics (rights), plus beat detection and lyric-line scene types |
| stories-and-illustration (12) | none | need illustration/character primitives that do not exist; two need blocked map data |
| motion-effects-and-formats (9), visual-treatments (8) | none | need talking-head footage (and person matte for 9 of them) |

No media was fabricated and no blocked skill is claimed to work. Fixtures that would be permissible and useful: one rights-cleared 9:16 talking-head clip, one owned song with lyrics, one owned podcast clip.

### 12.8 Highest-impact remaining blockers and the minimal reversible fixes

1. **No source media** (73 skills). Fix: supply three files (clip, song+lyrics, podcast) with rights status; no code change.
2. **No human listening to Hindi/Hinglish audio, and no independent critic run.** Fix: you listen to `experiments/multilingual/audio/*.wav`; run `contentos.production.critic` with a reviewer that did not build it.
3. **Static holds** (12.4). Fix: word-aligned focus cues in scenekit data scenes (small, behind a style flag).
4. **Beat detection and lyric scene types** gate the 23 song-driven skills. Fix: a numpy onset module and a `lyric` scene type reading word timing.
5. **Person matte** for 9 effects: decision on MediaPipe in its own venv (`docs/MULTILINGUAL.md` section 8).
6. **Odia**: gated models, needs your HF login and terms acceptance.
7. Teal/plum cinematic grounds off-identity; Studio form does not accept the new fields.

## 13. Ledger (generated: `python -m contentos.skills ledger`)

| id | skill | category | status | readiness | execution | inputs needed | missing capability / blocker | evidence |
|---|---|---|---|---|---|---|---|---|
| 1 | anime-reel | stories-and-illustration | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio, script_or_topic | align.forced_mms | - |
| 2 | madhubani-kahani | stories-and-illustration | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms | - |
| 3 | katha-video | spoken-content-and-editing | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms | - |
| 4 | lyric-video | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms, audio.beat_detect | - |
| 5 | watercolor-map | stories-and-illustration | `blocked-by-dependency` | blocked | track-b-agent-authored | script_or_topic | data.world_atlas: needs the world-atlas npm dataset for real map boundaries; `npm install` needs owner approval (licence vetting first) | - |
| 6 | news-report | spoken-content-and-editing | `adapted-with-fallback` | ready-to-run | track-a-scenekit | script_or_topic | align.forced_mms | sample-skill-news-report |
| 7 | talking-head-edit | spoken-content-and-editing | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 8 | podcast-explainer | spoken-content-and-editing | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms | - |
| 9 | podcast-comic | spoken-content-and-editing | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | lyrics, voiceover_audio, photos | align.forced_mms | - |
| 10 | hindi-lyric-video | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms, audio.beat_detect | - |
| 11 | pusho-reel | stories-and-illustration | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms | - |
| 12 | titan-anime | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio, script_or_topic | align.forced_mms, audio.beat_detect | - |
| 13 | personal-explainer | explainers-and-motion-graphics | `adapted-with-fallback` | ready-to-run | track-a-scenekit | script_or_topic | align.forced_mms | sample-skill-personal-explainer |
| 14 | sketch-music-video | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms | - |
| 15 | kinetic-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms, audio.beat_detect | - |
| 16 | latent-reel | stories-and-illustration | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms | - |
| 17 | latent-comic | stories-and-illustration | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio, footage | align.forced_mms | - |
| 18 | comic-reel | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms, audio.beat_detect | - |
| 19 | sketch-to-motion | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | photos | align.forced_mms, audio.beat_detect | - |
| 20 | blueprint-explainer | explainers-and-motion-graphics | `adapted-with-fallback` | ready-to-run | track-a-scenekit | script_or_topic | align.forced_mms | sample-skill-blueprint-explainer |
| 21 | podcast-cartoon | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio, footage, photos | align.forced_mms, audio.beat_detect | - |
| 22 | ink-line-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms, audio.beat_detect | - |
| 23 | mirzapur-video | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms, audio.beat_detect | - |
| 24 | party-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms, audio.beat_detect | - |
| 25 | anime-fight | stories-and-illustration | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio, script_or_topic | align.forced_mms | - |
| 26 | rap-video | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics, photos | align.forced_mms, audio.beat_detect | - |
| 27 | aarti-video | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms | - |
| 28 | shadow-puppet | stories-and-illustration | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio, script_or_topic | align.forced_mms | - |
| 29 | kids-story | stories-and-illustration | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio, script_or_topic | align.forced_mms | - |
| 30 | neon-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics, photos | align.forced_mms, audio.beat_detect | - |
| 31 | paper-cutout | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms, audio.beat_detect | - |
| 32 | street-interview | spoken-content-and-editing | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms | - |
| 33 | bairan-style | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms, cv.person_matte | - |
| 34 | 3d-explainer | explainers-and-motion-graphics | `blocked-by-dependency` | blocked | track-b-agent-authored | voiceover_audio, script_or_topic | 3d.blender: Blender is not installed and a 3D look cannot be faked in HyperFrames; install needs owner approval (GPL, ~300 MB); data.world_atlas: needs the worl | - |
| 35 | beat-transition-edit | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, footage, photos | cv.face_detect, audio.beat_detect | - |
| 36 | scribble-edit | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, footage | cv.person_matte, cv.face_detect, audio.beat_detect | - |
| 37 | sketch-doodle-edit | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song | audio.beat_detect | - |
| 38 | crayon-carousel | motion-effects-and-formats | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | photos | cv.face_detect | - |
| 39 | painted-beat-edit | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song | align.forced_mms, audio.beat_detect | - |
| 40 | glow-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms | - |
| 41 | minimal-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms | - |
| 42 | watercolor-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics, photos | align.forced_mms | - |
| 43 | spotify-particle-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics, photos | align.forced_mms, audio.beat_detect | - |
| 44 | pink-spotify-clip-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics, footage, photos | align.forced_mms, cv.person_matte, audio.beat_detect | - |
| 45 | night-glow-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics, footage | align.forced_mms, audio.beat_detect | - |
| 46 | red-rap-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics | align.forced_mms, audio.beat_detect | - |
| 47 | glass-to-neon-lyrics | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | song, lyrics, footage, photos | align.forced_mms, cv.person_matte, audio.beat_detect | - |
| 48 | maut-ke-bare-mai-sochte-ho | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms, audio.beat_detect | - |
| 49 | madira-peekar-soo-gaye | stories-and-illustration | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms | - |
| 50 | baba-pusho | stories-and-illustration | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms | - |
| 51 | woof-woof | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | voiceover_audio | align.forced_mms, audio.beat_detect | - |
| 52 | personal-short-form-reels | motion-effects-and-formats | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 53 | personal-broll-library | motion-effects-and-formats | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 54 | depth-ui-reel | visual-treatments-and-edit-styles | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.person_matte, cv.face_detect | - |
| 55 | youtube-clips | motion-effects-and-formats | `blocked-by-dependency` | blocked | track-b-agent-authored | footage | net.yt_dlp: yt-dlp on PATH is an x86 build that dies with 'bad CPU type'; `brew install yt-dlp` (arm64) needs approval. Also downloads third-party video: rights | - |
| 56 | educational-youtube-editor | explainers-and-motion-graphics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 57 | ranking-format | motion-effects-and-formats | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 58 | business-short-form-reels | motion-effects-and-formats | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 59 | match-cut | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect, audio.beat_detect | - |
| 60 | shutter-stack | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect, audio.beat_detect | - |
| 61 | led-matrix-text | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect, audio.beat_detect | - |
| 62 | glass-stat-card | motion-effects-and-formats | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 63 | particle-chart | explainers-and-motion-graphics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 64 | particle-text | music-and-lyrics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect, audio.beat_detect | - |
| 65 | price-tag-zoom | explainers-and-motion-graphics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 66 | podcast-reel-edit | spoken-content-and-editing | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 67 | dark-red-timeline-motion-graphics | explainers-and-motion-graphics | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 68 | instagram-ui-hinglish | motion-effects-and-formats | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.person_matte, cv.face_detect | - |
| 69 | hindi-pastel-reel-edit | motion-effects-and-formats | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.person_matte, cv.face_detect | - |
| 70 | kinetic-talking-head-edit | spoken-content-and-editing | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 71 | red-kinetic-collage-edit | visual-treatments-and-edit-styles | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 72 | iphone-style-by-aansh | visual-treatments-and-edit-styles | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 73 | rgb-glitch-live | visual-treatments-and-edit-styles | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 74 | magazine-cover | visual-treatments-and-edit-styles | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.person_matte, cv.face_detect | - |
| 75 | comic-halftone | stories-and-illustration | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 76 | breaking-news | spoken-content-and-editing | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 77 | neon-outline | visual-treatments-and-edit-styles | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.person_matte, cv.face_detect | - |
| 78 | cinema-scope | visual-treatments-and-edit-styles | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| 79 | triptych-timecode | visual-treatments-and-edit-styles | `adapted-with-fallback` | needs-user-media | track-b-agent-authored | footage | cv.face_detect | - |
| core:factory-skill-integrator | factory-skill-integrator | core-workflow | `integrated-and-tested` | ready-to-run | existing-implementation | - | - | - |
| core:publishing-packager | publishing-packager | core-workflow | `adapted-with-fallback` | ready-to-run | existing-implementation | - | - | - |
| core:reference-video-analyzer | reference-video-analyzer | core-workflow | `adapted-with-fallback` | ready-to-run | existing-implementation | - | - | - |
| core:script-to-storyboard | script-to-storyboard | core-workflow | `already-supported` | ready-to-run | existing-implementation | - | - | - |
| core:style-architect | style-architect | core-workflow | `already-supported` | ready-to-run | existing-implementation | - | - | - |
| core:video-director | video-director | core-workflow | `already-supported` | ready-to-run | existing-implementation | - | - | - |
| core:video-qa-critic | video-qa-critic | core-workflow | `already-supported` | ready-to-run | existing-implementation | - | - | - |

