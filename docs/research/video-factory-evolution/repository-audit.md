# A — Repository audit (19 upstream repositories)

Audit date **2026-10-14**. Research only: **nothing was installed, cloned, executed, rendered or downloaded from any
upstream repository**, no paid API or model weight was touched, no global skill or agent configuration was changed, and no
file on this machine was modified.

## 0. Method, evidence labels and limits

Each repository was inspected through fetched public pages and files — the GitHub REST API for identity/metadata, the
contents API for trees, and `raw.githubusercontent.com` for README, LICENSE, `SKILL.md`, scripts and CI configuration.
Seven of the nineteen were already audited at recorded commit pins in
`docs/video-intelligence/05-external-repository-audit.md` and `docs/research/motion-design-integration/01-repository-audit.md`;
those findings are marked **[carried]** and were re-verified only where the refresh below says so.

| Label | Meaning |
|---|---|
| **[read]** | I (or the research agent) fetched and read the file this session. Path given. |
| **[carried]** | Taken from a prior audit at a recorded pin; not re-derived this session. |
| **[claim]** | The upstream project's own statement. Not verified by me. |
| **[not verified]** | Could not check. |
| **[mine]** | My inference or recommendation. |

**Stated limits, plainly:**

- **No upstream code ran.** "Works" means "the code path exists and reads coherently".
- **No upstream video or GIF was watched.** Nothing here is a statement about how any upstream output looks or sounds. A
  slick demo is not evidence of code quality and was not weighted as such.
- **Repository identity is "the content at that URL today."** A silent GitHub rename-redirect would not have been visible
  in every case; where a rename *was* detected it is reported explicitly (repo 4).
- **Popularity metrics are not evidence and are largely omitted.** Star/fork counts reported by different fetches were
  inconsistent and several looked implausible. They are recorded as **[claim]** where given, are never used to support a
  decision, and should not be quoted.
- **Some agent-reported numbers could not be re-derived.** Where a figure drives a decision it is attributed to the
  upstream file it came from; where it does not, it is dropped.
- **This is not legal advice.** Licence readings are of the files present at the time of reading.

### Pinned commits / refresh status

| # | Repository | Pin or status |
|---|---|---|
| 1 | `AbubakrChan/product-launch-motion` | metadata + full tree read this session |
| 2 | `charlie947/motion-graphics-skills` | metadata + 3 SKILL.md read this session |
| 3 | `howseen-ai/claude-motion-design` | **[carried]** pin `3d90d349…`, 2026-10-02 |
| 4 | `nateherkai/hyperframes-student-kit` | **[read] RENAMED → `nateherkai/herk-edit-kit`** |
| 5 | `Barty-Bart/motion-graphics` | metadata + 4 SKILL.md read this session |
| 6 | `cth9191/animate` | **[read] refresh: HEAD == pin `7e5eb56f…`, 2026-10-05, UNCHANGED** |
| 7 | `whaleyxbt/claude-motion` | **[read] refresh: HEAD == pin `e6279415…`, 2026-10-09, UNCHANGED** |
| 8 | `haidrrrry/claude-remotion-skill` | **[read] refresh: HEAD == pin `1dcbe5e3…`, 2026-08-12, UNCHANGED** |
| 9 | `Tejashmakwana/motionmaxxing` | **[read]** created and pushed 2026-10-06; 2 commits, 0 releases |
| 10 | `feitangyuan/onetake` | **[read]** LICENSE read in full |
| 11 | `Priyanshsharma21/aansh-video` | **[read]** all implementing files read |
| 12 | `motiondivision/motion` | **[carried]** pin `e6bf03ea…` + metadata this session |
| 13 | `199-biotechnologies/motion-dev-animations-skill` | **[read]** README/SKILL/LICENSE |
| 14 | `heygen-com/hyperframes` | **[read]** npm metadata, CLI help text, release bodies, docs |
| 15 | `remotion-dev/remotion` | **[read]** `LICENSE.md`, npm metadata, licensing docs |
| 16 | `remotion-dev/skills` | **[read]** tree + `contents/LICENSE` → **404**, API `license: null` |
| 17 | `greensock/gsap-skills` | **[read]** `LICENSE`, `AGENTS.md`, 4 SKILL.md |
| 18 | `LottieFiles/motion-design-skill` | **[carried]** pin `f9a8a041…` + SKILL/tables read this session |
| 19 | `morluto/rea` | **[read]** README, `package.json`, `SECURITY.md`, `DISCLAIMER.md`, SKILL |

---

## 1. Summary of decisions

| # | Repository | What it really is | Adds something distinct? | Decision |
|---|---|---|---|---|
| 1 | product-launch-motion | Skill: creative-direction doctrine, 10 laws, 14-shot catalogue, frame-diff seam scan | Partly — direction dials, structural axes, measured cue placement | **REFERENCE** |
| 2 | motion-graphics-skills | 15 brand/launch-oriented skills, docs-only, plus a skill-hygiene validator | Marginally — the validator and the token-file convention | **ADAPT** |
| 3 | claude-motion-design | One very large skill + a real Playwright/ffmpeg renderer + a "remake" pipeline | Partly — pop/flash/loop-seam detectors, adaptive subframes | **ADAPT** (techniques) · **REJECT** remake + scraping |
| 4 | hyperframes-student-kit (**now herk-edit-kit**) | Footage-editing template kit on HyperFrames; transcript-driven cuts; ~30-row QA gate table | Yes for *editing* — outside the current pipeline | **DEFER** (paid hooks + rights) · **REJECT** bundled media |
| 5 | Barty-Bart/motion-graphics | 6 skills incl. a measured, licence-aware sound pass and a CC0 SFX library | **Yes** — measured audio QA, which the factory lacks entirely | **ADAPT** |
| 6 | cth9191/animate | Canvas procedural-animation skill: 7 style kits, `FORMATS.md` grammar, 3 approvals | **Yes** — the best source for style *contracts* and structural checks | **ADAPT** |
| 7 | whaleyxbt/claude-motion | Remotion toolkit + `timeline.json` + stdlib procedural SFX + labelled sheets | Partly — **already partly absorbed** by this repo | **ADAPT** (remaining: SFX) |
| 8 | haidrrrry/claude-remotion-skill | One Remotion skill; `spring()` for every entrance | **No** — and it conflicts with R1 | **REJECT** |
| 9 | Tejashmakwana/motionmaxxing | Measured motion catalogue + DOM "page-chrome" linter + audio-sync audit | Two things: the G5 lint taxonomy and audio cut-sync | **REFERENCE** |
| 10 | feitangyuan/onetake | Skill + frame-capture renderer **under PolyForm Noncommercial** | Method only; **LICENCE WALL** | **REFERENCE** (code-level REJECT) |
| 11 | Priyanshsharma21/aansh-video | Voice → animated host + word captions on HyperFrames | **Yes** — the documented "lip-synced cartoon host" gap | **ADAPT** |
| 12 | motiondivision/motion | The Motion/Framer Motion animation library | **No** for video | **REFERENCE** |
| 13 | motion-dev-animations-skill | A React/Next UI-animation skill, stale (claims v11; current v14) | **No** — wrong domain | **REJECT** |
| 14 | heygen-com/hyperframes | **The pinned renderer** + 20+ official skills + much more | **Yes** — unused subsystems and known fixes | **ADOPT** |
| 15 | remotion-dev/remotion | Second renderer; non-OSI two-tier licence; bills per render above 3 employees | **No demonstrated need** | **DEFER** |
| 16 | remotion-dev/skills | Generated mirror of Remotion's 12 official skills | **No**, and **unlicensed** | **REJECT** |
| 17 | greensock/gsap-skills | Official GSAP API skills | API-correctness reference for the engine already in use | **ADAPT** |
| 18 | LottieFiles/motion-design-skill | 18 markdown files of vendor-neutral motion principles | A quantified threshold table, UI-scaled | **ADAPT** (numbers only) |
| 19 | morluto/rea | MCP server + CLI for reverse-engineering **source-less** artifacts | **No** — solves the inverse of this project's problem | **REJECT** |

**Three of nineteen are near-duplicates of one another.** Repos 1, 3 and 5 (and repo 2's `motion-effects`) implement the
same method — one HTML page where every frame is a pure function of time (`seek(t)` / `window.renderAt(t)`), captured
frame-by-frame in headless Chromium/Playwright, blended with FFmpeg `tmix` at a ~180° shutter, with SFX placed by
**measured peak** and a "one shape never cuts" doctrine. They cross-credit each other and even share wording. Auditing them
as four independent discoveries would overstate the diversity of the ecosystem; they are one method in four wrappers.

---

## 2. Repository-by-repository

### 1. `AbubakrChan/product-launch-motion` — REFERENCE

| Field | Finding |
|---|---|
| Artifact type | Agent **skill** (`SKILL.md` + `references/` prose doctrine), plus a frozen `legacy/` (v1) script set |
| Primary use case | Creative *direction* for a short launch film: a discipline, not a renderer |
| Best verified capabilities | Numbered motion laws; a "direction dials" method (energy, density, ground, depth, camera, type, texture, colour, product, sound, voice) with the rule that two films should differ on ≥4 dials; a second table of **structural axes** motivated by its own finding that two films with different surfaces had twelve structural convergences; a "two-film test"; word-locked cueing; a `verify-cue` script that proves a cue is present in the *delivered* file via a per-100 ms peak envelope |
| Relevant source paths | `SKILL.md`; `references/prompts.md`, `references/technique.md`, `references/11-creative-direction.md`, `references/03-word-locked-sync.md`, `references/07-sound-and-master.md`; `legacy/scripts/verify-cue.sh`; `NOTICE` |
| Dependencies | Node ≥20, Playwright, FFmpeg, Python + numpy; a royaltent-free track; an agent. **No paid service** |
| Licence | **MIT** © 2026 Abubakr Chan. **`NOTICE` excludes the reference film and example imagery**, which are the author's client's |
| Overlap | High on doctrine — its motion rules agree with `explainer-motion-craft` R1–R6 and the 70-entry technique registry; it renders in the same family (HTML + headless Chrome + GSAP) |
| Potential value | The **structural-axes method** (the factory's `style/1` uses exactly this idea — six axes — and this repo is its best-written justification), the *diverge-then-kill-two* requirement, and the measured-audibility idea |
| Integration boundary | Cite the direction/structural-axes docs when writing style cards and the variety report. **Do not** install the skill (its "you are the director, no creative limits" model is LLM-in-the-selection-path) and **do not** copy the pipeline or grade scripts |
| Operational cost | Free/local. Its v2 forks the renderer to bare Playwright, which differs from the HyperFrames pin |
| Risks | Doctrine is prose, not code; one author; no tests or CI; the headline demo asset is not redistributable; setup fetches GSAP over the network |
| Confidence | **High** — tree, `SKILL.md`, `README`, `LICENSE`, `NOTICE` and releases all read |

### 2. `charlie947/motion-graphics-skills` — ADAPT

| Field | Finding |
|---|---|
| Artifact type | **Skill pack**, 15 `SKILL.md` folders, docs-only, ships no renderer |
| Primary use case | A menu of named motion jobs (launch film, "vox explainer", animated chart, 16 UI effects, reel export) |
| Best verified capabilities | A fixed 8 s loop contract in `motion-effects` (move 0→2.2 s, hold →6.6 s, return →8.0 s; `seek(0) == seek(8)`; specified check frames); a 7-beat 45 s structure in `launch-video`; **`validate-skills.sh`** — a ready-made skill-hygiene validator enforcing frontmatter shape, name==folder, description length, and house style |
| Relevant source paths | `skills/*/SKILL.md`; `skills/motion-effects/references/effects.md`; `prompts/*.md`; `validate-skills.sh` |
| Dependencies | Agent only. Optional HyperFrames or FFmpeg+Chrome. "Nothing here needs an API key" **[claim]** |
| Licence | **MIT** © 2026 Charlie Hills |
| Overlap | High: the 16 effects are a subset of the 70 registered techniques; brand tokens overlap the design registry; house rules overlap the existing banned-defaults |
| Potential value | The **skill/registry validator** (directly useful given this repo has 400+ installed skills and hash-verified upstream ones) and the on-frame "example/illustrative" labelling rule |
| Integration boundary | Port the validator and token-file convention into project tooling. Do not adopt the skill menu |
| Operational cost | Free; MP4 export depends on an external HyperFrames skill |
| Risks | Inconsistent skill count across README/description/tree; no releases; docs-only so quality is delegated; no tests |
| Confidence | **High** for the files read; the skill count discrepancy is noted rather than resolved |

### 3. `howseen-ai/claude-motion-design` — ADAPT (techniques) / REJECT (remake, scraping)

**[carried]** pin `3d90d349…`, 2026-10-02, MIT © 2026 Howseen AI.

A Claude Code skill for code-only motion design (HTML + Playwright + ffmpeg) where a film is one HTML page whose state is
`window.seek(t)`, plus a **real** Python renderer (`render_template.py`, `audio_template.py`, `analyze_song.py`) and a
`remake/` subsystem. Genuinely useful and **already partly covered** by this repo's own tools:

- **Pop and one-frame-flash detection** — this repo already has an equivalent in `production/motion_audit.py` (ydif-based
  pops). **Do not add a second.**
- **Loop seam checked in position *and* velocity** — a real addition; the factory's loop checks are weaker.
- **Adaptive subframes** for rendered motion blur — relevant only if motion blur is wanted.
- **Drop/BPM analysis by band energy** with the explicit warning "never trust an auto beat grid" — relevant only to
  music-led video, which the style schema currently refuses.
- Captured **sprint presets** and an explicit "2× `requestAnimationFrame` after every `seek`" capture-hygiene rule.

**Reject:** `remake/` (a frame-locked 1:1 remake of any launch video — a derivative-work and likeness risk), the
`yt_dlp` meme downloads, the generated-face source, and the paid TTS path. Its asset workflow reaches out to Mixkit,
Unsplash, Pexels, svgl and a third-party MCP client at runtime.

Licence MIT for code; third-party media keeps its own terms; brand logos belong to their owners.

### 4. `nateherkai/hyperframes-student-kit` — **RENAMED**; DEFER

| Field | Finding |
|---|---|
| Identity | The supplied URL redirects: **`nateherkai/hyperframes-student-kit` → `nateherkai/herk-edit-kit`**. Its own README states "Formerly the HyperFrames Student Kit." Treat the old URL as an alias |
| Artifact type | **Template/boilerplate kit** — 15 skills duplicated across `.agents/skills/` and `.claude/skills/`, ~406 motion-graphics cards, scene templates, Node tooling, built on HyperFrames |
| Primary use case | Editing **existing footage** (transcript-driven silence/mistake cuts, EDL review) plus short-form planning and QA |
| Best verified capabilities | A **~30-row quality-gate table applied to the encoded final** (first three seconds, open loops, cadence, ">2.2 s gap without a deliberate story hold", editorial variety, duplicate-footage ledgers); a mechanical cut-candidate finder that **refuses to decide** (emphatic repetition is indistinguishable from a stutter) and therefore *requires* human review; and the single most valuable line in the whole audit set: **"Calibrate new validators with negative controls. A caption shifted by 0.3 seconds, a one-frame scene gap, and an omitted spoken word should fail the relevant checks."** |
| Relevant source paths | `.agents/skills/{hyperframes,hyperframes-cli,hyperframes-registry,gsap,cut-silences,cut-mistakes,short-form-edit,motion-showreel,…}`; `short-form-edit/references/quality-gates.md`; `scripts/{validate-plan,validate-footage,cut-mistakes}.mjs`; `.github/workflows/check.yml` |
| Dependencies | Node ≥22, FFmpeg, Chrome, GSAP, HyperFrames (pinned 0.7.109 — older than ours). **Optional paid**: ElevenLabs Scribe, Kie.ai, OpenAI, Gemini, Groq |
| Licence | **NOASSERTION / "Other"** — MIT for original material, but the LICENSE states brand assets "are not licensed for reuse", and `THIRD_PARTY_NOTICES.md` records that example media retains its rights |
| Overlap | **Highest of the five motion-design repos** — its `hyperframes`/`gsap`/`hyperframes-cli`/`hyperframes-registry` skills are verbatim copies of upstream HyperFrames, which this repo already pins and hash-verifies |
| Potential value | The **negative-control QA discipline** and the editorial-variety gate language. Both are ideas, not code |
| Integration boundary | Adopt the principle into a seeded-fault harness (doc F). Do not vendor; the repo is ~460 MB |
| Operational cost | Large checkout, a Node toolchain beside the Python one, paid-API hooks |
| Risks | Paid integrations conflict with the house rule; brand-asset carve-outs; four of its skills are not original; `is_template: true` |
| Decision | **DEFER** — useful QA ideas, wrong input type (footage) for today's pipeline |
| Confidence | **High** — rename proven by redirect plus the README's own admission |

### 5. `Barty-Bart/motion-graphics` — ADAPT

| Field | Finding |
|---|---|
| Artifact type | **6 skills, two with real engines** — `motion-broll` (engine + build/render/beats scripts), `sound-effects` (`sound_pass.py`), `object-separation` (SAM 2), three explainer templates with a `seek(t)` HTML + renderer |
| Best verified capabilities | A **measured, licence-aware sound pass**: ≈−16 LUFS integrated, true peak < −4 dBFS, bed −12 dB under SFX, duck 8–12 dB under voice; a beat grid checked against kick drums with median-offset correction; per-source licence checks with a `CREDITS.txt`; and the five riskiest timestamps handed to the human. Plus a word-timing method that states plainly that SRT/VTT word times are **estimates (±0.2 s)** rather than pretending to precision |
| Relevant source paths | `skills/sound-effects/{SKILL.md,scripts/sound_pass.py,sfx/manifest.json,LICENSES.md}`; `skills/motion-broll/{SKILL.md,engine/*,reference/engine-api.md}`; `skills/explainer-*/SKILL.md` |
| Dependencies | Node + Playwright + Chromium; Python 3.10+ (`librosa`, `soundfile`, `numpy`, `scipy`, `matplotlib`; `torch`/`transformers` for SAM 2); FFmpeg; a bundled **CC0** SFX set |
| Licence | **MIT** © 2026 Bart, plus Geist fonts **OFL 1.1**, Lucide icons **ISC**, and bundled SFX recorded as **CC0** in `LICENSES.md`. Mixkit items are downloaded at runtime and **never committed** (no-redistribution) |
| Overlap | None for audio — **the factory has no music, SFX or ducking at all** (`mpt.py` sets `--bgm-type=none`). The one-shape/`seek(t)` doctrine overlaps existing techniques |
| Potential value | The **only upstream with a measured audio-QA method plus a licence-clean sample set**. Fills a verified absence |
| Integration boundary | Port the *method* and its targets into the factory's QA/audio stage; compare its CC0 library against a procedural synth and the renderer's own bundled SFX in a listening test before choosing. **Reject** `object-separation` for now (heavy ML, and person/hand footage is not a current input) |
| Operational cost | Free/local; adds a librosa-class Python stack; SAM 2 on CPU is slow |
| Risks | First-run model download for SAM 2; Mixkit runtime downloads; the repo was changing on the audit date, so any reuse must pin a commit |
| Confidence | **High** — tree, LICENSE, README and 4 SKILL.md read |

### 6. `cth9191/animate` — ADAPT

**[read] refresh: HEAD is byte-identical to the recorded pin `7e5eb56f…` (2026-10-05). No commits landed. MIT © 2026 cth9191 confirmed. No CI, no test suite.**

Procedural canvas animation in any style: one `<canvas>` drawn and scored procedurally, deterministic frame by frame,
captured with Playwright and encoded with FFmpeg. **A style is a plug-in**: story grammar, timing, sound, renderer and tools
stay constant while the style supplies the drawing kit.

Genuinely distinct, and the best-written answer to "genuinely different visual languages" in the whole set:

- **`styles/<name>/STYLE.md` as a written contract** — one governing rule ("nothing is painted, everything is printed"), a
  palette table with *measured* values, screen angles, pitch per layer, misregistration offsets, motion habits ("on 2s",
  cuts on the 8th grid), a **frame checklist of ten checkable items**, and a kit API. This is precisely the "checkable
  signature features and failure modes" that `config/design-library.json` lacks — and this repo's `style/1` cards were
  modelled on this shape.
- **`grammar/FORMATS.md`** — every piece is one choice from four columns (plot engine, stage, clock, medium) with coupling
  rules, six invariants ("silence before the payoff, loudest on the payoff"; "the end is the start, changed"), and
  **per-format measured checks** proven by `review.mjs` (≥80 % of cuts on the grid; ≥85 % still frames on a fixed stage;
  ≤−40 dB before the loudest hit). Several formats are labelled "studied, not yet built" — an honesty worth copying.
- **Three cheap approvals before animating**: story check, a look check of 2–4 full-size style frames, then a storyboard.
  This is the origin of the **style-frame checkpoint** recommended in doc C §5.

**Reject:** the ElevenLabs voice path (a paid account; a local OS-voice and local faster-whisper path also exist) and its
Playwright renderer as a second lane. **Reference** the seven style kits.

### 7. `whaleyxbt/claude-motion` — ADAPT (partly already absorbed)

**[read] refresh: HEAD is byte-identical to the recorded pin `e6279415…` (2026-10-09). No commits landed. MIT © 2026 whaleyxbt confirmed. No CI workflows.**

A Remotion-based toolkit plus a Python-standard-library sound engine, contact-sheet and waveform scripts, and browser
"sims". **Its two best ideas have already been absorbed into this repository, written independently:** the
shared-timeline pattern (`contentos/production/timeline.py`, `timeline/1`, shadow) and the labelled contact sheet
(`contentos/production/sheet.py`, `sheet/1`, initial). That lowers this repo's marginal value below what the earlier audit
projected, and it should be recorded as such.

**Not yet absorbed:** the procedural SFX + mastering engine (~900 lines of pure Python stdlib: synth generators, a
`Mix.put(t, …)` placement API, a BS.1770 loudness implementation, and a `master()` that targets −14 LUFS with true peak
≤ −2 dBFS and *warns when a sparse mix cannot reach target without clipping*). It carries **no samples and no licence
baggage** — the licence-cleanest audio option of the three candidates. Runtime concern: it loops per sample in Python, so
a 60 s mix must be measured before committing.

Remotion-coupled parts stay deferred.

### 8. `haidrrrry/claude-remotion-skill` — REJECT

**[read] refresh: HEAD is byte-identical to the recorded pin `1dcbe5e3…` (2026-08-12). Unchanged. MIT © 2025 haidrrrry. No CI, no tests.**

One 136-line Remotion skill plus example projects. It states that "every entrance prefers `spring()`", which **conflicts
directly with house rule R1** (no back/elastic/bounce unless the brief asks). It is Remotion-bound and was already rejected
as a duplicate in `docs/factory-v2/07-motion-graphics-skills-audit.md`. Nothing new has landed. **Do not unpack its
packaged `.skill` archive into any skills directory.**

### 9. `Tejashmakwana/motionmaxxing` — REFERENCE

| Field | Finding |
|---|---|
| Identity | Created and last pushed **2026-10-06**, **2 commits**, **0 releases, 0 tags**, no CI, no test suite. Description: "Looksmaxxing for motion graphics" |
| Artifact type | Agent **skill** + **executable scripts** + a vendored JS runtime + templates + examples and a precedent library (716 rows) |
| Licence | **Apache-2.0** for the original work, but `NOTICE` states the bundled **GSAP 3.12.5 is under the GreenSock Standard "No Charge" licence and "This is NOT an open-source license"**, and that the Apache grant "does not grant you any rights in GSAP". three.js/opentype MIT; Inter OFL |
| Best verified capabilities | **Measurable, not prose.** Duration medians from 4,288 measured moves (@30 fps): translate 12 frames, scale 10, rotation 11, opacity 6 in / 7 out, **all-moves median 10 frames (0.33 s)**; landing **58 % ease-out** vs leaving **37 % ease-in**; overshoot on **8.8 %** of moves with median 19 % of travel; stagger gaps **56 % exactly 1 frame**; 12 closed-form named eases with fitted values; and hard gate constants (`FLAT_STD 1.5`, runs of >3 flat frames fail; end hold ≤1.4 s; final shot ≤25 % of film; UI text ≥0.04 H) |
| Two genuinely new deterministic things | (a) **`lint.mjs`, a G5 DOM "page-chrome" linter** that seeks the page in headless Chrome and reads the DOM geometry/typography at `t` and `t+0.1 s` — checking corner labels, tracked caps, counters, metadata, footer bars, kicker-over-headline, deck layout, progress bar, letter-typed headlines and a "vibe-coded UI" family. A **frame-based** audit cannot see this. (b) An **audio cut-sync audit**: LUFS, true peak, silent-tail flag, and the share of cuts within **±80 ms** of an audio onset |
| Is the score validated? | **No.** `look.py`'s own docstring says "**Facts only, no scores**". The only numeric score is a **human** 1–10 rating entered by hand. Its `KNOWN-LIMITS.md` admits a **single rater**, "rows are unverified", and "**No A/B exists yet for this generation of the skill**". Its headline quality claims are **UNVERIFIED marketing** |
| Dependencies | Node 22+, Python 3.9+, FFmpeg, **Chrome**; vendored GSAP/three.js/opentype/fflate/Inter. **Optional paid/hosted:** ElevenLabs for voice/SFX/music, and a hosted image-generation path |
| Executes generated code / egress | **All three.** Loads the generated HTML in headless Chrome; fetches remote URLs at runtime (an SVG-logo API, a CDN, and the target brand's own site); and the optional voice path sends the script text to a third-party API |
| Overlap | **High.** Its frame-difference motion stats and flat-run detection ≈ this repo's `motion_audit.py` pops; its `references/motion.md` ≈ R1–R6; its gates ≈ `critic.py` plus Rule A/B |
| Potential value | The **G5 lint taxonomy** and the **audio cut-sync check** — re-implement them in-house. And its measured catalogue as a cross-check on R1–R6 |
| Integration boundary | **Reference only.** Do not adopt the skill or runtime: its ideation and idea-selection are the model's judgement, which violates this repo's deterministic-selection rule; the vendored GSAP is not open source; and the artifact is a funnel for a commercial host (FinalMotion) that asserts **its own house style outranks HyperFrames'** when they disagree — an authority claim this project should not accept |
| Risks | Non-open bundled engine; paid-API paths; runs generated HTML in Chrome; lint is blind to text inside `<canvas>`/images; one author, two commits, no releases |
| Confidence | **High** for the repo contents (files fetched). **The efficacy claims are Unverified** — one rater, single-day history, no independent benchmark |

### 10. `feitangyuan/onetake` — REFERENCE, with a hard licence wall

| Field | Finding |
|---|---|
| Artifact type | Agent **skill**: `SKILL.md` + Python scripts + a 39-move JS library. Films' source is deliberately not shipped |
| Primary use case | 10–30 s product/skill motion films, "one continuous camera", kinetic type, real-UI rebuilt in HTML |
| Best verified capabilities | Single HTML comp where every value is a pure `f(t)`; frame-by-frame capture with **real 180° shutter motion blur**; an **oracle script** with a continuity "carry score" that fails slideshow-style cuts; `analyze_ref.py`, which deconstructs a reference video into numbers |
| Licence | **PolyForm Noncommercial 1.0.0** — read in full. Required notice: *"Copyright (c) 2026 Patrick. onetake is free for noncommercial use only."* The grant covers "any permitted purpose", and the **only** class of permitted purpose defined is **Noncommercial**; sublicensing is barred by the "No Other Rights" clause. The README adds "Commercial use is not permitted" |
| **Commercial-use verdict** | **NOT COVERED — this is RESOLVED, not unresolved.** The licence affirmatively excludes commercial and monetized use rather than merely being silent on it. **Do not copy, vendor, or derive from any onetake file in a monetized pipeline.** Bundled fonts are separately OFL 1.1 and independently usable; the scripts and JS library are not |
| Overlap | Very high — same substrate (single HTML comp, headless Chrome, deterministic `f(t)`, captions, a QA oracle). It explicitly claims to run "without HyperFrames or Remotion", i.e. it would *replace* the pinned renderer |
| Potential value | Method study only: the carry/continuity metric, shutter-blur integration, and reference-to-numbers deconstruction are worth *knowing about* when writing motion rules. Only non-copyrightable ideas may be drawn on, independently re-implemented, with no verbatim text or logic lifted |
| Risks | Licence contamination if any file is copied; a paid "Pro" edition means the public skill is partial; films' source withheld; single author |
| Confidence | **High** — the LICENSE file was read verbatim; the licence question is textually closed |

### 11. `Priyanshsharma21/aansh-video` — ADAPT

| Field | Finding |
|---|---|
| Identity | **2 commits, both 2026-10-11**; a small repo; described as a "starter edition" |
| Artifact type | Agent **skill** + a `template/` starter project + tools |
| Primary use case | A recording → animated captioned explainer / podcast-style video with a cartoon host, rendered to MP4 through HyperFrames |
| Best verified capabilities (all read in code, not inferred from the README) | A **code-drawn host** (`engine.js` `host()`: head, hair, eyes with blink, brows, mouth, shirt from primitives); **lip synchronisation** by an **audio-amplitude mouth envelope** (`tools/mouth.py` produces `window.MOUTH`; `engine.js` `mouthAt(t)` drives an ellipse height); **voiceover handling** (`tools/transcribe.sh` → whisper word times; `tools/align.py` aligns *the user's exact script*); **word-by-word captions** (4-word groups highlighting the current word); and a **paused-GSAP → `FILM.render(ctx,t)`** HyperFrames composition |
| Licence | **MIT** © 2026 aansh.ai, with the noted exception that the bundled `gsap.min.js` is under the GreenSock licence |
| Overlap | Same substrate (HyperFrames + `f(t)` + captions), but at a **newer HyperFrames pin (0.8.143 vs 0.8.114)** and a CLI workflow rather than `./contentos.sh` |
| Potential value | **Fills a documented gap**: this project lists "a lip-synced cartoon host" as NOT built. The technique is small and self-contained (~20 lines for the envelope plus a caption function) |
| Integration boundary | MIT code is vendorable, but port the **technique**, not the skill: the mouth envelope plus the script-forced-alignment caption pattern. Be explicit that this is **amplitude-driven, not viseme-accurate** — it is a mouth open/close amount, not phoneme lip-sync |
| Operational cost | $0, fully local (librosa + whisper.cpp + canvas). Render is CPU-heavy |
| Risks | **Starter edition**: custom characters, studio sets, icon libraries and a multi-language pipeline are withheld; **2 commits on a single day** means effectively no maintenance; one generic default character; the newer HyperFrames pin may not match 0.8.114 |
| Confidence | **High** — every implementing file was read verbatim |

### 12. `motiondivision/motion` — REFERENCE

The Motion / Framer Motion animation library (MIT © Motion B.V.; a separate optional paid content plan, not a licence gate
on the library). Best verified capabilities: a hybrid JS/native engine with springs, gestures, layout/FLIP, scroll-linked
animation and timelines.

**A web-UI animation library, not a video workflow.** The renderer registers seek adapters for GSAP, CSS, WAAPI, Anime.js,
Lottie, Three.js and others — **there is no Motion adapter**, and Motion exposes no documented `seek(t)` timeline primitive
comparable to GSAP's. Its WAAPI-backed animations might be seekable through the WAAPI adapter, but whether a render would be
frame-exact is **not verified** and would need an isolated experiment. Nothing demonstrated is missing: spring physics and
stagger already exist through GSAP, and the registry lists spring rules. A second animation runtime inside compositions
would enlarge the determinism-audit surface. **Not to be confused with `motiondivision/ai-kit`**, already recorded in
`config/capabilities.json` as reference-only.

### 13. `199-biotechnologies/motion-dev-animations-skill` — REJECT

A legitimate, structured MIT skill that teaches an agent to emit Motion.dev code for React/Next/Svelte/Astro **UI**
animation (clarify → plan → implement → verify, an API table, quality gates such as ≥60 fps, CLS=0,
`prefers-reduced-motion`, <50 KB). **Wrong domain for a headless video pipeline**, and stale: its `SKILL.md` references
Motion.dev **v11** while the library is at **v14.2.0**, and it vendors no code. It even concedes that for SVG/Canvas work
"GSAP [is] better suited". Nothing here belongs in the render path.

### 14. `heygen-com/hyperframes` — ADOPT

| Field | Finding |
|---|---|
| Artifact type | The **renderer** (CLI, engine, producer, player, studio, shader transitions, cloud deploy) **plus** an official skills tree, a registry/catalogue, and docs |
| Licence | **Apache-2.0** © 2026 HeyGen, Inc. Its README states "no per-render fees or commercial-use thresholds" **[claim, consistent with the licence]**. Optional hosted services (cloud render, hosted voices/music, publish) require an account; **local rendering needs none** |
| Version reality | `main` is far ahead of the pin. The factory pins **0.8.114 (published 2026-10-03)**; current is **~0.8.157**. That is a very large number of releases in a short window, and **several releases after the pin fix bugs that directly affect this project** — see the box below |
| Architecture | Headless-Chrome frame capture (BeginFrame API / Puppeteer) plus FFmpeg encode. Deterministic seek of paused timelines; adapters for GSAP, CSS, WAAPI, Anime.js, Lottie, Three.js, TypeGPU and map libraries; shader transitions via WebGL; a composition-wide audio FX chain |
| **Concurrency facts that shape doc D** | `--workers` defaults to **auto**, and **each worker launches a separate Chrome process at ~256 MB RAM**; auto-sizing is bounded by CPU, system RAM, **the V8 heap**, and frame count, and records which bound it; `--max-concurrent-renders` is **1–10 (default 2)**; `--batch-concurrency` defaults to **1** "because each render already parallelizes across workers"; the `drawElementImage` capture path **forces 1 worker** because Chrome's canvas draw is non-deterministic across concurrent browser instances; low-memory mode auto-engages at ≤8 GB. **Upstream's own field note records an OOM on a 24 GB machine** — *"0.7.66 on 24GB: auto-picked 6 workers blew Node's default ~4GB heap"* — which is this machine's RAM size |
| Shared state to watch | A global content-addressed frame-extract cache under the temp dir; `~/.hyperframes/config.json` (upstream comments say **there is no file locking**); and a parallel-router flag upstream documents as safe only for **sequential** renders |
| Unused by this project (concrete) | Audio FX chain, ducking and `--normalize-audio`; **beat analysis** (`hyperframes beats`); the registry/catalogue; non-GSAP frame adapters; keyframe diagnostics; colour grade and HDR; extra output formats (MOV/ProRes, WebM/VP9 with alpha, GIF, PNG sequence, **HLS**); `--resolution` and supersampling; `--batch`/`--variables`; a frame-PSNR parity/regression harness that is deeper than the current 9 ffprobe checks; and local TTS/transcription |
| **Post-pin fixes that matter here** | A fix for **black last-8-pixel columns at widths like 1080** — i.e. exactly this project's 9:16 output width; a **VFR sample-by-timestamp fix for FFmpeg 8** — this machine runs **FFmpeg 9.0.2**; and a fix for per-frame memory growth during long renders. Also a **breaking** relocation of artifacts into `.hyperframes/artifacts/` |
| Decision detail | **ADOPT the upgrade path and the unused subsystems — but test the upgrade**, because it contains breaking changes and the docs warn that arm64/Docker output is not byte-identical. This is a **separate, owner-approved task with a regression run**, not a side effect of any other work |
| Confidence | **High** — npm metadata, CLI help text, release bodies and docs read |

### 15. `remotion-dev/remotion` — DEFER

A mature React video framework with a large ecosystem (Studio, CLI, renderer, Lambda, captions, transitions, a player and
official agent skills). Architecturally sound: compositions are pure functions of `useCurrentFrame()`, rendered by
headless Chrome plus a bundled FFmpeg, with **built-in parallel rendering and encoding**.

**The licence is not MIT or OSI.** `LICENSE.md` is the **Remotion License**, a two-tier model, and npm reports
`"SEE LICENSE IN LICENSE.md"`. **Free** for an individual; a for-profit organisation with **up to 3 employees**; a
non-profit; or evaluation. **Disallowed even when free**: copying or modifying Remotion code in order to sell, license or
sublicense a derivative. Above the free tier a **Company License** is required, and the published automation tier is
**$0.01 per render with a $100/month minimum** — a per-render cost with a metering key. The file also states the licence
"will slightly change" in v5. Package metadata is not uniform: some packages are MIT, some say "SEE LICENSE", and at least
one declares `"license": "UNLICENSED"` in its own `package.json`.

That is a **licence-imposed recurring cost and a metering dependency**, strictly worse than the pinned renderer's plain
Apache-2.0. **No demonstrated limitation of HyperFrames justified a second renderer anywhere in this audit** — the only
candidates are hypotheses that have not been tested on HyperFrames. Migrating would cost a full HTML→React rewrite, a
bundler build step, a second timeline model and second font/asset handling. **Defer, with no adapter.**

### 16. `remotion-dev/skills` — REJECT

Contains 12 skills (a best-practices router plus captions, create, docs, interactivity, maps, markup, multimedia, render,
saas, studio, upgrade) — a **generated mirror** of the monorepo package. Two independent disqualifiers:

1. **There is no licence.** `contents/LICENSE` returns **404** and the API reports `license: null`; `package.json` is
   `private: true` with no licence field. Under this project's file-presence rule the text must not be vendored.
2. **Paradigm conflict.** Its method is frame-indexed React (`useCurrentFrame()` / `interpolate()` / `Easing.*`), and it
   explicitly instructs against CSS transitions and animations — the opposite of a paused GSAP timeline with
   `tl.set(...)` word highlights. It is also coupled to paid services in places (maps tokens, cloud rendering) and a GPU
   path.

The one transferable concept is the caption **data model** (per-clip caption arrays with a word-level shape, and the rule
to keep each clip's captions grouped with the clip so trims and rate changes apply to both) — a design idea, not code.

### 17. `greensock/gsap-skills` — ADAPT

| Field | Finding |
|---|---|
| Artifact type | Official GSAP **skill bundle** — 8 skills (core, timeline, plugins, ScrollTrigger, frameworks, performance, utils) plus agent manifests. No build, no tests |
| Licence | **MIT** © 2026 GreenSock |
| Overlap | **Same engine the project already uses.** Timeline semantics, position parameters and performance rules overlap the pinned HyperFrames animation/keyframe skills and `explainer-motion-craft` |
| Potential value | A small **API-correctness and plugin-availability checklist** — e.g. preferring `autoAlpha`, transform aliases, `immediateRender: false` on stacked `from()` tweens, and `SplitText` for per-word/per-character splits. Plus the author's own statement that GSAP and the formerly member-only plugins are now free, which is consistent with the vendor's published Standard "No Charge" licence |
| Integration boundary | Adapt a handful of correctness rules into the renderer's guidance. Do **not** add a dependency and do **not** install the bundle |
| Risks | Vendor-locked to the GSAP API; **version drift** against the GSAP bundled inside the pinned renderer (some plugin options are newer than 0.8.114's build); a skill that duplicates existing guidance |
| Confidence | **High** — LICENSE, AGENTS.md, README and four SKILL.md files read |

**Related licence correction:** a prior document in this repo flagged the GSAP licence as unresolved ("turns on how your
project is monetised"). The vendor's current published position is that GSAP — including the former Club plugins — is free
for commercial use under the Standard "No Charge" licence (effective 2025-04-30), the sole prohibited use being to build a
competing no-code animation builder. **This project's local rendering use does not fall in the prohibited class.** Anyone
relying on this should still read the licence page directly; it is not legal advice.

### 18. `LottieFiles/motion-design-skill` — ADAPT (numbers only)

**[carried] pin `f9a8a041…`, 2026-05-18, MIT © 2025 LottieFiles.** Eighteen markdown files, ~57 KB, no code or scripts.

Vendor-neutral motion direction for **interactive UI**: a quantification-heavy rule set including a duration-by-element
table, distance→duration multipliers, directional easing tables with concrete cubic-bézier literals, stagger budgets, the
"1/3 rules", overshoot budgets, spring stiffness/damping ranges, a three-layer motion model, and a quality checklist with
severity tiers.

**What transfers to narrated video:** emotional intent first; one motion personality per project; primary/secondary/ambient
layering; decelerate-in / accelerate-out; entrances longer than exits; limiting simultaneous movers; a micro-narrative per
beat; and the concrete easing values.

**What does not:** the duration table itself (80–1,200 ms is interactive-UI scale; a video reveal needs second-scale
reading holds), hover/press/loading-state patterns, and the accessibility guidance aimed at components.

**Conflict to resolve explicitly:** its "Playful" archetype prescribes 10–20 % overshoot, which contradicts house rule R1.
The resolution already adopted by the style schema is correct — an overshoot allowance belongs on a **card**, not in a
global default. **Do not install the skill globally.**

### 19. `morluto/rea` — REJECT

| Field | Finding |
|---|---|
| Artifact type | **MCP server + CLI** (npm `rea-agents`, bin `rea`) plus a bundled agent skill |
| Primary use case | Recover how a feature works **from a shipped, source-less artifact**, with evidence |
| What it can inspect **[read]** | Native binaries (via Hopper/Ghidra/IDA), offline ELF layout, Go/Rust binaries, WASM, EVM bytecode, SQLite, recorded Linux crashes, JavaScript/Electron bundles, live websites, saved network captures, .NET assemblies, Android APKs and devices, Flutter apps, firmware, packet captures, and process behaviour |
| Setup | Node 22.x/24.x/26+ and npm; an MCP registration step (which this audit did **not** perform); optional commercial native engines that the user must license themselves. **No API keys, no bundled model** |
| Does it run LLM calls? | **No.** It is a local tool that returns evidence to whatever agent calls it; the model and its cost belong to the user's agent client |
| Useful for readable source repos? | **No — and it says so itself.** Its own skill instructs: *"Skip REA for ordinary source-repository architecture analysis"* and *"For ordinary analysis of a complete source repository, use normal repository tools"* |
| Would it improve any Video Factory task? | **NO.** This project is local-first over its **own fully readable source** — Python modules, HTML/GSAP compositions, ffprobe QA, pinned registries. There is no shipped source-less binary whose behaviour must be recovered. The one conceivable overlap (peering inside the bundled Chrome/Electron behind the renderer) is unnecessary because the renderer is pinned and source-available |
| Security posture | Bridge auth uses per-session capability tokens over Unix sockets / authenticated loopback. But its own `SECURITY.md` states plainly: **"This is not a sandbox"** — opening an untrusted binary delegates parsing to local providers with the user's permissions, and runtime workflows can affect application state, files, accounts and devices |
| Licence | **MIT** © 2026 morluto, with third-party notices for the optional engines |
| Maintenance | Strong — many commits, active, multi-OS CI, mutation testing, releases. The most professionally maintained repository in this set, which is exactly why the rejection should be read as **out of scope, not low quality** |
| Confidence | **High** for contents; its own scope statement is the decisive evidence |

---

## 3. Licensing and rights matrix

| # | Repo | Code licence | Licence file present | Third-party media / fonts / samples | Paid service or external API | Data leaving the machine | Note for the owner |
|---|---|---|---|---|---|---|---|
| 1 | product-launch-motion | MIT | ✔ | Reference film and example imagery **excluded** by `NOTICE`; GSAP/FFmpeg/music own terms | none | none (setup fetches GSAP) | Cite the doctrine; do not copy the demo media |
| 2 | motion-graphics-skills | MIT | ✔ | sample/brand imagery not assessed | none | none | — |
| 3 | claude-motion-design | MIT | ✔ | Mixkit/Pexels/Unsplash/svgl downloaded, not redistributed; brand logos owned | optional 21st.dev key; optional paid TTS | prompts; **runtime asset downloads** | **Reject** remake mode, meme downloads, generated faces |
| 4 | herk-edit-kit (was student-kit) | **NOASSERTION / Other** | ✔ | AIS brand assets **not licensed for reuse**; showcase videos retain rights | **ElevenLabs, Kie.ai, OpenAI, Gemini, Groq (all optional)** | media upload to Kie.ai if enabled | Do not vendor; paid hooks conflict with house policy |
| 5 | Barty-Bart | MIT + OFL fonts + ISC icons | ✔ | bundled SFX recorded **CC0** in `LICENSES.md`; Mixkit items **never committed** | none required | none | Verify each used sample's row against its source page |
| 6 | animate | MIT | ✔ | style demos are original subjects; reference measurements not redistributed | **optional ElevenLabs**; a local voice + local whisper fallback exists | prompts | Use the API-free parts; the style-grammar cards are the extractable core |
| 7 | claude-motion | MIT | ✔ | none for the sound engine (fully procedural) | none | none | The `sfx/` engine is the licence-clean audio piece |
| 8 | claude-remotion-skill | MIT | ✔ | — | none | none | Rejected on duplication and R1 conflict, not licensing |
| 9 | motionmaxxing | **Apache-2.0 for original work, but bundled GSAP is NOT open source** | ✔ + `NOTICE` | three.js/opentype MIT; Inter OFL | **ElevenLabs**; hosted image generation | **fetches remote URLs; loads generated HTML in Chrome** | Non-open bundled engine + a host product that claims precedence over HyperFrames' house style |
| 10 | onetake | **PolyForm Noncommercial 1.0.0** | ✔ | fonts OFL 1.1 (separately usable) | none in the public skill | none | **Commercial use excluded. Do not copy any file.** Ideas only |
| 11 | aansh-video | MIT | ✔ | bundled `gsap.min.js` under the GreenSock licence | none | none | Technique is small and portable; maintenance is effectively nil |
| 12 | motion | MIT | ✔ | — | optional paid content plan (not a licence gate) | none | A UI library; not a video tool |
| 13 | motion-dev-animations-skill | MIT | ✔ | — | none | none | Wrong domain; stale API version |
| 14 | hyperframes | **Apache-2.0** | ✔ | catalogue media/preset fonts carry their own terms | **optional** hosted render/voices/publish | none for local render | The cleanest licence in the set; upgrade carries breaking changes |
| 15 | remotion | **Remotion License** (two-tier; free ≤3 employees; **$0.01/render, $100/mo min** above) | ✔ | Chrome headless shell downloaded at first run | cloud rendering **costs money** | none locally | A per-render cost with a metering key conflicts with the house policy |
| 16 | remotion-dev/skills | **NONE — 404** | ✘ | — | — | — | **Must not be vendored** |
| 17 | gsap-skills | MIT | ✔ | — | none | none | API reference only |
| 18 | LottieFiles | MIT | ✔ | — | none | none | Numbers are UI-scale; the "Playful" preset conflicts with R1 |

**Generated outputs.** None of the permissive repositories claims ownership of videos you make with them. That is a
statement about *software* licensing and says nothing about third-party media you include.

**Source-media rights are separate.** The ability to ingest or transform footage (repo 4, repo 3's remake mode, repo 1's
legacy scripts) does **not** imply permission to reuse that footage, voice, likeness or music. Any supplied media needs a
recorded rights status, which this project already models in `supplied-audio/1` where `unknown` blocks publication.

**Voice cloning is not adopted anywhere.** Repo 3's paid TTS path and repo 9's hosted voice are the only voice-upload
surfaces in the set; both stay off. Any future provider must satisfy a written consent policy before a single sample is
uploaded.

---

## 4. Cross-cutting observations

1. **Most third-party "motion skill" packs re-teach what the pinned renderer's official skills and this repo's own skills
   already encode** — easing, holds, restraint, deterministic seeking, word sync. Where they add value it is **direction
   and verification method**, not motion technique.
2. **Three genuinely new kinds of thing appear in the set:** (a) *structural variety as a written method* (1, 6);
   (b) *measured audio and sync verification* (1, 5, 9); (c) *negative-control QA discipline* (4). **None requires a new
   renderer.**
3. **Two rights patterns recur:** permissive code with explicitly excluded media (1, 4, 9), and repositories with **no
   licence file at all** (16 — and note that 10 is licensed but noncommercially). Software licence ≠ media licence.
4. **Paid or egress paths hide in optional steps**: ElevenLabs (3, 6, 9), hosted image generation (9, 4), a hosted render
   service (14), and cloud rendering (15). All must stay off by default, and any one of them enabled silently would break
   the "never spend money" rule.
5. **Popularity is not evidence.** Several repositories in this set are days old with a single author and no releases,
   while the most professionally maintained one (19) is out of scope. Star counts and demo GIFs carried no weight here.
6. **Two upstream artifacts assert authority over this project's own rules** — repo 9 states its house style wins over
   HyperFrames', and repo 5's explainer templates carry their own `seek(t)` engine. Both must be read as **one vendor's
   opinion**, not as governance.
7. **The renderer's own repository is under-exploited and is the highest-leverage source in the set** — its post-pin
   release notes contain fixes for defects that plausibly affect this project's output today (a 1080-width pixel defect
   and an FFmpeg 8-era VFR sampling defect, on a machine running FFmpeg 9), and it ships audio FX, beat analysis, a
   registry and a parity harness that are unused.

---

## 5. What this repository set is *not* evidence of

- No repository here is evidence that any style or effect **renders well in this factory**. Only a render on this machine,
  through the existing gates, plus human review, is.
- LLM-judged scores (one repo's "9 of 10 picks", another's "7.57–8.21") and social view counts are **marketing-grade
  evidence** and were not weighted.
- "Works with Claude Code" concerns **skill loading**, not output quality.
- A repository being popular, actively maintained, or well-licensed says nothing about whether its output is good.

---

## 6. Local checkouts verified on this machine

Two of the nineteen were found **checked out locally**, which is stronger evidence than fetched pages because the actual
files can be read. Reviewed read-only; nothing was executed.

| Local path | Upstream identity | State | Review impact |
|---|---|---|---|
| `/Users/kishore/git/animate` | `cth9191/animate` | remote `git@github.com:cth9191/animate`; HEAD `7e5eb56` — **byte-identical to the recorded pin**; contains `plugins/animate/skills/animate/{styles/*/STYLE.md, grammar/FORMATS.md}` | **Strengthens repo 6's ADAPT verdict.** The style contracts and the format grammar were read directly from disk. `styles/cut-paper/STYLE.md` is exactly the "checkable signature features + failure modes" contract that this project's `style/1` cards were modelled on, and `grammar/FORMATS.md` carries the six invariants (including *"silence before the payoff, loudest on the payoff"*) plus per-format measured checks |
| `/Users/kishore/git/rea` | `morluto/rea` | MIT (`package.json` `"license": "MIT"`, `name: rea-agents`, version **6.5.0**); HEAD `1438422df`; full source with `bridge/`, `native/`, `tests/`, `vitest.*.config.ts` and `stryker*.config.mjs`; **not registered as an MCP server** (only `graft` appears in `~/git/.mcp.json`) | **Confirms repo 19's REJECT-as-out-of-scope.** Its own local skill file settles the question: *"Skip REA for ordinary source-repository architecture analysis"* and *"For ordinary analysis of a complete source repository, use normal repository tools and do not run REA readiness or provider commands."* Its `metadata.version` is `42` |

**Also present and relevant** (not on the audited list, recorded so they are not re-discovered as "new"):
`/Users/kishore/git/youtube-agentic-ai-studio` (remote `raunakpatil/youtube-agentic-ai-studio`) — a local channel-research
project whose purpose overlaps this project's `learn.py`/`competitor.py` research path. Its contents were **not** audited
here [not verified].

### A naming collision to record

**The installed `animate` skill is not this `animate` repository.** [read] Every agent config
(`~/.claude/skills/animate`, and the `~/.commandcode`/`~/.cursor` symlinks into `~/.agents/skills/animate`) resolves to a
skill whose frontmatter reads *"Build an animation from scratch … should it animate at all, what purpose, which tool, which
properties, which curve and duration …"* — a **generic UI/component animation authoring** skill, with no provenance to
`cth9191`. Meanwhile `/Users/kishore/git/animate` **is** `cth9191/animate`.

**Consequence:** an instruction to "use the animate skill" in a video-production context will load the **wrong** skill. Any
prompt that wants the procedural-canvas style contracts must name the repository path explicitly. The same caution applies
to the other generic-sounding names in this set (`motion-graphics`, `animate`, `video-edit`), several of which exist both as
upstream repositories and as unrelated installed skills.
