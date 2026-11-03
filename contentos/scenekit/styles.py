"""scenekit styles: versioned render styles for Track A.

A style is more than a palette. It fixes the frame LAYOUT (where headline, stage and caption sit), typography, a
primary motion preset plus alternates, a scene transition, the caption treatment and which scene types it prefers.
Two styles must differ on at least MIN_DIFF of the structural axes (checked by `distinct()`), so a recolour cannot
pass as a new style. Fonts are system stacks: nothing is downloaded at render time.

Status is `unvalidated` until a real render on this Mac has been inspected (see docs/video-intelligence/08-*).
"""
from __future__ import annotations

import itertools

STYLE_SCHEMA = "scenekit-style/1"
MIN_DIFF = 3
LAYOUTS = ("top-head", "lower-third", "split-editorial", "kinetic")
MOTIONS = ("rise", "push", "slam", "push-in", "wipe", "cut")
CAPTIONS = ("pill", "plain", "rule")
STAGE_TYPES = ("diagram", "code", "compare", "stat", "steps")
TEXT_TYPES = ("statement", "pullquote", "split")

SANS = '"Helvetica Neue",Helvetica,Arial,sans-serif'
MONO = '"SF Mono",Menlo,Consolas,monospace'

STYLES: dict[str, dict] = {
    "clean-explainer": {
        "version": 1, "name": "Clean Technical Explainer", "card": None,
        "summary": "Light paper ground, one blue accent, big diagrams, quiet rise-in motion. Clarity over atmosphere.",
        "best_for": ["kubernetes", "networking", "cloud", "how-to", "concept"],
        "layout": "top-head", "caption": "pill", "motion": "rise", "alt_motions": ["wipe"],
        "affinity": {"statement": 2, "pullquote": 0, "split": 1, "diagram": 3, "code": 2, "compare": 3, "stat": 3, "steps": 3},
        "grounds": ['linear-gradient(180deg,#f3f1ea,#ece9df)', 'linear-gradient(180deg,#e2eaf6,#d8e3f2)', 'linear-gradient(180deg,#f7e5d6,#f1dac8)'],
        "tokens": {
            "bg": "#f6f5f1", "bg2": "#e9e7df", "ink": "#14161a", "muted": "#5b6270", "accent": "#2563eb",
            "accent2": "#ea580c", "hl": "#fbbf24", "capbg": "rgba(20,22,26,.92)", "capink": "#ffffff",
            "panel": "#ffffff", "line": "#c9c6bb", "font": SANS, "hfont": SANS, "mono": MONO,
            "cw": 0.6, "hweight": 800, "hcase": "none", "hscale": 0.072, "hero": 0.105, "track": "-0.02em",
            "bgcss": "radial-gradient(circle at 80% 0%,#fffdf6 0,#f6f5f1 45%,#e9e7df 100%)",
        },
    },
    "kinetic-type": {
        "version": 1, "name": "Kinetic Typography", "card": "kinetic-typography",
        "summary": "Black ground, acid-yellow accent, giant condensed words that slam in on the beat. Hard cuts.",
        "best_for": ["hook", "opinion", "short", "announcement"],
        "layout": "kinetic", "caption": "plain", "motion": "slam", "alt_motions": ["cut"],
        "affinity": {"statement": 2, "pullquote": 4, "split": 1, "diagram": 1, "code": 1, "compare": 2, "stat": 3, "steps": 1},
        "grounds": ['linear-gradient(180deg,#0a0a0a,#111)', 'linear-gradient(180deg,#2a0a16,#1c0710)', 'linear-gradient(180deg,#170b34,#0f0724)'],
        "tokens": {
            "bg": "#0a0a0a", "bg2": "#161616", "ink": "#ffffff", "muted": "#9a9a9a", "accent": "#d9ff3f",
            "accent2": "#ff3d71", "hl": "#d9ff3f", "capbg": "transparent", "capink": "#ffffff",
            "panel": "#151515", "line": "#333333", "font": SANS,
            "hfont": 'Impact,"Haettenschweiler","Arial Narrow Bold",sans-serif', "mono": MONO,
            "cw": 0.5, "hweight": 400, "hcase": "uppercase", "hscale": 0.095, "hero": 0.185, "track": "0",
            "bgcss": "linear-gradient(180deg,#0a0a0a,#111)",
        },
    },
    "editorial-magazine": {
        "version": 1, "name": "Editorial / Magazine", "card": None,
        "summary": "Warm paper, high-contrast serif, big section numerals, hairline rules, left-aligned and asymmetric. Horizontal push.",
        "best_for": ["history", "research", "industry", "explainer", "analysis"],
        "layout": "split-editorial", "caption": "rule", "motion": "push", "alt_motions": ["rise"],
        "affinity": {"statement": 1, "pullquote": 3, "split": 4, "diagram": 2, "code": 1, "compare": 3, "stat": 4, "steps": 2},
        "grounds": ['linear-gradient(180deg,#f2eadb,#e9dfca)', 'linear-gradient(180deg,#e0e6cf,#d5ddc0)', 'linear-gradient(180deg,#eed6c9,#e6c8b8)'],
        "tokens": {
            "bg": "#efe6d6", "bg2": "#e4d8c3", "ink": "#1b1a17", "muted": "#6a604f", "accent": "#c2410c",
            "accent2": "#0f3d3e", "hl": "#c2410c", "capbg": "transparent", "capink": "#1b1a17",
            "panel": "#f8f2e6", "line": "#1b1a17", "font": 'Charter,"Iowan Old Style",Georgia,serif',
            "hfont": 'Didot,"Bodoni 72","Playfair Display",Georgia,serif', "mono": MONO,
            "cw": 0.58, "hweight": 700, "hcase": "none", "hscale": 0.082, "hero": 0.115, "track": "-0.015em",
            "bgcss": "linear-gradient(180deg,#f2eadb,#e9dfca)",
        },
    },
    "blueprint-architecture": {
        "version": 2, "name": "Architecture and Data Visualization", "card": "blueprint-diagram",
        "summary": "Light engineering-drafting paper, blue linework on a fine grid, red annotations, monospace labels, diagram-dominant frames with flowing data packets. Wipe reveals.",
        "best_for": ["architecture", "distributed", "devops", "microservices", "pipeline", "event"],
        "layout": "top-head", "caption": "plain", "motion": "wipe", "alt_motions": ["rise"],
        "affinity": {"statement": 1, "pullquote": 0, "split": 0, "diagram": 5, "code": 2, "compare": 3, "stat": 3, "steps": 4},
        "grounds": [
            'linear-gradient(rgba(29,78,216,.10) 1px,transparent 1px),linear-gradient(90deg,rgba(29,78,216,.10) 1px,transparent 1px),linear-gradient(180deg,#eef3f9,#e3ebf5)',
            'linear-gradient(rgba(29,78,216,.10) 1px,transparent 1px),linear-gradient(90deg,rgba(29,78,216,.10) 1px,transparent 1px),linear-gradient(180deg,#f7f1e4,#efe6d2)',
            'linear-gradient(rgba(29,78,216,.10) 1px,transparent 1px),linear-gradient(90deg,rgba(29,78,216,.10) 1px,transparent 1px),linear-gradient(180deg,#e6f2ec,#d9eadf)'],
        "tokens": {
            "bg": "#eef3f9", "bg2": "#e3ebf5", "ink": "#0f2a4a", "muted": "#4b6a8f", "accent": "#1d4ed8",
            "accent2": "#dc2626", "hl": "#dc2626", "capbg": "transparent", "capink": "#0f2a4a",
            "panel": "rgba(255,255,255,.72)", "line": "#9db6d6", "font": SANS, "hfont": MONO, "mono": MONO,
            "cw": 0.66, "hweight": 700, "hcase": "uppercase", "hscale": 0.052, "hero": 0.115, "track": "0.02em",
            "bgcss": ("linear-gradient(rgba(29,78,216,.10) 1px,transparent 1px),"
                      "linear-gradient(90deg,rgba(29,78,216,.10) 1px,transparent 1px),"
                      "linear-gradient(180deg,#eef3f9,#e3ebf5)"),
            "bgsize": "64px 64px,64px 64px,auto",
        },
    },
    "code-first": {
        "version": 1, "name": "Code-First Developer Tutorial", "card": None,
        "summary": "Editor-dark ground, syntax-coloured code panels and terminals that fill the frame. Hard cuts, lines reveal in order.",
        "best_for": ["programming", "api", "cli", "tutorial", "debugging", "python"],
        "layout": "top-head", "caption": "pill", "motion": "cut", "alt_motions": ["rise"],
        "affinity": {"statement": 1, "pullquote": 0, "split": 0, "diagram": 2, "code": 5, "compare": 3, "stat": 2, "steps": 3},
        "grounds": ['linear-gradient(180deg,#0d1117,#0a0d12)', 'linear-gradient(180deg,#0a2a1c,#071e14)', 'linear-gradient(180deg,#1d1230,#140b24)'],
        "tokens": {
            "bg": "#0d1117", "bg2": "#010409", "ink": "#e6edf3", "muted": "#8b949e", "accent": "#7ee787",
            "accent2": "#ffa657", "hl": "#7ee787", "capbg": "#161b22", "capink": "#e6edf3",
            "panel": "#161b22", "line": "#30363d", "font": SANS, "hfont": '"Avenir Next","Segoe UI",Helvetica,sans-serif', "mono": MONO,
            "cw": 0.6, "hweight": 700, "hcase": "none", "hscale": 0.060, "hero": 0.115, "track": "-0.01em",
            "bgcss": "linear-gradient(180deg,#0d1117,#010409)",
        },
    },
    "cinematic-documentary": {
        "version": 1, "name": "Cinematic Tech Documentary", "card": "slow-parallax-story",
        "summary": "Warm-black ground, amber light, serif lower-third titles, letterbox bars and a slow push-in. Slow crossfades.",
        "best_for": ["history", "story", "ai", "infrastructure", "why", "future"],
        "layout": "lower-third", "caption": "plain", "motion": "push-in", "alt_motions": ["rise"],
        "affinity": {"statement": 4, "pullquote": 3, "split": 1, "diagram": 2, "code": 1, "compare": 2, "stat": 3, "steps": 1},
        "grounds": ['radial-gradient(ellipse at 30% 25%,#5a3516 0,#2b1808 55%,#150c05 100%)', 'radial-gradient(ellipse at 30% 25%,#12525a 0,#0b2c31 55%,#06161a 100%)', 'radial-gradient(ellipse at 30% 25%,#5a1c58 0,#2e0f2d 55%,#170817 100%)'],
        "tokens": {
            "bg": "#0b0807", "bg2": "#050404", "ink": "#f3ead8", "muted": "#b8a98f", "accent": "#e0a458",
            "accent2": "#6fa8a0", "hl": "#e0a458", "capbg": "transparent", "capink": "#f3ead8",
            "panel": "rgba(243,234,216,.06)", "line": "#5a4a36", "font": SANS,
            "hfont": '"Iowan Old Style",Palatino,Georgia,serif', "mono": MONO,
            "cw": 0.58, "hweight": 600, "hcase": "none", "hscale": 0.075, "hero": 0.115, "track": "0",
            "bgcss": "radial-gradient(ellipse at 30% 25%,#3a2616 0,#150e0a 45%,#050404 100%)",
        },
    },
}

AXES = ("layout", "caption", "motion", "font_family", "ground")


def _ground(t: dict) -> str:
    h = t["bg"].lstrip("#")
    return "light" if sum(int(h[i:i + 2], 16) for i in (0, 2, 4)) > 450 else "dark"


def axes_of(style_id: str) -> dict:
    s = STYLES[style_id]
    return {"layout": s["layout"], "caption": s["caption"], "motion": s["motion"],
            "font_family": s["tokens"]["hfont"].split(",")[0].strip('"'), "ground": _ground(s["tokens"])}


def ground_for(style_id: str, index: int, seed: int) -> int:
    """Deterministic ground index for scene `index` (1-based). Cyclic, so any >= 3 scenes use all 3 grounds."""
    return (index + seed) % len(STYLES[style_id]["grounds"])


def get(style_id: str) -> dict:
    if style_id not in STYLES:
        raise ValueError(f"unknown visual style {style_id!r}; known: {', '.join(sorted(STYLES))}")
    return STYLES[style_id]


def distinct() -> list[tuple[str, str, int]]:
    """Pairs of styles that differ on fewer than MIN_DIFF axes (should be empty)."""
    bad = []
    for a, b in itertools.combinations(STYLES, 2):
        n = sum(axes_of(a)[k] != axes_of(b)[k] for k in AXES)
        if n < MIN_DIFF:
            bad.append((a, b, n))
    return bad


def validate() -> list[str]:
    problems = []
    for sid, s in STYLES.items():
        if s["layout"] not in LAYOUTS: problems.append(f"{sid}: bad layout")
        if s["motion"] not in MOTIONS or any(m not in MOTIONS for m in s["alt_motions"]): problems.append(f"{sid}: bad motion")
        if s["caption"] not in CAPTIONS: problems.append(f"{sid}: bad caption")
        for t in STAGE_TYPES + TEXT_TYPES:
            if t not in s["affinity"]: problems.append(f"{sid}: affinity missing {t}")
    for sid, s in STYLES.items():
        if len(s["grounds"]) < 3: problems.append(f"{sid}: needs >= 3 grounds (Rule A)")
    problems += [f"{a} and {b} differ on only {n} axes" for a, b, n in distinct()]
    return problems
