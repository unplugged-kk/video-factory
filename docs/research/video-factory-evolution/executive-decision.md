# H — Executive decision

**Every conclusion is marked [verified] (read or measured this session), [inferred] (my reasoning on top of verified
facts), or [pending] (needs evidence that does not exist yet).**

**Nothing in this audit changed the working system.** HEAD is unchanged at `ec4eb774…`, the stash is empty, the only new
untracked path is `docs/research/video-factory-evolution/`, and the test suite is **green**. The full suite was run once
with bytecode and pytest caching disabled (`PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`) and passed
**548 passed, 1 skipped, 0 failed** [verified].

---

## 1. Which three to five repositories offer the highest value, and exactly what to extract?

Ranked by value per unit of risk, not by repository quality:

1. **`heygen-com/hyperframes` — the renderer already pinned. ADOPT, selectively.** [verified]
   It is the one repository whose *own release notes* contain fixes plausibly affecting this project's shipped pixels: a
   fix for **black last-8-pixel columns at widths like 1080** (this project's vertical width) and a **VFR
   sample-by-timestamp fix for FFmpeg 8** — on a machine running **FFmpeg 9.0.2** — plus a fix for per-frame memory growth.
   It also ships unused and relevant subsystems: an audio FX chain with ducking, beat analysis, a registry, extra output
   formats (MOV/ProRes, WebM with alpha, GIF, PNG sequence, HLS), and a frame-PSNR parity harness deeper than the current 9
   ffprobe checks. **Extract:** the upgrade evaluation (task V-1, in a scratch copy, never in place) and the audio/ducking
   subsystem once audio exists.
2. **`cth9191/animate` — ADAPT: the style contract format.** [verified — the repo is also checked out locally at
   `~/git/animate`, HEAD byte-identical to the recorded pin `7e5eb56`]
   Its `styles/<name>/STYLE.md` is a *written contract*: one governing rule, measured palette values, motion habits, a
   ten-item frame checklist and a kit API. Its `grammar/FORMATS.md` supplies six invariants and per-format measured
   checks. **This project's `style/1` cards already derive from it** (T2 is done, verified). **Extract:** nothing more now;
   use it to write better cards, and mine the invariant *"silence before the payoff, loudest on the payoff"* for a
   report-only check.
3. **`Barty-Bart/motion-graphics` — ADAPT: the only measured, licence-aware audio method.** [verified]
   It is the only upstream with real numbers for audio plus a licence-clean sample set: ≈−16 LUFS integrated, true peak
   < −4 dBFS, bed −12 dB under SFX, duck 8–12 dB under voice, and a beat grid checked against kick drums. This project has
   **no music, SFX or ducking at all**. **Extract:** the method and its targets (task A/T8), and its honesty that SRT/VTT
   word times are estimates ±0.2 s — which matches this project's `timing_trust: asr-derived-unverified`.
4. **`Priyanshsharma21/aansh-video` — ADAPT: the animated host, which is a documented gap.** [verified in code]
   A ~20-line audio-amplitude mouth envelope plus script-forced caption alignment gives the "lip-synced cartoon host" this
   project lists as **NOT built**. Be explicit that it is amplitude-driven, not viseme-accurate, and that the repo has
   **2 commits on one day** — treat it as a technique, never a dependency.
5. **`Tejashmakwana/motionmaxxing` — REFERENCE: exactly two deterministic measurements this project cannot make.** [verified]
   An **audio cut-sync audit** (share of cuts within ±80 ms of an onset) and a **DOM-level "page-chrome" lint** family — a
   frame-based audit cannot see DOM geometry at `t` and `t+0.1 s`. **Re-implement in-house** (task V-3). Do **not** vendor
   it: its bundled animation engine is **not open source**, and the artifact is a funnel for a commercial product that
   asserts its house style *outranks* this renderer's.

**Runner-up worth naming:** `charlie947/motion-graphics-skills` for one small thing — a ready-made **skill-hygiene
validator**, genuinely useful in a repo with hundreds of installed skills and hash-verified upstream ones. [verified]

---

## 2. Which repositories add little or nothing, because the factory already has the capability?

| Repository | Why it adds little | Mark |
|---|---|---|
| `LottieFiles/motion-design-skill` | Its rules are **UI-scale** (80–1,200 ms; hover/press states). `explainer-motion-craft` R1–R6 plus the 70-entry technique registry already cover the transferable part, and its "Playful" 10–20 % overshoot **conflicts with R1** | [verified] |
| `greensock/gsap-skills` | Same engine already in use; the pinned HyperFrames animation/keyframe skills already encode the seek-safe GSAP subset. Worth only a small API-correctness checklist | [verified] |
| `motiondivision/motion` | A UI library, not a video tool; the renderer has **no Motion adapter**, and spring/stagger already exist through GSAP | [verified] |
| `howseen-ai/claude-motion-design` and `whaleyxbt/claude-motion` | Their best ideas are **already absorbed**: pops/flash detection exists in `motion_audit.py`; the shared timeline and labelled sheet were written independently into `timeline.py`/`sheet.py`. Remaining value is small | [verified] |
| `AbubakrChan/product-launch-motion` | Excellent direction doctrine, and its structural-axes method is **already realised** in the six-axis `style/1` schema. Reference the prose; install nothing | [verified] |
| `nateherkai/hyperframes-student-kit` (**now `herk-edit-kit`**) | Highest overlap of the set — four of its skills are verbatim copies of the HyperFrames skills already pinned. Its real value is one sentence about negative-control calibration and a QA gate table | [verified] |
| `remotion-dev/remotion`, `remotion-dev/skills`, `199-biotechnologies/motion-dev-animations-skill` | No demonstrated limitation of the current renderer; a licence tier that bills per render; an unlicensed mirror; and a stale React-UI skill respectively | [verified] |
| `feitangyuan/onetake` | Technically closest to this project's renderer, but **its licence affirmatively excludes commercial use** | [verified] |
| `morluto/rea` | Solves the inverse problem — see §3 | [verified] |

**Three of the nineteen are near-duplicates of each other** (repos 1, 3, 5 share one `seek(t)` + FFmpeg `tmix` + "SFX by
measured peak" method, and cross-credit each other). Auditing them as four independent discoveries would overstate the
diversity of this ecosystem. [verified]

---

## 3. What should never be installed or used in the production path, and why?

| Never | Why |
|---|---|
| **`feitangyuan/onetake` code (any file)** | **PolyForm Noncommercial 1.0.0**, read in full: the grant covers "any permitted purpose" and the only permitted class is **Noncommercial**; sublicensing is barred. It is *affirmatively* excluded for a monetized pipeline, not merely silent. Ideas only | [verified] |
| **`remotion-dev/skills`** | **No licence at all** — `contents/LICENSE` returns 404, API `license: null`. Must not be vendored |
| **Remotion as the production renderer** | Its licence is not OSI, and above three employees it costs **$0.01 per render with a $100/month minimum** plus a metering key — a direct conflict with "never spend money", for a capability the current renderer already provides |
| **`motionmaxxing`'s bundled runtime, and its GSAP** | Its `NOTICE` states the bundled GSAP "is NOT an open-source license" and that its Apache grant "does not grant you any rights in GSAP" |
| **Any `npx … skills update` / `@latest` line from an upstream skill** | 10 of 18 candidate skills inside the pinned renderer tag open by running a network update; the repo's own T1 review flagged these as needing to be blocked before adoption |
| **Paid paths anywhere** | ElevenLabs (3 repos), hosted image generation, a hosted render service, cloud rendering. Each is off by default and one silent enable breaks a house rule |
| **`media-use` / `faceless-explainer` (HeyGen sign-in)** | A service dependency; excluded pending an owner decision | 
| **`kie.mjs`, `object-separation`, remake mode, generated faces, meme downloads** | Paid, heavy, or a rights/likeness risk. "Ability to ingest ÷ right to reuse" |
| **REA in the render path** | See below — it is a good tool aimed at a different problem |
| **A workflow engine, message broker, second queue, or unowned detached workers** | The SQLite queue, per-job process model, manifest and `flock` already exist and are sufficient |
| **A second animation runtime inside compositions** | Enlarges the determinism-audit surface for no demonstrated gain |

**On REA specifically.** [verified] It is checked out locally at `~/git/rea` (MIT, version 6.5.0, HEAD `1438422df`, with
tests, CI, and mutation-test configs) — a genuinely well-maintained tool, and **not registered as an MCP server** in this
machine's configuration. Its own local skill file is decisive about scope: *"Skip REA for ordinary source-repository
architecture analysis"* and *"For ordinary analysis of a complete source repository, use normal repository tools and do not
run REA readiness or provider commands."* This project is local-first over its **own fully readable source**, so REA has no
task here. **It is out of scope for this pipeline, not low quality** — and its own `SECURITY.md` states plainly that it is
**not a sandbox** and that opening an untrusted binary delegates analysis to local providers with the user's permissions,
which is a reason to keep it away from any automated path regardless.

**A naming collision worth recording.** [verified] `~/git/animate` is **`cth9191/animate`** (the procedural canvas animation
skill). But the installed `animate` skill in every agent config is a **different** skill — a generic UI/component animation
authoring skill (`"should it animate at all, what purpose, which tool…"`). An instruction to "use the animate skill" in a
video context would therefore load the **wrong** skill. Name the repo explicitly in any prompt rather than relying on the
skill name.

---

## 4. What would materially improve the videos' visual quality most efficiently?

Ranked by expected effect per unit of risk: [inferred, on verified facts]

1. **Validate one style, end to end, on this machine.** The creative layer is structurally complete but has **zero render
   evidence**: 0 of 76 design-library entries and 0 of 3 style cards are validated here. Until one card has a real render
   recording as evidence, every style claim is aspirational and `status: validated` is unreachable. This is the highest-value
   work and it is cheap — one bake-off, already specified as T9.
2. **The style-frame checkpoint (T4).** The last cheap moment to discover a direction does not work, before an expensive
   render. Caveat: it depends on a labelled sheet, and `sheet.py` **fails closed on this Mac** because the installed FFmpeg
   has no `drawtext`; use `./contentos.sh preview … --sheet` and **not** `--allow-unlabelled`. [verified]
3. **Audio design (method from repo 5, then T7/T8).** This project has none — no music, no SFX, no ducking. A measured,
   ducked cue track is the largest *unexplored* improvement, and the licence-clean procedural option carries no samples.
4. **The two checks the current audit cannot make (V-3):** audio cut-sync and DOM page-chrome.
5. **Renderer defect fixes (V-1).** Verify whether the post-pin fixes for 1080-width columns and FFmpeg-8-era VFR sampling
   actually affect this output. If they do, this is the single most *consequential* item in the whole audit; if they do not,
   "not affected" is a valuable result. **It must be evaluated in a scratch copy — the upgrade is breaking.** [verified]

**A hard limit on this answer:** nothing above can claim a quality improvement. The only honest statement is that the
creative machinery exists, is deterministic, and is unevidenced. Quality is a subjective judgement that only the bake-off
plus an independent reviewer plus the owner can inform. [inferred]

---

## 5. What should the creative director consider before choosing a style?

In this order, and the order matters because it is a filter, not a score: [inferred, implementations verified]

1. **Hard constraints first — filter, never score.** Factual accuracy and labelled illustrative data; legibility and
   accessibility; clean rights (`unknown` blocks publication, already enforced); the six R1–R6 motion rules; platform
   length and aspect budgets. A direction that breaks any of these is **removed**, and **a creative score may never override
   a hard failure.**
2. **What the viewer's job is** — understand a system, feel a story, evaluate a claim, learn a procedure, or see a thing —
   plus **prior knowledge** and **factual density**. A high-density explainer for a low-prior-knowledge audience is filtered
   out before scoring; that is why `audience.prior_knowledge` and `visual_referents` are the two brief fields most worth
   adding.
3. **Whether visual referents exist.** "No referents" rules out photographic modes outright.
4. **The learning objective** (or the entertainment goal — exactly one), which is what the "explain why this technique was
   chosen" requirement points at.
5. **The hook, chosen from the material with rejected alternatives recorded.** One primary hook; a hook requiring
   word-accurate timing is **ineligible** while `timing_trust` is `asr-derived-unverified`.
6. **Structural novelty against recent videos** — ≥2 of 6 structural axes differing from the previous video, no 6-axis
   combination repeated inside the window. **Palette is deliberately not an input**, and each of the top three candidates
   must be ≥3-axes distinct from the others, so a recolour cannot pass as a new direction.
7. **Whether the required capability is actually installed** — and whether the card is `validated` **here**. An unvalidated
   card requires explicit human approval (the `requires_explicit_approval` flag).
8. **Sound strategy**, limited today to narration-led or silent, because music-led is refused while beat analysis does not
   exist.
9. **Trade-offs stated, and the reason the rejected directions lost** — enforced in code by a mandatory rejection reason.

And the governing rule: **never sacrifice accuracy, accessibility, clarity or audience fit to maximise novelty.**
Consistency inside a video and across a series is desirable; accidental sameness between unrelated videos is not.

---

## 6. What is the actual concurrency bottleneck today?

**Not the pipeline being "one command, one job".** The real constraints, established from code: [verified]

1. **The renderer is already internally parallel, and it has a documented ceiling on this machine's RAM.** Each of its
   workers is a **separate Chrome process at ~256 MB**; auto-sizing is bounded by CPU, RAM, **the V8 heap** and frame count;
   its own `--max-concurrent-renders` default is **2**; and its upstream notes record *"field OOM, 0.7.66 on **24GB**:
   auto-picked 6 workers blew Node's default ~4GB heap"* — this machine has **24 GB**. One capture mode even **forces 1
   worker** because canvas draw is non-deterministic across concurrent browsers. So a single auto render is already several
   processes, and multiplying renders multiplies that.
2. **The ContentForge v1 worker is single-lane by explicit design** — `tick()` returns immediately if anything is in
   `work/`, claims are directory **moves**, and a heartbeat file permits only one worker per workspace. Intentional.
3. **One SQLite ledger for the whole workspace, with no `busy_timeout` set** — every stage of every job writes to it.
4. **A hung job holds a pool slot forever** — `queue._run`'s subprocess has **no timeout and no signal handling**, so
   effective concurrency silently falls below the configured value. This is very likely why "one video at a time" is what
   gets observed.
5. **One shared MPT Docker container** for the whole workspace.
6. **No per-job run lock at all** — nothing prevents two runs of the same `content_id` from interleaving writes into
   `audio/`, `project/` and `video.mp4`. Isolation is the missing foundation, not throughput.
7. **The Python pool size** is whatever `--concurrency` says (default 2).

Also [verified]: `VIDEO_FACTORY_CACHE_DIR` is declared and printed but **no code writes to it**, and the parallel-router
flag is safe only for sequential renders.

---

## 7. What is the likely safe first concurrency target, and what measurements are needed?

**Answer: 2 concurrent renders and a small `max_active_jobs`, as a conservative floor — and the honest position is that
this is an estimate, not a finding.** [inferred, pending measurement]

The floor is not arbitrary: **2 is the renderer's own documented default**, each worker is ~256 MB, and the renderer already
parallelises internally, so two render *processes* is closer to serial than it sounds. Nothing here supports a claim that
5 or 10 simultaneous renders are safe on 24 GB — and it would be wrong to chase a round number by degrading quality or
destabilising the machine.

Crucially, **N concurrent renders is not N concurrent videos.** The throughput lever is **stage pipelining**: while two jobs
render, others can be in voice, compose, QA or export. A 5–10 videos/hour target may well be reachable at a render
concurrency of 2 or 3. That hypothesis is exactly what the benchmark tests.

**Nothing may be raised without measuring:** (a) per-render peak RSS and CPU time — **not documented anywhere**; (b) whether
`voice` (ONNX) or `qa` (FFmpeg decode, currently no timeout) binds *before* `render` does; (c) whether two simultaneous
renders are byte-reproducible given a shared global frame cache and an unlocked `~/.hyperframes/config.json`; (d) disk
growth of the global frame-extract cache; (e) thermal behaviour under sustained load; (f) interactive responsiveness while
rendering. Task C-9, with explicit owner approval, is the measurement — and "unsafe above 2" is a valid result.

**[pending] This is the single largest evidence gap in the entire audit.** Every concurrency number above is a conservative
floor derived from documented behaviour, not a measurement.

---

## 8. How should the system scale beyond ten concurrent jobs?

**It should not scale by renders on this machine.** [inferred, on verified renderer facts] Ten simultaneous auto renders on a
24 GB box is not a tuning problem; it is resource exhaustion, and the renderer's own OOM note at exactly 24 GB is the
warning. Beyond the measured saturation point:

1. **Pipeline the stages** — a bounded number of render slots with higher per-stage limits for the cheap stages, so jobs
   overlap without overlapping renders. This is a scheduling change, not new hardware.
2. **Serialize renders, parallelise everything else** — if measurement shows renders saturate first, the correct answer is
   a render *queue* with everything upstream running concurrently, plus the `export` I/O cap at 1.
3. **Raise per-render workers deliberately** before raising the render count — with an explicit `--workers N` and a lifted
   Node heap, rather than two processes each guessing `auto`.
4. **Cross-machine only if the resource profile changes** — the renderer supports cloud/Lambda paths, but those cost money
   and are forbidden by house rules, so this is not a lever today.
5. **Any future expansion must keep submission unbounded and running bounded**, keep per-job isolation, and keep the
   automatic-reduction signal (thermal or memory pressure) working. **Never** add a broker, a workflow engine, or detached
   workers to get there.

---

## 9. What is required for multi-niche and multi-platform expansion?

**One separation and one kind of research.** [inferred, on verified state]

- **Separate niche strategy from platform packaging.** A niche decides *what the video is* (audience, fact-check rules,
  narrative shapes, suitable creative families, rights policy); a platform decides *how it is packaged* (duration, aspect,
  opening hook, caption treatment, pacing, packaging text). One approved concept may need an X cut as well as a ~3 min
  master — and the correct response is **two render manifests over one concept**, each independently QA'd, never one
  manifest with conditional logic. The existing code already respects this boundary (`platforms.py` knows nothing about
  visual language), and it must stay that way.
- **Build niches as data, not code.** One `niche/1` file validated in the `style/1` style — a status that **requires**
  evidence, a named reviewer, and refusal of any requirement that is not an `installed` capability. A niche should be
  `validated` only with real render evidence on this machine. The existing `content_type` vocabulary means no new code path.
- **Platforms need first-party evidence, and today two rows have only third-party evidence** (LinkedIn, TikTok), two
  formats are needed where one is currently assumed (a ≤140 s X cut vs a ~3 min master), and safe-zone numbers are
  **hard-coded heuristics explicitly labelled "NOT published platform specs"** and should move to config marked
  `unverified`. [verified]
- **What must be researched before any adapter:** automation permission and review paths, duplicate-content rules,
  monetisation eligibility, AI-disclosure obligations, posting costs, music/font licensing for monetised video, and dated
  safe-zone geometry — each from a **first-party** source with an access date. [pending]
- **Two niches are blocked before they are candidates:** anything presenting health, legal, financial or political advice
  as an expert persona is already prohibited by this project's own rules, and **Odia/Hindi voice output is not built**, so a
  niche whose audience needs a language the pipeline cannot speak is not a candidate yet. [verified]

---

## 10. What is the smallest high-value next task, now that the prerequisites are satisfied?

**The prerequisites *are* satisfied.** [verified] The owner **cleared** the ContentForge gate on 2026-10-12 (the run log
records: "ContentForge is a separate repo, not a prerequisite for these Video Factory changes. Gate CLEARED"), and
ContentForge is a live system that owns decisions, research and publication — **nothing in this roadmap needs a
ContentForge change, and no new direct factory→ContentForge call may be introduced.**

Given the standing instruction that the system is working and must not be broken:

**The smallest high-value next task is a documentation correction — task R-2.** Correct four statements that this audit
proved false, each with a file:line citation: G3/G6 marked "not built" though both exist; the safe-zone entry omitting that
it has **no production caller**; two files still saying implementation is blocked on ContentForge; and the claim that Track A
uses the proportional caption index when it now calls `align_words`. It touches only `docs/`, changes no behaviour, cannot
break a render, and stops the next agent from acting on a false premise. **Effort: S.** [verified]

**The smallest high-value *code* task is C-2** — set a `busy_timeout` on the ledger and keep write transactions short. It is
one of the few changes that is strictly beneficial even at concurrency 1, removes the most likely spurious failure in a
shared-workspace design, adds no parallelism, and cannot affect a render. **Effort: S.** [inferred]

**The highest-value task overall is completing the existing plan's T4 (the style-frame checkpoint) and then T9 (the
bake-off)** — because the creative layer is structurally finished and completely unevidenced. That is the work that turns
"we have a creative director" into "we have one validated look". [inferred]

---

## Recommendation

# **PROCEED CONDITIONALLY**

Nothing here justifies a stop, and nothing here justifies a broad push. Every verified problem is either a documentation
error, a missing safeguard on the existing serial path, or an unevidenced creative layer — and every proposed fix is
additive, removable by deleting a file, and incapable of touching a render unless a task says so.

**Conditions:**

1. **Do not touch the working path until the owner disposes of the uncommitted WIP** (task R-1). The suite is green *with*
   that WIP; it is the one thing that could be lost by careless work, and six files are in a no-go zone until it is settled.
2. **One task per session, each verified by a different session.** The plan already requires this; keep it. The implementer
   never grades its own work.
3. **No renderer change, no pin change, and no `config/*.yaml` change** except inside the V-1 evaluation, which runs in a
   scratch copy and whose deliverable is a memo.
4. **No concurrency number is set before C-9 measures one.** Until then, isolation work (C-1 to C-3) proceeds and nothing
   else does.
5. **No speculation about quality.** The creative layer cannot claim a look is better; only a bake-off with an independent
   reviewer and the owner can inform that.

---

## Blockers

| Blocker | Owner of the decision | Blocks |
|---|---|---|
| Disposition of the uncommitted WIP (9 modified, 10 untracked) | Owner | R-4, V-1, C-1, X-1, and any task touching `pipeline.py`, `storage.py`, `visual_gate.py`, `export.py`, `supplied_audio.py` |
| Approval to run renders (T9, V-1, V-2, C-9) | Owner | All of Tier 2 and Tier 4 |
| Whether to pursue the renderer upgrade at all — it is explicitly out of scope of the existing plan | Owner | V-1 |
| Whether the safe-zone check becomes a QA step or stays a manual tool | Owner | R-4 |
| Whether to add audio at all (music/SFX/ducking is currently absent by design) | Owner | T7, T8, and the adopted method from repo 5 |
| First-party platform policy research | Research, then owner | X-3 and any publishing adapter |
| Independent verifier sessions | Owner schedules | Every task's acceptance |

---

## Unresolved questions

1. **What is the safe concurrency number?** Unmeasured. Doc D §6 defines the experiment; nothing else can answer it.
2. **Do the renderer's post-pin fixes actually affect this output?** The symptoms are *plausibly* present (1080-wide output,
   FFmpeg 9) but **not reproduced**. This is a hypothesis until V-1 runs. [pending]
3. **Is `voice` or `qa` the binding stage before `render`?** If `voice` binds first, the render cap is the wrong knob.
4. **Are two simultaneous renders byte-reproducible**, given a shared global frame cache and an unlocked config file?
5. **What was `VIDEO_FACTORY_CACHE_DIR` reserved for?** Declared, printed, never written.
6. **Did the earlier "1 known failing test" actually exist, or was it mis-transcribed?** The suite is now fully green, and
   the old allowance should not be carried forward.
7. **What is the `mpt` lane's real concurrency behaviour?** Its task store is outside this repo and is unverified.
8. **Is the ContentForge exchange worker intended to run alongside the Python queue against the same workspace?** Both
   designs were read; they were never observed together.
9. **Which three of the ten candidate niches are actually wanted?** The framework is proposed; the choice is the owner's.

---

## The exact next approved task

**Task R-2 — correct the four verified stale statements, documentation only.**

Concretely: `docs/video-intelligence/04-visual-reliability-gate.md:351` (G3 and G6 exist), `06-video-factory-target-architecture.md:275`
(safe-zone has no production caller), `docs/research/motion-design-integration/04-prioritized-roadmap.md:3` and
`00-executive-summary.md:13` (the ContentForge gate is cleared), and any remaining claim that Track A captions use the
proportional index (`pipeline.py:130-138` replaced it). Each new line must cite the code path that contradicts the old one.

**Why this one:** it is the smallest change available, it touches no code, it cannot affect a render or a test, it is fully
reversible, and it removes the false premises that would otherwise misdirect every subsequent session — including two
premises that currently tell future agents the opposite of the truth about a cleared gate and about features that already
exist.

Run it in a fresh session. Then verify it in a **different** session. Then pick a single task from Tier 1 and do the same.
