"""Rendered-output gate: catches visual failures that lint/check and exit codes do not.

Static `hyperframes check` passed while (KF-004) shader transitions rendered as hard cuts or black frames and (KF-005)
opaque scene backgrounds hid the captions. This module looks at the render itself (frames, log) and at the layer order in
the source, so success is never inferred from "no error".

  python -m contentos.production.visual_gate log <render.log> [--shader]
  python -m contentos.production.visual_gate layers <project dir | index.html>
  python -m contentos.production.visual_gate captions <video.mp4> --region x,y,w,h --canvas 1080x1920 (--timing timing.json | --windows a:b,...)
  python -m contentos.production.visual_gate transitions <video.mp4> --at start:duration[:kind] [--at ...] [--allow-dip]

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
    ends_black = int(is_black(la)) + int(is_black(lb))
    black_frac = (sum(r["black"] for r in rows) + ends_black) / (len(rows) + 2)
    inter = sum(r["intermediate"] and not r["black"] for r in rows)
    if ab < MIN_ENDPOINT_DISTANCE or (la < BLACK_LUMA and lb < BLACK_LUMA):
        verdict = "inconclusive"
    elif black_frac > MAX_BLACK_FRACTION and not allow_dip:
        verdict = "black"
    elif inter >= MIN_INTERMEDIATE:
        verdict = "blend"
    else:
        verdict = "hard_cut"
    return {"kind": kind, "start": start, "duration": duration, "verdict": verdict, "ok": verdict == "blend",
            "endpoint_distance": round(ab, 4), "neighbour_luma": [round(la, 4), round(lb, 4)], "margin": round(margin, 3),
            "black_fraction": round(black_frac, 3), "intermediate_samples": inter, "samples": rows,
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
    if uses_shaders is None:
        uses_shaders = bool(re.search(r'"hasShaderTransitions":\s*true', text))
    out = []
    for pat, code, sev, msg in _LOG_RULES:
        if re.search(pat, text):
            shader_only = code.startswith("shader_") or code == "page_side_compositing_unavailable"
            if shader_only and not uses_shaders:
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
            ok = frac >= MIN_TEXT_FRACTION
            visible += ok
            rows.append({"t": round(t, 3), "ink_fraction": round(frac, 4), "visible": ok})
    ratio = visible / len(rows) if rows else 0.0
    return {"ok": bool(rows) and ratio >= MIN_VISIBLE_RATIO, "visible_ratio": round(ratio, 3), "required": MIN_VISIBLE_RATIO,
            "samples": rows, "region": list(region), "canvas": list(canvas),
            "limits": "detects absence of text-like ink in the region; narration gaps legitimately show no caption, hence a ratio"}


def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _rules(css):
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", _strip_comments(css)):
        yield [s.strip() for s in m.group(1).split(",")], m.group(2)


def _prop(body, name):
    m = re.search(r"(?<![\w-])" + re.escape(name) + r"\s*:\s*([^;}]+)", body)
    return m.group(1).strip() if m else None


def _opaque(value):
    """True when the background value contains a solid colour (6/3-digit hex, rgb(), or rgba with alpha ~1)."""
    v = (value or "").lower()
    if re.search(r"#[0-9a-f]{6}\b|#[0-9a-f]{3}\b", v) or "rgb(" in v:
        return True
    return any(float(x) >= 0.99 for x in re.findall(r"rgba\([^)]*,\s*([\d.]+)\s*\)", v))


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
        z = inline.get(sid, info["z"] if info["z"] is not None else default_scene["z"])
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
    css = html
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
    return 0 if res.get("ok", True) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="visual_gate", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    lg = sub.add_parser("log"); lg.add_argument("log"); lg.add_argument("--shader", action="store_true", default=None)
    ly = sub.add_parser("layers"); ly.add_argument("target")
    cp = sub.add_parser("captions"); cp.add_argument("video"); cp.add_argument("--region"); cp.add_argument("--canvas", default="1080x1920")
    cp.add_argument("--timing"); cp.add_argument("--windows"); cp.add_argument("--project", help="read the caption region from this project's CSS")
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
