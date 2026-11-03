# 08 - Multi-style scene system (scenekit): audit, research, build, validation

Date: **2026-11-03**. Evidence labels: **[ran]** I executed it and looked at the output, **[read]** I read the file, **[claim]** upstream says so, **[not verified]**.
Companion reports: `05` (external audit, other repos), `06` (target architecture), `07` (roadmap). This report does not repeat them.

## 1. Result in one paragraph

Track A rendered every video with one scene grammar: a centred headline over a word-highlighted caption on one navy gradient. `visual_style:` in a spec now selects one of **six** structurally different styles (layout, typography, motion, transition, caption treatment, ground family) and a planner picks a scene type per line from **five data-backed primitives** (diagram, code, compare, stat, steps) and three text-only ones, with an anti-repetition score and a variety report. It is **opt-in**: a spec without `visual_style` takes the old path byte for byte. The same approved script was rendered in five styles plus the legacy template and inspected frame by frame **[ran]**. It is **not yet human-reviewed on a phone**, every style is `unvalidated`, and no independent critic has graded it (section 9).

## 2. Baseline (before any change) [ran]

Contact sheets are in `$VIDEO_FACTORY_WORKSPACE/experiments/style-evolution/baseline/` for four shipped episodes (kubernetes-pods-014, kv-cache-008, mcp-025, how-claude-code-works-01).

| Observation | Evidence |
|---|---|
| All four share one ground, one palette, one layout: tag top-left, headline, a small diagram, caption at the bottom | contact sheets; mean luminance 0.10 in all four |
| The diagram occupies roughly a quarter of a 9:16 frame; the rest is empty ground | contact sheets |
| Within-video frame variation is low (mean pairwise thumbnail distance 0.041 / 0.046 / 0.051 / 0.066) | `scripts/style_diversity.py` |
| Existing gates: 884 tests pass, 8 skip; QA 9 checks pass with the documented `frozen_frames` WARN | pytest, `./contentos.sh qa` |
| Rule B (differ from the last five shipped on >= 2 of 5 fields) fails for the legacy Track A template rendered from the new sample script | `visual check` |

## 3. Root cause of the monotony [read + ran]

| # | Cause | Evidence |
|---|---|---|
| 1 | `pipeline.s_compose` has exactly one scene grammar (`head` + `cap`), one font stack, one entrance animation, one fade-out for every line | `contentos/pipeline.py` s_compose |
| 2 | The "variety" hooks do not change composition. `style_card` records a decision; `visual_layer` varies a backdrop gradient and an **empty decorative box** | `features/style_card.py`, `features/visual_layer.py` |
| 3 | Style cards (`config/styles`, `intelligence/styles.py`) are declared "shadow mode: no pipeline reads cards yet" | module docstring |
| 4 | Track A has no primitive for structure: no diagram, code, comparison, stat or steps scene, so there was nothing to vary toward | `grep` of s_compose |
| 5 | The gates check correctness and backdrop count (Rule A/B), not layout, motion or scene-type variety | `visual_gate.py`, `visual.py` |
| 6 | Track B is hand-authored by an agent and converges on the same look anyway (the four baseline episodes) | baseline sheets |

Not a cause: the renderer. HyperFrames rendered all six styles plus a 16:9 variant without modification.

## 4. Research ledger (searched 2026-11-03)

Method **[ran]**: shallow clone of each repo into `/tmp`, read README, licence, file tree, and the parts named below. **Not done:** issues, releases, CI, running any upstream code, watching upstream demo videos. "Latest commit" is the only maintenance signal I checked. Social posts were not used as evidence.

| Repo | What it actually is | Latest commit | Licence [read] | Decision | Why |
|---|---|---|---|---|---|
| `cth9191/animate` | Claude Code skill: canvas piece + headless-browser frame render, 7 styles each with `STYLE.md` (palette, motion habits, frame checklist), story grammar, storyboard and measured review tools (text cut-off/overlap, loudness, frame-hash) | 2026-10-05 | MIT | **Adapt ideas** | A style is a drawing kit plus rules plus a frame checklist: matches our `style/1` cards. Adopted: frame-hash reproducibility check, "style = structural contract". Not adopted: its canvas renderer (a second renderer), ElevenLabs voice path |
| `Tejashmakwana/motionmaxxing` | Agent skill for brand/launch films; a "slop" catalogue, gates G0-G5 (`lint.mjs` DOM lint for corner labels, counters, deck layouts; `look.py` dead-frame and end-card checks) | 2026-10-06 | Apache-2.0; NOTICE says bundled GSAP, fonts etc. keep their own licences | **Adapt ideas, prototype later** | Its "deck layout" and "page chrome" list describes our baseline closely. Many rules suit brand films, not narrated explainers (we keep section tags and captions), so only the dead-frame and no-corner-counter ideas are candidates. Not adopted: code (Node 22 + Chrome pipeline) |
| `Vibha-Ramprakash/claude-video-effects` | 51 overlay effects for talking-head footage (face tracking with mediapipe, OpenCV) | 2026-11-02 | MIT; bundled OFL fonts and model files with their own notices | **Reference only** | Needs a person on camera. Our content is narrated explainers. Font list is a useful licence-clean reference |
| `yihui-dev/awesome-opus5-5-videos` | Index of 703 shared prompts and preview images, no engine | 2026-10-13 | MIT (index); the prompts belong to their authors | **Reference only** | Inspiration for scene ideas, nothing to integrate |
| `zhuyansen/awesome-opus-5.5-video` | Another prompt/video index scraped from X | 2026-11-02 | **No LICENSE file found** | **Reject for reuse** | Unclear rights to the scraped prompts |
| `mutonby/openshorts` | Long-video to vertical clips (OpusClip alternative), Docker app with a hosted paid tier | 2026-11-01 | MIT | **Reference only** | Solves clipping footage, not building explainers. Speaker-aware split layout is an idea only |
| `jub0t/concat` | Cross-platform desktop video editor ("CapCut replacement") | 2026-11-03 | **AGPL-3.0-or-later** (dual licensed, commercial on request) [read `LICENSING.md`] | **Reject** | GUI editor, no overlap; copyleft that reaches network use |
| `SegFault42/HeliosGen` | Desktop canvas for chaining AI image/video model calls | 2026-09-17 | README says MIT, **no LICENSE file in the tree** | **Reject** | Generative, paid-model oriented; licence unverifiable |
| `affaan-m/ECC` | Large agent-harness collection; includes `manim-video`, `motion-*`, `remotion-video-creation`, `tasteforge-video` skills | 2026-10-29 | MIT | **Monitor** | I read only the skill front matter and file lists, not their bodies. Remotion and Manim would each add a renderer. Revisit only if a concrete need appears |
| `JetBrains/go-modern-guidelines` | Guidelines so agents write modern Go | 2026-09-10 | Apache-2.0 | **Reject (irrelevant)** | Go-only; not related to video |

Consistent with report 05: no new renderer, no paid service, no generative image/video, no copied code. What was taken is design pattern only, so no third-party licence obligations arise from this change.

## 5. What was built

```
contentos/scenekit/
  styles.py      6 styles, versioned (scenekit-style/1); distinct() fails if two differ on < 3 structural axes
  planner.py     style choice, intent classification, scene-type scoring, authored-data validation, variety report
  primitives.py  diagram, code, compare, stat, steps (HTML/SVG + seekable GSAP, no onUpdate/random/Date)
  compose.py     Track A composer driven by style + plan; writes visual-plan.json and variety-report.json
  __main__.py    python -m contentos.scenekit {styles|validate|recommend|plan} [SPEC]
contentos/pipeline.py   +5 lines: dispatch to scenekit only when spec['visual_style'] is present
examples/styles/        three sample specs (kafka events, retry backoff, why GPUs power AI)
scripts/style_matrix.py     same spec in several styles; never runs export or publish
scripts/scene_sheet.py      contact sheet at each scene's 75% point, times read from the composition
scripts/style_diversity.py  descriptive frame metrics
tests/test_scenekit.py      49 tests (all hermetic)
```

### Styles

| id | layout | motion | caption | ground | best for |
|---|---|---|---|---|---|
| `clean-explainer` | top-head | rise | pill | light | concepts, how-to |
| `kinetic-type` | kinetic | slam (hard cut alternate) | plain | dark | hooks, short opinion |
| `editorial-magazine` | split-editorial | push | rule | light | history, analysis |
| `blueprint-architecture` | top-head | wipe (sweep band) | plain | dark | architecture, distributed systems |
| `code-first` | top-head | cut | pill | dark | tutorials, APIs |
| `cinematic-documentary` | lower-third + letterbox | push-in | plain | dark | story, AI, infrastructure |

The style ids map to the closest of the existing cards (`kinetic-typography`, `blueprint-diagram`, `slow-parallax-story`) in a `card` field; the cards are not otherwise read by scenekit.

### Scene types and how they are chosen

Data-backed types need an authored `visual:` block on the script line and are **never invented**:

```yaml
- say: "..."
  headline: "..."
  visual: {type: diagram, nodes: [{id: a, label: Producer}, ...], edges: [[a, b, writes]]}
  # type: code (code, focus, file, kind: terminal) | compare (left/right title+points) |
  #       stat (value|bars, label, source | illustrative: true) | steps (steps: [...])
```

Validation fails closed: unknown node ids, labels over 22 chars, more than 8 nodes, code over 12 lines or 42 columns, and any stat/chart without `source` or `illustrative: true`. Text-only lines get `statement`, `pullquote` or `split`, chosen by `intent fit + style affinity - repetition`, ties broken by a seeded hash. Motion alternates rotate deterministically and never repeat back to back; the hook always uses the style's signature motion.

### Selecting a style

```yaml
visual_style: {id: auto, seed: 7}          # auto = keyword/data recommendation, recorded with scores
visual_style: editorial-magazine           # explicit override
visual_style: {id: clean-explainer, version: 1, seed: 3}   # version mismatch is an error
```

Style id, version, selection mode, seed and per-scene `why` are written to `visual-plan.json` in the job folder. Same spec + seed gives byte-identical `index.html` (tested) and frame-identical video (checked on a re-render, section 7).

### Variety report (`variety-report.json`)

Checks V1-V6 with `PASS|WARN|BLOCK`, scene, evidence, remediation, `human_review`. **Thresholds are provisional**: the only measured baseline is "every scene identical", so the numbers only catch degenerate plans (for example V1 BLOCK when 4+ scenes share one signature). Do not read them as calibrated.

## 6. Defects found by looking at frames (all fixed, none visible in metadata) [ran]

| Defect | Cause | Fix |
|---|---|---|
| Un-highlighted caption words invisible (dark on dark pill) | base colour was `ink`, not the pill's own text colour | base colour = style `capink` |
| Cinematic layout shifted, headline overlapped the diagram | letterbox bars were grid items | bars absolutely positioned |
| Editorial diagram overlapped the headline | grid template had 4 rows for 3 children | corrected rows |
| Headline missing on stage scenes (cinematic, code-first compare) | DOM order vs grid rows; fixed stage height overflowed on long captions | `order`, and stage height computed per scene from caption/headline length |
| "REBALANCING" ran off the frame (kinetic) | fixed hero size | fit-to-width per scene from longest word and a per-style glyph-width factor (test fails if removed) |
| Edge labels struck through by the curves | label on the line | offset outward |
| Arrowheads visible before their edge drew | SVG markers ignore dash offset | path hidden until it draws |
| 16:9 compare cards stacked and overflowed; steps crowded the caption | sizes tied to 1080 short side | content scaled to stage height; side-by-side in landscape |
| Wipe flooded the frame with solid cyan | full-width sweep | 40% band |

Two of my own diagnoses were wrong and corrected: I first judged `clip-path` broken from a scene that was actually a `rise` scene, and my first "coverage" metric was inflated by gradient grounds. Both were re-measured before anything was recorded.

## 7. Validation

All numbers from this machine (Apple Silicon, HyperFrames 0.8.114, 1080x1920 unless stated). Renders live under `$VIDEO_FACTORY_WORKSPACE/jobs/2026/11/03/sample-*`; contact sheets, transition strips and diversity tables under `experiments/style-evolution/`.

**Tests.** 933 passed, 8 skipped (884 + 49 new; skips unchanged). Mutation checks: removing the repetition penalty fails 15 tests; removing fit-to-width fails 1. Two of my first-draft tests survived those mutations, so I rewrote them.

**Matrix tested.**

| Script | Styles rendered |
|---|---|
| kafka-events (architecture) | blueprint, editorial, kinetic, clean, cinematic, **legacy template** (same script); editorial in **16:9** |
| retry-backoff (code) | code-first (auto-selected) |
| why-gpus-ai (concept) | cinematic (auto-selected) |

Auto-selection chose blueprint, code-first and cinematic for the three topics. Not run: every style on every topic (9 of 18 cells not rendered).

**Gates on the new renders.**

| Gate | Result |
|---|---|
| `hyperframes lint` (runs in compose) | pass on all 9 renders |
| `hyperframes check` | run on blueprint only: pass, 103/103 text checks WCAG AA |
| `contentos qa` (9 checks) | pass, with the documented `frozen_frames` WARN on text slides |
| Rule A (>= ceil(n/2) distinct backdrops, measured) | pass (3 of 6, or 3 of 5) on the 7 scenekit 9:16 renders; not run on the legacy or 16:9 renders. Failed 1 of 6 on every style before per-scene grounds were added |
| Rule B (vs last five shipped) | pass on 7 of 9; **fails** for blueprint (differs only on texture / structure from two shipped videos) and for the legacy template (accents) |

**Diversity (same script, 34 s each; `style_diversity.py`, thumbnails 108x192 at 1 fps).** Descriptive only.

| video | content (edge density) | within-video variation | mean luminance |
|---|---|---|---|
| legacy template | 0.104 | 0.064 | 0.11 |
| blueprint | 0.136 | 0.129 | 0.22 |
| editorial | 0.145 | 0.120 | 0.84 |
| kinetic | 0.173 | 0.237 | 0.14 |
| clean | 0.149 | 0.166 | 0.79 |
| cinematic | 0.131 | 0.170 | 0.13 |

Content density rose 26-66% and within-video variation 1.9-3.7x over the legacy render. Caveats: a thumbnail blurs fine text; within-video variation is partly the per-scene ground tint (needed for Rule A), so it overstates structural change; the dark styles sit close to the legacy video in raw pixel distance (0.20-0.36) because ground luminance dominates that metric. This is not a quality score.

**Reproducibility.** Re-rendering the kinetic job gave identical per-second frame hashes and PSNR `inf` over the whole video.

**Performance (single runs, not benchmarks).** Voice ~15 s, compose ~6 s (includes lint), render 27-39 s for 34 s of video, QA ~1 s. Legacy template render of the same script: 22 s. Scenekit renders are somewhat slower than the legacy template (more DOM and SVG); I did not measure peak memory or retries, and there were no failed renders.

**Mid-transition frames inspected [ran]:** slam (words arrive in sequence), wipe sweep (band crosses the frame), diagram edge draw (no early arrowheads).

## 8. Operating it

```bash
# list / validate / plan without rendering
~/.contentos/venv/bin/python -m contentos.scenekit styles
~/.contentos/venv/bin/python -m contentos.scenekit validate examples/styles/kafka-events.yaml
~/.contentos/venv/bin/python -m contentos.scenekit plan examples/styles/kafka-events.yaml

# render one video in a style (normal pipeline, gates apply)
./contentos.sh pipeline run my-spec.yaml          # spec contains visual_style

# compare several styles on one script (sample-* ids only; uses the private approval shortcut; never exports or publishes)
PATH=/opt/homebrew/bin:$PATH ~/.contentos/venv/bin/python scripts/style_matrix.py examples/styles/kafka-events.yaml blueprint-architecture,editorial-magazine
python scripts/scene_sheet.py <job-dir> <out-dir>        # contact sheet from the composition's own scene times
```

Reproduce a render: keep the spec (it holds style id, version, seed) and rerun; compare `visual-plan.json`. Diagnose: read the job's stage logs, `variety-report.json`, then open `project/index.html`; `hyperframes check` in `project/`. **Add a style:** add a dict to `styles.STYLES` (it needs >= 3 grounds and must differ from every existing style on >= 3 axes; `python -m contentos.scenekit styles` and `tests/test_scenekit.py` enforce this), render a sample, look at the sheet. **Add a scene type:** write a builder in `primitives.py` returning `(html, js)`, add it to `BUILDERS`, `STAGE_TYPES`, validation in `planner.validate_visual`, and CSS in `compose.py`. **Roll back:** remove `visual_style` from the spec, or delete `contentos/scenekit/` and the 5-line dispatch in `pipeline.s_compose`; nothing else depends on it.

## 9. Known limits and what is not done (read before relying on this)

- **No human review and no independent critic run.** Every style is `unvalidated`. The next required step is the owner viewing the five renders on a phone and running `contentos.production.critic` with an independent reviewer (AGENTS.md: a builder never grades its own video).
- **Gate shortcut used for samples.** The samples were rendered with `--approve-private` because you asked for rendered samples. They are `sample-*` jobs, were never exported, and publish stayed a dry run. If you want that stricter, revoke those approvals in the ledger.
- **Blueprint style fails Rule B** against two shipped videos, and `auto` selection still picks it for Kafka-like topics. The recommender does not yet read Rule B history; until it does, run `visual check` before composing.
- **Fonts are macOS system fonts** (Impact, Didot, Avenir Next, Charter, SF Mono). Another machine will substitute. Vendoring fonts (`hyperframes-localize-fonts`) is not done.
- **Track B is untouched.** Hand-authored explainers do not consume styles or the planner yet.
- **No `style_fidelity` critic dimension**, no safe-zone pixel check, no scene-level overflow measurement beyond `hyperframes check` and my per-scene stage sizing estimate (text-length based, not measured).
- **Variety thresholds are provisional** and uncalibrated. The motionmaxxing-style dead-frame and no-chrome checks were not implemented.
- **Not built from the brief:** the eight suggested agent skills (`analyze-reference-video`, `generate-storyboard`, ...), a code-first terminal sample, stat/chart rendered in a real video (primitive and validation exist and are unit-tested; no sample uses it), SFX/music, shader transitions (KF-004 still stands), 9 of 18 style-by-topic cells.
- Cinematic ground variants (teal, plum) are more saturated than the amber identity; they exist so Rule A passes honestly and may deserve a softer palette after review.

## 10. Summary

| Change | Reason | Files | Validation | Measured benefit | Status |
|---|---|---|---|---|---|
| Style registry (6 styles, versioned, >= 3 axes apart) | Monotony root cause 1-3 | `scenekit/styles.py` | tests, `distinct()` | Six structurally different looks from one script | Unvalidated by a human |
| Data-backed scene primitives | Root cause 4 | `scenekit/primitives.py` | tests, 9 renders, frame inspection | Diagram, compare, steps, code scenes in real renders | Working; stat not yet in a render |
| Planner with no-invention rules, anti-repetition, seeds | Root cause 1, 5 | `scenekit/planner.py` | 49 tests, 2 mutation checks | Deterministic plans; legacy failure mode BLOCKs | Working, thresholds provisional |
| Composer with adaptive layout and per-scene grounds | Root cause 1 | `scenekit/compose.py`, `pipeline.py` | renders, Rule A pass on 7/7 measured, hyperframes check (blueprint) | Diagram/content density +26-66%, variation 1.9-3.7x | Working, 16:9 checked on one style |
| Variety report | Root cause 5 | `planner.variety_report` | tests | Machine-readable PASS/WARN/BLOCK per render | Working |
| Frame-diversity and sheet scripts | Evidence | `scripts/` | run on 12 videos | Descriptive numbers | Coarse |
| Research of 10 repos | Brief | section 4 | clones read | 0 adopted as code, 2 ideas adapted | Depth limits stated |

Next: owner phone review; independent critic run; teach the recommender about Rule B; vendor fonts; decide whether Track B should consume `visual-plan.json`.
