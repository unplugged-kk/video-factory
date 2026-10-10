# 07 - Motion-graphics skills audit (Video Factory v2)

Audit date / source access date: **2026-10-10**. Scope: nine upstream repositories named in the task brief (plus the three sibling repos that `iart-ai/motion-skills` points to). Method: shallow clones read from disk, files opened, scripts run where they were runnable, plus one controlled comparison on a copy of Pilot 001. Nothing was published, no credentials were touched, nothing was installed globally. The separate file list and test results are in `08-motion-skills-implementation-report.md`.

> Naming note: `07-guides-vs-implementation.md` (earlier phase) already uses the `07-` prefix. The brief fixed this file's name, so both stay; this one is the audit, the other is the guide comparison.

## 1. Executive recommendation

1. **Keep HyperFrames as the default renderer. No framework change.** Nothing in this audit demonstrates that Remotion or Motion Canvas would give a better result for our formats. Both were studied for design rules only and neither was rendered.
2. **The current HyperFrames *workflow* is sufficient to render, but not sufficient to direct or to catch its own mistakes.** The controlled test found concrete defects in our own Pilot 001 build that no existing gate caught: 5 overshoot (`back.out`) eases on cards, a camera that snaps at scene cuts, and scene-long camera drift that is flagged as "paced-slow" by the upstream animation map. All pass `hyperframes lint` and `check`.
3. **Adopt, pinned and hash-verified, three official HyperFrames skills** (`hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes`) from tag `v0.8.114`, the same version our renderer is pinned to. They carry the composition contract, the motion rules and the `animation-map.mjs` tool.
4. **Add two small factory skills** instead of importing more: `explainer-motion-craft` (the rules that were demonstrated to matter, ported from the upstream doctrine) and `explainer-visual-qa` (an independent critic pass plus measurable gates). Add a small, tested Python module for the measurements (`contentos/production/motion_audit.py`, `critic.py`) and a reproducible comparison harness (`scripts/motion_compare.py`).
5. **Do not adopt:** Remotion, Motion Canvas, Bang Motion's runtime, any `install.sh`/`curl | bash` path, the HeyGen-audio / ElevenLabs / Kie.ai / Higgsfield-bridge paths, and the `haidrrrry` skill (conflicts with our doctrine). See section 9.
6. **What the experiment does and does not prove.** It proves, with numbers, that variant B removes the overshoot eases, 4 isolated one-frame "pops" per format, and cuts file size by 42% (landscape) / 34% (portrait) with identical audio, captions, duration, resolution, fps and no lint/check regressions. It does **not** prove variant B looks better to a viewer. That needs a human A/B (section 10.4). It also introduced a mild genuine downside: more static time (see 10.3).

Decisions needed from you are listed in section 12 (two small ones; neither blocks anything).

## 2. Verification method and confidence

| Level | Meaning in this document |
|---|---|
| **Verified** | I opened the file or ran the command in this session. |
| **Read, not run** | I read the files but did not execute them. |
| **Listed only** | I only saw the directory listing / README; no judgement beyond existence and license. |
| **Assumption** | Stated explicitly as such. |

Primary sources are the repositories themselves, cloned from GitHub on 2026-10-10 (commit hashes below). Blog posts, stars and README claims were not used as evidence of quality. Where a README makes a claim I could not test, it is marked.

## 3. Repository inventory (verified sources)

| # | Repo | Default branch | Commit read (date) | License (file read) | What it actually is | Maintained? | Confidence |
|---|---|---|---|---|---|---|---|
| 1 | `heygen-com/hyperframes` | `main` | `bb9e507e` (2026-10-10); renderer pin tag `v0.8.114` = `01c6f600` (2026-10-02) | Apache-2.0 (`LICENSE`) | The renderer itself (monorepo: `packages/*`, `registry/`) **plus** 21 agent skills in `skills/` | Very active (daily commits) | High (skills read, `animation-map.mjs` run) |
| 2 | `Liamrjohnston/remotion-motion-graphics-skill` | `main` | `b860c792` (2026-07-23), 14 commits | MIT, (c) 2026 Promptible (`LICENSE`) | 4 Remotion skills (`motion-graphics`, `cinematic-camera`, `terminal-inserts`, `article-highlights`), reference videos, a gate script, `install.sh` | Low-moderate (last commit ~11 weeks old) | High for skills, medium for scripts (read, not run; needs Remotion) |
| 3 | `haidrrrry/claude-remotion-skill` | `main` | `1dcbe5e3` (2026-08-12) | MIT (`LICENSE`) | One Remotion skill (`remotion-motion-graphics/SKILL.md` + 2 references), demo media, `build-skill.sh`, example SFX/track generator scripts | Low | High (read fully) |
| 4 | `apoorvlathey/motion-canvas-skills` | `main` | `5cdaf357` (2026-01-26) | MIT (`LICENSE`) | One Motion Canvas skill (`SKILL.md`, `references/api-reference.md`, `references/patterns.md`) | Stale (9 months) | High |
| 5 | `VideoZero/skills` | `main` | `670ff96a` (2026-10-03) | Apache-2.0 (`LICENSE`) | Three skills: `animation-basics`, `motion-canvas`, `motion-canvas-agent`; 17 Motion Canvas reference files | Active | High for `motion-canvas/`, medium for `animation-basics` (generic) |
| 6 | `Wismio/hyperframes-video-create` | `main` | `b1afdb1d` (2026-09-08) | MIT (c) 2026 Nate Herk (`LICENSE`) **plus** `THIRD_PARTY_NOTICES.md`: bundled HyperFrames skills are Apache-2.0; "imported pipeline resources" under `licenses/PIPELINE-USE-PERMISSION.txt`; example media/brand assets carry **no** rights grant | A "student kit": ~15 HyperFrames skills, `style-library/`, `style-templates/`, validators, example videos. Provenance: the notice names Nate Herk as the original author; this repo appears to be a derivative/mirror of his student kit (origin not independently verified) | Moderate | High for skills/scripts read; the extra permission file was **not** reviewed in full - see 7 |
| 7 | `RFTaurus/motion-skill` ("Bang Motion") | `main` | `c1aa65e9` (2026-09-15) | MIT (c) 2026 Bang Tutorial (`LICENSE`) | One skill + references (`anti-ppt.md`, `techniques.md`, `explainer.md`, `architecture.md`, `ae-bridge-higgsfield.md`...), a local server (`scripts/serve.py`) and frame tools (`snap.mjs`, `export-frames.mjs`) | Active | Medium-high (read; not run) |
| 8 | `iart-ai/motion-skills` | **`master`** | `4a982237` (2026-09-30) | MIT (`LICENSE`) | **An index/showcase repo**: `README.md`, `showcase.html/gif`, `tools/verify`, `tools/showcase-to-gif.mjs`. The skills live in sibling repos `iart-ai/motion-design-skills` (`3c129f76`, 2026-06-22) and `iart-ai/explainer-video-skills` (`3e2d4117`, 2026-06-22), both MIT | Low (sibling repos 3.5 months old) | **Low-medium: sibling skill directories were listed (names only), SKILL.md bodies were not read in depth.** I do not rate them on description alone |
| 9 | `remotion-dev/skills` | `main` | `32b241b9` (2026-10-07), 30 commits | **No LICENSE file in the repo; `package.json` (`@remotion/skills` 4.0.534) has no license field** - license not verifiable from this repo | Official Remotion agent skills: `remotion-best-practices`, `-captions`, `-create`, `-docs`, `-interactivity`, `-maps`, `-markup`, `-multimedia`, `-render`, `-saas`, `-studio`, `-upgrade` (many duplicated map-technique trees) | Very active | High for structure; Remotion-specific |

All nine exist and were reachable. None had to be reported as unavailable. The brief's repository #8 does not contain skills itself (verified); that was the one surprise.

Framework licensing carried over from Milestone A (`04-licensing-matrix.md`): Remotion has a free tier with an employee-count limit and a company licence above it; **re-verify at remotion.dev before any use**, since this was not re-checked today and the 5.0 changes noted earlier are unconfirmed.

## 4. Evidence of reading, and its limits

Only claims in this document that cite a file path rest on a file I opened. Depth varied, and I am stating it rather than implying every file was read line by line:

- **Read for substance (their rules are quoted or ported below):** HyperFrames `faceless-explainer/references/motion-language.md`, `hyperframes-studio/SKILL.md` (safe zones), `hyperframes-core`, `hyperframes-animation` (`SKILL.md`, `scripts/animation-map*.mjs`, `package-loader.mjs`), `hyperframes-keyframes/SKILL.md`; Liamrjohnston `cinematic-camera`, `terminal-inserts`, `motion-graphics/references/visual-critic.md`; haidrrrry `SKILL.md` + `references/design-rules.md`; Wismio `MOTION_PHILOSOPHY.md`, `video-storytelling`, `hyperframes-video-beats`, `THIRD_PARTY_NOTICES.md`; Bang Motion `SKILL.md`, `references/anti-ppt.md`, `references/ae-bridge-higgsfield.md`.
- **Skimmed (structure, headings, scripts' option handling), not studied line by line:** the remaining HyperFrames creation-workflow skills (`faceless-explainer` scripts, `music-to-video`, `talking-head-recut`, `motion-graphics` agents), VideoZero / apoorvlathey Motion Canvas references, `remotion-dev/skills`, Wismio `short-form-edit` and `make-a-video`.
- **Listed only:** `iart-ai` sibling skill bodies; Remotion map technique trees; binary example media in every repo.
- **Executed:** HyperFrames `animation-map.mjs` (pinned, sha256-checked) and our own tooling. **No third-party installer or script other than `animation-map.mjs` was run.** `install.sh`, `build-skill.sh`, `serve.py` and the media scripts were read or only listed.

Where a matrix row below rests on a skimmed or listed source, the confidence column says so.

## 5. Capability matrix (15 dimensions)

Paths are relative to the repository root. "HF" = `heygen-com/hyperframes` at tag `v0.8.114`, under `skills/`. "VF has" is what Video Factory / contentos already provides, verified in code or in the Pilot. Classification codes: **DR** directly reusable skill, **DP** design principles for an existing skill, **TC** template/component, **ST** standalone tool, **FW** alternative framework, **DUP** duplicate, **INC** incompatible/unsuitable.

| # | Dimension | VF has | Best upstream implementation (exact files) | Class | Genuinely missing in VF | Source confidence |
|---|---|---|---|---|---|---|
| 1 | Storyboard and scene decomposition | `contentos/production/sceneplan.py`, `scene-plan.json` per project, `sceneplan/1` contract (05-architecture) | HF `hyperframes-creative/references/{storyboard-recipe,story-spine,beat-direction}.md`; HF `faceless-explainer/references/story-design.md`, `scripts/lib/storyboard.mjs`; Wismio `.agents/skills/make-a-video/references/storyboard-template.md` | DP | Nothing blocking. A "story spine" check (hook, tension, payoff per scene) is optional | Medium (skimmed) |
| 2 | Visual storytelling and continuity | One `#stage` camera wrapper in the Pilot builder | Liamrjohnston `skills/cinematic-camera/SKILL.md` (one connected world, shared camera, "no disconnected panels in a void"); Wismio `.agents/skills/video-storytelling/SKILL.md`; Bang Motion `references/anti-ppt.md` (structural bans on slideshow layouts) | DP | The continuity rules were not written down. Now captured as R3/R4 in `explainer-motion-craft` | High |
| 3 | Kinetic typography and animated captions | Word-timed caption band from `align.py` + `word-timings.json`; contrast checked by `hyperframes check` | HF `hyperframes-animation/rules/{kinetic-beat-slam,asr-keyword-glow,discrete-text-sequence,gradient-text-sweep}.md`, `blueprints/kinetic-type-beats.md`; HF `hyperframes-creative/references/typography.md`; Wismio `.agents/skills/hyperframes/references/{captions,typography}.md` | TC / DR | Caption *styles* beyond one house style (not needed for the pilot) | Medium |
| 4 | Motion principles, easing, timing, choreography | `power3`/`power2` eases in the builder, plus 5 `back.out` (defect) | HF `faceless-explainer/references/motion-language.md` (smooth `power3` over bouncy; sequential reveal timed to VO; velocity-matched cuts; seek-safe rules); HF `hyperframes-creative/references/motion-principles.md`; HF `hyperframes-animation/{techniques.md,rules-index.md}`; Wismio `MOTION_PHILOSOPHY.md` | **DR** (pinned skills) + DP | Written house rules and a way to measure them: added (`explainer-motion-craft`, `motion_audit.py`) | High |
| 5 | Camera movement and cinematic transitions | Stage zoom/pan per scene; hard cuts | Liamrjohnston `skills/cinematic-camera/SKILL.md`; HF `hyperframes-animation/transitions/*` (13 files, `TRANSITION-REGISTRY.md`), `rules/{multi-phase-camera,depth-of-field-blur,viewport-change}.md`, `blueprints/camera-journey.md`; Bang Motion `references/techniques.md` (shot sizes) | DR (HF) + DP (others) | Camera snap at cuts (measured). Fixed by rule R3 in variant B; builder not yet changed in contentos | High |
| 6 | Data visualization and explanatory diagrams | Hand-built SVG/HTML cards in the Pilot | HF `hyperframes-animation/rules/{chart-scrub-readout,stat-bars-and-fills,counting-dynamic-scale,svg-path-draw}.md`, `blueprints/dataviz-countup.md`, `blueprints/comparison-split.md`; HF `registry/blocks/` (50+ installable blocks, e.g. `data-chart`) | TC | A reusable chart/diagram component set. Registry blocks are the candidate (not installed; needs a separate review of each block) | Medium |
| 7 | Terminal recordings, code demos, technical explainers | Hand-built scene cards in the Pilot; no terminal-specific component or authenticity checklist | Liamrjohnston `skills/terminal-inserts/SKILL.md` (authenticity rules: real prompt, real timing, no fake output); HF `hyperframes-animation/blueprints/{typewriter-reveal,agent-progress-theater,cursor-ui-demo}.md` | DP / TC | Authenticity checklist for terminal inserts (not ported yet; low effort, noted in 8) | Medium-high |
| 8 | Audio, word and beat synchronization | Kokoro audio + whisper.cpp word timings + `align.py` (script-to-ASR match); music bed synthesized locally | HF `hyperframes-creative/references/{beat-direction,audio-reactive}.md`, `scripts/extract-audio-data.py`; HF `music-to-video/references/*`; Wismio `.agents/skills/hyperframes-video-beats/SKILL.md` (anchor-word window about -0.2 to +1.8 s) | DP | **A post-build validator** that checks, on the *built* composition, that each visual beat lands within a window of its anchor word. Not built (see 8) | Medium |
| 9 | Music videos and lyric animation | Nothing (no lyric template, no music rights ledger in use) | HF `music-to-video/references/{planning,storyboard-format,frame-skeleton,montage}.md` and `references/templates/{split-anchor-word-slot,held-text-strobe-burst}/`; Wismio `hyperframes-video-beats` | TC | The whole format. Owned/authorized music only (guide constraint). Upstream templates are the starting point; not integrated | Medium (skimmed) |
| 10 | Documentary and narrated video | Narrated explainer pipeline (Pilot) | HF `faceless-explainer/SKILL.md` + `references/{visual-design,story-design,cut-catalog}.md`; HF `talking-head-recut/SKILL.md` + `references/{layouts,frames,styles}/` (overlay on existing footage) | DP (explainer), TC (podcast overlays) | Podcast/talking-head overlay template. The `faceless-explainer` *workflow* was not adopted (see 9) | Medium |
| 11 | Reusable characters, illustration style, asset consistency | None | Wismio `.agents/skills/style-library/SKILL.md`, `style-library/`, `style-templates/`; Bang Motion `references/kartun-panggung.md`, `scripts/ae/bridge/rig-tokoh.py` (needs After Effects/Higgsfield); HF `hyperframes-creative/{frame-presets,palettes}/` | DP (style tokens), INC (AE bridge) | Brand tokens file per channel. Palettes/frame presets are a free starting point | Medium |
| 12 | Landscape and vertical composition | Both formats built from one scene plan (Pilot: 1920x1080 and 1080x1920) | HF `hyperframes-studio/SKILL.md` (action-safe 90% / title-safe 80%; caption band bottom ~17%); HF `hyperframes-core/references/full-screen-motion.md` | DP | Platform UI overlap zones for 9:16 are **unverified** (phone check pending, carried over) | Medium |
| 13 | Preview, screenshot inspection, lint, quality gates | `contentos preview` (frames + contact sheet), `qa.py`, `hyperframes lint` + `check`, `align.py` | HF `hyperframes-animation/scripts/animation-map.mjs` (+ `animation-map-sampling.mjs`, tests); Liamrjohnston `skills/motion-graphics/references/visual-critic.md`, `scripts/promptible-gate.mjs`; haidrrrry `SKILL.md` (mandatory visual-inspection loop); Wismio `short-form-edit/references/quality-gates.md`, `scripts/validate-plan.mjs` | **ST** (animation-map) + DP (critic) | Motion gates and an independent critic: **added** (`motion_audit.py`, `critic.py`, `explainer-visual-qa`). Thresholds uncalibrated | High (animation-map run), medium (others read) |
| 14 | Render verification and iterative repair | Worker retries, `qa.py`, resumable stages, tree-hash habit on the Pilot | Same as 13, plus HF `faceless-explainer/scripts/{build-frame,assemble-index}.mjs` (per-frame build + assembly) | DP | A closed loop "gate fails -> builder revises -> re-gate" is documented in `explainer-visual-qa` but not automated | Medium |
| 15 | Templates and configurable branding | Pilot builder with hard-coded channel look | HF `hyperframes-creative/{frame-presets,palettes,references/design-spec.md}`; HF `registry/`; Wismio `style-library/`, `style-templates/`, `DESIGN.ais-example.md` | TC | Channel brand file ("Your AI Buddy") that the builder reads. Not built | Medium |

### Reading the matrix
- Rows 4, 5, 13 are where measurable value was found and acted on.
- Rows 6, 8, 9, 10, 15 are genuine gaps but belong to *format work* (music/podcast/branding), not to this audit's integration. They should be done per format, borrowing the cited upstream templates.
- Rows 1, 2, 3, 7, 12 are mostly covered; upstream adds polish, not capability.

## 6. Classification of every finding

| Finding | Class | Reason |
|---|---|---|
| HF `hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes` | **Directly reusable skills** | Same renderer and version; official; Apache-2.0. Adopted, pinned (section 11) |
| HF `animation-map.mjs` | **Standalone tool worth testing - tested** | Ran on 4 compositions. Useful for `paced-slow` (camera drift) and dead zones; `collision` is noisy (36-41 flags, unreviewed) so it is advisory only. Optional dependency install is gated behind an explicit opt-in |
| HF `hyperframes-creative`, `hyperframes-studio`, `hyperframes-registry`, `music-to-video`, `talking-head-recut` | Design principles / templates, **not installed now** | Useful for later formats. Install only when that format is built, pinned the same way |
| HF `faceless-explainer` workflow, router skill `hyperframes`, `media-use` | Not adopted | Workflow regenerates narration and overlaps our gates; `media-use` routes to HeyGen audio; see 9 |
| Liamrjohnston `cinematic-camera`, `terminal-inserts`, `visual-critic.md` | **Design principles** | Rules ported by wording into `explainer-motion-craft` / `critic-rubric.md`; the skills themselves target Remotion |
| Liamrjohnston `install.sh` | **Incompatible / rejected** | Scaffolds a Remotion project via `create-video@latest` and is designed for `curl | bash` |
| haidrrrry `remotion-motion-graphics` | **Duplicate + conflicting** | Overlaps the HF rules and prescribes idle "breathing", which contradicts the seek-safe, stillness-first doctrine that the A/B supports. Its "inspect the render" loop is a good idea we already have |
| Wismio / Student Kit (`video-storytelling`, `hyperframes-video-beats`, `style-library`) | **Design principles / templates** | Persistent-world storytelling and the anchor-word window are the useful parts. Repo is a derivative of third-party kit with mixed permissions (section 7); no code vendored |
| Bang Motion (`RFTaurus/motion-skill`) | **Design principles only** | `anti-ppt.md` and shot-size camera are useful. Runtime uses a real-time browser clock and CDN assets, which breaks seek-safe deterministic rendering; Higgsfield/After Effects bridge needs paid/unavailable tools |
| `apoorvlathey/motion-canvas-skills`, `VideoZero/skills` | **Alternative rendering framework (API reference)** | Useful only if Motion Canvas is adopted. No demonstrated advantage; `animation-basics` is generic |
| `iart-ai/motion-skills` | **Duplicate / index** | The named repo holds no skills; sibling repos not studied in depth, so no integration value claimed either way |
| `remotion-dev/skills` | **Alternative rendering framework** | Remotion-specific; license file absent from the repo. Not adopted |

## 7. License and dependency findings

| Item | Finding | Commercial use for a monetised channel |
|---|---|---|
| HyperFrames repo + skills | Apache-2.0, `LICENSE` read. Copy kept at `.claude/skills/_upstream/hyperframes.LICENSE` with provenance | Permitted, keep notice |
| Liamrjohnston, haidrrrry, apoorvlathey, Bang Motion, iart-ai (x3) | MIT, `LICENSE` read in each | Permitted for the text/code. Their bundled demo/reference media were not reused. Liamrjohnston's README says product names and logos in examples belong to their owners |
| VideoZero | Apache-2.0, `LICENSE` read | Permitted |
| Wismio kit | MIT for original student-kit material; HyperFrames skills inside are Apache-2.0; other "pipeline resources" rely on `licenses/PIPELINE-USE-PERMISSION.txt` (**not reviewed in full**); example media and brand assets give **no** rights | No code or media vendored from it. If anything is wanted later, read the permission file first and prefer the upstream HyperFrames original |
| `remotion-dev/skills` | **No license file and no `license` field in `package.json`.** License of these skill texts cannot be verified from the repo | Not used. Remotion itself: see Milestone A matrix `04-licensing-matrix.md`; re-verify before any use |
| Remotion / Motion Canvas (frameworks) | Not installed, so their dependency trees were not audited | n/a |
| GSAP | Already a dependency of HyperFrames compositions; license terms per gsap.com standard licence. Unchanged by this work | Already in use |

**Dependency findings for what was integrated.** The three vendored skills are text, HTML examples and scripts; nothing is installed or executed by vendoring them. Only `animation-map.mjs` needs npm packages (browser tooling) and it goes through `scripts/package-loader.mjs`, which I read: it pins `HYPERFRAMES_SKILL_PKG_VERSION`, runs `npm install --ignore-scripts`, and asks y/N unless `HYPERFRAMES_SKILL_BOOTSTRAP_DEPS=1` is set. I ran it only after reading it, with the pin set to 0.8.114.

**Install-script review.**
- `Liamrjohnston .../install.sh`: read, **not executed**. It runs `npx create-video@latest --yes --blank` (unpinned remote code), installs the Remotion best-practices skill from a second repo, and is advertised as `curl ... | bash`. Rejected.
- `haidrrrry .../scripts/build-skill.sh`: packaging helper, read only, not needed.
- Bang Motion `scripts/serve.py`: a local server for its own runtime; not needed because the runtime is not adopted.
- Wismio kit `package.json` / scripts: not run.
- HF `skills update` CLI path: not used. Skills were copied from a clone at the pinned commit and hash-verified instead (section 11), so no network fetch happens at install or verify time beyond the one-time clone.

**Security posture of the integration.** No credentials read or written. No global config modified (`~/.claude`, `~/.agents` untouched). No paid service called. Vendored skill trees are gitignored; the lock file records tag, commit, license, access date and per-skill SHA-256; `verify` fails on any drift; `remove` deletes only the vendored directories.

## 8. Compatibility, duplicates and missing capabilities

**Compatibility with the existing stack.**
- HyperFrames skills at tag v0.8.114 match the pinned renderer (`package.json`). Skills on `main` (0.8.145 at audit time) describe newer CLI behaviour; using them against 0.8.114 risks guidance the renderer does not honour. This is why the pin is the tag, not `main`. Upgrading the renderer is a deliberate act that should re-pin the lock file and rerun the comparison.
- The vendored skills work with the existing contentos flow because they only constrain composition HTML and add an optional analysis script. They do not touch `contentos/pipeline.py`, gates or the ledger.
- Skills use the standard `SKILL.md` + frontmatter format (validated for all five). **Not verified:** that Claude Code *on the Mac* loads these project-scoped skills. A global finding may interfere (section 12, item 1).

**Duplicates (no integration value).** haidrrrry skill vs HF motion rules; Liamrjohnston `motion-graphics` vs HF `motion-graphics` (same name, different framework); Motion Canvas skills from two repos; Remotion best-practices vs HF core for our purposes; iart-ai index repo vs its siblings; HF `hyperframes-creative/motion-principles.md` vs HF `faceless-explainer/references/motion-language.md` (overlap inside upstream, we use the latter's rules).

**Genuinely missing in Video Factory after this work** (ordered by value):
1. **Beat-vs-anchor-word validator on built compositions.** We align script to ASR, but nothing checks that a visual beat lands within a window around its anchor word (Wismio suggests about -0.2 to +1.8 s; unvalidated by us). Tooling idea: parse GSAP timeline tweens against `word-timings.json`.
2. **Folding the builder rules into the contentos pipeline.** Rules R1-R6 live in a skill and in the A/B variant; the Pilot builder inside `contentos` is unchanged. Variant B's two transforms exist only in `scripts/motion_compare.py`.
3. **Music-video / lyric and podcast-overlay templates** (rows 9, 10). Start from HF `music-to-video/references/templates/*` and `talking-head-recut/references/*`; install and pin only when that format starts.
4. **Brand token file per channel** (row 15).
5. **9:16 platform UI safe zones, verified on a phone** (row 12).
6. **Hindi/Odia** word alignment and typography (carried over from Milestone A; unaffected by this audit).
7. **Terminal-insert authenticity checklist** (row 7): low effort, port when a terminal-heavy video is planned.
8. **Calibrated critic thresholds.** Current numbers are provisional; need several human-reviewed videos to calibrate.

## 9. Rejected alternatives and reasons

| Alternative | Reason (evidence) |
|---|---|
| Switch to **Remotion** | No quality or maintainability advantage was demonstrated; HyperFrames already renders our formats; Remotion adds React toolchain, license obligations above a team size, and a rewrite of the Pilot builder. The only Remotion-specific value found (camera, terminal inserts, critic) was portable as rules |
| Switch to **Motion Canvas** | Imperative generator-based model with its own renderer; the two skill repos are API references. No demonstrated advantage; one repo last updated about 8.5 months before the audit |
| **Bang Motion** runtime | Real-time browser clock and CDN assets conflict with seek-safe deterministic rendering; Higgsfield/After Effects bridge needs unavailable or paid tools. Only its anti-slideshow rules were kept |
| **haidrrrry** skill | Prescribes idle/"breathing" motion; upstream doctrine says not to (the A/B did not test breathing, so that conflict is doctrinal, not measured). Redundant otherwise |
| **Liamrjohnston `install.sh`** | Unpinned remote scaffolding command and `curl | bash` pattern |
| **Official `faceless-explainer` workflow** | Starts from text and regenerates narration; needs HeyGen audio/media services and sub-agent fan-out; overlaps our `SCRIPT_APPROVED`/align/QA gates. Not run, so no quality claim is made about it. Its `references/motion-language.md` was taken instead |
| **Installing the full 21 HF skills** | The brief says not to; most address formats we are not building yet |
| **ElevenLabs, Kie.ai, HeyGen audio API, Higgsfield** paths in the Student Kit / Bang Motion / `media-use` | Paid or account-bound services; violates local-first and no-spend constraint |
| **Wismio kit as a whole** | Mixed permissions, example media with no rights, derivative provenance; its good ideas exist upstream under Apache-2.0 |
| **Auto-fixing the global skills symlink loop** | Unrelated global configuration; needs approval (section 12) |

## 10. Controlled comparison (executed)

### 10.1 Design and what it can and cannot say
- **Source:** a copy of Pilot 001 (`workspace/experiments/motion-ab-001/`). The Pilot directory itself was hash-checked before and after: **283 files identical**. Inputs identical between arms (checked byte-for-byte): `audio/mix.wav`, `captions/word-timings.json`, `script/narration.txt`, `src/scene-plan.json`. Same duration (48.2 s), resolution (1920x1080 and 1080x1920), 30 fps, same renderer (hyperframes 0.8.114), same machine and session.
- **Arms.** *Control* = the existing builder output, unchanged. *Variant B* = the same builder with two scripted changes derived from the upstream doctrine: (a) the five `back.out(...)` entrance eases become `power3.out`; (b) the per-scene camera becomes a single move of at most 0.9 s (`power2.inOut`, starting where the last one ended), then a hold, instead of a scene-long drift with a reset start.
- **Only one alternative was tested.** I did not render a Remotion or Motion Canvas version and I did not run the official `faceless-explainer` workflow. No claim is made about them.
- **Replicates:** one render per arm and format. Timing is therefore indicative only.

### 10.2 Measured results (from `results.json`, `render-times.json`)

| Format | Metric | Control | Variant B |
|---|---|---|---|
| Landscape | File size | 13.95 MB | 8.03 MB (-42%) |
| Portrait | File size | 11.01 MB | 7.27 MB (-34%) |
| Landscape / portrait | Overshoot easings (`back`) | 5 / 5 | 0 / 0 |
| Landscape | One-frame "pops" | 16 | 12 |
| Portrait | One-frame "pops" | 23 | 19 |
| Landscape / portrait | Mean frame-to-frame luma change | 0.153 / 0.168 | 0.145 / 0.151 |
| Landscape / portrait | Static-frame fraction | 0.516 / 0.517 | 0.635 / 0.632 |
| Landscape / portrait | Longest still | 3.5 s / 3.07 s | 3.5 s / 3.07 s |
| Both | `hyperframes lint` / `check` | 0 / 0 exit | 0 / 0 exit |
| Landscape / portrait | Render time (single run) | 30.0 s / 29.2 s | 27.5 s / 27.0 s |
| Both | Upstream animation-map `paced-slow` flags | 7 / 7 | 0 / 0 |
| Both | Upstream animation-map `collision` flags | 36 / 38 | 35-39 / 41 (advisory; unreviewed) |
| Both | Upstream animation-map dead zones | none flagged | 4-5 zones, e.g. 6.5-10 s |

Visual evidence saved: `frames/sheet-*.png` (contact sheets per arm and format) and `inspect/boundary-14.8.png` (the frame pair around one scene cut). At that pair the control's stage jumps by about 22 px; this was measured at **one** pair, not averaged over all cuts.

### 10.3 Reading the numbers honestly
- **Objective improvements:** the five overshoot eases are gone, four fewer isolated one-frame jumps in each format, the scene-long drift flagged by the upstream tool is gone, and files are 34-42% smaller with nothing else changed. Smaller files are a consequence of less moving pixels, not proof of better quality.
- **A cost I introduced:** variant B is *stiller*. Static-frame fraction rose from about 0.52 to about 0.63, and the animation-map now reports dead zones (for example 6.5-10 s) where nothing develops while narration continues. Some of that is correct (a hold after a settled move), but a 3.5 s stretch of nothing during speech is a real weakness. The right fix is to time sequential reveals to the narration (rule R2), not to put the drift back. Not done yet.
- **Pops are evidence, not verdicts.** The remaining 12/19 pops include intended caption swaps and hard cuts. I attributed one to a camera snap by looking at the frames; I did not classify all.
- **Render time:** 27.5 vs 30.0 s is inside the variation I saw between two control renders (about 2 s). No time advantage is claimed.
- **Not measured:** viewer preference, "looks better", typography quality, A/V sync beyond identical-input equality (caption timings and audio are byte-identical by construction), and human correction effort. Variant B required zero manual edits (two scripted transforms), but how long a person would take to fix the control defects by hand was not timed.
- **Conclusion allowed by the data:** the defects in our own build are real and measurable, the fix is cheap, and nothing regressed on the automated gates. **Not allowed:** "variant B is better looking" or "the upstream skill is superior".

### 10.4 Human review requested
Please watch `workspace/experiments/motion-ab-001/control/renders/control-{landscape,portrait}.mp4` against `.../variant-b/renders/variant-b-{landscape,portrait}.mp4` (landscape and portrait), blind if possible, and tell me which you prefer and why. If B loses on the long still stretches, the next change is reveal timing, not reverting the doctrine.

### 10.5 Reproduce
```
PY=~/.contentos/venv/bin/python
$PY scripts/motion_compare.py prepare workspace/projects/<project> workspace/experiments/<exp>   # refuses to overwrite
$PY scripts/motion_compare.py build   workspace/experiments/<exp>
$PY scripts/motion_compare.py render  workspace/experiments/<exp>    # long: run detached, poll
$PY scripts/motion_compare.py measure workspace/experiments/<exp>
$PY scripts/motion_compare.py frames  workspace/experiments/<exp> --at 1.5 5 9
$PY scripts/motion_compare.py report  workspace/experiments/<exp>
```
`experiment.json` in the experiment directory records the variants; `SOURCE-TREE-SHA256.before.json` records the source hash. The upstream map was run per arm with `HYPERFRAMES_SKILL_PKG_VERSION=0.8.114 HYPERFRAMES_SKILL_BOOTSTRAP_DEPS=1 node .../animation-map.mjs <dir> --out <out> --width W --height H --fps 30` (script copy and wrapper: `workspace/experiments/upstream-animation-map/`, `motion-ab-001/run-animmap.sh`).

**Validating a future upgrade** (renderer bump, new skill version, new rule): run `python scripts/upstream_skills.py verify`; run the full test suite; `prepare` a new experiment from the same Pilot copy so the control is the previous release; compare the table in 10.2; require no new lint/check failures and no new overshoot or pop regressions, then a human look at the frames. Repeat renders three times before claiming any timing difference.

## 11. Recommended skills, exact sources, plan and rollback

### 11.1 Integrated (justified by 10.2)
| Skill | Origin | Exact source path | Pin | Purpose |
|---|---|---|---|---|
| `hyperframes-core` | official | `heygen-com/hyperframes` `skills/hyperframes-core/` | tag `v0.8.114`, commit `01c6f6004a00ecfa6e77ab4025b47a46a5e925fc`, tree sha256 `24231d50...62a11` | Composition contract and determinism rules |
| `hyperframes-animation` | official | `skills/hyperframes-animation/` (includes `scripts/animation-map.mjs`, `rules/`, `blueprints/`, `transitions/`) | same commit, sha256 `39bfce44...71336` | Atomic motion rules, blueprints, motion-analysis tool |
| `hyperframes-keyframes` | official | `skills/hyperframes-keyframes/` | same commit, sha256 `faebacc6...c953` | Seek-safe keyframing and diagnostics |
| `explainer-motion-craft` | ours | `.claude/skills/explainer-motion-craft/SKILL.md` | not gitignored; commit with the repo | Rules R1-R6, distilled from `faceless-explainer/references/motion-language.md`, `cinematic-camera`, `hyperframes-studio`, Bang Motion `anti-ppt.md` |
| `explainer-visual-qa` | ours | `.claude/skills/explainer-visual-qa/{SKILL.md,references/critic-rubric.md,templates/critic-output.example.json}` | not gitignored; commit with the repo | Gates, frame inspection, independent critic, A/B discipline |

Executable support: `contentos/production/motion_audit.py`, `contentos/production/critic.py`, `contentos/upstream_skills.py`, `scripts/motion_compare.py`, `scripts/upstream_skills.py`, `config/upstream-skills.lock.json`. Tests: see `08-motion-skills-implementation-report.md`. The two factory skills have separate responsibilities (author vs. inspect) and do not compete with any existing factory skill.

### 11.2 Deferred (install only when that format is built; each needs the same pin-and-verify treatment)
`music-to-video` and `hyperframes-creative` (music/lyric format); `talking-head-recut` (podcast overlay format); `hyperframes-registry` (reusable data/diagram components); `hyperframes-studio` (safe-zone reference, already summarized in R5).

### 11.3 Implementation plan (remaining, in order)
1. Human A/B review (10.4).
2. Fold R1-R3 into the contentos explainer builder behind the existing gates, with a test that fails on overshoot eases; keep variant B as the regression baseline.
3. Add R2 reveal timing (anchor-word cues) and the beat-vs-anchor-word validator; re-run the comparison; target: dead zones during speech reduced without reintroducing pops.
4. Calibrate critic thresholds on 3-5 human-reviewed videos.
5. 9:16 phone safe-zone check; then lock the portrait caption band.
6. Only then start music/lyric and podcast formats using the deferred skills.

### 11.4 Rollback (clean removal)
```
python scripts/upstream_skills.py remove        # deletes only the 3 vendored upstream skill trees (+ _upstream)
rm -r .claude/skills/explainer-motion-craft .claude/skills/explainer-visual-qa
# remove the comment and 2 lines added to .gitignore for .claude/skills/hyperframes-*/ and .claude/skills/_upstream/
rm contentos/production/motion_audit.py contentos/production/critic.py contentos/upstream_skills.py \
   scripts/motion_compare.py scripts/upstream_skills.py config/upstream-skills.lock.json \
   tests/test_motion_audit.py tests/test_critic.py tests/test_upstream_skills.py
```
Nothing else was changed: Pilot 001, `contentos/pipeline.py`, gates, `~/.claude` and `~/.agents` are untouched. Experiments under `workspace/experiments/` are gitignored and can simply be deleted. (`contentos/cli.py`, `align.py`, `sceneplan.py`, `preview.py` and their tests predate this task and must **not** be removed by this rollback.)

## 12. Decisions and authorizations needed

1. **Global skills directory (approval needed).** `~/.claude/skills` is a symlink to `~/.agents/skills` that loops, and 25 of 434 entries dangle, including every HyperFrames skill. I did not touch it (global configuration). Effect: personal HyperFrames skills may not load. A project-local pin avoids relying on it, but I could not confirm Claude Code on the Mac loads the project skills over a same-name dangling personal entry. Proposed fix, if you approve: list the dangling entries to you first, then repair or remove only those after a backup.
2. **Adopt variant B's rules into the contentos builder (routine, reversible, I will proceed unless you object).** It follows your instruction to proceed on reversible engineering decisions, but I am asking you to watch the A/B first because the result is a taste question.

No spend, publishing or rights decision is involved. Nothing was uploaded; `PUBLISH_APPROVED` has not been granted.

## 13. Sources (accessed 2026-10-10)
- https://github.com/heygen-com/hyperframes (tag `v0.8.114`, `main` at `bb9e507e`)
- https://github.com/Liamrjohnston/remotion-motion-graphics-skill (`b860c792`)
- https://github.com/haidrrrry/claude-remotion-skill (`1dcbe5e3`)
- https://github.com/apoorvlathey/motion-canvas-skills (`5cdaf357`)
- https://github.com/VideoZero/skills (`670ff96a`)
- https://github.com/Wismio/hyperframes-video-create (`b1afdb1d`)
- https://github.com/RFTaurus/motion-skill (`c1aa65e9`)
- https://github.com/iart-ai/motion-skills (`4a982237`, default branch `master`), https://github.com/iart-ai/motion-design-skills (`3c129f76`), https://github.com/iart-ai/explainer-video-skills (`3e2d4117`)
- https://github.com/remotion-dev/skills (`32b241b9`)
- Local evidence: `workspace/experiments/motion-ab-001/{results.json,render-times.json,report.md,frames/,inspect/}`, animation-map logs `anim-map-*.log`.
