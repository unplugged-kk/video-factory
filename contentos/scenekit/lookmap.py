"""lookmap: compile a look/1 preset into a scenekit style (P1-1 M1, compile only, nothing in the pipeline calls it yet).

A look is data (3 colours, a font name, a texture tag, motion 1-5). scenekit needs a complete style (layout, 12+ tokens,
grounds, motion, caption). So a look is compiled ONTO a tested base style: the base supplies layout, caption kind, affinity
and the token skeleton; the look overrides palette, fonts, motion and texture. Fails closed: an unmapped font or texture,
an unknown base style or poor contrast raises LookBlocked naming the reason. Nothing is substituted silently.

Not read in this milestone, and reported as such: look `effects`, free-text `layout`, `audio`, `captions` wording.

  python -m contentos.scenekit.lookmap report        which of the presets compile, and why the rest are blocked
  python -m contentos.scenekit.lookmap show <id>     the compiled style as JSON
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from urllib.parse import quote

from ..intelligence import looks as L
from . import styles as S

MIN_INK, MIN_ACCENT = 4.5, 3.0   # WCAG-style ratios: text, chart marks

_SANS = '"Avenir Next","Helvetica Neue",Helvetica,Arial,sans-serif'
_HELV = '"Helvetica Neue",Helvetica,Arial,sans-serif'
_IMPACT = 'Impact,"Haettenschweiler","Arial Narrow Bold",sans-serif'
_SERIF = 'Didot,"Bodoni 72",Georgia,serif'
_HAND = '"Marker Felt","Bradley Hand","Chalkboard SE",cursive'
_DEVA = '"Kohinoor Devanagari","Devanagari Sangam MN",sans-serif'

# look font name -> installed macOS stack plus the heading traits the stack implies (cw = avg glyph width in em)
FONTS: dict[str, dict] = {
    "Outfit": {"stack": _SANS, "cw": 0.6, "weight": 800, "case": "none"},
    "Inter": {"stack": _HELV, "cw": 0.6, "weight": 800, "case": "none"},
    "Anton": {"stack": _IMPACT, "cw": 0.5, "weight": 400, "case": "uppercase"},
    "Bangers": {"stack": _IMPACT, "cw": 0.5, "weight": 400, "case": "uppercase"},
    "Noto Sans Devanagari": {"stack": _DEVA, "cw": 0.6, "weight": 700, "case": "none"},
    "Space Mono": {"stack": S.MONO, "cw": 0.62, "weight": 700, "case": "none"},
    "DM Serif Display": {"stack": _SERIF, "cw": 0.56, "weight": 700, "case": "none"},
    "Fraunces": {"stack": _SERIF, "cw": 0.56, "weight": 700, "case": "none"},
    "Playfair Display": {"stack": _SERIF, "cw": 0.56, "weight": 700, "case": "none"},
    "Permanent Marker": {"stack": _HAND, "cw": 0.58, "weight": 700, "case": "none"},
    "Kalam": {"stack": _HAND, "cw": 0.55, "weight": 700, "case": "none"},
    "Caveat": {"stack": _HAND, "cw": 0.5, "weight": 700, "case": "none"},
}

BASE_BY_FAMILY = {"explainer": "clean-explainer", "talking-head": "clean-explainer", "story": "cinematic-documentary",
                  "lyric": "kinetic-type", "repurpose": "clean-explainer", "any": "clean-explainer"}
MOTION_BY_INTENSITY = {1: "rise", 2: "rise", 3: "push", 4: "cut", 5: "slam"}

NO_TEXTURE = {"flat", "flat-card", "flat-ui", "flat-fill", "flat-pastel", "flat-shade", "mono"}
# CSS-only textures. Each returns (image, size) layers; compose paints them in M2 (grounds are one-size shorthand, so
# tiles cannot live in `grounds`).
GRAIN = {"paper-grain": (0.8, .10), "paper-sketch": (0.9, .08), "paper-cutout": (0.7, .07), "crayon-grain": (0.55, .14),
         "chalk-dust": (1.1, .12), "graphite": (1.0, .10), "film-grain": (0.9, .14)}
PAINTABLE = set(GRAIN) | {"halftone-dots", "grid", "scanline", "glow", "neon-glow", "wash", "print", "red-grade"}
# everything else needs illustration, particles or a backdrop filter that scenekit does not have
BLOCKED_TEXTURE = {"rain", "smoke", "curtain", "paint-splat", "frosted-glass", "depth-blur", "marker-swipe", "pattern-fill",
                   "starry-backdrop", "clean-outline", "line-art", "double-outline", "panel-border", "decorated-border"}


class LookBlocked(ValueError):
    def __init__(self, look_id: str, reasons: list[str]):
        self.look_id, self.reasons = look_id, reasons
        super().__init__(f"look {look_id!r} cannot compile onto scenekit: " + "; ".join(reasons))


# ---- colour maths ----------------------------------------------------------------------------------------------------
def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(c) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in c)


def mix(a: str, b: str, t: float) -> str:
    """t=0 -> a, t=1 -> b."""
    return _hex(tuple(x + (y - x) * t for x, y in zip(_rgb(a), _rgb(b))))


def rgba(h: str, a: float) -> str:
    r, g, b = _rgb(h)
    return f"rgba({r},{g},{b},{a})"


def _lin(v: int) -> float:
    v /= 255
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def lum(h: str) -> float:
    r, g, b = (_lin(v) for v in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


# ---- textures --------------------------------------------------------------------------------------------------------
def _grain(freq: float, alpha: float, dark: bool) -> str:
    c = 1 if dark else 0
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'>"
           f"<feTurbulence type='fractalNoise' baseFrequency='{freq}' numOctaves='2' stitchTiles='stitch'/>"
           f"<feColorMatrix values='0 0 0 0 {c} 0 0 0 0 {c} 0 0 0 0 {c} 0 0 0 {alpha * 6:.2f} 0'/></filter>"
           "<rect width='100%' height='100%' filter='url(#n)'/></svg>")
    return "url(data:image/svg+xml;utf8," + quote(svg, safe="") + ")"   # fully escaped: no quote or paren can leak into a style attr


def texture_layers(tag: str, fg: str, accent: str, dark: bool) -> list[dict]:
    if tag in GRAIN:
        return [{"image": _grain(*GRAIN[tag], dark), "size": "180px 180px"}]
    return {
        "halftone-dots": [{"image": f"radial-gradient({rgba(fg, .12)} 1.3px,transparent 1.8px)", "size": "14px 14px"}],
        "grid": [{"image": f"linear-gradient({rgba(fg, .07)} 1px,transparent 1px)", "size": "40px 40px"},
                 {"image": f"linear-gradient(90deg,{rgba(fg, .07)} 1px,transparent 1px)", "size": "40px 40px"}],
        "scanline": [{"image": "repeating-linear-gradient(0deg,rgba(0,0,0,.18) 0 2px,transparent 2px 4px)", "size": "auto"}],
        "glow": [{"image": f"radial-gradient(circle at 50% 30%,{rgba(accent, .28)},transparent 60%)", "size": "auto"}],
        "neon-glow": [{"image": f"radial-gradient(circle at 50% 30%,{rgba(accent, .34)},transparent 62%)", "size": "auto"}],
        "wash": [{"image": f"radial-gradient(ellipse at 30% 20%,{rgba(accent, .18)},transparent 55%)", "size": "auto"},
                 {"image": f"radial-gradient(ellipse at 80% 80%,{rgba(accent, .12)},transparent 50%)", "size": "auto"}],
        "print": [{"image": f"repeating-linear-gradient(0deg,{rgba(fg, .06)} 0 1px,transparent 1px 6px)", "size": "auto"}],
        "red-grade": [{"image": "linear-gradient(180deg,rgba(180,0,0,.18),rgba(80,0,0,.28))", "size": "auto"}],
    }[tag]


# ---- compile ---------------------------------------------------------------------------------------------------------
def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _base_id(look: dict, reasons: list[str]) -> str | None:
    want = look.get("base_style")
    if want:
        for sid, s in S.STYLES.items():
            if want in (sid, s.get("card")):
                return sid
        reasons.append(f"base_style {want!r} matches no scenekit style (known: {', '.join(sorted(S.STYLES))})")
        return None
    return BASE_BY_FAMILY[look["family"]]


def to_style(look: dict, base: str | None = None) -> dict:
    """Return a complete scenekit style dict for `look`, or raise LookBlocked. Pure and deterministic."""
    reasons: list[str] = []
    if look.get("kind") != "look":
        raise LookBlocked(look.get("id", "?"), ["only kind=look compiles to a style, not an effect"])
    base_id = base or _base_id(look, reasons)
    typ, pal = look["typography"], look["palette"]
    for role in ("display", "body"):
        if typ.get(role) not in FONTS:
            reasons.append(f"font {typ.get(role)!r} ({role}) has no system mapping; add it to FONTS or choose another")
    tags = look.get("texture", [])
    for t in tags:
        if t in NO_TEXTURE or t in PAINTABLE:
            continue
        reasons.append(f"texture {t!r} " + ("needs illustration or particles scenekit lacks" if t in BLOCKED_TEXTURE else "is not mapped"))
    bg, fg, acc = pal["bg"], pal["fg"], pal["accent"]
    if contrast(fg, bg) < MIN_INK:
        reasons.append(f"ink/bg contrast {contrast(fg, bg):.2f} < {MIN_INK}")
    if contrast(acc, bg) < MIN_ACCENT:
        reasons.append(f"accent/bg contrast {contrast(acc, bg):.2f} < {MIN_ACCENT}")
    if reasons:
        raise LookBlocked(look["id"], reasons)

    st = copy.deepcopy(S.STYLES[base_id])
    dark = lum(bg) < 0.4
    tk = st["tokens"]
    muted = next(mix(fg, bg, t) for t in (.35, .25, .15, 0) if contrast(mix(fg, bg, t), bg) >= MIN_INK)
    disp, body = FONTS[typ["display"]], FONTS[typ["body"]]
    pill = st["caption"] == "pill"
    bg2 = mix(bg, fg, .06)
    tk.update({
        "bg": bg, "bg2": bg2, "ink": fg, "muted": muted, "accent": acc, "accent2": mix(acc, fg, .45), "hl": acc,
        "panel": mix(bg, fg, .08) if dark else mix(bg, "#ffffff", .6), "line": mix(bg, fg, .25),
        "capbg": rgba(fg, .92) if pill else "transparent", "capink": bg if pill else fg,
        "font": body["stack"], "hfont": disp["stack"], "mono": S.MONO,
        "cw": disp["cw"], "hweight": disp["weight"], "hcase": disp["case"],
    })
    grounds = [f"linear-gradient(180deg,{bg},{bg2})",
               f"linear-gradient(180deg,{mix(bg, acc, .08)},{mix(bg, acc, .14)})",
               f"linear-gradient(180deg,{mix(bg, tk['accent2'], .08)},{mix(bg, tk['accent2'], .14)})"]
    tk["bgcss"] = grounds[0]
    layers = [x for t in tags if t in PAINTABLE for x in texture_layers(t, fg, acc, dark)]
    tk["texture"] = layers   # painted by compose in M2; empty list = none
    motion = MOTION_BY_INTENSITY[int(look["motion"]["intensity"])]
    st.update({
        "name": look["name"], "card": None, "summary": look["summary"], "best_for": [look["family"]], "grounds": grounds,
        "motion": motion, "alt_motions": [m for m in (st["alt_motions"] + ["wipe", "rise"]) if m != motion][:1],
        "version": 1,
    })
    bad = S.check_style(look["id"], st)
    if bad:
        raise LookBlocked(look["id"], bad)
    st["look"] = {"id": look["id"], "base": base_id, "look_digest": _digest(look),
                  "unread": [k for k in ("effects", "layout") if look.get(k)],
                  "style_digest": _digest({k: v for k, v in st.items() if k != "look"})}
    return st


def axes(style: dict) -> dict:
    return {"layout": style["layout"], "caption": style["caption"], "motion": style["motion"],
            "font_family": style["tokens"]["hfont"].split(",")[0].strip('"'), "ground": S._ground(style["tokens"])}


def axes_differing(a: dict, b: dict) -> int:
    x, y = axes(a), axes(b)
    return sum(x[k] != y[k] for k in S.AXES)


def compile_all(directory=L.PRESETS_DIR) -> dict[str, dict | LookBlocked]:
    out: dict[str, dict | LookBlocked] = {}
    for i, d in L.load_dir(directory).items():
        if d["kind"] != "look":
            continue
        try:
            out[i] = to_style(d)
        except LookBlocked as e:
            out[i] = e
    return out


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    res = compile_all()
    if a[:1] == ["show"] and len(a) == 2:
        r = res.get(a[1])
        if r is None:
            print(f"unknown look {a[1]!r}", file=sys.stderr)
            return 2
        if isinstance(r, LookBlocked):
            print(r, file=sys.stderr)
            return 1
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0
    ok = [i for i, r in res.items() if not isinstance(r, LookBlocked)]
    print(f"{len(ok)} of {len(res)} looks compile onto scenekit\n")
    for i, r in res.items():
        print(f"  OK       {i}" if i in ok else f"  BLOCKED  {i}: " + "; ".join(r.reasons))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
