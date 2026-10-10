# Design library

`config/design-library.json` lists the designs, palettes, styles and transitions HyperFrames ships (pinned v0.8.114), tagged so a topic can be matched to options instead of defaulting to one look. `python -m contentos.intelligence.designs` queries it.

## What is in it (76 entries)

| Kind | Count | Source | What it gives you |
| --- | --- | --- | --- |
| `frame_preset` | 13 | `skills/hyperframes-creative/frame-presets/*/FRAME.md` | A whole video look: colours, fonts, geometry, caption skin. 9:16 documented for all 13. |
| `palette` | 9 | `.../palettes/*.md` | Colour sets by subject (dark-premium, neon-electric, nature-earth, ...). |
| `visual_style` | 8 | `.../references/visual-styles.md` | Named directions (Swiss Pulse, Data Drift, Shadow Cut, ...) each paired with upstream's suggested shader. |
| `shader_transition` | 14 | `packages/shader-transitions` | WebGL scene-to-scene effects. **Not usable yet, see below.** |
| `css_transition` | 32 | `.../transitions/css-*.md` | Push, iris, dissolve, blur, zoom, blinds, glitch, light leak, and more. Fast render path. |

Tags (register, mood, topic, energy, aspect) are Claude's judgement, `reviewed: false`. Facts (colours, fonts, names) come from upstream files. Every entry is `unverified` until a real render in this pipeline records `verified.result`.

## Choosing by topic

```
python -m contentos.intelligence.designs recommend --topic ai-ml --mood futuristic --register dark --energy medium --aspect 9:16
python -m contentos.intelligence.designs recommend --topic security --mood raw --energy high --prefer-fast --avoid preset:broadside
```

Ranking is addition of visible components (topic +3, mood +2 each, register +2, energy +2/+1, confidence bonus, slow render -1). It proposes candidates by subject only. **Rule A/B still decide whether the result differs enough from recent videos.** 13 topics are covered: ai-ml, software-dev, data-science, science, security, finance-business, productivity, news-opinion, history-culture, consumer-lifestyle, wellness-nature, kids-education, announcements.

## Evidence from the ep3 spike (all on a copy; shipped ep3 untouched)

Environment: cloud Linux, 2 cores, 8 GB, software GL, hyperframes 0.8.114, 1080x1920, draft quality.

| Test | Result |
| --- | --- |
| Baseline ep3 | `check` passes, renders in 1m56s. Rule A **fails** (1 distinct backdrop of 6). |
| Variant A: six preset-derived backdrops (ink, cobalt, charcoal, forest, plum, orange) | Rule A **passes** (6/6), `check` passes (98/98 contrast). Independent critic: "six templates from one pack", continuity 6 vs 9, would ship the baseline. Computed verdict `revise`. |
| Variant C: one navy/indigo/teal family, varied by tier and structure | Rule A **passes** (5/6 distinct). `check` passes. Critic: reads as one series, no hard failure, would ship C. Computed verdict `revise` (avg 7.38; the remaining weakness is composition shared with the baseline). Baseline computes `reject` (hard failure `generic_template_look`). |
| Variant D: C + CSS push-slide (2->3) + blur-crossfade (4->5) | `check` passes; blur-crossfade raises `content_overlap` warnings; push-slide none. Renders in 1m45s, frames confirm both transitions. |
| Shader sampler, all 14 shaders | Default path: silent hard cuts. Node-side path: effects over **black** scene textures, 13m55s for 18 s of video. **Fail in this environment; unverified on a Mac.** |

The critic's score for the unchanged baseline moved up to 2 points between rounds. Treat single-round scores as direction, not measurement.

## Rules this implies

1. Pick backdrops from one preset or palette family. Vary tier and structure, not hue family. Rule A counts differences; the critic judges whether they belong together.
2. Raise shared layers (captions, progress, brand marks) above scenes before giving scenes opaque backgrounds.
3. Use CSS transitions for production. Mark overlap windows `data-layout-allow-overlap`. Do not use shader transitions until a Mac render proves them (record it with `verified`).
4. Vendor preset fonts into `assets/` before rendering (`hyperframes-localize-fonts`); presets assume web fonts.
5. Do not mix a preset's colours with another preset's typography by hand without re-running `check`; spike A mixed four presets' colours only and did not test typography or caption skins.

## Open work (needs owner approval before changing the pipeline)

- Fix Rule B to read the opening scene or measured backdrops (DL-005); until then Rule B mislabels per-scene-backdrop videos.
- Per-series `brand/design.md` shell read by compose, with shared accent tokens.
- Test shader transitions and one full preset (`frame.md` typography, caption skin) on the Mac.
- Composition fixes the critic raised, independent of backdrops: content fills only ~60% of the 9:16 frame, faint secondary text, handle does not spell the channel name.
- Evidence overlay writer (`<workspace>/intelligence/design-evidence.json`) fed by the critic, so confidence moves from evidence, not from this file.
