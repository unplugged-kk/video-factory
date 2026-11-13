# P1-1 proposal: a chosen look must change rendered frames

Status: PROPOSAL, nothing implemented. Written 2026-11-11 on `feat/standalone-acceptance` (HEAD `016b5a5`).
Labels: **[read]** read in code, **[ran]** executed, **[inferred]**, **[decision]** needs the owner.

## 1. Root cause

There are three separate "style" layers and they are not connected. ROADMAP P1-1 describes the problem too loosely: it is not that
nothing changes frames, it is that the layer named `look/1` changes none.

| Layer | Where | Reaches frames? |
|---|---|---|
| `look/1` presets, 30 looks + 27 effects | `config/presets/`, `contentos/intelligence/looks.py` | **No.** [read] `looks.py` is only imported by its own CLI and tests; no pipeline code reads a preset. [ran] grep for `intelligence.looks` outside the module found nothing. |
| scenekit styles, 6 built in | `contentos/scenekit/styles.py`, chosen by spec `visual_style` | **Yes**, fully: layout, type, tokens, grounds, motion, caption. This is what the Hindi sample used (`editorial-magazine`). Only 6, hard-coded in Python. |
| legacy `style_card` and `visual_layer` hooks | `contentos/features/style_card.py`, `visual_layer.py` | Barely. A style card is resolved and recorded, then `visual_layer` swaps one `card_style` border/background string chosen by substring of the card id (`"sketch" in style_id`) over a fixed 7-colour `BACKDROPS` table. Dials, axes and motion never arrive. Only on the legacy path, not scenekit. |

Why a look cannot reach frames today [read]:
1. `s_compose` (`contentos/pipeline.py`, `visual_style` branch near line 239) dispatches to scenekit only on `visual_style`; scenekit reads only `STYLES[...]["tokens"]`. No code maps a `look/1`
   (`palette{bg,fg,accent}`, `typography{display,body}`, `motion.intensity`, `texture[]`, `effects[]`, `captions`, `layout`) onto those tokens.
2. A look is much poorer than a scenekit style. It has 3 colours (scenekit needs 12 tokens: `bg2 ink muted accent accent2 hl capbg capink panel line ...`), no layout in 26 of 30
   presets (the `layout` key is free text such as `three-panels` on 4), a font **name** only, a texture **tag** only, and motion as a 1-5 number. Nothing says what `paper-grain` or `halftone-dots` should paint.
3. Fonts: [ran] none of the look fonts (Playfair Display, Anton, Outfit, Inter, Caveat, Fraunces, Space Mono, Bangers, Kalam, Noto Sans Devanagari, ...) exist in
   `/System/Library/Fonts`, `/Library/Fonts` or `~/Library/Fonts`. scenekit states "fonts are system stacks: nothing is downloaded at render time", and the Indic path forces Kohinoor / Devanagari Sangam
   regardless. So even a wired look would silently render in a fallback face unless a font map exists.
4. The job's `look.json` is the export stage's shipped-look signature (structure, temperature, texture), computed after the fact from the render. It is not an input. The names collide (AGENTS.md section 10 already warns).

Empty scenes (scenes 1 and 6 of the sample) have a separate and independent cause [read, ran]: a text-only scene gets class `no-stage`; the `.stage` div is hidden and the grid is
`minmax(0,1fr) auto`, so headline sits in a large flexible band with nothing in it. The planner refuses to invent data (correct), and no primitive exists for a scene whose only content is a number or a time span already
present in its own script. The "04 / scene 4 of 6" is the `split` type's only stage, hard-coded English (`compose.py`, `split` branch).

## 2. Files involved today

`contentos/pipeline.py` (`s_compose` dispatch), `contentos/scenekit/{planner,styles,compose,primitives}.py`, `contentos/intelligence/looks.py`, `config/presets/looks/*.json`,
`contentos/lang/typography.py` (script font override), `contentos/features/{style_card,visual_layer}.py` (legacy, leave alone), `tests/test_scenekit.py`, `tests/test_looks.py`.

## 3. Proposed architecture (minimal, no new renderer, no new dependency)

One new module, `contentos/scenekit/lookmap.py`, and one spec key. **A look is compiled into a scenekit style; scenekit stays the only composer.**

```
spec.look: <look-id>  (optionally  look: {id, base_style, seed})
        |
looks.load_dir()  ->  lookmap.to_style(look, base)  ->  an in-memory scenekit style dict
        |                                                  (same shape as STYLES[...], validated by S.validate rules)
scenekit.compose(...)  unchanged apart from reading texture/stat treatments from tokens
```

`to_style(look, base)`:
- **Base style**: `look.base_style` if present, else chosen from `look.layout`/`family` by a small explicit table (explainer -> `clean-explainer`, story/lyric -> `cinematic-documentary` or `kinetic-type`,
  talking-head -> `clean-explainer`). The base supplies the layout, caption kind, motion preset and the 12-token skeleton, so every look is already a complete, tested style.
- **Overrides from the look**: `palette.bg/fg/accent` -> `bg`, `ink`, `accent`, `hl`; derived tokens (`bg2`, `muted`, `panel`, `line`, `capbg`, `grounds`) computed by one deterministic function (mix toward bg/fg, luminance-checked); `typography.display/body` -> font stacks
  through an explicit **font map** (look font -> best installed system stack, e.g. Playfair Display -> `Didot, Georgia, serif`; Anton -> `Impact`; Outfit/Inter -> `Avenir Next`; Caveat/Kalam -> `Marker Felt`). Unmapped font fails validation, never a silent fallback;
  `motion.intensity` 1-5 -> motion preset plus stagger/duration scale (1 = `rise`, 5 = `slam`; intensity also gates decoration); `texture[]` -> a CSS layer from a **texture table** of about 10 CSS-only treatments (see below).
- **Fail closed**: unknown look id, unmapped font, unmapped texture, or a derived palette whose ink/bg contrast is under 4.5:1 raises with the known ids/keys. Never substitute another look.
- Look id, look-file digest and the compiled style digest are written to `visual-plan.json` and `ctx` (and a `look_applied` field in the manifest). This is *input* provenance, distinct from the output-side `look.json`; name it `look-input.json` to end the collision.

Texture table, CSS and inline SVG only [read: scenekit already emits gradient grounds]: `paper-grain` (SVG `feTurbulence` or a Python-generated tiny noise PNG as a data URI), `halftone-dots` (radial-gradient tile), `grid`
(already exists in `blueprint-architecture`), `scanline` (repeating-linear-gradient), `glow` (text-shadow + radial), `flat` / `flat-card` (none), `film-grain`, `wash`, `print` (hairline rules). Textures with no cheap CSS form (`rain`, `smoke`, `curtain`, `paint-splat`, `character-sheet-first`) are
**not mapped**: a look needing them stays `blocked` for scenekit and says so. Those need an illustration path (out of scope).

Effects (`effects[]`) stay unread in this milestone. Say so in the look report; do not fake them.

## 4. Same script, two looks: the Hindi SIP sample

Spec, narration, data and timings stay identical. Only `visual_style: {id: editorial-magazine}` is replaced by `look: <id>`.

| | Current (`editorial-magazine`) | `look: flat-dark-news` (derived) | `look: watercolor-wash` (derived; `magazine-masthead` is too close to current) |
|---|---|---|---|
| Ground | warm paper gradient, 3 tints | `#242021` charcoal, flat card panels | `#f7f3ea` paper, a soft `wash` tint per scene |
| Type | Kohinoor Devanagari bold, serif Latin numerals | same Devanagari (forced), heavy sans Latin numerals, uppercase tag bar | Devanagari, handwritten-feel Latin numerals via Marker Felt |
| Accent | burnt orange `#c2410c` | news red `#e63946` | blue `#3a86ff` |
| Chart | thin pill bars, hairline rules | thick bars inside a flat panel, red value chip | bars drawn as washed strokes |
| Motion | horizontal push | hard cut with accent bar wipe (intensity 4) | slow rise (intensity 2) |
| Caption | rule above, plain | pill | plain |

Acceptance for the pair: the structural-axes check already in `styles.distinct()` (layout, caption, motion, font family, ground) must differ on at least 3 axes between the two compiled styles, and the
contact sheets must differ in palette, headline weight and chart treatment on sight. Devanagari glyph rendering and the Latin fallbacks are checked frame by frame.

## 5. Filling empty scenes meaningfully

Rule kept: the planner never invents data. So the fix is new **data-from-the-script** primitives plus a layout rule, not decoration.
- `figure` primitive (scene 1 and 6 need it): one anchor number or phrase already stated in the narration, e.g. `₹5,000 / महीना` for scene 1 and the first step for scene 6, sized as the stage. Authored under `visual: {type: figure, value, label}`; no source needed when the value is quoted from the script itself, `illustrative` otherwise.
- `ticks` primitive (optional, scene 1): a 10 x 12 grid of 120 monthly deposits that fill in on the beat, the direct picture of "10 years of 5000" and the same 120 the arithmetic used. Count comes from the spec, so it is not invented.
- Layout fix independent of data: when a scene has no stage, anchor headline and caption in the optical centre, scale the headline to `hero`, and let the look's texture and rule carry the surface; delete the empty band by switching the grid to `1fr auto` with the headline vertically centred. Same change makes `no-stage` consistent across layouts.
- Remove the English ornament: `split` shows `NN` plus a localized label only when `language` is English, otherwise just the numeral, or better the tag text already in the spec (`उदाहरण`, `ध्यान दें`). The stage text must come from the spec language, never from compose.py.

Not allowed as fillers: random shapes, stock/AI illustration, constant particles.

## 6. Motion and transitions

Intensity governs three things, all deterministic: entrance preset (rise, push, wipe, slam), stagger and duration scale, and how many elements animate. Intensity 1-2 looks (finance, editorial) animate the headline once and the number counting up (a `stat` primitive count-up is
meaningful motion for money); intensity 4-5 looks get slam/cut. Transitions: keep the existing six; add none. Nothing animates without a reason: a bar grows to show the value, a tick fills on its word, a step appears as it is spoken. All timeline-addressable (paused GSAP), so the pinned HyperFrames 0.8.114 stays.

## 7. Mobile acceptance criteria (1080x1920, judged on a phone-size sheet)

1. Body/caption >= 40 px equivalent (>= 3.7 % of width), chart labels >= 34 px, footnote >= 28 px; nothing under those anywhere.
2. Ink/bg contrast >= 4.5:1 for text, >= 3:1 for chart marks, computed from the compiled tokens, not eyeballed.
3. Nothing in the bottom 307 px except captions and nothing clipped at any edge; headline <= 3 lines in Devanagari.
4. No scene has a content gap over about 30 % of height; every scene has a focal element that is a number, a figure, a chart or a headline set at hero size.
5. Two looks differ on >= 3 axes and on-sight in palette, headline weight, chart treatment.
6. No English string in a non-English video that did not come from the spec (grep of the composed HTML).

## 8. Before/after plan

Fixed inputs: `examples/finance/sip-small-savings-hi.yaml` plus the existing job audio (`jobs/.../audio/*.wav`; compose only, no voice regeneration, so ~7 s per compose). Compose twice, render both,
`./contentos.sh preview <video> --at 1,9,14,19,24,32,37 --out DIR --sheet` for each, plus the baseline already at `/tmp/vfprev2`. Three sheets side by side go in a scratch workspace folder; diff them by measured per-frame palette/edge statistics as well as by eye. An independent critic (`explainer-visual-qa` with the
`critic` module) reviews the pair; a human views one sheet. No export, no `ready/`.

## 9. Regression matrix

| Test | Asserts |
|---|---|
| lookmap unit | all 30 presets: each either compiles to a valid style or fails with a named blocker (font/texture); no silent fallback |
| determinism | same look + seed -> byte-identical `index.html` |
| two-look diff | same spec, two looks -> different CSS tokens and >= 3 axes differ |
| fail closed | unknown id, unmapped font, low contrast raise with known ids |
| absent look | spec without `look` or `visual_style`: composed HTML byte-identical to today (golden) |
| existing `visual_style` | the 6 scenekit styles compose byte-identically before and after |
| language | Hindi spec contains no English chrome string; English unchanged |
| no-stage layout | empty band removed, headline centred, within safe zone |
| provenance | `look-input.json` has id, file digest, compiled-style digest |
| legacy | `style_card`/`visual_layer` paths untouched and tests unchanged |
| render | one real render per accepted look, QA 8+ PASS, frame sheet inspected |

Baseline to protect: 1085 passed, 8 skipped. `tests/test_scenekit.py`, `test_looks.py`, `test_pipeline_export.py`, `test_generic_cli.py` first.

## 10. Performance

Compose is ~7 s and render ~30 s per 38 s video [ran]. Everything added is CSS and inline SVG; textures must be measured: SVG `feTurbulence` repainting per frame can slow the headless capture, so prefer a once-generated data-URI tile.
Budget: render time within +20 % of the baseline for the same video; if a texture exceeds it, it is dropped or tiled. No extra model, no network.

## 11. Rollback

Additive and opt-in: a new module, a new spec key, and new primitives behind new `visual.type` names. Removing `look:` from a spec returns today's path byte for byte (golden test). Code rollback = delete `lookmap.py`, the new primitives and their tests; no config, gate, pin or
preset change is involved. Each milestone below is one commit that can be reverted alone (when the owner authorizes commits).

## Milestones (each small and testable)

1. **M1 lookmap, compile only**: `lookmap.py`, font map, texture table, contrast check, `looks.py`-level `to_style` tests; no pipeline change. Report which of 30 compile.
2. **M2 wire**: `look:` spec key in `s_compose`/`planner.resolve_style`, provenance file, golden tests proving absent key is unchanged.
3. **M3 empty-scene fix**: `no-stage` layout, localized `split`, `figure` and `ticks` primitives, tests.
4. **M4 look polish for finance**: two chosen looks, real render of the Hindi sample in both, before/after sheets, critic and human view; set look status to evidence-recorded only if the owner accepts.
5. **M5 docs**: ROADMAP P1-1, `docs/generic-video/`, AGENTS.md section 10 corrected (the sentence "builder does not read a chosen look" becomes precise).

Files expected to change: new `contentos/scenekit/lookmap.py`; edit `contentos/scenekit/{compose,planner,primitives}.py` and `contentos/pipeline.py` (one dispatch condition); new tests `tests/test_lookmap.py`, edits to `tests/test_scenekit.py`;
new example spec `examples/finance/sip-small-savings-hi-looks.yaml`; docs. No change to `config/*.yaml`, presets, gates, ContentForge, CEH or the HyperFrames pin.

## Risks

- 30 looks are only data; many assume textures/characters scenekit cannot paint. Mitigation: say `blocked`, do not approximate.
- Font fallbacks change the intended look of Latin-heavy presets. Mitigation: map is explicit and reviewable; Devanagari already forced to Kohinoor.
- A look with 3 colours leaves derived tokens to a formula; contrast failures are possible. Mitigation: validation, and an optional per-look `tokens` override later.
- Hindi finance tone: fixed disclaimers and `illustrative` labelling stay mandatory regardless of look.

## Decisions for the owner

- **[decision] D1**: compile a look into a scenekit style (recommended) versus teaching the legacy builder. Recommended: scenekit only; the legacy path is frozen.
- **[decision] D2**: font policy: system fonts only with an explicit map (recommended, matches "nothing downloaded at render time") versus bundling open-licence fonts into the repo (adds binary assets and licence tracking).
- **[decision] D3**: whether `figure`/`ticks` belong in this milestone or a following one.

## Recommendation

Ready to implement M1 and M2 now: the cause is traced, the change is additive, a golden test protects every existing render, and no dependency, spend or gate is touched. Hold M3 and M4 for D3 and the owner's visual review. P1-1 as worded in ROADMAP should be rewritten before work starts, because its "unread by the builder" claim is true for `look/1` but not for scenekit styles.
