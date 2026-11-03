"""scenekit primitives: data-backed stage builders. Each returns (html, js) for one scene.

Contract: input is the authored `visual:` mapping (already validated by planner.validate_visual). Output is plain
HTML/SVG plus GSAP calls on the shared paused timeline `tl`, all time-addressable (no onUpdate, no Math.random, no
timers). Element ids are prefixed with the scene id so scenes never collide. `g` is the geometry/token dict from
compose: sw/sh (stage px), U (short side), portrait, tk (style tokens).
"""
from __future__ import annotations

import html
import re

e = html.escape


def _split2(label: str) -> list[str]:
    if len(label) <= 12 or " " not in label:
        return [label]
    words, best = label.split(), None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        cand = (max(len(a), len(b)), [a, b])
        best = cand if best is None or cand[0] < best[0] else best
    return best[1]


def _layers(ids: list[str], edges: list) -> tuple[dict, set]:
    """Longest-path layering over a DFS-acyclic edge set. Returns (layer by id, indexes of back edges)."""
    adj = {i: [] for i in ids}
    for k, ed in enumerate(edges):
        adj[ed[0]].append((ed[1], k))
    state, back = {}, set()

    def dfs(u):
        state[u] = 1
        for v, k in adj[u]:
            if state.get(v) == 1:
                back.add(k)
            elif v not in state:
                dfs(v)
        state[u] = 2
    for i in ids:
        if i not in state:
            dfs(i)
    layer = {i: 0 for i in ids}
    for _ in range(len(ids)):
        for k, ed in enumerate(edges):
            if k not in back and layer[ed[1]] < layer[ed[0]] + 1:
                layer[ed[1]] = layer[ed[0]] + 1
    return layer, back


def diagram(v, sid, t, d, g):
    nodes, edges = v["nodes"], v["edges"]
    ids = [n["id"] for n in nodes]
    layer, back = _layers(ids, edges)
    nl = max(layer.values()) + 1
    sw, sh, U, tk = g["sw"], g["sh"], g["U"], g["tk"]
    pad = 0.05 * U
    rows: dict[int, list[str]] = {}
    for i in ids:
        rows.setdefault(layer[i], []).append(i)
    vertical = g["portrait"]
    along, across = (sh, sw) if vertical else (sw, sh)
    pos, size = {}, {}
    for l, members in rows.items():
        k = len(members)
        for j, i in enumerate(members):
            a = pad + (l + 0.5) * (along - 2 * pad) / nl
            c = (j + 0.5) * across / k
            slot = (along - 2 * pad) / nl
            if vertical:
                bw, bh = min(across / k - 0.03 * U, 0.46 * U), min(0.125 * U, slot * 0.66)
            else:
                bw, bh = min(slot * 0.72, 0.30 * U), min(0.125 * U, across / k - 0.03 * U)
            pos[i] = (c, a) if vertical else (a, c)
            size[i] = (bw, bh)
    fs_min, fs_max = 0.030 * U, 0.046 * U
    lines = {n["id"]: _split2(n["label"]) for n in nodes}
    svg = [f'<svg viewBox="0 0 {sw:.0f} {sh:.0f}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">',
           f'<defs><marker id="{sid}ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           f'<path d="M0,0 L10,5 L0,10 z" fill="{tk["accent"]}"/></marker></defs>']
    js, order = [], sorted(ids, key=lambda i: (layer[i], ids.index(i)))
    reveal = 0.55 * d
    for r, i in enumerate(order):
        cx, cy = pos[i]
        bw, bh = size[i]
        fs = max(fs_min, min(fs_max, bh * 0.30, bw / (max(len(x) for x in lines[i]) * 0.62)))
        tx = "".join(f'<tspan x="{cx:.1f}" dy="{(0 if q == 0 else fs * 1.15):.1f}">{e(x)}</tspan>' for q, x in enumerate(lines[i]))
        y0 = cy + fs * 0.36 - (len(lines[i]) - 1) * fs * 0.575
        svg.append(f'<g id="{sid}n{r}" opacity="0"><rect x="{cx - bw / 2:.1f}" y="{cy - bh / 2:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="{0.018 * U:.0f}" '
                   f'fill="{tk["panel"]}" stroke="{tk["accent"]}" stroke-width="3"/>'
                   f'<text x="{cx:.1f}" y="{y0:.1f}" text-anchor="middle" font-family="{e(tk["hfont"], quote=True)}" '
                   f'font-weight="700" font-size="{fs:.0f}" fill="{tk["ink"]}">{tx}</text></g>')
        js.append(f'tl.fromTo("#{sid}n{r}",{{opacity:0,y:18}},{{opacity:1,y:0,duration:.35,ease:"power3.out"}},{t + 0.15 + reveal * r / max(len(order), 1):.2f});')
    idx = {i: r for r, i in enumerate(order)}
    n_e = len(edges)
    for k, ed in enumerate(edges):
        a, b = ed[0], ed[1]
        (x1, y1), (x2, y2) = pos[a], pos[b]
        (w1, h1), (w2, h2) = size[a], size[b]
        fwd = layer[b] > layer[a] and k not in back
        if fwd and vertical:
            p = (x1, y1 + h1 / 2, x2, y2 - h2 / 2); c = (x1, (y1 + y2) / 2, x2, (y1 + y2) / 2)
        elif fwd:
            p = (x1 + w1 / 2, y1, x2 - w2 / 2, y2); c = ((x1 + x2) / 2, y1, (x1 + x2) / 2, y2)
        else:                                            # same-layer or back edge: bow out to the side
            off = 0.09 * U
            p = (x1 + w1 / 2, y1, x2 + w2 / 2, y2); c = (x1 + w1 / 2 + off, y1, x2 + w2 / 2 + off, y2)
        d_attr = f"M{p[0]:.1f},{p[1]:.1f} C{c[0]:.1f},{c[1]:.1f} {c[2]:.1f},{c[3]:.1f} {p[2]:.1f},{p[3]:.1f}"
        svg.append(f'<path id="{sid}e{k}" d="{d_attr}" pathLength="1" fill="none" stroke="{tk["accent"]}" stroke-width="4" '
                   f'stroke-dasharray="1" stroke-dashoffset="1" opacity="0" marker-end="url(#{sid}ar)"/>')   # markers ignore the dash, so hide the whole path until it draws
        et = t + 0.15 + reveal * (max(idx[a], idx[b]) + 0.3) / max(len(order), 1)
        js.append(f'tl.set("#{sid}e{k}",{{opacity:1}},{et:.2f});tl.to("#{sid}e{k}",{{strokeDashoffset:0,duration:.4,ease:"power2.out"}},{et:.2f});')
        if len(ed) > 2:
            mx = 0.125 * p[0] + 0.375 * c[0] + 0.375 * c[2] + 0.125 * p[2]
            my = 0.125 * p[1] + 0.375 * c[1] + 0.375 * c[3] + 0.125 * p[3]
            side = -1 if mx < sw / 2 - 1 else 1                     # push the label off the curve, outward
            svg.append(f'<text id="{sid}l{k}" x="{mx + side * 0.03 * U:.1f}" y="{my:.1f}" text-anchor="{"end" if side < 0 else "start"}" opacity="0" '
                       f'font-family="{e(tk["mono"], quote=True)}" font-size="{0.028 * U:.0f}" '
                       f'fill="{tk["accent2"]}" stroke="{tk["bg"]}" stroke-width="6" paint-order="stroke">{e(ed[2])}</text>')
            js.append(f'tl.to("#{sid}l{k}",{{opacity:1,duration:.3}},{et + 0.3:.2f});')
        # data packet: sampled bezier keyframes, one hop per edge, after the reveal
        steps = 14
        kf = []
        for s in range(1, steps + 1):
            u = s / steps; m = 1 - u
            x = m ** 3 * p[0] + 3 * m * m * u * c[0] + 3 * m * u * u * c[2] + u ** 3 * p[2]
            y = m ** 3 * p[1] + 3 * m * m * u * c[1] + 3 * m * u * u * c[3] + u ** 3 * p[3]
            kf.append(f'{{x:{x - p[0]:.1f},y:{y - p[1]:.1f},duration:{0.9 / steps:.3f},ease:"none"}}')
        svg.append(f'<circle id="{sid}p{k}" cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{0.011 * U:.1f}" fill="{tk["accent2"]}" opacity="0"/>')
        hop_t = t + reveal + 0.35 + k * min(0.6, max(0.2, (0.9 * d - reveal - 0.35) / max(n_e, 1)))
        hop_t = min(hop_t, t + d - 1.2)
        js.append(f'tl.set("#{sid}p{k}",{{opacity:1,x:0,y:0}},{hop_t:.2f});'
                  f'tl.to("#{sid}p{k}",{{keyframes:[{",".join(kf)}]}},{hop_t:.2f});'
                  f'tl.set("#{sid}p{k}",{{opacity:0}},{hop_t + 0.92:.2f});')
    svg.append("</svg>")
    return "".join(svg), "".join(js)


_KW = re.compile(r"\b(def|class|return|if|else|elif|for|in|import|from|const|let|var|function|async|await|try|catch|while|with|as|true|false|null|None|True|False|echo|export)\b")
_TOK = re.compile(r"(#.*$|//.*$)|(\"[^\"]*\"|'[^']*')|(\b\d+(?:\.\d+)?\b)|(\b[A-Za-z_]+\b)")


def _hl(line: str, tk) -> str:
    out, pos = [], 0
    for m in _TOK.finditer(line):
        out.append(e(line[pos:m.start()]))
        txt = e(m.group(0))
        if m.group(1): out.append(f'<span style="color:{tk["muted"]}">{txt}</span>')
        elif m.group(2): out.append(f'<span style="color:#a5d6ff">{txt}</span>')
        elif m.group(3): out.append(f'<span style="color:{tk["accent2"]}">{txt}</span>')
        elif _KW.fullmatch(m.group(0)): out.append(f'<span style="color:#ff7b72">{txt}</span>')
        else: out.append(txt)
        pos = m.end()
    out.append(e(line[pos:]))
    return "".join(out)


def code(v, sid, t, d, g):
    tk, U, sw = g["tk"], g["U"], g["sw"]
    lines = str(v["code"]).rstrip("\n").split("\n")
    term = v.get("kind") == "terminal"
    cols = max(len(x) for x in lines)
    fs = min(0.036 * U, (sw - 0.10 * U) / (max(cols, 16) * 0.6))
    rows = []
    for k, ln in enumerate(lines):
        if term and ln.startswith("$ "):
            body = f'<span style="color:{tk["accent"]}">$</span> {e(ln[2:])}'
        elif term:
            body = f'<span style="color:{tk["muted"]}">{e(ln)}</span>'
        else:
            body = _hl(ln, tk)
        gutter = "" if term else f'<span class="gut">{k + 1}</span>'
        rows.append(f'<div class="cl" id="{sid}c{k}" style="opacity:0">{gutter}<span class="ct">{body or "&nbsp;"}</span></div>')
    title = e(v.get("file") or ("terminal" if term else "code"))
    htm = (f'<div class="codepanel" style="font-size:{fs:.0f}px"><div class="cbar"><i></i><i></i><i></i><b>{title}</b></div>'
           f'<div class="cbody">{"".join(rows)}</div></div>')
    js, n = [], len(lines)
    for k in range(n):
        js.append(f'tl.fromTo("#{sid}c{k}",{{opacity:0,x:-14}},{{opacity:1,x:0,duration:.25,ease:"power2.out"}},{t + 0.15 + 0.45 * d * k / max(n, 1):.2f});')
    focus = v.get("focus") or []
    base = t + 0.62 * d
    for j, f in enumerate(focus):
        at = base + j * (0.34 * d / len(focus))
        for k in range(n):
            on = (k + 1) == f
            js.append(f'tl.to("#{sid}c{k}",{{opacity:{1 if on else 0.32},backgroundColor:"{"rgba(126,231,135,.16)" if on else "rgba(0,0,0,0)"}",duration:.2}},{at:.2f});')
    return htm, "".join(js)


def compare(v, sid, t, d, g):
    cols, js = [], []
    for si, (side, color) in enumerate((("left", "accent"), ("right", "accent2"))):
        s = v[side]
        pts = "".join(f'<li id="{sid}{side[0]}p{k}" style="opacity:0">{e(p)}</li>' for k, p in enumerate(s["points"]))
        cols.append(f'<div class="cmp" id="{sid}{side[0]}" style="opacity:0;border-color:{g["tk"][color]}">'
                    f'<h3 style="color:{g["tk"][color]}">{e(s["title"])}</h3><ul>{pts}</ul></div>')
        t0 = t + 0.2 + si * 0.28 * d
        js.append(f'tl.fromTo("#{sid}{side[0]}",{{opacity:0,y:30}},{{opacity:1,y:0,duration:.4,ease:"power3.out"}},{t0:.2f});')
        for k in range(len(s["points"])):
            js.append(f'tl.fromTo("#{sid}{side[0]}p{k}",{{opacity:0,x:-16}},{{opacity:1,x:0,duration:.3}},{t0 + 0.3 + k * 0.18 * (d / 4):.2f});')
    return f'<div class="cmpwrap">{cols[0]}<div class="vs">VS</div>{cols[1]}</div>', "".join(js)


def stat(v, sid, t, d, g):
    tk = g["tk"]
    parts, js = [], []
    if v.get("value"):
        parts.append(f'<div class="bigstat" id="{sid}v" style="opacity:0">{e(str(v["value"]))}</div>')
        js.append(f'tl.fromTo("#{sid}v",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:.5,ease:"power3.out"}},{t + 0.15:.2f});')
    if v.get("label"):
        parts.append(f'<div class="statlabel" id="{sid}lb" style="opacity:0">{e(v["label"])}</div>')
        js.append(f'tl.to("#{sid}lb",{{opacity:1,duration:.4}},{t + 0.45:.2f});')
    bars = v.get("bars") or []
    if bars:
        mx = max(b["value"] for b in bars) or 1
        unit = e(v.get("unit", ""))
        for k, b in enumerate(bars):
            pct = 100 * b["value"] / mx
            col = tk["accent"] if k % 2 == 0 else tk["accent2"]
            parts.append(f'<div class="bar"><span class="bl">{e(b["label"])}</span><div class="bt"><div class="bf" id="{sid}b{k}" style="width:0;background:{col}"></div></div>'
                         f'<span class="bv">{e(str(b["value"]))}{unit}</span></div>')
            js.append(f'tl.to("#{sid}b{k}",{{width:"{pct:.1f}%",duration:.7,ease:"power3.out"}},{t + 0.5 + k * 0.18:.2f});')
    foot = f'Source: {e(v["source"])}' if v.get("source") else "Illustrative data, not a measurement"
    parts.append(f'<div class="foot">{foot}</div>')
    return f'<div class="statwrap">{"".join(parts)}</div>', "".join(js)


def steps(v, sid, t, d, g):
    items, js = [], []
    n = len(v["steps"])
    for k, s in enumerate(v["steps"]):
        items.append(f'<div class="stp" id="{sid}s{k}" style="opacity:0"><span class="sn">{k + 1}</span><span class="st">{e(s)}</span></div>')
        at = t + 0.2 + 0.62 * d * k / n
        js.append(f'tl.fromTo("#{sid}s{k}",{{opacity:0,x:-24}},{{opacity:1,x:0,duration:.35,ease:"power3.out"}},{at:.2f});')
    return f'<div class="stpwrap"><div class="spine"></div>{"".join(items)}</div>', "".join(js)


BUILDERS = {"diagram": diagram, "code": code, "compare": compare, "stat": stat, "steps": steps}
