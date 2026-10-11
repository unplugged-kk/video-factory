# 05 — External repository audit (seven upstream repositories)

Audit date: **2026-10-11**. Scope: research only. Nothing was installed, executed, rendered or downloaded from any upstream repository, and no paid API or model weight was touched.

## 0. Method, evidence labels and limits

Each repository was shallow-cloned (`git clone --depth 1`, no tags) into an isolated cloud scratch folder, **outside** the Video Factory checkout, and read statically: README, skills, prompts, source, manifests, licences, tests/CI. Nothing in them was run.

| Label | Meaning |
|---|---|
| **[read]** | I read the file at the pinned commit. Path given. |
| **[claim]** | Upstream's own statement (README, description, package field); not verified by me. |
| **[not verified]** | I could not check it in this session. |
| **[mine]** | My inference or recommendation, not an upstream fact. |

Limits, stated plainly:
- **No upstream code ran.** "Works" below means "the code path exists and reads coherently", not "I observed it work".
- **No upstream video or GIF was watched.** I looked at four README preview frames from `mg-styles-15` (flat-vector, collage, line-art, cel-boil) to confirm the styles are visually distinct. I make **no** claim about upstream render quality, smoothness or sync.
- GitHub's API was not reachable for repositories outside this session, so release/tag metadata and the licence of the standalone `remotion-dev/skills` repository were **not re-checked**.
- This is not legal advice. Licence readings are of the files in force at the pinned commits.

### Pinned commits

| # | Repository | Commit (full SHA) | Commit date | Browse at pin |
|---|---|---|---|---|
| 1 | `howseen-ai/claude-motion-design` | `3d90d349ef3fdde9b7e89de4df4a2159c9e8697f` | 2026-10-02 | https://github.com/howseen-ai/claude-motion-design/tree/3d90d349ef3fdde9b7e89de4df4a2159c9e8697f |
| 2 | `Anil-matcha/vox-ai-motion-graphics-generator` | `c6856442a45761f86ae67cb05efbf25f65228e7c` | 2026-09-02 | https://github.com/Anil-matcha/vox-ai-motion-graphics-generator/tree/c6856442a45761f86ae67cb05efbf25f65228e7c |
| 3 | `remotion-dev/template-prompt-to-motion-graphics-saas` | `b3a5e1c845ecd0655373b49380d934937a7741f4` | 2026-10-05 | https://github.com/remotion-dev/template-prompt-to-motion-graphics-saas/tree/b3a5e1c845ecd0655373b49380d934937a7741f4 |
| 4 | `Vincentwei1021/mg-styles-15` | `49052d80bfaf9fa8412cc9710530e5e95a3b8d8c` | 2026-10-05 | https://github.com/Vincentwei1021/mg-styles-15/tree/49052d80bfaf9fa8412cc9710530e5e95a3b8d8c |
| 5 | `whaleyxbt/claude-motion` | `e627941543d9988b155dc610bb9cc0115a5e365e` | 2026-10-09 | https://github.com/whaleyxbt/claude-motion/tree/e627941543d9988b155dc610bb9cc0115a5e365e |
| 6 | `lottiefiles/motion-design-skill` | `f9a8a041b85185ee4881b3471d3415e939aac772` | 2026-05-18 | https://github.com/lottiefiles/motion-design-skill/tree/f9a8a041b85185ee4881b3471d3415e939aac772 |
| 7 | `remotion-dev/remotion` | `32af7e8f8ac67493ef81498d311af3dc9ca953a6` | 2026-10-09 | https://github.com/remotion-dev/remotion/tree/32af7e8f8ac67493ef81498d311af3dc9ca953a6 (packages at 4.0.534) |

To cite a file, append its path to `https://github.com/<owner>/<repo>/blob/<sha>/`. Paths below are relative to each repository root.

## 1. Summary of recommendations

| Repo | What it really is | Adds something distinct? | Recommendation |
|---|---|---|---|
| 1 claude-motion-design | One long skill (`skill/motion-design/SKILL.md`, ~34 KB) + Playwright/ffmpeg render, audio and "remake" scripts around a hand-written `seek(t)` HTML page | Partly: render hygiene, beat/drop analysis, brief/critique discipline. Most of its determinism and pop-scan ideas the factory already has | **ADAPT** (a few techniques) · **REFERENCE ONLY** (rest) · **REJECT** remake mode and the meme / AI-face / stock-scraping parts |
| 2 vox (muapi-director) | A paid-API pipeline: topic → generated collage keyframes → image-to-video → TTS → ffmpeg | Ideas only (beat-map arcs, two approval gates, style bake-off, shot cadence). The pipeline itself is not deterministic or local | **REFERENCE ONLY**; do not take code (no licence file in the checkout) |
| 3 Remotion prompt-to-motion SaaS | A Next.js app: classifier → skill picker → GPT code generation → in-browser `new Function` preview | No. The factory already selects techniques by catalogue and validates plans. Its "sanitization" is not a security boundary | **REFERENCE ONLY** |
| 4 mg-styles-15 | 15 styles × (prompt + full source + rubric) with a `window.renderAt(t)` render harness | **Yes**: a style taxonomy with checkable signature features, a style-prompt template and an independent review rubric | **ADAPT** (schema + rubric) · **SPIKE** (style bake-off) |
| 5 claude-motion | Remotion-based toolkit + `timeline.json` + stdlib-Python sound engine + contact-sheet/waveform scripts + web sims | **Yes**: a shared timeline, beat-labelled contact sheets, and a licence-free procedural SFX/mastering engine; the factory has no SFX/music/ducking at all | **ADAPT** (timeline pattern, sheet script, sfx engine) · **DEFER** (sims, Remotion parts) |
| 6 LottieFiles motion-design-skill | 18 markdown files of UI-oriented motion principles | Marginally: emotion → motion mapping and personality archetypes. Numbers are UI-scale | **REFERENCE ONLY** (lift two ideas into style cards) |
| 7 Remotion | A React/Chrome renderer + 12 official agent skills + player/Lambda/captions/transitions packages | A second renderer. No current use case the HyperFrames default cannot handle acceptably | **DEFER** (no adapter); reference its transitions and captions packages |

The factory-side reasoning behind these (what exists, what is partial, what is absent) is in `06-video-factory-target-architecture.md` §2 and the gap matrix in `07-prioritized-integration-roadmap.md`.

---

## 2. `howseen-ai/claude-motion-design` — **ADAPT (techniques) / REFERENCE ONLY**

**1. Intended use and architecture.** A Claude Code skill for "motion design videos in pure code: HTML + Playwright + ffmpeg" [claim: `README.md`]. A film is one HTML page whose whole state is `window.seek(t)`; a Python script screenshots frames and ffmpeg encodes them [read: `skill/motion-design/SKILL.md` §2–3, `skill/motion-design/scripts/render_template.py`]. One worked example (`examples/howseen-launch/film.html`, 28 KB) plus a "remake" subsystem [read: `skill/motion-design/scripts/remake/`].

**2. Engine and dependencies.** Python (`playwright`, `imageio-ffmpeg`, `numpy`, `pillow`) + Chromium + ffmpeg [read: `README.md` Install]. No Node build, no Remotion. No manifest file (`package.json`/`requirements.txt`) exists in the repo; dependencies are listed in prose only [read: file listing].

**3. Implemented vs. only described.**
- Implemented in code [read]: `render_template.py` — `probe`, `beats`, `draft` (30 fps, 960 px), `full` (N subframes per frame blended with ffmpeg `tmix`, `SHUTTER=0.5`, `CUTS` clamp so subframes never straddle a hard cut), `pops` (frame-diff spikes > 3× neighbours), `loop` (seam check on position and velocity); fonts-ready wait, `getAnimations()` pause and **2× `requestAnimationFrame` after every `seek`** before the screenshot; `WEBGL=1` SwiftShader flags. `audio_template.py` — places SFX **by measured peak** (argmax of |s|) and does two-pass `loudnorm` to −14 LUFS. `analyze_song.py` — onset-autocorrelation BPM estimate + 1-second energy profile for locating a "drop".
- Only described in prose [claim/not verified]: "Films > 25 s: render in 3 parallel chunks (`render_par.py`)" — that script is **not in this repo**; the "film library" and `INDEX.md` it tells you to read live on the author's Desktop [read: SKILL.md §00].
- Demonstrated only in the single example: spring maths, camera in log-space, shared-element hand-offs, floods, the 21st.dev component ports.

**4. Reusable pieces.** (a) The capture hygiene list (fonts ready, pause WAAPI, 2 rAF) — useful as a checklist for any browser-driven renderer. (b) Pop and one-frame-flash detection — **the factory already has an equivalent** in `contentos/production/motion_audit.py` (`motion_stats`, ydif-based pops); do not add a second. (c) Adaptive subframe idea (SKILL.md §9c, credited to another skill) — relevant only if the factory wants rendered motion blur. (d) Drop-finding by band energy ("never trust an auto beat grid") — relevant only to music-led videos. (e) The brief-before-code and "silent one-sentence test" disciplines.

**5. Distinct over the current stack?** Slightly. HyperFrames already documents motion blur and keyframes (`.claude/skills/hyperframes-animation/references/motion-blur.md`, `rules/motion-blur-streak.md` in the factory) [read: factory repo]; the factory already has pops/flash detection and a critic. The genuinely new items are beat/drop analysis and the music-synced SFX *placement* idea.

**6. Integration effort, runtime and maintenance.** Importing the renderer would create a second capture pipeline beside HyperFrames: not recommended. Lifting `analyze_song.py` (≈20 lines, numpy) is S. [mine]

**7. Operating cost / network.** The code itself is free and local. The skill's **asset workflow is network-dependent**: Mixkit music/SFX download URLs, Unsplash/Pexels, svgl logos, a 21st.dev MCP client with an API key, `thispersondoesnotexist.com` faces, and `yt_dlp` meme downloads [read: SKILL.md §5, `scripts/mcp21_client.py`, `scripts/mixkit_sfx_search.py`, `examples/howseen-launch/fetch_assets.py`].

**8. Licence.** Code: **MIT**, © 2026 Howseen AI (Raphaël Aubry) [read: `LICENSE`]. Third-party media is *not* redistributed and "stays under its own licence" (Mixkit free licence, Pexels/Unsplash, OFL for Geist) [claim: README]; I did not read those licence texts. Brand logos belong to their owners. **Rights flags [mine]:** the "memes" workflow (downloading film clips with `yt_dlp`), AI-generated "people" photos, and "Remake mode" (a frame-locked 1:1 remake of any launch video, `skill/motion-design/scripts/remake/`) are derivative-work and likeness risks. They also violate the factory's own source-media rule. Do not adopt them.

**9. Deterministic, time-addressable?** Yes by construction: `seek(t)` only, no timers or CSS transitions [read: SKILL.md §2, §9 "never `Math.random`; seeded PRNG"]. Equivalent in spirit to HyperFrames' single paused timeline. Pixel-reproducibility across reruns was **not tested** by me (upstream lists deterministic Chromium flags in §9c; unverified).

**10. Recommendation: ADAPT** two small items (drop/BPM analysis if/when music-led videos are wanted; the capture-hygiene checklist as a review note) and **REFERENCE ONLY** for the rest. **REJECT** remake mode and the meme/face/stock scraping flows. Tests/CI: **none** (no test-like files, no workflows) [read].

---

## 3. `Anil-matcha/vox-ai-motion-graphics-generator` — **REFERENCE ONLY**

**1. Intended use and architecture.** "Turn ONE topic, talking-head video, or photo into a finished Vox-style paper-collage explainer" on the **MuAPI** platform (`api.muapi.ai`) plus local ffmpeg [read: `SKILL.md`]. Three modes: B-roll (topic), A-roll (talking-head restyle that "preserves facial features, lip-sync and gestures"), C-roll (photo/product anchored into collage). Driven by one `beats.json` [read: `SKILL.md`, `examples/sample-beats.json`].

**2. Engine and dependencies.** No local renderer. Stages: `style_bakeoff.py → keyframes.py → clips.py → audio.py → assemble.py` (ffmpeg muxing, ducking, burned captions, watermark) [read: `AGENTS.md`, `scripts/`]. Requires `MUAPI_API_KEY`, ffmpeg, Pillow. Generative models named in the README: `flux-dev` / `nano-banana-2` (images), `veo3.1-image-to-video` (motion), `minimax-speech-2.6-turbo` (TTS), plus a music model [read: `README.md`, `examples/sample-beats.json`; model list is also a **[claim]** I did not test]. ~1,800 lines of Python in 13 scripts [read: `wc -l`].

**3. Implemented vs. only described.** Implemented [read]: a provider abstraction with MuAPI as primary and an `atlas_cloud` fallback (`scripts/provider.py`), job polling/retry (`run_jobs`), a 220-line style bible (`scripts/styles.py`: era bases, a `STYLE_LIBRARY` of collage idioms such as american-retro, modern-flat, zine, newsprint-editorial and gilded-deco, `THEME_PRESETS` with palette/type/finish/mood/`motion_style`, and `compose_collage_prompt`), ASR → beat segmentation (`scripts/asr_beats.py`: `MAX_BEAT_DUR=9.5`, `MIN_BEAT_DUR=2.0`, `PAUSE_GAP_S=0.35`). The "style bake-off" renders **one** beat in 3–4 themes via the image model and stops for a human pick (`scripts/style_bakeoff.py`). The demo outputs shown in the README are claims; I did not view them.

**4. Reusable ideas (not code).** (a) The narrative-arc table (`hook_payoff`, `pas`, `bab`, `how_it_works`, `timeline`, `man_in_hole`) and shot-cadence rules — "hook in ≤3 s, cut every ~4–6 s, 30 s = 6–8 shots" [read: `references/beat-layer.md`]. (b) Exactly **two** human gates (beat map, theme). (c) Flat-safe camera moves for flat artwork. (d) A bake-off that fixes content and varies only style — the same shape as our Experiment E2. All of these are generic craft ideas the factory can write down itself.

**5. Distinct over the stack?** The *ideas* overlap with `video-director` (arc, hook, scene plan) and the existing approval gates. The *pipeline* is distinct only in that it generates pictures and motion with paid models, which the factory has deliberately excluded.

**6. Integration effort / impact.** Not integrable as code: no render timeline, each clip is a model output, so there is no deterministic, seekable representation to align captions or cues to. [mine]

**7. Cost, network, data egress.** Paid. Every image, clip, voice and music call goes to MuAPI; the A-roll path uploads the **user's video/audio** for ASR, and `scripts/muapi_client.py:237` also references `https://api.openai.com/v1/chat/completions` [read]. Per-video cost formula (prices **not** obtained, so no number is given): `cost ≈ Σ_beats(images × p_img + clip_seconds × p_vid_s) + TTS_chars × p_tts + music_calls × p_music`. Missing input: MuAPI's current price list. `assemble.py` stamps a default watermark "Made with MuAPI · muapi-director" [read: `scripts/assemble.py:13`].

**8. Licence.** **No LICENSE file exists in the checkout** (`find` for `LICEN*` returned nothing). `package.json` says `"license": "MIT"` and a README badge says MIT [read], **but** `package.json`'s `name`/`homepage` point to a different repo (`muapiapp/muapi-director`) [read], so provenance is ambiguous (mirror or fork?). Treat code as **not licensed for copying** until a licence file is confirmed. Outputs are additionally subject to MuAPI and each model provider's terms [not verified]. The README also advertises "narration (TTS or voice cloning)" and a `clone_ref` input in `scripts/audio.py` [read] — with no consent mechanism of any kind.

**9. Deterministic timeline?** No. Clip durations come from model output; the beat JSON is a plan, not a seekable timeline.

**10. Recommendation: REFERENCE ONLY.** Take the arc table and the two-gate / bake-off pattern as *ideas* into our own docs. Do not adopt the pipeline, the MuAPI dependency, A-roll restyling or `clone_ref`. Tests/CI: **none** [read].

---

## 4. `remotion-dev/template-prompt-to-motion-graphics-saas` — **REFERENCE ONLY**

**1. Intended use and architecture.** A Next.js SaaS template: `User Prompt → Validation → Skill Detection → Code Generation → Sanitization → Live Preview` [claim, and matches the code: `README.md`, `src/app/api/generate/route.ts`].

**2. Engine and dependencies.** Remotion + `@ai-sdk/openai` + `ai`; the route calls **`gpt-5.2`** via the OpenAI API (`OPENAI_API_KEY`) [read: `route.ts` lines ≈300–360; `.env.example`]. Optional AWS Lambda rendering (`REMOTION_AWS_*`; region/ram/disk/timeout in `config.mjs`, `deploy.mjs`) [read]. In-browser Babel (`@babel/standalone`), Monaco, Three. Package version `4.0.379` — **older** than the monorepo's current packages (`4.0.534`) [read].

**3. Implemented vs. described.** Implemented [read]: (a) a cheap **classifier prompt** (`VALIDATION_PROMPT`) that rejects non-motion prompts before the expensive call; (b) **dynamic skill selection** (`src/skills/index.ts`: 8 guidance skills + 9 example-code skills; `SKILL_DETECTION_PROMPT` asks the model to return matching categories; selected skills are concatenated into the system prompt); (c) a single-shot system prompt with hard rules (constants-first, no shadowing imports, backgrounds from frame 0); (d) follow-up **search/replace edits** with a Zod schema (`FollowUpResponseSchema`); (e) post-processing in `src/helpers/sanitize-response.ts` and `src/remotion/compiler.ts`.

**4. Reusable ideas.** Lightweight intent gate before a costly step; "inject only the relevant skills" to keep the base prompt small; style-specific *example code* beside *guidance*; edit-by-search/replace for revisions. The factory already has a catalogue query (`contentos/intelligence/catalogue.py`), a validator (`production/direction.py`) and skills, so none of this is a gap. [mine]

**5. Security finding (verified by reading).** "Sanitization" is **cosmetic, not a security boundary**: `sanitize-response.ts` only strips markdown fences, does a regex "has JSX" check and brace-counts the component; `compiler.ts` strips `import` statements with regexes, transpiles with Babel, then runs the result via **`new Function("React","Remotion",…, code)`** in the page [read]. Model output therefore executes with full page privileges. Do **not** copy this pattern for anything that accepts untrusted prompts. For the factory, where an agent writes HyperFrames HTML under validators and nothing is `eval`'d in a user-facing app, the point is moot but worth recording.

**6–7. Effort, cost, network.** Not integrable (a different renderer and a hosted-app architecture). Cost formula: `OpenAI tokens (classifier + skill detection + generation) × price` + optional Lambda `(render seconds × memory × rate)`; prices **not** looked up. All prompts leave the machine to OpenAI.

**8. Licence.** **No LICENSE file in this standalone repo** [read]. The README says "for some entities a company license is needed" and links the Remotion licence; the same template also lives in the Remotion monorepo at `packages/template-prompt-to-motion-graphics` (version 4.0.379) [read], where `LICENSE.md` applies. Treat it under the **Remotion License** (§8 below).

**9. Deterministic timeline?** The generated component is a pure function of `useCurrentFrame()` (Remotion model) but the LLM-written code itself is non-deterministic and unvalidated.

**10. Recommendation: REFERENCE ONLY.** Tests/CI: **none** [read].

---

## 5. `Vincentwei1021/mg-styles-15` — **ADAPT (schema + rubric) / SPIKE (bake-off)**

**1. Intended use and architecture.** "Fifteen styles, one 10-second film each, all made by Claude Opus 5.5 writing code", each with style notes, **full prompt**, and complete source [claim: `README.md`]. Every film is a web page exposing `window.renderAt(t)`; `harness/render.mjs` captures frames in headless Chrome; `demos/<n>/audio.py` synthesises that film's soundtrack on the same `cues.json`; ffmpeg muxes; a *second* AI reviews with `rubric.md` for two revision rounds [read: `harness/render.mjs` header, `README.md`].

**2. Engine and dependencies.** Node ≥ 22.12 + `puppeteer-core` 25.12, three, d3, simplex-noise, opentype.js; Python ≥ 3.11 with numpy, scipy, numba, pedalboard, librosa, pyloudnorm for audio; Blender for the one 3D film [read: `package.json`, `requirements.txt`, `README.md`]. 62 Python and 30 JS files; repo is 1.2 GB mostly media (`videos/` 421 MB, `lib/` 56 MB, `demos/` 64 MB) [read: `du`].

**3. Implemented vs. described.**
- Implemented [read]: `harness/render.mjs` — deterministic HTML→MP4 with `renderAt(t)`, WAAPI seeked via `currentTime`, `--stills`, `--workers`, `--shutter` motion blur, per-OS GPU flags. 15 prompts (`prompts/*.md`) built from a **fixed template** (`template.md`): Style · Output spec · Suggested technical route · Creative seed (timed beats) · **Signature features and key techniques** [read]. `rubric.md`: a 7-dimension jury prompt (`style_fidelity`, `concept_wow`, `motion_craft`, `design_typography`, `finish_texture`, `sound_sync`, `technical`) plus a spec checklist and a "revise" prompt [read].
- Claimed, not verified by me: "final AI-jury scores run 7.57 to 8.21 out of 10" [claim: README]. These are LLM scores, not human judgements, and I do not rely on them.
- Observed from 4 preview frames: flat-vector (solid blue ground, coral dot), collage (newsprint + halftone Victorian portrait cut-out + NASA-style nebula), line-art (thin gold outline on navy), cel-boil (hand-drawn matchbox) — four unmistakably different looks.

**4. Reusable pieces.** (a) **The style schema.** "Signature features" written as *checkable* techniques with numbers, e.g. flat-vector: `overshoot cubic-bezier(0.34,1.56,0.64,1)`, `stagger 2–4 frames`, `one subject moves at a time`; collage: `2–4 px white scissor edge + halftone filter`, `12 fps stepped motion with ±2 px jitter` [read: `prompts/01-flat-vector.md`, `prompts/06-collage.md`] — this is exactly the "required signature features and failure modes" our style library needs. (b) The **rubric** as an independent-review prompt (worded to be harsh and specific; asks for timecoded, observable faults with concrete fixes). (c) The **hook/hero-moment rules** ("hook in 0.5 s, hero at 60–75 %, end frame held 0.8–1.2 s with living micro-motion"). (d) The principle that **picture and sound read one cue sheet**. (e) Procedurally generated everything: "No image or video generation" [claim; consistent with the code I read].

**5. Distinct over the stack?** **Yes** — the factory has presets/palettes/transitions (`config/design-library.json`, 76 entries) but no per-style *fidelity checklist* and no style-specific failure modes; its critic has no `style_fidelity` dimension [read: `contentos/production/critic.py`].

**6. Integration effort / impact.** Write our own 3 style cards in the factory's format (S–M each); add `style_fidelity` as a conditional critic dimension (S). **Do not** vendor the repo (1.2 GB), the prompts verbatim, or the `renderAt` harness (a second renderer). [mine]

**7. Cost / network.** None at runtime: fully local; audio libs and Blender are heavy installs, which we would not do. The AI-jury loop costs only agent time.

**8. Licence.** Code and prompts: **MIT**, © 2026 Vincentwei1021 [read: `LICENSE`]. **Assets are mixed and not individually verified:** fonts are *not* in the repo and "licences differ" per its own note; the list includes Alibaba PuHuiTi, HarmonyOS Sans SC, Douyin Sans and others [read: `assets/fonts/README.md`] — each has its own terms [not verified]. `lib/audio` ships **102 FLAC samples**, which its README calls "CC0 VCSL samples" [claim: `lib/audio/README.md`; sample licences not verified]; photos are "CC0 or public domain" in "a few films" [claim]. Reusing *prompts and ideas* needs only the MIT notice; reusing *any asset* needs its own check.

**9. Deterministic, time-addressable?** Yes — this is its core contract (`renderAt(t)`, seeded randomness, no wall-clock) [read: prompts' "Rules" section and `harness/render.mjs`]. Same shape as a HyperFrames composition.

**10. Recommendation: ADAPT** the schema, rubric and hook rules into project-owned style cards and critic text; **SPIKE** a three-style bake-off (Experiment E2). Tests/CI: **none** [read].

---

## 6. `whaleyxbt/claude-motion` — **ADAPT (timeline, sheets, sfx) / DEFER (sims, Remotion parts)**

**1. Intended use and architecture.** "A motion design toolkit for coding agents": taste rules, a visual self-review loop, a procedural sound engine, one timeline, and a second pipeline that renders web "sims" to 60 fps [claim: `README.md`; matches `AGENTS.md`, `.claude/skills/*`]. Main example (`src/EffortVideo.tsx`, 22 s, 1080×1080, 60 fps) is **Remotion**; `sims/` is plain HTML + three.js captured by Playwright.

**2. Engine and dependencies.** Remotion `4.0.529`, React 19, Playwright 1.63, esbuild, three 0.186; Python 3 stdlib only for `sfx/`; ffmpeg [read: `package.json`].

**3. Implemented vs. described [all read, none run].**
- **`timeline.json`** — every beat a named timestamp, grouped by scene; `scripts/sheet.mjs`, `scripts/wave.mjs` and `sfx/cues/effort.py` all read it, so "retiming the video retimes the sound and the checks" [read: `timeline.json`, `AGENTS.md`].
- **`scripts/sheet.mjs`** — builds contact sheets from the timeline: one frame per beat taken **0.3 s after** it so motion has settled, tiled, each tile labelled by timestamp via ffmpeg `drawtext` (falls back to unlabelled), plus `--from/--to/--every` scrubbing for transitions [read].
- **`scripts/wave.mjs`** — waveform with every timeline beat drawn as a line, plus `ebur128` loudness and peak, targets −14 LUFS and ≤ −1 dBTP [read].
- **`sfx/`** — ~900 lines of pure Python stdlib (`dsp.py` 453, `synth.py` 193, `mix.py` 111, `loudness.py` 72, `__main__.py` 61): synth generators (typing, clicks, pops, whooshes, risers, impacts, pads), a `Mix.put(t, samples, gain, pan)` placement API, and `master()` that soft-clips and sets gain so integrated loudness (own BS.1770 implementation in `sfx/loudness.py`) hits −14 LUFS with true peak ≤ −2 dBFS; it warns when a sparse mix cannot reach target without clipping [read: `sfx/mix.py`, `sfx/loudness.py`, `sfx/synth.py`]. **No sample files, no downloads.**
- `.claude/skills/review-loop/SKILL.md` — a draft → sheet → checklist → fix loop; rule "do not claim a fix you haven't re-rendered and looked at" [read].
- `sims/` — pure `render(t)` pages + Python `beats.py` for tempo/drop; three examples [read: README, `sims/`].
- Not verified: the "340K+ views" and other social claims; performance claims in `sfx/dsp.py` comments; whether `npm run build` works on this machine (not run).

**4. Reusable pieces.** (a) The **timeline-as-single-source** pattern: it is how the factory's "authoritative timeline" can be built from `sceneplan.resolve()` + aligned words, with captions, cues, sheets and QA all deriving from one file. (b) The **beat-labelled contact sheet** (settle offset + timestamp labels + scrub mode) — a drop-in improvement on `contentos/production/preview.py::contact_sheet`, which tiles a hand-picked list with no labels. (c) The **procedural SFX + mastering engine** — the only upstream audio component with no sample or licence baggage; fills a verified factory absence (no music/SFX/ducking). (d) The review checklist and its "report what you checked / fixed / which sheet shows it" rule.

**5. Distinct over the stack?** **Yes** for (a)–(c). The motion rules overlap the factory's `explainer-motion-craft` R1–R6 and mostly agree (ease-out entrances, exits ≈ half of entrances, reading holds); they differ on "idle elements breathe / nothing is dead-still", which the factory rejected for explainers (R4).

**6. Integration effort / impact.** Timeline schema + loader: M. Labelled sheet: S (ffmpeg only, already a factory dependency). SFX engine: M (copy a ~900-line stdlib module under MIT with notice; add a cue-sheet writer that reads the timeline); runtime concern — it loops per sample in pure Python [read], so measure render time for a 60 s mix before committing [not tested].

**7. Cost / network.** None; all local.

**8. Licence.** Code: **MIT**, © 2026 whaleyxbt [read: `LICENSE`]. The Remotion-based example is subject to the Remotion License (§8). Fonts via `@fontsource/*` (typically OFL; not verified). The sound engine generates audio, so there are no third-party samples.

**9. Deterministic timeline?** Yes: "animation is a pure function of `useCurrentFrame()`; no CSS animations, `Math.random()` or `Date`" [read: `AGENTS.md`]; `Mix` seeds its RNG (`random.seed(seed)`) [read: `sfx/mix.py`].

**10. Recommendation: ADAPT** timeline pattern, labelled sheet and (after Experiment E1) the sfx engine; **DEFER** `sims/` (a different content type) and anything that would pull Remotion in. Tests/CI: no tests; `.github` has only an issue template [read].

---

## 7. `lottiefiles/motion-design-skill` — **REFERENCE ONLY**

**1. Intended use.** "Universal motion design principles for AI agents. Philosophy-first, implementation-agnostic" — for **UI** animation (buttons, cards, modals, micro-interactions, loading/success/error, scroll) [claim and read: `README.md`, `skills/motion-design/SKILL.md` "When to Apply"].

**2–3. Content [read].** 18 markdown files, ~57 KB, no code: an 8-step checklist; four **motion personalities** (Playful 150–300 ms ease-out-back 10–20 % overshoot; Premium 350–600 ms, 0 %; Corporate 200–400 ms; Energetic 100–250 ms, 15–30 %); a duration table whose range is **80 ms–1,200 ms**; entrance/exit and feedback patterns; Disney's 12 principles "adapted for UI"; emotion → motion mapping; choreography ("1/3 rules", stagger); a micro-narrative framework (setup → action → resolution) [read: `SKILL.md`, `director/*.md`, `patterns/*.md`, `reference/*.md`].

**4. What transfers to narrated video, and what does not [mine].**

| Transfers | Does not transfer |
|---|---|
| Emotional intent first (what should the viewer feel); one **motion personality per project**; primary/secondary/ambient layers; staging a hero element; decelerate-in / accelerate-out; entrances longer than exits; limit simultaneous movers (the 1/3 rule); micro-narrative per beat | The duration table (tooltip 80 ms, button 120 ms, hover/press feedback) — video reveals need reading holds of seconds; loading/success/error state patterns; hover and press; accessibility/reduced-motion guidance; property tables aimed at interactive components |

Conflict to resolve explicitly: its *Playful* archetype (10–20 % overshoot) contradicts factory rule R1 (no `back/elastic/bounce` unless the brief asks). Resolution: make "motion personality" a field on a **style card**, with an overshoot allowance stated per style, not a global default.

**5. Distinct over the stack?** Marginal. `explainer-motion-craft` + `hyperframes-animation` already cover timing and easing with video-specific numbers; the new part is *naming* emotional intent and personality.

**6–7. Effort / cost.** Text only; no dependencies, no cost, no network at run time.

**8. Licence.** **MIT**, © 2025 LottieFiles [read: `LICENSE`; `SKILL.md` frontmatter also says MIT].

**9. Deterministic timeline?** Not applicable (guidance, not an engine).

**10. Recommendation: REFERENCE ONLY.** Lift two ideas into style cards (`emotional_intent`, `motion_personality`). Do not install the skill globally (the factory's rule: no global skills changes in this audit). Tests/CI: **none** [read].

---

## 8. `remotion-dev/remotion` — **DEFER (no adapter); reference transitions and captions**

**1. Intended use and architecture.** "Video tools for the agent era": React code is the source of truth; Studio, CLI, player, Lambda, captions, transitions, 12 official agent skills [claim and read: `README.md`, `packages/`]. A monorepo of ~137 packages at **4.0.534** [read: `packages/core/package.json`].

**2. Engine and dependencies.** Bun/turbo monorepo [read: `AGENTS.md`, `package.json`]. The renderer drives Chrome: `packages/renderer/src/browser/BrowserFetcher.ts` selects `chrome-headless-shell` [read]; native `@remotion/compositor-*` binaries are optional dependencies of `@remotion/renderer` [read: its `package.json`]. Node 20+ [read: claude-motion's README for the example; Remotion's own requirement **not verified**].

**3. Implemented vs. described.** Real and large. Relevant parts [read, not run]: `@remotion/transitions` — presentations including `fade`, `slide`, `wipe`, `flip`, `iris`, `clock-wipe`, `cross-zoom`, `film-burn`, `linear-blur`, `zoom-blur`, `dissolve`, `ripple`, `book-flip` (`packages/transitions/src/presentations/`); `@remotion/captions` (MIT); `@remotion/install-whisper-cpp`, `@remotion/whisper-web`; `@remotion/sfx`; `@remotion/web-renderer`; `@remotion/mcp` (MIT); `packages/skills-evals` and CI workflows exist, i.e. the project tests itself [read].

**Official agent skills.** `packages/skills/skills/` holds 12 skill folders, 109 files: `remotion-best-practices` (router), `remotion-create`, `remotion-markup` (3d, audio, captions-related, transitions, motion-blur, light-leaks, voiceover, sfx, silence-detection, text-highlights …), `remotion-captions`, `remotion-render`, `remotion-studio`, `remotion-maps`, `remotion-saas`, `remotion-interactivity`, `remotion-docs`, `remotion-multimedia`, `remotion-upgrade` [read]. Published with `npx skills add remotion-dev/skills` [read: `packages/skills/README.md`]. One router rule worth knowing: "Don't render the video by default … start Studio and open the preview" [read].

**4. Reusable pieces.** The transitions catalogue as *reference* for naming and parameters; the captions/whisper packaging as a design reference for word-level caption handling. Nothing is needed *as code* — the factory already has `hyperframes tts`/`transcribe`, CSS transitions and `align.py`.

**5. Distinct over the stack?** Only as a **second renderer** (React components, Lambda scale-out, a Studio UI). The factory's own earlier audit found "no demonstrated advantage; neither was rendered" and I found nothing in this pass that changes that: every requirement in the target architecture can be met with HyperFrames + project code.

**6. Integration effort / runtime / maintenance.** Adding it means a second adapter, a Node/React toolchain, a second timeline model (`useCurrentFrame` vs paused GSAP timeline), second font/asset handling, and a licence process. XL. [mine]

**7. Cost / network.** Local rendering is free for eligible users. Lambda and other cloud paths cost money (formula: render-seconds × memory × rate + storage; not priced). Chrome download on first use if no browser is present (documented by claude-motion README; not verified for 4.0.534).

**8. Licence (read `LICENSE.md` at the pin).** The **Remotion License**: *free* for "an individual", "a for-profit organization with up to 3 employees", non-profits, and evaluation; otherwise a paid **Company License**. Disallowed: copying/modifying Remotion "for the purpose of selling … your own derivative". The file says it "will slightly change" in Remotion 5.0 [read]. Package metadata is **not uniform**: core/renderer/cli/player/lottie/web-renderer say "SEE LICENSE IN LICENSE.md"; `@remotion/captions`, `@remotion/three`, `@remotion/mcp` say **MIT**; `media-parser` and `webcodecs` carry their own "Remotion License" wording; **`@remotion/transitions` declares `"license": "UNLICENSED"`** in its own `package.json` [read] — ambiguous, to be clarified before any use. `@remotion/skills` is `private` with no licence field [read]; the standalone `remotion-dev/skills` repository's licence was **not re-checked** (a prior project finding says it has no licence file; I could not confirm either way). Eligibility depends on the legal entity running the channel; **the owner should confirm which tier applies.**

**9. Deterministic, time-addressable?** Yes: compositions are pure functions of `useCurrentFrame()` [read: claude-motion `AGENTS.md`; Remotion skills text].

**10. Recommendation: DEFER.** No adapter. Revisit only with a concrete trigger (see roadmap): data-driven batch templates at volume, or a use case HyperFrames demonstrably cannot render. Tests/CI: yes — `.github/workflows/` (`push.yml` etc.) and `packages/skills-evals` [read].

---

## 9. Licence and rights matrix (as read at the pinned commits)

| Repo | Code licence in force | File present? | Third-party media / fonts / samples | Paid service or external API | Data leaving the machine | Notes for the owner |
|---|---|---|---|---|---|---|
| claude-motion-design | MIT (Howseen AI) | `LICENSE` ✔ | Mixkit free licence, Pexels/Unsplash, svgl logos (brand-owned), Geist OFL — downloaded, not redistributed; texts **not read** | 21st.dev key (optional) | prompts to the agent; asset downloads | Do not adopt meme/yt-dlp, AI-face and remake-a-launch-video flows (rights/likeness) |
| vox | **Unclear**: `package.json`/README say MIT; **no LICENSE file**; `homepage` points to another repo | ✘ | model-provider terms **not read** | **MuAPI (paid)**; one script references OpenAI | topic, images, clips, TTS text, **user video/audio/photos**, voice samples (`clone_ref`) | Voice cloning and face-preserving restyle exist with **no consent control**; default watermark "Made with MuAPI" |
| Remotion SaaS template | none in standalone repo; falls under the Remotion License | ✘ | — | **OpenAI (paid)**, optional AWS Lambda | every prompt to OpenAI; renders to AWS if deployed | `new Function` executes model output |
| mg-styles-15 | MIT (Vincentwei1021) | `LICENSE` ✔ | fonts **excluded** (each has own terms: Alibaba PuHuiTi, HarmonyOS Sans, Douyin Sans …); 102 FLAC samples called CC0 VCSL **[claim]**; some CC0/PD photos **[claim]** | none | none | Verify any asset before use; our own style cards need none of them |
| claude-motion | MIT (whaleyxbt) | `LICENSE` ✔ | none for the sound engine (procedural); `@fontsource` fonts (not verified); Remotion example under Remotion License | none | none | The `sfx/` engine is the licence-clean piece |
| LottieFiles skill | MIT (LottieFiles) | `LICENSE` ✔ | none (text) | none | none | — |
| Remotion | Remotion License (free tier: individual / ≤3-employee for-profit / non-profit / evaluation); some packages MIT; **`@remotion/transitions` says UNLICENSED** | `LICENSE.md` ✔ | Chrome headless shell downloaded at first run (not verified) | none locally; **Lambda/cloud costs money** | none locally | Owner to confirm eligible tier; re-read licence at Remotion 5.0 |

**Generated outputs.** None of the MIT repositories claims ownership of videos you make with them; the Remotion License is likewise about using the software "for the purpose of creating videos" [read]. This is not a statement about third-party media you include.

**Source-media rights.** The ability to ingest or transform footage (vox A-roll, claude-motion-design remake mode) does not imply permission to reuse that footage, voice, likeness or music. The factory should treat any supplied footage/audio as needing a recorded rights status (see report 06 §5 and report 07 §4).

**Voice cloning.** Not adopted. vox's `clone_ref` is the only cloning code in the seven repos; it uploads a voice sample to a third-party API with no consent record. Any future provider must satisfy the consent policy in report 06 §7 before a single sample is uploaded.

## 10. What each repository is *not* evidence of

- No repo here is evidence that a style, effect or pipeline **renders well in this factory**. Only a render on the named Mac environment with the existing gates, plus human review, is.
- LLM-jury scores (mg-styles-15's 7.57–8.21) and social view counts (claude-motion) are marketing-grade evidence for our purposes.
- "Works with Claude Code" statements concern skill-loading, not output quality.
