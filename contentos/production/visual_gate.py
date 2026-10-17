"""Rendered-output gate: catches visual failures that lint/check and exit codes do not.

Static `hyperframes check` passed while (KF-004) shader transitions rendered as hard cuts or black frames and (KF-005)
opaque scene backgrounds hid the captions. This module looks at the render itself (frames, log) and at the layer order in
the source, so success is never inferred from "no error".

  python -m contentos.production.visual_gate log <render.log> [--shader]
  python -m contentos.production.visual_gate layers <project dir | index.html>
  python -m contentos.production.visual_gate captions <video.mp4> --region x,y,w,h --canvas 1080x1920 (--timing timing.json | --windows a:b,...)
  python -m contentos.production.visual_gate transitions <video.mp4> --at start:duration[:kind] [--at ...] [--allow-dip]
  python -m contentos.production.visual_gate safezone <video.mp4> (--times t,t,... | --timing timing.json) [--canvas 1080x1920] [--zone name:x,y,w,h ...]

Exit codes: 0 ok, 1 finding, 2 unreadable input. Output is JSON on stdout.

Every check is measured from pixels or text and states its limits: it detects "this is a hard cut / black / hidden", it does
not judge whether a transition looks good. Pure Python + ffmpeg (no numpy/PIL), so it runs wherever the factory runs.
Thresholds are provisional and documented next to each function; they are calibrated on the ep3 spike renders only."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

W_S, H_S = 24, 42                      # steady-state frame thumbnail (area-averaged); enough to tell scenes/blends apart
BLACK_LUMA = 0.04                      # mean luma below this counts as a black frame
ENDPOINT_MIN_LUMA = 0.05               # black only counts when a neighbour is at least this bright (pure blue is 0.072; just above BLACK_LUMA)
HARD_CUT_RATIO = 0.10                  # a sample within 10% of AB distance from an endpoint is "still an endpoint"
MIN_INTERMEDIATE = 1                   # blend needs at least this many samples that look like neither endpoint
MAX_BLACK_FRACTION = 0.30
MIN_ENDPOINT_DISTANCE = 0.02           # below this the neighbours are the same picture; nothing to tell
TEXT_DEVIATION = 0.18                  # a pixel this far from the region median luma counts as "text" ink
MIN_TEXT_FRACTION = 0.01               # fraction of region pixels that must be ink for captions to count as visible
MAX_TEXT_FRACTION = 0.60               # MORE ink than this is texture (a busy picture), not caption text: text is sparse
MIN_VISIBLE_RATIO = 0.70               # share of sampled caption moments where captions must be visible


class GateError(Exception):
    pass


# ---- pixels ---------------------------------------------------------------------------------------------------------

def _ffmpeg_frame(video, t, vf, size):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{max(t, 0):.3f}", "-i", str(video), "-frames:v", "1", "-vf", vf,
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    try:
        p = subprocess.run(cmd, capture_output=True, check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GateError(f"ffmpeg failed: {exc}") from exc
    need = size[0] * size[1] * 3
    if len(p.stdout) < need:
        raise GateError(f"no frame at t={t:.3f}s in {video} ({p.stderr.decode(errors='replace').strip()[:160] or 'past end?'})")
    return p.stdout[:need]


def frame(video, t, w=W_S, h=H_S):
    return _ffmpeg_frame(video, t, f"scale={w}:{h}:flags=area", (w, h))


def region_luma(video, t, canvas, region, w=108, h=21):
    cw, ch = canvas
    x, y, rw, rh = region
    x, y = max(0, min(x, cw - 1)), max(0, min(y, ch - 1))
    rw, rh = max(1, min(rw, cw - x)), max(1, min(rh, ch - y))
    buf = _ffmpeg_frame(video, t, f"crop={rw}:{rh}:{x}:{y},scale={w}:{h}:flags=area", (w, h))
    return [(0.2126 * buf[i] + 0.7152 * buf[i + 1] + 0.0722 * buf[i + 2]) / 255.0 for i in range(0, len(buf), 3)]


def _mean_rgb(buf):
    n = len(buf) // 3
    return [sum(buf[c::3]) / n / 255.0 for c in range(3)]


def _luma(buf):
    r, g, b = _mean_rgb(buf)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _dist(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a) / 255.0


# ---- KF-004: transitions and render log ---------------------------------------------------------------------------

DENSE_FPS = 60                         # dense scan of a transition window: up to this many frames per second of window...
DENSE_MAX_FRAMES = 240                 # ...and never more than this many frames per window (bounds cost: one ffmpeg call, 32x32 gray-ish thumbs)
_DENSE_PX = 32


def dense_black_frames(video, start, duration):
    """Mean luma of (nearly) every frame inside [start, start+duration], from ONE ffmpeg decode of the window scaled to
    32x32. Rate = min(DENSE_FPS, DENSE_MAX_FRAMES/duration) frames/s, so cost is bounded (<=240 tiny frames) however long
    the window is. Returns [] when the window cannot be decoded (the spot-check samples still run)."""
    if duration <= 0:
        return []
    fps = min(DENSE_FPS, DENSE_MAX_FRAMES / duration)
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{max(start, 0):.3f}", "-t", f"{duration:.3f}", "-i", str(video),
           "-vf", f"fps={fps:.4f},scale={_DENSE_PX}:{_DENSE_PX}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    try:
        p = subprocess.run(cmd, capture_output=True, check=False, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return []
    n = _DENSE_PX * _DENSE_PX * 3
    return [_luma(p.stdout[i:i + n]) for i in range(0, len(p.stdout) - n + 1, n)]


def check_transition(video, start, duration, kind="css", samples=7, allow_dip=False, margin=None):
    """Sample inside [start, start+duration] and compare with steady frames taken `margin` seconds outside the window
    (default half the window, at least 0.1s), so a blackout that begins at the window edge cannot hide as "steady".

    verdict: blend (ok) | hard_cut (the window never leaves one neighbour's picture) | black (too many black frames, including a
    black neighbour, while the other neighbour is not black) | inconclusive (both neighbours are the same picture, or both
    black, so a transition is undetectable). `allow_dip` accepts a dip to black as intended (colour-dip transitions)."""
    margin = max(0.1, duration * 0.5) if margin is None else margin
    a = frame(video, start - margin)
    b = frame(video, start + duration + margin)
    ab = _dist(a, b)
    la, lb = _luma(a), _luma(b)
    bright = max(la, lb) > ENDPOINT_MIN_LUMA

    def is_black(luma):
        return luma < BLACK_LUMA and bright

    rows = []
    for k in range(samples):
        t = start + duration * (k + 1) / (samples + 1)
        s = frame(video, t)
        da, db, ls = _dist(s, a), _dist(s, b), _luma(s)
        rows.append({"t": round(t, 3), "d_from_before": round(da, 4), "d_from_after": round(db, 4), "luma": round(ls, 4),
                     "black": is_black(ls), "intermediate": min(da, db) > HARD_CUT_RATIO * max(ab, 1e-9)})
    dense = dense_black_frames(video, start, duration)
    dense_black = sum(1 for v in dense if is_black(v))
    ends_black = int(is_black(la)) + int(is_black(lb))
    black_frac = (sum(r["black"] for r in rows) + ends_black) / (len(rows) + 2)
    inter = sum(r["intermediate"] and not r["black"] for r in rows)
    if ab < MIN_ENDPOINT_DISTANCE or (la < BLACK_LUMA and lb < BLACK_LUMA):
        verdict = "inconclusive"
    elif (black_frac > MAX_BLACK_FRACTION or any(r["black"] for r in rows) or dense_black) and not allow_dip:
        # ANY black frame inside the window is a black gap (a single black frame in a blend is a visible flash). Besides the
        # `samples` spot checks, the dense scan looks at (nearly) every frame of the window, so a 2-3 frame flash between
        # spot checks is caught. Only a flash shorter than the dense scan spacing (1/DENSE_FPS s) can still be missed.
        verdict = "black"
    elif inter >= MIN_INTERMEDIATE:
        verdict = "blend"
    else:
        verdict = "hard_cut"
    return {"kind": kind, "start": start, "duration": duration, "verdict": verdict, "ok": verdict == "blend",
            "endpoint_distance": round(ab, 4), "neighbour_luma": [round(la, 4), round(lb, 4)], "margin": round(margin, 3),
            "black_fraction": round(black_frac, 3), "intermediate_samples": inter, "samples": rows,
            "dense_frames_scanned": len(dense), "dense_black_frames": dense_black,
            "limits": "detects hard cuts/black/no-op only; does not judge whether the transition looks good"}


_LOG_RULES = (
    (r"falling back to opacity-flip", "shader_fallback_opacity_flip", "error",
     "HyperShader fell back to opacity flips: shader transitions render as HARD CUTS in this environment."),
    (r"drawElementImage/WebGL is not available", "page_side_compositing_unavailable", "error",
     "Page-side shader compositing is unavailable (no drawElementImage in this Chromium)."),
    (r"failed to compile", "shader_compile_failed", "error", "A shader failed to compile and was replaced by a crossfade."),
    (r"Unknown shader", "shader_unknown", "error", "A transition names a shader that does not exist."),
    (r"Render failed|render_cancelled|capture_hdr_layered\"[^\n]*\"status\":\"error\"", "render_failed", "error",
     "The render did not finish."),
    (r"Streaming encoder exited", "encoder_exited", "error", "The encoder stopped mid-render."),
    (r"Low-memory render profile active", "low_memory_profile", "info",
     "Low-memory profile chose screenshot capture; shader/page-side behaviour differs from a high-memory machine."),
    (r"BeginFrame did not run", "no_beginframe", "info", "BeginFrame capture unavailable; screenshot capture used (slower)."),
)


def scan_render_log(text, uses_shaders=None):
    """Findings from a hyperframes render log. `uses_shaders` defaults to what the log itself says."""
    auto = uses_shaders is None                     # an explicit uses_shaders=False from the caller still suppresses shader rules
    if uses_shaders is None:
        uses_shaders = bool(re.search(r'"hasShaderTransitions":\s*true', text))
    out = []
    for pat, code, sev, msg in _LOG_RULES:
        if re.search(pat, text):
            shader_only = code.startswith("shader_") or code == "page_side_compositing_unavailable"
            # A fallback / unknown-shader line is itself proof that shaders were requested, so it is reported even when the
            # log lacks the hasShaderTransitions marker (older HyperFrames, trimmed logs). The other shader_* rules stay gated.
            self_evident = auto and code in ("shader_fallback_opacity_flip", "shader_unknown")
            if shader_only and not uses_shaders and not self_evident:
                continue
            out.append({"code": code, "severity": sev, "message": msg})
    return out


def fallback_plan(findings):
    """Explicit, recorded fallback when shaders cannot be trusted. Data only: nothing here edits a composition."""
    if any(f["code"].startswith("shader_") or f["code"] == "page_side_compositing_unavailable" for f in findings):
        return {"action": "use_css_transition", "suggest": ["css-transition:push-slide", "css-transition:crossfade"],
                "reason": "shader transitions are not renderable here; do not report them as succeeded",
                "record": "set the library entry's validation for this environment to fail"}
    return None


# ---- KF-005: captions ---------------------------------------------------------------------------------------------

def check_captions(video, windows, canvas, region, samples_per_window=1):
    """Is there caption ink in the caption region at the given moments? Ink = pixels far from the region's median luma.
    Rendered proof; a structural layer check alone cannot show captions are actually on screen."""
    rows, visible = [], 0
    for (t0, t1) in windows:
        for k in range(samples_per_window):
            t = t0 + (t1 - t0) * (k + 1) / (samples_per_window + 1)
            lum = region_luma(video, t, canvas, region)
            med = sorted(lum)[len(lum) // 2]
            frac = sum(abs(v - med) > TEXT_DEVIATION for v in lum) / len(lum)
            # Busy background with no captions deviates from the median almost everywhere (measured 0.37-0.81 on testsrc2;
            # box-text captions measure ~0.23), so an upper bound keeps texture from passing as captions.
            ok = MIN_TEXT_FRACTION <= frac <= MAX_TEXT_FRACTION
            visible += ok
            rows.append({"t": round(t, 3), "ink_fraction": round(frac, 4), "visible": ok})
    ratio = visible / len(rows) if rows else 0.0
    return {"ok": bool(rows) and ratio >= MIN_VISIBLE_RATIO, "visible_ratio": round(ratio, 3), "required": MIN_VISIBLE_RATIO,
            "samples": rows, "region": list(region), "canvas": list(canvas),
            "max_ink_fraction": MAX_TEXT_FRACTION,
            "limits": "detects absence of text-like ink in the region (ink above max_ink_fraction counts as texture, not text); narration gaps legitimately show no caption, hence a ratio"}


# ---- G6: 9:16 safe zones ----------------------------------------------------------------------------------------------

EDGE_JUMP = 0.08                       # a neighbour-to-neighbour luma step this large counts as a hard edge (text, outlines). Was 0.20, which
                                       # missed e.g. dark-grey text (luma 0.22) on a near-black background (step 0.13). Measured on the two real
                                       # known-good/-bad renders: ceiling worst zone edge fraction 0.0035 at 0.08 (limit 0.01; 0.0074 at 0.06),
                                       # so 0.08 keeps ~3x headroom. Steps below ~0.08 (barely visible) are still not seen.
MAX_ZONE_EDGE_FRACTION = 0.01          # more edge pixels than this share of a zone means "content sits in the zone"
# Fractions of the canvas as (name, x, y, w, h). Conservative HEURISTICS carried over from the motion-ab experiments
# (top ~150 px, bottom ~350 px, right ~180 px strip below y=1000 on 1080x1920). They are NOT published platform specs;
# platform UI changes, so override with --zone and verify on a real phone.
DEFAULT_SAFE_ZONES_9_16 = (
    ("top", 0.0, 0.0, 1.0, 150 / 1920),
    ("bottom", 0.0, 1 - 350 / 1920, 1.0, 350 / 1920),
    ("right", 1 - 180 / 1080, 1000 / 1920, 180 / 1080, (1 - 350 / 1920) - 1000 / 1920),
)


def default_zones(canvas):
    """Pixel zones [(name, x, y, w, h)] for a canvas. Only defined for portrait (9:16-ish); returns [] otherwise."""
    cw, ch = canvas
    if cw >= ch:
        return []
    return [(n, int(fx * cw), int(fy * ch), max(1, int(fw * cw)), max(1, int(fh * ch))) for n, fx, fy, fw, fh in DEFAULT_SAFE_ZONES_9_16]


_CANVAS_RE = re.compile(r"^\s*(\d+)\s*[xX]\s*(\d+)\s*$")
_ZONE_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_INT_RE = re.compile(r"^-?\d+$")


def parse_canvas(text):
    """'1080x1920' -> (1080, 1920). Positive integers only; anything else is a GateError that says what was expected."""
    m = _CANVAS_RE.match(str(text))
    if not m or int(m.group(1)) <= 0 or int(m.group(2)) <= 0:
        raise GateError(f"--canvas must look like 1080x1920 (positive whole numbers), got {text!r}")
    return int(m.group(1)), int(m.group(2))


def video_size(video):
    """(width, height) of the first video stream, via ffprobe. GateError when it cannot be read.
    Coded size: a rotated phone clip whose display size differs will not match and is reported as a mismatch (fail closed)."""
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(video)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
        st = json.loads(p.stdout or "{}").get("streams") or []
        if p.returncode != 0 or not st:
            raise GateError(f"cannot read video dimensions from {video} ({p.stderr.strip()[:160] or 'no video stream'})")
        return int(st[0]["width"]), int(st[0]["height"])
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
        raise GateError(f"cannot read video dimensions from {video}: {exc}") from exc


def check_canvas_matches_video(video, canvas):
    """The configured canvas is never replaced by the detected size; a difference is an error, not a pass."""
    actual = video_size(video)
    if tuple(canvas) != actual:
        raise GateError(f"--canvas {canvas[0]}x{canvas[1]} does not match the video's actual size {actual[0]}x{actual[1]}; "
                        "pass the real size (nothing was measured)")
    return actual


def parse_zone(spec):
    """'name:x,y,w,h' -> (name, x, y, w, h). Syntax only; bounds are checked against the canvas by validate_zones."""
    name, sep, box = str(spec).partition(":")
    if not sep or not _ZONE_NAME_RE.match(name):
        raise GateError(f"--zone {spec!r}: expected name:x,y,w,h (name of letters, digits, _ or -), e.g. caption:0,1500,1080,300")
    parts = [v.strip() for v in box.split(",")]
    if len(parts) != 4:
        raise GateError(f"--zone {spec!r}: expected exactly 4 numbers x,y,w,h after the name, got {len(parts)}")
    bad = [v for v in parts if not _INT_RE.match(v)]
    if bad:
        raise GateError(f"--zone {spec!r}: x,y,w,h must be whole numbers, got {bad[0]!r}")
    x, y, w, h = (int(v) for v in parts)
    return name, x, y, w, h


def validate_zones(zones, canvas):
    """GateError for a zone with a negative origin, a non-positive size, a duplicate name, or an extent outside the canvas."""
    cw, ch = canvas
    seen = set()
    for name, x, y, w, h in zones:
        if name in seen:
            raise GateError(f"zone {name!r} is given more than once")
        seen.add(name)
        if x < 0 or y < 0:
            raise GateError(f"zone {name!r}: x and y must not be negative (got {x},{y})")
        if w <= 0 or h <= 0:
            raise GateError(f"zone {name!r}: width and height must be positive (got {w}x{h})")
        if x + w > cw or y + h > ch:
            raise GateError(f"zone {name!r}: {x},{y},{w},{h} extends outside the {cw}x{ch} canvas")


def _edge_fraction(video, t, canvas, zone, max_w=216):
    cw, ch = canvas
    _, x, y, zw, zh = zone
    x, y = max(0, min(x, cw - 1)), max(0, min(y, ch - 1))
    zw, zh = max(1, min(zw, cw - x)), max(1, min(zh, ch - y))
    w = max(2, min(zw, max_w))
    h = max(2, round(zh * w / zw))
    buf = _ffmpeg_frame(video, t, f"crop={zw}:{zh}:{x}:{y},scale={w}:{h}:flags=area", (w, h))
    lum = [(0.2126 * buf[i] + 0.7152 * buf[i + 1] + 0.0722 * buf[i + 2]) / 255.0 for i in range(0, len(buf), 3)]
    edges = 0
    for r in range(h):
        for c in range(w):
            v = lum[r * w + c]
            if (c + 1 < w and abs(lum[r * w + c + 1] - v) > EDGE_JUMP) or (r + 1 < h and abs(lum[(r + 1) * w + c] - v) > EDGE_JUMP):
                edges += 1
    return edges / (w * h)


def check_safe_zones(video, times, canvas, zones=None):
    """Is hard-edged content (text, outlines, icons) sitting in the platform-UI zones at the sampled moments?
    Smooth gradients and flat backgrounds have no hard edges and do not count. ok = no sample exceeds the threshold.
    This is a pixel heuristic on a render: it cannot tell a caption from decoration, and the default zones are not platform specs."""
    cw, ch = canvas
    if cw <= 0 or ch <= 0:
        raise GateError(f"canvas must have positive dimensions, got {cw}x{ch}")
    check_canvas_matches_video(video, canvas)               # before anything else: a wrong canvas must never look like a result
    zones = default_zones(canvas) if zones is None else zones
    validate_zones(zones, canvas)
    if not zones:
        # Nothing was checked, so this must never read as a pass: ok False, status "not_applicable", vacuous True, checked
        # False. The CLI exits 3 for it (distinct from 1 = content found, 2 = error); see _out.
        return {"ok": False, "applicable": False, "status": "not_applicable", "vacuous": True, "checked": False, "zones": [], "samples": [], "canvas": list(canvas),
                "reason": "no default safe zones for this canvas; the gate did not look at the picture",
                "limits": "no default zones for a landscape canvas; pass --zone to check one"}
    rows, flagged = [], []
    for t in times:
        for z in zones:
            frac = _edge_fraction(video, t, canvas, z)
            hit = frac > MAX_ZONE_EDGE_FRACTION
            rows.append({"t": round(t, 3), "zone": z[0], "edge_fraction": round(frac, 4), "content": hit})
            if hit:
                flagged.append({"t": round(t, 3), "zone": z[0]})
    return {"ok": bool(rows) and not flagged, "applicable": True, "flagged": flagged, "threshold": MAX_ZONE_EDGE_FRACTION,
            "zones": [{"name": n, "region": [x, y, w, h]} for n, x, y, w, h in zones], "samples": rows, "canvas": list(canvas),
            "limits": "pixel-edge heuristic on sampled frames only; cannot tell caption from decoration; zones are conservative "
                      "heuristics, not published platform specs (platform UI changes); thresholds provisional, uncalibrated on real renders"}


def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _rules(css):
    css = re.sub(r"</?style\b[^>]*>", " ", css, flags=re.I)      # a whole html file passed as css: do not glue <style> onto the first selector
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", _strip_comments(css)):
        yield [s.strip() for s in m.group(1).split(",")], m.group(2)


def _prop(body, name):
    m = re.search(r"(?<![\w-])" + re.escape(name) + r"\s*:\s*([^;}]+)", body)
    return m.group(1).strip() if m else None


_NAMED_COLOURS = frozenset("""aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood
cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgreen
darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray
darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia
gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender
lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink
lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon
mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise
mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid
palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown
royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen
steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen""".split())
_ALPHA_OPAQUE = 0.99


def _alpha(arg_text):
    """Alpha of a css colour function's argument text: 4th comma part, or the part after '/', else 1 (opaque)."""
    parts = re.split(r"\s*/\s*|\s*,\s*", arg_text.strip()) if ("/" in arg_text or "," in arg_text) else arg_text.split()
    if len(parts) < 4 and "/" not in arg_text:
        return 1.0
    a = parts[-1].strip()
    try:
        return float(a[:-1]) / 100 if a.endswith("%") else float(a)
    except ValueError:
        return 1.0


def _opaque(value):
    """Conservative: True when the background value contains ANY fully opaque colour. Recognised: #rgb/#rrggbb (and
    #rgba/#rrggbbaa with alpha ~1), rgb()/rgba()/hsl()/hsla() with alpha ~1, and CSS named colours (not `transparent`).
    A gradient (or multiple backgrounds) counts as opaque if any stop is opaque: a gradient with one opaque stop can still
    hide captions, and a false "opaque" only asks for a higher caption z-index, while a missed one hides captions silently."""
    v = re.sub(r"url\([^)]*\)", " ", (value or "").lower())
    for m in re.finditer(r"#([0-9a-f]+)\b", v):
        h = m.group(1)
        if len(h) in (3, 6) or (len(h) == 4 and h[3] == "f") or (len(h) == 8 and h[6:] == "ff"):
            return True
    for m in re.finditer(r"\b(?:rgba?|hsla?)\(([^)]*)\)", v):
        if _alpha(m.group(1)) >= _ALPHA_OPAQUE:
            return True
    outside = re.sub(r"\b(?:rgba?|hsla?)\([^)]*\)", " ", v)
    return any(w in _NAMED_COLOURS for w in re.findall(r"[a-z]+", outside))


CAPTION_SEL = re.compile(r"^(#captions?|\.captions?|#caption-layer|\.caption-layer|#cap\b)")


def check_caption_layering(css, html=""):
    """Static: can an opaque scene sit above the caption layer? Structural only, JS-set styles are not seen.

    Intent: add `data-captions-intent="behind"` on the caption element to declare captions are meant to sit under scenes. The
    structural finding is then reported as `declared` and a rendered check (`captions`) is REQUIRED, not optional."""
    css = _strip_comments(css)
    cap_z, cap_sel = None, None
    scenes = {}                                     # selector -> {"z": int|None, "opaque": bool}
    default_scene = {"z": None, "opaque": False}
    for sels, body in _rules(css):
        for s in sels:
            if CAPTION_SEL.match(s):
                z = _prop(body, "z-index")
                if z is not None and re.fullmatch(r"-?\d+", z):
                    cap_z = int(z)
                cap_sel = cap_sel or s
            elif re.fullmatch(r"\.scene", s):
                z = _prop(body, "z-index")
                bg = _prop(body, "background") or _prop(body, "background-color") or _prop(body, "background-image")
                if z is not None and re.fullmatch(r"-?\d+", z):
                    default_scene["z"] = int(z)
                default_scene["opaque"] = default_scene["opaque"] or _opaque(bg)
            elif re.match(r"#s-[\w-]+$|#scene[-_][\w-]+$|\.scene[-_][\w-]+$", s):
                bg = _prop(body, "background") or _prop(body, "background-color") or _prop(body, "background-image")
                z = _prop(body, "z-index")
                d = scenes.setdefault(s, {"z": None, "opaque": False})
                d["opaque"] = d["opaque"] or _opaque(bg)
                if z is not None and re.fullmatch(r"-?\d+", z):
                    d["z"] = int(z)
    # inline z-index on scene elements in the html
    inline = {}
    for m in re.finditer(r"<(?:section|div)\b([^>]*)>", html or ""):
        attrs = m.group(1)
        idm = re.search(r'\bid="([^"]+)"', attrs)
        if not idm or not re.search(r'class="[^"]*\bscene\b', attrs):
            continue
        zm = re.search(r"z-index\s*:\s*(-?\d+)", attrs)
        inline["#" + idm.group(1)] = int(zm.group(1)) if zm else None
    intent = bool(re.search(r'data-captions-intent="behind"', html or ""))
    scene_ids = set(inline) | set(scenes)
    opaque_z = []
    for sid in scene_ids:
        info = scenes.get(sid, {"z": None, "opaque": False})
        opaque = info["opaque"] or default_scene["opaque"]
        css_z = info["z"] if info["z"] is not None else default_scene["z"]
        z = inline.get(sid)                                  # inline style wins; an html scene WITHOUT inline z-index uses the CSS rule's
        z = css_z if z is None else z
        if opaque:
            opaque_z.append((sid, 0 if z is None else z))
    findings = []
    cap_eff = 0 if cap_z is None else cap_z
    cap_pos = (html or "").find('id="captions"')
    last_scene = (html or "").rfind('class="scene')
    captions_after = cap_pos < 0 or last_scene < 0 or cap_pos > last_scene      # equal z-index: later in the DOM paints on top
    hiding = [sid for sid, z in opaque_z if z > cap_eff or (z == cap_eff and not captions_after)]
    if cap_sel is None:
        findings.append({"code": "no_caption_layer_found", "severity": "info",
                         "message": "no #captions/.captions rule found; nothing to check"})
    elif hiding:
        sev = "declared" if intent else "error"
        findings.append({"code": "opaque_scene_above_captions", "severity": sev, "scenes": sorted(hiding),
                         "caption_z": cap_z, "message": ("Opaque scene backgrounds sit at or above the caption layer's z-index; "
                                                         "captions can be hidden. Raise the caption layer (z-index above every scene).")
                         + (" Declared intentional; run the rendered `captions` check." if intent else "")})
    ok = not any(f["severity"] == "error" for f in findings)
    return {"ok": ok, "findings": findings, "rendered_check_required": bool(intent or hiding),
            "limits": "static parse of CSS + inline z-index; JS-set styles and shadow DOM are not seen"}


def caption_region_from_css(css, canvas):
    """Pixel region of the caption layer from its CSS (px units only). Returns (x, y, w, h) or None."""
    cw, ch = canvas
    for sels, body in _rules(css):
        if any(CAPTION_SEL.match(s) for s in sels):
            def px(name, body=body):
                v = _prop(body, name)
                m = re.fullmatch(r"(-?[\d.]+)px", v or "")
                return float(m.group(1)) if m else None
            left, right, top, bottom, width, height = (px(n) for n in ("left", "right", "top", "bottom", "width", "height"))
            if height is None:
                continue
            x = left or 0
            w = width if width is not None else cw - x - (right or 0)
            y = top if top is not None else (ch - (bottom or 0) - height if bottom is not None else None)
            if y is None:
                continue
            return (int(x), int(y), int(w), int(height))
    return None


# ---- CLI ------------------------------------------------------------------------------------------------------------

def _find_html(target):
    t = Path(target)
    if t.is_file():
        return t
    for rel in ("project/index.html", "portrait/index.html", "hf/index.html", "index.html"):
        if (t / rel).is_file():
            return t / rel
    raise GateError(f"no index.html under {target}")


def _read_css_html(target):
    p = _find_html(target)
    html = p.read_text(encoding="utf-8", errors="replace")
    blocks = re.findall(r"<style\b[^>]*>(.*?)</style>", html, flags=re.S | re.I)
    css = "\n".join(blocks) if blocks else html            # style blocks only: JS braces in <script> must not parse as css rules
    for href in re.findall(r'<link[^>]+href=["\']([^"\'#?]+\.css)', html):
        if "://" not in href and (p.parent / href).is_file():
            css += "\n" + (p.parent / href).read_text(encoding="utf-8", errors="replace")
    return css, html


def _windows_from_timing(doc, per_scene=2):
    out = []
    for s in doc.get("scenes", []):
        st = s.get("start", s.get("t0"))
        if st is None:
            continue
        d = s.get("dur") or ((s.get("end", st) - st) if "end" in s else 0)
        if d <= 0:
            continue
        for k in range(per_scene):
            out.append((st + d * (0.35 + 0.4 * k / max(per_scene - 1, 1)), st + d * (0.35 + 0.4 * k / max(per_scene - 1, 1)) + 0.0001))
    return out


def _out(res):
    print(json.dumps(res, indent=1))
    if res.get("status") == "not_applicable":
        return 3                                   # nothing was checked: not a pass (0), not a finding (1), not an error (2)
    return 0 if res.get("ok", True) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="visual_gate", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    lg = sub.add_parser("log"); lg.add_argument("log"); lg.add_argument("--shader", action="store_true", default=None)
    ly = sub.add_parser("layers"); ly.add_argument("target")
    cp = sub.add_parser("captions"); cp.add_argument("video"); cp.add_argument("--region"); cp.add_argument("--canvas", default="1080x1920")
    cp.add_argument("--timing"); cp.add_argument("--windows"); cp.add_argument("--project", help="read the caption region from this project's CSS")
    sz = sub.add_parser("safezone"); sz.add_argument("video"); sz.add_argument("--canvas", default="1080x1920")
    sz.add_argument("--times"); sz.add_argument("--timing"); sz.add_argument("--zone", action="append")
    tr = sub.add_parser("transitions"); tr.add_argument("video"); tr.add_argument("--at", action="append", required=True)
    tr.add_argument("--allow-dip", action="store_true"); tr.add_argument("--margin", type=float)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "log":
            text = Path(a.log).read_text(encoding="utf-8", errors="replace")
            f = scan_render_log(text, a.shader)
            return _out({"ok": not any(x["severity"] == "error" for x in f), "findings": f, "fallback": fallback_plan(f)})
        if a.cmd == "layers":
            css, html = _read_css_html(a.target)
            return _out(check_caption_layering(css, html))
        if a.cmd == "captions":
            cw, ch = (int(v) for v in a.canvas.lower().split("x"))
            region = tuple(int(v) for v in a.region.split(",")) if a.region else None
            if region is None and a.project:
                css, _ = _read_css_html(a.project)
                region = caption_region_from_css(css, (cw, ch))
            if region is None:
                raise GateError("give --region x,y,w,h or --project with a px-sized #captions rule")
            if a.windows:
                wins = [tuple(float(v) for v in w.split(":")) for w in a.windows.split(",")]
            elif a.timing:
                wins = _windows_from_timing(json.loads(Path(a.timing).read_text()))
            else:
                raise GateError("give --timing or --windows")
            return _out(check_captions(a.video, wins, (cw, ch), region))
        if a.cmd == "safezone":
            cw, ch = parse_canvas(a.canvas)
            if a.times:
                times = [float(v) for v in a.times.split(",")]
            elif a.timing:
                times = [w[0] for w in _windows_from_timing(json.loads(Path(a.timing).read_text()))]
            else:
                raise GateError("give --times or --timing")
            zones = None
            if a.zone:
                zones = [parse_zone(spec) for spec in a.zone]
            return _out(check_safe_zones(a.video, times, (cw, ch), zones))
        if a.cmd == "transitions":
            res = []
            for spec in a.at:
                p = spec.split(":")
                res.append(check_transition(a.video, float(p[0]), float(p[1]), p[2] if len(p) > 2 else "css", allow_dip=a.allow_dip, margin=a.margin))
            return _out({"ok": all(r["ok"] for r in res), "transitions": res})
    except (GateError, OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
