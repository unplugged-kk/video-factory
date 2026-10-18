# Video Factory — Multi-Renderer & Motion Intelligence Guide

This guide covers the two-provider rendering architecture, the 6-family motion design catalog, feature flags, and how each component is invoked.

---

## 1. Multi-Renderer Architecture

Video Factory unifies video synthesis across multiple underlying rendering technologies through the [`RenderProvider`](../contentos/renderers/base.py) protocol (`contentos/renderers/`). The architecture provides deterministic rendering, word-level caption alignment, audio mastering, and automated QA gates across all providers.

```
contentos/renderers/
├── __init__.py       # Exports RenderProvider, get_renderer, list_renderers, register
├── base.py           # Abstract base class: preflight, validate, compose, render, inspect
├── hyperframes.py    # HyperFramesRenderer (Default: HTML + GSAP timeline)
├── remotion.py       # RemotionRenderer (Selectable: React + TypeScript + spring physics)
├── mpt.py            # MPTRenderer (Containerized stock b-roll + burned subtitles)
└── registry.py       # Provider registry & router
```

### Provider Matrix

| Provider ID | Spec Key (`render:`) | Engine / Runtime | Best For | Default? |
|---|---|---|---|---|
| `hyperframes` | `hyperframes` (or omit) | HTML, GSAP 3, CSS Grid | Technical diagrams, kinetic typography, branded explainers | **Yes** |
| `remotion` | `remotion` | React 18, TypeScript, Remotion CLI | Spring physics, fluid component animations, React layouts | No (Optional) |
| `mpt` | `mpt` | MoneyPrinterTurbo (Docker) | Faceless b-roll shorts using stock footage | No |

---

## 2. How to Select a Renderer in Spec YAML

The rendering engine is selected via the top-level `render:` field in the job spec.

### Example A: HyperFrames (Default)
```yaml
content_id: my-hf-explainer
title: "Autonomous State Persistence"
format: "9:16"
voice: af_heart
render: hyperframes    # Optional; HyperFrames is the default if omitted
features:
  style_card:
    chosen: "sketch-hand-drawn"
  visual_layer: true
  audio_bed: true
  captions_hook: true
  qa_extra: true
script:
  - say: "Every autonomous agent needs durable memory."
    headline: "Agents Need Memory"
    tag: HOOK
```

### Example B: Remotion (React + TypeScript)
```yaml
content_id: my-remotion-explainer
title: "Real-Time Streaming Tokens"
format: "9:16"
voice: af_heart
render: remotion       # Routes to RemotionRenderer
features:
  style_card:
    chosen: "kinetic-typography"
  visual_layer: true
  audio_bed: true
  captions_hook: true
  qa_extra: true
script:
  - say: "Waiting three seconds for an AI response feels broken."
    headline: "Waiting Feels Broken"
    tag: HOOK
```

---

## 3. Motion Design Catalog (6 Visual Families)

The motion catalog (`config/styles/catalog/`) defines structural visual languages. Each style card specifies 6 structural axes (layout system, motion grammar, scene rhythm, depth model, illustration mode, transition family) and dials. Every pair of cards in the catalog strictly differs on &ge; 3 axes.

| Visual Family | Style ID | Layout System | Motion Grammar | Depth Model | Transitions |
|---|---|---|---|---|---|
| **1. Sketch / Hand-drawn** | `sketch-hand-drawn` | `centered-stage` | `draw-on` | `flat` | `morph` |
| **2. Product Launch** | `product-launch` | `stacked-cards` | `eased-glide` | `pseudo-3d` | `push` |
| **3. Kinetic Typography** | `kinetic-typography` | `full-bleed` | `type-driven` | `flat` | `cut` |
| **4. Data Storytelling** | `data-storyteller` | `stacked-cards` | `snap-cut` | `flat` | `cut` |
| **5. Spatial Generative** | `spatial-generative` | `centered-stage` | `eased-glide` | `layered` | `push` |
| **6. Hybrid Craft** | `hybrid-craft` | `split` | `type-driven` | `layered` | `push` |

In addition to the expanded catalog, the 3 foundational seed cards remain in `config/styles/`:
- `blueprint-diagram`: Grid diagrammatic explainer with wipe transitions.
- `punch-split`: Punctuated split screen with eased pushes.
- `slow-parallax-story`: Layered textural depth narrative with dissolves.

### How to Inspect and Validate Styles
```bash
# Validate all catalog styles and verify >= 3 differing axes
~/.contentos/venv/bin/python -m contentos.intelligence.styles validate --dir config/styles/catalog
~/.contentos/venv/bin/python -m contentos.intelligence.styles distinct --dir config/styles/catalog

# Show details of a specific style card
~/.contentos/venv/bin/python -m contentos.intelligence.styles show kinetic-typography --dir config/styles/catalog
```

---

## 4. Pipeline Execution & Production Gates

Every video job passes through 9 deterministic stages:
```
brief > script > voice > compose > render > qa > package > export > publish
```

Two human/operator approval gates protect the production line:
1. **`SCRIPT_APPROVED`**: Required before the `voice` stage generates Kokoro voice audio.
2. **`PRODUCTION_APPROVED`**: Required before the `render` stage compiles and renders video frames.

### Step-by-Step Invocation
```bash
# 1. Check toolchain health
./contentos.sh doctor

# 2. Grant Script Approval for your job
./contentos.sh approve <content_id> SCRIPT_APPROVED

# 3. Grant Production Approval for your job
./contentos.sh approve <content_id> PRODUCTION_APPROVED

# 4. Run the full pipeline
./contentos.sh pipeline run path/to/spec.yaml

# 5. Inspect QA metrics on the rendered MP4
./contentos.sh qa "$VIDEO_FACTORY_WORKSPACE"/jobs/YYYY/MM/<content_id>/video.mp4
```

---

## 5. Feature Flags Explained

Milestone 2 and 3 introduced modular feature hooks behind `spec['features']`. All features are opt-in and leave baseline behavior 100% byte-identical when omitted.

| Feature Hook | Key in `features:` | What It Does |
|---|---|---|
| `style_card` | `style_card: true` or `{chosen: "<id>"}` | Selects or scores a visual style card and writes a creative decision record (`creative-decision.json`). |
| `scene_plan` | `scene_plan: true` | Consumes or synthesizes structured `sceneplan/1` pacing. |
| `visual_layer` | `visual_layer: true` | Injects style-family container decorations and distinct backdrops (Rule A compliant: &ge;4 distinct in 7 scenes). |
| `audio_bed` | `audio_bed: true` | Synthesizes an ambient harmonic pad bed, normalizes loudness to -14 &plusmn; 1 LUFS with true peak &le; -1.0 dBFS, and eliminates digital silence gaps. |
| `captions_hook`| `captions_hook: true` | Injects TikTok/Reels safezone elevation (bottom 460px padding, right 190px padding) to satisfy Gate G6. |
| `qa_extra` | `qa_extra: true` | Adds deterministic audio silence gap checks, end-hold checks, and frozen frame detectors. |

---

## 6. Safezone Compliance (Gate G6)

Vertical video (9:16 / 1080x1920) is viewed inside social app interfaces (YouTube Shorts, TikTok, Instagram Reels) that overlay action buttons, captions, and account tags.

Video Factory enforces strict safezone boundaries across both HyperFrames and Remotion:
- **Top Safezone:** Minimum 150px (default 160px) clear of system UI.
- **Bottom Safezone:** Minimum 460px (`safezone_bottom_padding: 0.24`) clear of app captions and audio badges.
- **Right Safezone:** Minimum 190px (`safezone_side_padding: 190px`) clear of vertical like/comment/share buttons.
- **Left Safezone:** Minimum 70-80px padding for visual breathing room.
