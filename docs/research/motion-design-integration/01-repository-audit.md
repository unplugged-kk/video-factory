# 01 — Repository audit (Deliverable A)

Audit date: **2026-10-12**. Scope: research only. Nothing was installed, executed, rendered or published. Upstream repositories were shallow-cloned (`git clone --depth 1 --no-tags`) into an isolated cloud scratch folder, **outside** the Video Factory checkout, and read statically.

Labels (same as `docs/video-intelligence/05-external-repository-audit.md`): **[read]** I read the file at the pinned commit · **[ran]** I ran a read-only command and saw output · **[claim]** upstream's own statement, not verified · **[not verified]** could not check · **[mine]** my inference or recommendation.

## 0. Method, depth and limits

- **No upstream code ran.** "Works" means "the code path exists and reads coherently".
- **No upstream video was watched.** Nothing here says how any upstream output looks or sounds.
- **GitHub API access was not enabled for these repositories in this session** (every `gh api` call returned 403), so stars, releases, tags, issue activity, archived flags and rename redirects were **not** checked. "Maintenance" below is only the date of the latest commit on the default branch in a shallow clone. A clone by the supplied `owner/name` succeeded for all 15 URLs; a silent GitHub rename-redirect would not have been visible, so repository identity is "the content at that URL today", not a verified ownership history.
- **Depth varies** and is stated per repository: *deep* (SKILL, references and scripts read), *medium* (SKILL, README, representative references/scripts), *shallow* (README and skill descriptions only), *carried* (re-verified only that the commit SHA is unchanged since the 2026-10-11 audit, then findings carried forward from doc 05).
- Seven of the 15 repositories were already audited yesterday in `docs/video-intelligence/05-external-repository-audit.md` (three of them are on this list: `howseen-ai/claude-motion-design`, `whaleyxbt/claude-motion`, `LottieFiles/motion-design-skill`; `remotion-dev/remotion` also, but its HEAD moved). This audit does not redo them; it adds the eight not covered, re-reads the HyperFrames upstream, and compares everything against the live checkout.

### Pinned commits (default-branch HEAD at clone time)

| # | Repository | Commit (full SHA) | Last commit | Checkout size |
|---|---|---|---|---|
| 1 | `AbubakrChan/product-launch-motion` | `951d6149d2748a15058f79dcf8e8c4bf00824121` | 2026-08-27 | 2.7 MB |
| 2 | `charlie947/motion-graphics-skills` | `229022ebca76972e119e36ada23a1648d51665ab` | 2026-10-11 | 25 MB |
| 3 | `howseen-ai/claude-motion-design` | `3d90d349ef3fdde9b7e89de4df4a2159c9e8697f` (same as doc 05) | 2026-10-02 | 8.5 MB |
| 4 | `nateherkai/hyperframes-student-kit` | `0d30152a82b9ceb93cfdd9bdbf46f0d5ab3cde86` | 2026-09-28 | 822 MB |
| 5 | `Barty-Bart/motion-graphics` | `d6e5d95e45167d95bb4260b9da4d674791143710` | 2026-10-12 | 55 MB |
| 6 | `cth9191/animate` | `7e5eb56feb2dd573f890e1b7b34748af43d58263` | 2026-10-05 | 19 MB |
| 7 | `whaleyxbt/claude-motion` | `e627941543d9988b155dc610bb9cc0115a5e365e` (same as doc 05) | 2026-10-09 | 30 MB |
| 8 | `haidrrrry/claude-remotion-skill` | `1dcbe5e3fc6cf970bd10d3cc05f0a8a5d19d0383` | 2026-08-12 | 30 MB |
| 9 | `motiondivision/motion` | `e6bf03ead39cae7a2c5f8fe902ce8a9c1a9a22e8` | 2026-10-09 | 540 MB |
| 10 | `199-biotechnologies/motion-dev-animations-skill` | `3feedfb4dba8adae40fc9a5f9a23e3dda2121205` | 2026-03-30 | 0.5 MB |
| 11 | `heygen-com/hyperframes` | `8b27935e8ce336ca7bc3873c0850b5a32dcd32cf` (main); tag `v0.8.114` = `01c6f6004a00ecfa6e77ab4025b47a46a5e925fc` (the factory's pin) | 2026-10-12 | 417 MB |
| 12 | `remotion-dev/remotion` | `5ce9514934716083274bb18221737223aba63318` (doc 05 pinned `32af7e8…`) | 2026-10-12 | 1.3 GB |
| 13 | `remotion-dev/skills` | `7ba4dcf8ebe1626b00baa41e1f2478113719b60b` | 2026-10-12 | 4 MB |
| 14 | `greensock/gsap-skills` | `aed9cfd3277740755f6bfc1155c7aa645403b760` | 2026-04-21 | 0.6 MB |
| 15 | `LottieFiles/motion-design-skill` | `f9a8a041b85185ee4881b3471d3415e939aac772` (same as doc 05) | 2026-05-18 | 0.3 MB |

**Numbering note.** The supplied list numbers 15 URLs under four groups; the prose says "14" in one place and the HyperFrames repository is entry 11. All 15 URLs were audited. Two similarly named things are **not** interchangeable and are kept apart: `motiondivision/motion` (the animation *library*, MIT) is not `motiondivision/ai-kit` (the "Motion AI Kit" already recorded in `config/capabilities.json` as `ref:motion-ai-kit`, reference-only), and `remotion-dev/skills` (a generated mirror of the monorepo's `packages/skills`) is not `haidrrrry/claude-remotion-skill` (a third-party skill; rejected in `docs/factory-v2/07-motion-graphics-skills-audit.md`).

## 1. Summary table

| # | Repository | What it really is | Depth | Recommendation | One-line reason |
|---|---|---|---|---|---|
| 1 | product-launch-motion | One skill: ten laws, 14-step pipeline, creative-direction method, 8 scripts, honest evals | deep | **ADAPT** (techniques) | Best source for *direction*, *word-locked cueing* and *measured audibility*; same renderer family; take principles, not the pipeline |
| 2 | charlie947 motion-graphics-skills | 15 launch/brand-oriented skills, newsletter-led | shallow | **REFERENCE** | Overlaps HyperFrames blueprints and our skills; marketing-genre bias; little verifiable evidence of quality |
| 3 | howseen claude-motion-design | `seek(t)` Playwright toolkit + one long skill | carried | **ADAPT** (two small items) / **REFERENCE**; **REJECT** remake and scraping flows | Unchanged since doc 05 |
| 4 | hyperframes-student-kit | Footage-editing kit: silence/mistake cuts, EDL review, short-form planning and QA tables, motion cards | medium | **ADAPT** (QA discipline, review-gated cuts) / **DEFER** (footage editing) / **REJECT** (paid generation path, card pack) | Rich *QA* ideas; footage editing is not a current factory use case |
| 5 | Barty-Bart motion-graphics | 6 skills: transcript-timed morph B-roll, measured SFX pass with CC0 library, SAM 2 separation, 3 explainer templates | medium | **ADAPT** (SFX pass method) / **DEFER** (B-roll) / **REJECT** (object separation) | The only upstream with a *bundled CC0 SFX library plus measured placement* |
| 6 | cth9191 animate | Canvas-based procedural animation skill: 7 style kits, story grammar with measured checks, 3 approval gates | deep | **ADAPT** (style-grammar format, formats formula, gates) / **REFERENCE** (kits) | The strongest answer to "genuinely different visual languages"; its renderer is a second renderer and is not adopted |
| 7 | whaleyxbt claude-motion | Remotion toolkit + `timeline.json` + stdlib sound engine + sheets | carried | **ADAPT** (already partly absorbed: timeline/1, sheet/1) | Remaining unabsorbed piece: procedural SFX |
| 8 | haidrrrry claude-remotion-skill | One Remotion skill, `spring()` for every entrance | medium | **REJECT** | Duplicate and conflicting with R1; Remotion-bound (already rejected in doc factory-v2/07) |
| 9 | motiondivision/motion | JS/React/Vue animation library (v14.1.0) | medium | **REFERENCE** / **DEFER** | A web-UI library, not a video workflow; not one of HyperFrames' runtime adapters |
| 10 | 199-biotechnologies motion-dev-animations-skill | A React/Next.js UI animation skill (Nov 2025, Motion v11 era) | shallow | **REJECT** | Wrong domain, stale |
| 11 | heygen-com/hyperframes | The renderer *and* 20+ official skills | medium | **ADOPT** (selectively, at the existing pin) | `faceless-explainer`, `hyperframes-creative`, `hyperframes-audio`, `talking-head-recut` exist **at tag v0.8.114** and are Apache-2.0 |
| 12 | remotion-dev/remotion | A second renderer + official skills | medium | **DEFER** | No demonstrated limitation of HyperFrames; licence tier needs owner confirmation; `@remotion/transitions` is `UNLICENSED` |
| 13 | remotion-dev/skills | Generated mirror of Remotion's 12 official skills | medium | **REFERENCE** | No LICENSE file in this repository; Remotion-specific |
| 14 | greensock/gsap-skills | Official GSAP API skills (core, timeline, ScrollTrigger, React, plugins, utils, perf) | medium | **REFERENCE** | Web-app oriented; HyperFrames' own GSAP guidance already covers the seek-safe subset |
| 15 | LottieFiles motion-design-skill | 18 markdown files of UI motion principles | carried | **REFERENCE** | Unchanged since doc 05 |

---

## 2. Repository sections

### 2.1 `AbubakrChan/product-launch-motion` — **ADAPT (techniques)**

| Field | Assessment |
|---|---|
| Identity | Repo at `AbubakrChan/product-launch-motion`, `951d614`, MIT © 2026 Abubakr Chan [read: `LICENSE`]. README links a v1.0.0 release film (45 s, for cheerful.ai) [claim; not viewed]. |
| Purpose | "Direction", not rendering: a discipline for launch films from code. Ten laws, a 14-step pipeline, a 14-shot catalogue and 34 recorded traps [claim; `references/10-traps.md` is 406 lines, I did not count entries]. |
| Artifact type | Skill (`SKILL.md` 237 lines) + 12 reference docs + 8 scripts + 5 templates + `evals/`. |
| Strongest capabilities | (1) **Law 10 / `references/11-creative-direction.md`**: the look is *derived*, never inherited. Eleven "direction dials" (energy, density, ground, depth, camera, type, texture, colour, product, sound, voice); "any two films should differ on ≥4 dials"; and a second table of **structural axes** (rhetorical device, arc, where the turn lands, the ending, the climax mechanic, opening state, copy placement, human presence, sound dramaturgy) because its own test found two films with different surfaces had **twelve structural convergences** [read]. Plus a "two-film test" (write your structure next to the last film's). (2) **Law 2 / `references/03-word-locked-sync.md`**: every reveal is cued to the measured start of the word it illustrates ("cue the meaning, not the noun"; lead by a hair when the eye needs travel; "one beat can carry two cues, never three") [read headings and rules]. (3) **Law 6 / `scripts/verify-cue.sh`**: proves a sound cue is present in the *delivered* file by a per-100 ms peak envelope, and catches a cue that starts late because the asset opens with room tone [read]. (4) Law 9 / two-gate QA, "verify the delivered file", versioned renders. (5) `evals/BASELINE.md` is candid: write-up, not a machine-checked benchmark, and the unaided model did well on one scenario [read]. |
| Dependencies | Node ≥ 20, ffmpeg, a seek-based renderer (HyperFrames default, "works with Remotion too" [claim]), GSAP vendored by a `curl` from jsdelivr at setup [read README], optional Whisper and optional local TTS. No paid service. |
| Licence | Code and docs MIT. **`NOTICE`** says the reference film and `examples/still-1.jpg` are Cheerful's and not reusable; GSAP, FFmpeg and any music/SFX/fonts carry their own terms [read]. |
| Maintenance | Last commit 2026-08-27 (6 weeks). Single author. No CI, no tests (evals are prose) [read: file listing]. |
| Existing overlap | `explainer-motion-craft` R1–R6 (smooth ease, hold, restraint) agrees with Law 7 and the "smooth beats bouncy" stance; `video-director` covers hook/arc/takeaway; `production/align.py` + `timeline/1` cover word cueing; `critic.py` covers review. **Not covered in the factory:** the structural-axes method, the "diverge then kill two" step as a *requirement*, the measured-audibility check, and any sound design. |
| Compatibility | **Adaptable.** Same renderer family; laws are renderer-neutral by its own statement. The pipeline assumes frame-per-HTML-file product films; our Track B differs. |
| Strategy | Adapt: (a) direction dials + structural axes + two-film test into the creative-decision record and a variety report; (b) cue practice into `video-director` cue guidance; (c) `verify-cue` idea as a small deterministic gate *if and when* SFX exist. Do not adopt the pipeline, the grade scripts (`wire-grade.mjs`) or the shot catalogue. |
| Risks | Launch-film genre assumptions; film-grade scripts change look globally; GSAP fetch at setup (network); a skill that tells the agent to run `curl` and `npx` must never be auto-loaded (AGENTS.md rule). |
| Recommendation | Read and cite `11-creative-direction.md`, `03-word-locked-sync.md`, `07-sound-and-master.md` when writing the style-card and variety-report prompts (doc 07). Pin nothing. |

### 2.2 `charlie947/motion-graphics-skills` — **REFERENCE**

| Field | Assessment |
|---|---|
| Identity | `229022e`, MIT © 2026 Charlie Hills [read]. 35 tracked files. Newsletter-branded README ("71k readers" badge [claim]). |
| Purpose | 15 skills: `brand-intake`, `launch-video`, `apple-launch-film`, `vox-explainer`, `motion-effects` (16 looping effects with `window.seek(seconds)`), `motion-brief-writer`, `reference-to-motion`, `milestone-reveal`, `model-showdown`, `title-sequence-3d`, `animated-chart`, `loop-cover`, `reel-export`, `newsletter-promo`, `motion-prompt-writer` [read: directory list]. |
| Artifact type | Skill pack. Export via HyperFrames, or ffmpeg + Chrome; "nothing here needs an API key" [read README]. |
| Strongest capabilities | `motion-brief-writer`: asks for exact numbers, "keeps real results apart from sample data, and never invents a figure" [read: description]; `reference-to-motion`: turns a reference video's moves into a scene-by-scene prompt [read: description]; `vox-explainer`: torn paper, halftone, motion on twos [read: description]. |
| Dependencies | Node/Chrome/ffmpeg; "pick Opus 5.5" in the README. HyperFrames optional (`npx skills add heygen-com/hyperframes`). |
| Licence | MIT. Output samples and brand imagery not assessed. |
| Maintenance | Active (last commit 2026-10-11). |
| Existing overlap | High: HyperFrames official blueprints (22 registered in our `capabilities.json`), our `video-director`, `explainer-motion-craft`, the `fabricated_data_unlabeled` hard failure in `critic.py`. |
| Compatibility | Unverified for our pin; brand and launch oriented. |
| Strategy | Reference only. **Depth: shallow** — I read the README and skill descriptions, not each `SKILL.md`. |
| Risks | "Vox-style" is a third-party house style; naming it on a card invites imitation claims. Keep any resulting card generic ("paper collage, halftone, stepped motion"). Marketing-grade evidence only. |
| Recommendation | No action. If the owner wants a paper-collage style card, derive it from `cth9191/animate`'s cut-paper `STYLE.md` and `mg-styles-15`'s collage prompt (doc 05), which have written signature features. |

### 2.3 `howseen-ai/claude-motion-design` — **ADAPT (two small items) / REFERENCE; REJECT remake & scraping**

**Carried from doc 05** (same SHA `3d90d34`). MIT. The relevant items are the capture hygiene list (fonts ready, pause WAAPI, 2×rAF), drop/BPM analysis (only if music-led videos are wanted) and the brief-before-code discipline. Pops/flash detection already exists in `motion_audit.py`. Remake mode (frame-locked 1:1 remake of any launch video), `yt_dlp` meme downloads and AI-face sources conflict with the factory's source-media rule. No new finding.

### 2.4 `nateherkai/hyperframes-student-kit` — **ADAPT (QA discipline, review-gated cuts) / DEFER (footage editing) / REJECT (paid generation, card pack)**

| Field | Assessment |
|---|---|
| Identity | `0d30152`, MIT © 2026 Nate Herk plus a bespoke `licenses/PIPELINE-USE-PERMISSION.txt` for the imported pipeline resources [read]. 1,049 tracked files, 822 MB checkout (`video-projects` 287 MB, `examples` 128 MB). |
| Purpose | A teaching kit for Codex and Claude Code: bring footage, cut dead air, review mistakes, plan the story, build motion graphics with HyperFrames and GSAP [read README]. 15 skills mirrored for both assistants; 406 "draft motion-graphics cards" in two styles; two scene templates; `npm test` runs 2 Node test files; one CI workflow (`check.yml`) [read]. |
| Artifact type | Skills + scripts + templates + example projects. |
| Strongest capabilities | **`cut-silences`, `cut-mistakes`** [read `cut-mistakes/SKILL.md`, `find-cut-candidates.mjs`]: a *mechanical* candidate finder (stutters, retakes by Jaccard similarity, false starts) that explicitly refuses to decide — emphatic repetition looks identical to a stutter — so a **review gate is required**; approved cuts become an EDL and a re-timed transcript (`apply-cuts.mjs`), reviewed with an HTML EDL review page. **`short-form-edit/references/quality-gates.md`** [read]: a ~30-row gate table applied "to the encoded final" — first three seconds, open loops, rhythm and reading load, cadence ("repeated template", ">2.2 s gap without a deliberate story hold"), editorial variety ("repeated card reveal with different words"), duplicate-footage ledgers, audio revision, delivery — plus the sentence **"Calibrate new validators with negative controls. A caption shifted by 0.3 seconds, a one-frame scene gap, and an omitted spoken word should fail the relevant checks."** `validate-plan.mjs`/`validate-footage.mjs` are 38 and 25 lines. `motion-showreel/scripts/beatgrid.mjs` lays chapters on a beat grid. |
| Dependencies | Node ≥ 22, ffmpeg/ffprobe, Chrome; pins **`hyperframes` 0.7.109** (ours is 0.8.114) and `gsap` 3.14.2 [read `package.json`]. Optional **ElevenLabs Scribe** (transcription) and **Kie.ai** (video/image generation) with API keys; `kie.mjs` uploads media to `kieai.redpandaai.co` [read]. |
| Licence | MIT for the original kit; the bundled HyperFrames skills carry Apache-2.0 notices; `THIRD_PARTY_NOTICES.md` says the previously published **example media and brand assets remain unchanged and "their inclusion does not grant third-party rights"**; library cards name "Vox, Kallaway, Infinite" as aesthetic references and use Google Fonts [read]. Treat every non-code asset as unlicensed until checked. |
| Maintenance | Last commit 2026-09-28; has CI and tests (unlike most others). |
| Existing overlap | The bundled `hyperframes`, `gsap`, `hyperframes-cli`, `hyperframes-registry` skills are copies of HyperFrames official skills at an older version — duplicates. QA overlap: `visual_gate.py`, `motion_audit.py`, `critic.py`, `sheet.py`. **No overlap:** transcript-aware cutting, EDLs, retake detection, footage ledgers. |
| Compatibility | The *ideas* are compatible; the workflow assumes the owner's recorded footage, which Video Factory does not process today (it is script → TTS → render; supplied *audio* is only now being added as provenance/rights, G3). |
| Strategy | **Adapt** the negative-control principle and the editorial-variety/cadence gate language into the seeded-fault QA experiment (doc 06 §E-QA). **Adapt** "mechanical finder + mandatory human review + EDL" as the *design* for any future supplied-audio retake review. **Defer** the whole editing workflow until supplied-audio ingest is finished and a footage-rights record exists. **Reject** `kie.mjs`/AI-generated video, the 406-card pack (draft, brand-adjacent) and importing any of the bundled example media. |
| Risks | Data egress (`kie.mjs`), older pinned renderer, large media, rights on examples, paid-service defaults. |
| Recommendation | Cite the gate table in prompts G-6/G-7; do not clone it into the repo. |

### 2.5 `Barty-Bart/motion-graphics` — **ADAPT (SFX pass method) / DEFER (B-roll) / REJECT (object separation)**

| Field | Assessment |
|---|---|
| Identity | `d6e5d95`, MIT © 2026 Bart [read]. 160 tracked files, 55 MB. The README promotes a paid community course (Skool). |
| Purpose | Six skills: `motion-broll` (talking-head video + transcript → one-shape morphing motion graphics timed to the speaker's words), `object-separation` (SAM 2 masks of a person/product/hand), `explainer-high-energy` (12–20 s beat-locked promo), `explainer-default` (45–90 s UI demo), `explainer-engaging` (10–30 s one-take story), `sound-effects` (measured sound pass) [read]. |
| Strongest capabilities | **`sound-effects`**: cue list → beat-grid check against kick drums → cuts on the beat → **one real SFX per cue from a bundled CC0 library** → mix and measure. 110 files, 2.7 MB, with per-file licence rows in `LICENSES.md` (Freesound CC0 and Kenney CC0 entries read; every row not verified), peak-normalised to −3 dBFS, ambience to −35 LUFS, 48 kHz [read]. Mixkit items are *downloaded at runtime and never committed* (no-redistribution licence) [read]. **`motion-broll`**: state changes placed "on their word"; it states word times from SRT/VTT are **estimates (±0.2 s)** and says so [read], and "Never invent numbers, quotes, prices or results" [read]. |
| Dependencies | `sound-effects`: Python venv with `librosa soundfile numpy scipy matplotlib` [read]. `object-separation`: `torch transformers opencv-python-headless`, downloads `facebook/sam2.1-hiera-*` weights from Hugging Face [read]. `motion-broll`: `faster-whisper` for word times. |
| Licence | Repo MIT; SFX CC0 per `LICENSES.md` (spot-read); Geist font OFL (`OFL-Geist.txt` shipped); Mixkit/Pixabay assets explicitly not redistributable. SAM 2 weights licence **not verified**. |
| Existing overlap | None for SFX (the factory has no SFX at all; `mpt.py` sets `--bgm-type=none` because bundled tracks have no verified licence [read]). B-roll overlaps nothing implemented. |
| Compatibility | The method is renderer-agnostic (cue list in, placed audio and measurements out). Needs a decision on *where* audio is mixed (see doc 03 §6). |
| Strategy | **Adapt** the *method* (cue list → real sample per cue → measured, never "louder = better"). The CC0 sample set is a candidate SFX source **to be compared** with `claude-motion`'s procedural synth and HyperFrames' own bundled 19-file SFX library (media-use) in a listening test (roadmap P2). **Defer** transcript-timed motion B-roll (needs supplied audio + transcript trust first). **Reject** `object-separation` for the core factory (heavy ML install; person/hand footage is not a current input). |
| Risks | Heavy Python audio stack (librosa); runtime downloads from Mixkit; Skool promotion; the repo is changing today (commit dated 2026-10-12) so a pin is mandatory before any reuse. |
| Recommendation | Pin `d6e5d95` if any file is ever copied; verify each used sample's `LICENSES.md` row against the source page first. |

### 2.6 `cth9191/animate` — **ADAPT (grammar, formats, gates) / REFERENCE (kits)**

| Field | Assessment |
|---|---|
| Identity | `7e5eb56`, MIT © 2026 cth9191 [read]. 114 tracked files; a Claude Code plugin (`.claude-plugin/marketplace.json`) and plain skill folder. |
| Purpose | "Procedural animation in any style": one `<canvas>`, drawn and scored procedurally, deterministic frame by frame, rendered with Playwright + ffmpeg [read README]. **A style is a plug-in**: the story grammar, timing, sound, renderer and tools stay constant; the style supplies the drawing kit [read]. |
| Artifact type | Skill + renderer/tools (`tools/build.mjs`, `export.mjs`, `review.mjs`, `still.mjs`, `tile.mjs`, `storyboard.mjs`, `beats.mjs`, `voice.mjs`, `capture.mjs`, `compare.mjs`, `framehash.mjs`, `textcheck.mjs`) + 7 style kits + a 60 s worked example. |
| Strongest capabilities | (1) **Style as a written contract** [read `styles/riso/STYLE.md`, 92 lines]: one governing rule ("nothing is painted, everything is printed"), a palette table with *measured* values, screen angles, pitch per layer, misregistration offsets, motion habits ("on 2s", cuts on the 8th grid), a **frame checklist** of ten checkable items and a kit API. This is exactly the missing "checkable signature features and failure modes". Seven styles: cut paper, crosshatch ink, riso print, sketchbook, math, pixel, isometric. (2) **`grammar/FORMATS.md`** [read]: every piece is one choice from four columns — plot engine (chronology, token through stations, call→catalogue, goal+helper, fixed subject × N, claims→proof), stage (beat-cut, one-sheet follow-camera, morph chain, locked-off build), clock (music grid, voice, even stations) and medium (style) — with coupling rules ("a voice takes over the clock"), six invariants ("silence before the payoff, loudest on the payoff", "the end is the start, changed") and **per-format measured checks** that `review.mjs` proves when `TIMELINE.format` is set (e.g. ≥80% of cuts on the grid; ≥85% still frames on a fixed stage; ≤−40 dB before the loudest hit). Several formats are labelled "studied, not yet built". (3) **Three cheap approvals before animating**: story check (format + numbered beat table), **look check (2–4 full-size style frames)**, storyboard (every beat as a key frame) [read README]. (4) **`new-style.md`**: a procedure that *measures* a reference (palette, line weight, texture, motion, cut rhythm), draws matched frames beside it, and compares. |
| Dependencies | Node 18+, Playwright + Chromium, ffmpeg; fonts are local system fonts [read]. Voice-over via the **ElevenLabs connector** (paid account, OAuth) or the user's recording; word times locally with `faster-whisper` [read SKILL.md]. |
| Licence | MIT. Style demos are "original subjects" per `riso/STYLE.md`; reference measurements were taken from third-party animations (not redistributed) [read]. |
| Maintenance | Last commit 2026-10-05. Single author. No tests or CI seen [read: file listing]. |
| Existing overlap | Factory: `config/design-library.json` has 8 `visual_style` entries (presets/palettes/transitions as *options*), Rule A/B (`intelligence/visual.py`) compares **backdrop colour/structure/texture signatures**, but has no per-style rules or checklists, and no structural-variety check. |
| Compatibility | The *format* of `STYLE.md` + grammar + gates is directly adaptable. The *kits* are canvas code built for its own renderer; HyperFrames can in principle host canvas content driven from a seekable timeline, but that is **[mine, not tested]** and is exactly the one controlled experiment worth running (doc 06 Variant B). |
| Strategy | **Adapt**: (a) `style/1` card = STYLE.md contract (governing rule, measured parameters, motion habits, transition set, sound dramaturgy, frame checklist, failure modes); (b) the four-column formula as the *structure* vocabulary of the creative-decision record; (c) the three approvals; (d) the measured structural checks as candidates for deterministic gates (cuts-on-grid, still-fraction, hero anchoring, loudest-after-silence). **Reference** the kits. **Reject** the ElevenLabs path and the Playwright renderer as a lane. |
| Risks | A second renderer if the kits are imported; paid voice path; one-author maintenance; "studied, not yet built" formats must not be treated as proven. |
| Recommendation | Highest-value source for the "different visual languages" requirement. Do not import code; write three style cards in the factory's own wording (doc 07, G-2). |

### 2.7 `whaleyxbt/claude-motion` — **ADAPT (already partly absorbed)**

**Carried from doc 05** (same SHA `e627941`). MIT. Already absorbed in the factory: the shared-timeline pattern (`timeline/1`, shadow) and the labelled contact sheet (`sheet/1`, initial) were both written by the project in its own code. Not yet absorbed: the stdlib procedural SFX/mastering engine (~900 lines, no samples) and `wave.mjs`-style waveform-with-beat-lines. Note the marginal value of this repo is lower today than doc 05 projected. Remotion-coupled parts stay deferred.

### 2.8 `haidrrrry/claude-remotion-skill` — **REJECT**

| Field | Assessment |
|---|---|
| Identity | `1dcbe5e`, MIT © 2025 haidrrrry [read]. 33 tracked files, 30 MB (`demo.mp4`, `demo.gif`, a packaged `remotion-motion-graphics.skill` zip). |
| Purpose | One 136-line Remotion skill (`SKILL.md`, `references/design-rules.md`, `references/motion-patterns.md`, `assets/theme.ts`) with example Remotion projects, including generated-audio scripts (`gen-sfx.mjs`, `gen-track.mjs`, not studied). |
| Overlap / conflict | Remotion-bound. States "every entrance prefers `spring()`" [read line 16], which conflicts with house rule R1 (no back/elastic/bounce unless asked). Already rejected as duplicate/conflicting in `docs/factory-v2/07-motion-graphics-skills-audit.md` [doc]. |
| Recommendation | **Reject.** Do not unpack the `.skill` archive into any skills directory. Depth: medium. |

### 2.9 `motiondivision/motion` — **REFERENCE / DEFER**

| Field | Assessment |
|---|---|
| Identity | `e6bf03e`, MIT © Motion B.V.; packages `motion`, `motion-dom`, `framer-motion` all `14.1.0` [read]. 540 MB checkout; yarn/turbo monorepo with Playwright tests. |
| Purpose | Animation library for JS, React and Vue [claim README]. Implements `JSAnimation` (a JS-driven animation with internal `currentTime`) and `NativeAnimation` (a Web Animations API wrapper) [read: `packages/motion-dom/src/animation/`]. |
| Category | A web-animation *library*. It is not a skill, not a video workflow and not a renderer. |
| HyperFrames fit | HyperFrames registers seek adapters for **GSAP, CSS, Web Animations (WAAPI), Anime.js, Lottie, Three.js, TypeGPU, d3, and map libraries** [ran: list of `packages/core/src/runtime/adapters/*` at both `main` and tag `v0.8.114`]; there is **no Motion adapter**. Motion's WAAPI-backed animations may be seekable through the WAAPI adapter, and `JSAnimation` is time-addressable in principle, but whether a render is frame-exact **is not verified** and would need an isolated experiment. |
| Gap it fills | None demonstrated. Spring physics, stagger and morphs are already available through GSAP in the pinned stack; the registry lists `hf.rule:spring-pop-entrance`, `hf.rule:press-release-spring`, `hf.rule:physics-press-reaction`. |
| Risk | A second animation runtime in compositions increases the determinism-audit surface; `Math.random`/`rAF`-driven behaviour is a lint failure in HyperFrames' contract. |
| Recommendation | **Reference** (spring-to-`linear()` easing concept is useful background); **defer** any use. Not an integration candidate until a specific shot cannot be built with GSAP + WAAPI. Note again: this is **not** `motiondivision/ai-kit` (see §0). |

### 2.10 `199-biotechnologies/motion-dev-animations-skill` — **REJECT**

`3feedfb`, MIT © 2025 [read]. A skill for React 19 / Next.js 15 / Svelte / Astro UI animations (scroll, gestures, layout) with "120fps GPU-accelerated" framing; frontmatter dated 2025-11-08; README badge says Motion v11 while the library is now 14.1.0 [read]. Wrong domain (interactive web UI, `allowed-tools: Read, Write, Edit, Bash...`), stale, no video relevance. Depth: shallow. **Reject.**

### 2.11 `heygen-com/hyperframes` — **ADOPT (selectively, at the existing pin)**

| Field | Assessment |
|---|---|
| Identity | `heygen-com/hyperframes`, Apache-2.0 [read: `LICENSE`, `packages/cli/package.json`]. `main` = `8b27935` with packages at **0.8.150**; the factory pins **0.8.114** (`package.json`; lock file tag `v0.8.114`, commit `01c6f6004a00ecfa6e77ab4025b47a46a5e925fc`). 36 patch versions apart. |
| Purpose | The renderer (CLI, engine, producer, player, studio, shader-transitions, aws-lambda, gcp-cloud-run) **and** a skills tree. |
| Artifact type | Renderer + skills + registry (blocks/components) + docs. |
| Strongest capabilities | **At tag v0.8.114** I checked the skills tree [ran: `git ls-tree`]: besides the three the factory pins (`hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes`) it already contains **`faceless-explainer`** (27 files: `story-design.md`, `motion-language.md`, `visual-design.md`, `cut-catalog.md`; scripts for frame packets, captions, transitions with tests), **`hyperframes-creative`** (79 files: `story-spine.md`, `beat-direction.md`, `storyboard-recipe.md`, `design-picker.md`, `narration.md`, audio-reactive), **`hyperframes-audio`** (7 files: ducking "voiceover carve", effect chains, automation; engine files `packages/core/src/audioFx.ts`, `audioFxPresets.ts` exist at that tag), **`talking-head-recut`** (28), **`product-launch-video`** (34), **`music-to-video`** (169), **`media-use`** (104), **`embedded-captions`** (144), **`motion-graphics`** (23) and **`remotion-to-hyperframes`** (77). `faceless-explainer`'s `motion-language.md` doctrine — "smooth beats bouncy, `power3` is the default", "sequential reveal in the back ~50% timed to the voiceover", "no motion over bad motion" — is consistent with R1–R6 [read headings]. Runtime adapters include `gsap.steps` tests (stepped motion) [ran]. |
| Dependencies | Node, ffmpeg, Chrome. `media-use` resolves BGM/SFX/images/voice through the **HeyGen catalog and the `heygen` CLI** with sign-in; offline fallbacks (local Kokoro) are described [read SKILL.md]. `faceless-explainer`'s SKILL tells the agent to run `npx hyperframes skills update …` and `init` "checks installed skills against the latest on GitHub and updates the global set" [read] — network and global-state mutation. |
| Licence | Apache-2.0 for code and skills. Catalogue media, fonts and templates referenced by presets carry their own terms (not assessed). |
| Maintenance | Very active (commit today). |
| Existing overlap | The renderer is the default. The factory pins and hash-verifies 3 skills (`scripts/upstream_skills.py`, `config/upstream-skills.lock.json`, `tree_sha256`). |
| Compatibility | **Compatible** for skills at the same tag; the pin mechanism already exists. |
| Strategy | **Adopt selectively**: review `hyperframes-creative` (story spine, beat direction, storyboard recipe, design picker) and the `faceless-explainer` references as *candidate additions to the pinned set at tag v0.8.114*, through the existing lock/hash process and an owner-approved review. Do **not** upgrade the renderer in this work (a separate decision with its own regression run). Do **not** enable `media-use` catalogue/auth paths (paid-account and egress risk); if its bundled local SFX library is wanted, treat it as a licence-review item. Strip or neutralise any `npx … skills update`/network instruction before a skill is allowed to load (AGENTS.md: "never auto-load skill text from outside this repo"). |
| Risks | Skill text that executes network commands; bundled scripts with bootstrap logic (`package-loader.mjs` exists in `hyperframes-creative/scripts`, the same pattern the registry already marks as opt-in for the animation map); drift between skills at the pin and a newer engine. |
| Recommendation | The single highest-leverage, lowest-risk step in this audit — see doc 04, P1-1. |

### 2.12 `remotion-dev/remotion` — **DEFER**

| Field | Assessment |
|---|---|
| Identity | `5ce9514`, packages at `4.0.535`; HEAD moved since doc 05 (`32af7e8`, 4.0.534). 1.3 GB. |
| Purpose | React-based video framework: Studio, CLI, renderer (Chrome headless shell), Lambda, captions, transitions, player, 12 agent skills [read]. |
| Licence | `LICENSE.md`: **free** for an individual, a for-profit organisation with up to 3 employees, non-profits, and evaluation; otherwise a paid **Company License**; the file says it "will slightly change" in Remotion 5.0 [read, re-read today]. Package metadata is not uniform: `@remotion/captions` MIT; `@remotion/renderer` "SEE LICENSE IN LICENSE.md"; **`@remotion/transitions` declares `"license": "UNLICENSED"`** [ran: grep]. Eligibility depends on the legal entity running the channel; the owner should confirm the tier. |
| Overlap | The factory's pinned renderer already renders HTML deterministically; the registry contains the equivalents (transitions as CSS/shader, captions via `align.py`). |
| Evidence of a HyperFrames limitation | **None found in this audit.** The only candidates are hypotheses (per-pixel canvas styles, large-scale parallel rendering) that have not been tested on HyperFrames. |
| Strategy | **Defer.** No adapter. `remotion-to-hyperframes` (an official HyperFrames skill) exists for the case where a Remotion composition must be ported one way. Revisit only with a named shot HyperFrames cannot render acceptably **and** a licence decision. |

### 2.13 `remotion-dev/skills` — **REFERENCE**

`7ba4dcf`. Contains 12 skills (`remotion-best-practices` router, `-captions`, `-create`, `-docs`, `-interactivity`, `-maps`, `-markup`, `-multimedia`, `-render`, `-saas`, `-studio`, `-upgrade`) [read]. The README says the file is **generated** from the monorepo (`packages/skills/scripts/sync-readme.ts`). **There is no LICENSE file in this repository**, and `package.json` is `private: true` with no `license` field [read]. Under the file-presence rule used in this project, the text must not be vendored. Content is Remotion-specific and overlaps HyperFrames' own guidance. **Reference only.**

### 2.14 `greensock/gsap-skills` — **REFERENCE**

`aed9cfd`, MIT © 2026 GreenSock [read]. Eight official skills: `gsap-core`, `-timeline`, `-scrolltrigger`, `-plugins`, `-react`, `-frameworks`, `-performance`, `-utils`. Aimed at web apps (ScrollTrigger, React/Vue/Svelte); HyperFrames' own `hyperframes-animation` already encodes the seek-safe GSAP subset. README claims GSAP and all former Club plugins are now free after the Webflow acquisition [claim]. **Licence caution:** `product-launch-motion/NOTICE` describes a "GSAP Standard 'No Charge' licence" whose terms "turn on how your project is monetised" [read], and `contentos/templates/gsap.min.js` is committed in the factory repository [ran]. The two statements are not reconciled here; the owner should read the current GSAP licence page for the intended business use. Use: occasional cross-check of GSAP API facts. **Reference.** No recommendation to change the GSAP dependency.

### 2.15 `LottieFiles/motion-design-skill` — **REFERENCE**

**Carried from doc 05** (same SHA `f9a8a04`). MIT. UI-scale motion principles; lift two ideas (`emotional_intent`, `motion_personality`) into style cards, with an overshoot allowance stated *per style* so the Playful archetype does not collide with R1.

---

## 3. Cross-repository observations

1. **Most of the third-party skill packs re-teach what the HyperFrames upstream already ships and the factory's own skills already encode** (easing, holds, restraint, deterministic seeking, word sync). Where they add something, it is *direction and verification method*, not motion technique.
2. **Three kinds of "new" are real:** (a) *structural-variety method* (product-launch-motion, animate); (b) *measured audio/sync verification* (product-launch-motion `verify-cue.sh`, Barty `sound_pass.py`, claude-motion `sfx`); (c) *negative-control QA discipline* (student-kit). None needs a new renderer.
3. **Two rights patterns recur:** MIT code with explicitly excluded third-party media (product-launch-motion NOTICE, student-kit THIRD_PARTY_NOTICES, mg-styles-15 fonts), and repositories with no LICENSE file (`remotion-dev/skills`). Software licence ≠ media licence; nothing here grants rights to example footage, music, fonts or brand marks.
4. **Paid or egress paths hide in optional steps**: ElevenLabs (animate, student-kit), Kie.ai (student-kit), HeyGen catalogue sign-in (HyperFrames media-use), Mixkit runtime downloads (Barty). All must stay off by default.
