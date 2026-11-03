"""scenekit compose: Track A composition driven by a style + a scene plan. Opt-in via spec['visual_style'].

pipeline.s_compose dispatches here only when the key is present, so every existing spec renders exactly as before.
Rollback = remove `visual_style` from the spec.
"""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

from ..lang import typography
from . import planner, primitives
from . import styles as S

ROOT = Path(__file__).resolve().parent.parent.parent
e = html.escape

_SEL = ["h1", ".tag", ".cap", ".cmp h3", ".cmp li", ".st", "svg text", ".numlabel"]
CSS = """
*{margin:0;box-sizing:border-box}
body{width:var(--W);height:var(--H);overflow:hidden;background:var(--bg);font-family:var(--font);color:var(--ink)}
#root{position:relative;width:var(--W);height:var(--H);background:var(--bg);overflow:hidden}
.scene{position:absolute;inset:0;opacity:0;display:grid;padding:var(--pt) var(--ps) var(--pb);row-gap:var(--gap);overflow:hidden}
.scene>*{position:relative;z-index:1}
.scene>.bg{position:absolute;inset:-6%;z-index:0;background:var(--bgcss);background-size:var(--bgsize)}
.head{display:flex;flex-direction:column;min-height:0}
.tag{font:700 var(--tagpx) var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:.5em}
h1{font-family:var(--hfont);font-weight:var(--hweight);text-transform:var(--hcase);letter-spacing:var(--track);font-size:var(--hs);line-height:1.06}
.stage{height:var(--sh);min-height:0}
.cap{font-size:var(--cappx);font-weight:700;line-height:1.28}
.cap span{display:inline-block;color:var(--capink)}
.no-stage .stage{display:none}
/* layouts */
.L-top-head{grid-template-rows:auto var(--sh) auto;align-content:space-between}
.L-top-head.no-stage{grid-template-rows:minmax(0,1fr) auto}
.L-top-head .head{align-items:flex-start}
.L-top-head.no-stage .head{justify-content:center;align-items:center;text-align:center}
.L-top-head.no-stage h1{font-size:var(--hero)}
.L-kinetic{grid-template-rows:auto var(--sh) auto;align-content:space-between}
.L-kinetic.no-stage{grid-template-rows:minmax(0,1fr) auto}
.L-kinetic .head{align-items:flex-start;justify-content:flex-start}
.L-kinetic h1{line-height:.92}
.L-kinetic.no-stage .head{justify-content:center}
.L-kinetic.no-stage h1{font-size:var(--hero)}
.L-kinetic .tag{background:var(--accent);color:#000;padding:.2em .6em;align-self:flex-start}
.L-lower-third{grid-template-rows:var(--sh) auto auto;align-content:end;text-align:left;padding-top:calc(var(--bar) + var(--U)*.04)}
.L-lower-third .stage{order:-1}
.L-lower-third.no-stage{grid-template-rows:minmax(0,1fr) auto auto}
.L-lower-third.no-stage .stage{display:block;height:auto}
.L-lower-third h1{font-size:var(--hs)}
.L-lower-third.no-stage h1{font-size:var(--hero)}
.L-lower-third>.bg::after{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at 50% 40%,transparent 35%,rgba(0,0,0,.75) 100%)}
.scene>.bars{position:absolute;inset:0;pointer-events:none;z-index:3}
.scene>.wipebar{position:absolute;top:0;bottom:0;left:0;width:40%;z-index:4;background:var(--accent);opacity:.9;transform:translateX(-101%);pointer-events:none}
.bars i{position:absolute;left:0;right:0;height:var(--bar);background:#000;z-index:3}
.bars i:first-child{top:0}.bars i:last-child{bottom:0}
.L-split-editorial{grid-template-rows:auto var(--sh) auto;align-content:space-between;text-align:left}
.L-split-editorial.no-stage{grid-template-rows:minmax(0,1fr) auto}
.L-split-editorial .tag{font-family:var(--hfont);font-size:var(--tagpx);letter-spacing:.04em;text-transform:none;color:var(--accent);border-bottom:3px solid var(--ink);padding-bottom:.35em;margin-bottom:.7em}
.L-split-editorial .cap{border-top:3px solid var(--ink);padding-top:.5em;font-family:var(--font);font-weight:600}
.L-split-editorial.no-stage h1{font-size:var(--hero)}
.L-split-editorial.no-stage .head{justify-content:center}
.cap-pill{background:var(--capbg);color:var(--capink);padding:.55em .85em;border-radius:.6em}
.cap-pill span{color:var(--capink)}
.cap-plain{text-shadow:var(--capshadow)}
/* text-only extras */
.numeral{font-family:var(--hfont);font-size:calc(var(--U)*.42);line-height:.9;color:var(--accent);opacity:.9}
.numlabel{font:700 calc(var(--U)*.034) var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-top:calc(var(--U)*.02)}
.quotebar{width:calc(var(--U)*.16);height:calc(var(--U)*.012);background:var(--accent);margin:0 0 calc(var(--U)*.03)}
/* data stages */
.stage svg{display:block;width:100%;height:100%}
.codepanel{background:var(--panel);border:2px solid var(--line);border-radius:.7em;height:100%;font-family:var(--mono);overflow:hidden}
.cbar{display:flex;align-items:center;gap:.5em;padding:.7em 1em;border-bottom:2px solid var(--line);color:var(--muted);font-size:.7em}
.cbar i{width:.8em;height:.8em;border-radius:50%;background:var(--line)}.cbar b{margin-left:.6em;font-weight:600}
.cbody{padding:.7em .4em;line-height:1.5}
.cl{display:flex;white-space:pre;padding:.05em .6em;border-radius:.3em;color:var(--ink)}
.cl .gut{width:2em;flex:none;color:var(--muted);text-align:right;margin-right:1em}
.cmpwrap{display:flex;flex-direction:column;justify-content:center;gap:calc(var(--U)*.03);height:100%;position:relative}
[data-orient=land] .cmpwrap{flex-direction:row}
[data-orient=land] .vs{top:50%}
.cmp{background:var(--panel);border:3px solid;border-radius:calc(var(--U)*.02);padding:calc(var(--U)*.03) calc(var(--U)*.04);flex:1;min-height:0}
.cmp h3{font-family:var(--hfont);font-size:calc(var(--U)*.048);text-transform:var(--hcase);margin-bottom:.4em;letter-spacing:var(--track)}
.cmp ul{list-style:none}.cmp li{font-size:calc(var(--U)*.036);line-height:1.35;padding:.12em 0;color:var(--ink)}
.cmp li:before{content:"\\2022  ";color:var(--muted)}
.vs{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);z-index:2;background:var(--ink);color:var(--bg);font:800 calc(var(--U)*.03) var(--mono);padding:.3em .7em;border-radius:99px}
.statwrap{height:100%;display:flex;flex-direction:column;justify-content:center;gap:calc(var(--U)*.02)}
.bigstat{font-family:var(--hfont);font-weight:var(--hweight);font-size:calc(var(--U)*.26);line-height:.95;color:var(--accent);letter-spacing:var(--track)}
.statlabel{font-size:calc(var(--U)*.044);color:var(--ink);font-weight:700}
.bar{display:grid;grid-template-columns:calc(var(--U)*.2) 1fr calc(var(--U)*.15);align-items:center;gap:calc(var(--U)*.02);font-size:calc(var(--U)*.034)}
.bt{height:calc(var(--U)*.05);background:var(--line);border-radius:99px;overflow:hidden}.bf{height:100%;border-radius:99px}
.bv{font-family:var(--mono);font-weight:700;text-align:right}.bl{color:var(--muted);font-weight:700}
.foot{font:600 calc(var(--U)*.026) var(--mono);color:var(--muted);margin-top:calc(var(--U)*.01)}
.stpwrap{height:100%;display:flex;flex-direction:column;justify-content:center;gap:calc(var(--U)*.035);position:relative}
.spine{position:absolute;left:calc(var(--U)*.04);top:12%;bottom:12%;width:4px;background:var(--line)}
.stp{display:flex;align-items:center;gap:calc(var(--U)*.04);position:relative}
.sn{flex:none;width:calc(var(--U)*.085);height:calc(var(--U)*.085);border-radius:50%;background:var(--accent);color:var(--bg);display:grid;place-items:center;font:800 calc(var(--U)*.042) var(--mono)}
.st{font-size:calc(var(--U)*.044);font-weight:700;line-height:1.2}
"""


def _vars(W, H, U, tk, cap_pad, side, portrait):
    sh = int(H * (0.46 if portrait else 0.44))
    px = {"W": f"{W}px", "H": f"{H}px", "U": f"{U}px", "pt": f"{int(H * 0.06)}px", "pb": f"{cap_pad}px", "ps": f"{side}px",
          "gap": f"{int(H * 0.02)}px", "sh": f"{sh}px", "hs": f"{int(U * tk['hscale'])}px", "hero": f"{int(U * tk['hero'])}px",
          "cappx": f"{int(U * 0.054)}px", "tagpx": f"{int(U * 0.03)}px", "bar": f"{int(H * 0.07)}px"}
    css = {k: v for k, v in tk.items() if k in ("bg", "ink", "muted", "accent", "accent2", "panel", "line", "capbg", "capink", "bgcss",
                                                  "font", "hfont", "mono", "hweight", "hcase", "track")}
    css["bgsize"] = tk.get("bgsize", "auto")
    css["capshadow"] = "none" if S._ground(tk) == "light" else "0 3px 14px rgba(0,0,0,.35)"   # a dark halo smudges dark text on a light ground
    css["accent"] = tk["accent"]
    allv = {**px, **{k: str(v) for k, v in css.items()}}
    return ":root{" + ";".join(f"--{k}:{v}" for k, v in allv.items()) + "}", sh


def _motion(m, i, t, d, W, tl_head_words):
    s, h, st, bg = f"#s{i}", f"#h{i}", f"#st{i}", f"#bg{i}"
    ex = t + d - 0.25
    if m == "rise":
        return (f'tl.fromTo("{s}",{{opacity:0}},{{opacity:1,duration:.3}},{t:.2f});'
                f'tl.fromTo("{h}",{{y:50,opacity:0}},{{y:0,opacity:1,duration:.5,ease:"power3.out"}},{t + .1:.2f});'
                f'tl.fromTo("{st}",{{y:34,opacity:0}},{{y:0,opacity:1,duration:.5,ease:"power3.out"}},{t + .25:.2f});'
                f'tl.to("{s}",{{opacity:0,duration:.25}},{ex:.2f});')
    if m == "push":
        return (f'tl.fromTo("{s}",{{x:{W * .06:.0f},opacity:0}},{{x:0,opacity:1,duration:.45,ease:"power3.out"}},{t:.2f});'
                f'tl.to("{s}",{{x:{-W * .05:.0f},opacity:0,duration:.3,ease:"power2.in"}},{ex:.2f});')
    if m == "slam":
        return (f'tl.set("{s}",{{opacity:1}},{t:.2f});'
                f'tl.fromTo("{h} .hw",{{scale:1.7,opacity:0,y:-24}},{{scale:1,opacity:1,y:0,duration:.26,ease:"power4.out",stagger:.085}},{t:.2f});'
                f'tl.fromTo("{st}",{{opacity:0,y:24}},{{opacity:1,y:0,duration:.35,ease:"power3.out"}},{t + .3:.2f});'
                f'tl.set("{s}",{{opacity:0}},{t + d - .03:.2f});')
    if m == "push-in":
        return (f'tl.fromTo("{s}",{{opacity:0}},{{opacity:1,duration:.6}},{t:.2f});'
                f'tl.fromTo("{bg}",{{scale:1}},{{scale:1.1,duration:{d:.2f},ease:"none"}},{t:.2f});'
                f'tl.fromTo("{h}",{{y:26,opacity:0}},{{y:0,opacity:1,duration:.8,ease:"power2.out"}},{t + .25:.2f});'
                f'tl.fromTo("{st}",{{opacity:0}},{{opacity:1,duration:.7}},{t + .35:.2f});'
                f'tl.to("{s}",{{opacity:0,duration:.5}},{t + d - .5:.2f});')
    if m == "wipe":          # transform-only colour sweep: clip-path did not animate visibly under HyperFrames' seek
        return (f'tl.set("{s}",{{opacity:1}},{t:.2f});'
                f'tl.fromTo("#wb{i}",{{x:"-101%"}},{{x:"260%",duration:.6,ease:"power2.inOut"}},{t:.2f});'
                f'tl.fromTo("{h}",{{opacity:0,x:-30}},{{opacity:1,x:0,duration:.4,ease:"power3.out"}},{t + .3:.2f});'
                f'tl.fromTo("{st}",{{opacity:0}},{{opacity:1,duration:.4}},{t + .3:.2f});'
                f'tl.set("{s}",{{opacity:0}},{t + d - .02:.2f});')
    return (f'tl.set("{s}",{{opacity:1}},{t:.2f});'                         # cut
            f'tl.fromTo("{h}",{{opacity:0}},{{opacity:1,duration:.12}},{t:.2f});'
            f'tl.set("{s}",{{opacity:0}},{t + d - .02:.2f});')


def _fit_stage(H, U, tk, caption_kind, say, head, has_tag, cap_pad, side, W):
    """Stage height left over after this scene's headline and caption (estimated from text length) and the paddings,
    so a long caption shrinks the stage instead of pushing the headline out of the frame."""
    sw = W - 2 * side
    cap_px = U * 0.054
    cap_lines = -(-int(len(say) * cap_px * 0.56) // int(sw - (0.1 * U if caption_kind == "pill" else 0)))
    cap_h = cap_lines * cap_px * 1.28 + (cap_px * 1.1 if caption_kind == "pill" else cap_px * 0.6)
    hs = U * tk["hscale"]
    head_lines = -(-int(len(head) * hs * tk["cw"]) // int(sw))
    head_h = head_lines * hs * 1.08 + (U * 0.03 * 1.8 if has_tag else 0)
    avail = H - int(H * 0.06) - cap_pad - cap_h - head_h - 3 * int(H * 0.02)
    return int(max(0.26 * H, min(0.46 * H, avail)))


def compose(ctx, *, dur, words_for, caption_words, stage, lint_cmd, cap_override=None):
    spec = ctx["spec"]
    W, H = map(int, ctx["res"])
    U, portrait = min(W, H), H > W
    style = planner.resolve_style(spec)
    sdef = S.get(style["id"])
    tk = sdef["tokens"]
    pl = planner.plan(spec, style)
    # Devanagari needs no letter-spacing/uppercase and a font that has the glyphs (a mono headline font would substitute and space words wildly)
    script_kind = typography.script_kind(" ".join(f"{l.get('say', '')} {l.get('headline', '')} {l.get('tag', '')}" for l in spec["script"]))
    cap_override = cap_override or {}
    cap_pad = int(H * cap_override["safezone_bottom_padding"]) if cap_override.get("safezone_bottom_padding") else int(H * 0.16)
    side = cap_override.get("safezone_side_padding", 70)
    root_css, sh = _vars(W, H, U, tk, cap_pad, side, portrait)
    g = {"sw": W - 2 * side, "sh": sh, "U": U, "portrait": portrait, "tk": tk}
    proj = ctx["dir"] / "project"
    (proj / "assets/voice").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "contentos/templates/gsap.min.js", proj / "gsap.min.js")
    t, scenes, audios, anim, durs = 0.0, [], [], [], []
    n = len(spec["script"])
    for i, (ln, sc) in enumerate(zip(spec["script"], pl["scenes"]), 1):
        wav = ctx["dir"] / "audio" / f"{i:02d}.wav"
        shutil.copy(wav, proj / f"assets/voice/{i:02d}.wav")
        d = round(dur(wav) + 0.35, 2)
        durs.append(d)
        wd = ctx["dir"] / "audio" / f"tx{i:02d}"
        _lang = ln.get("lang") or spec.get("language")
        _kw = {"language": _lang} if _lang not in (None, "en") else {}     # English call shape is unchanged
        asr = words_for(wav, wd, log_path=ctx["log_path"], **_kw) if ctx.get("log_path") else words_for(wav, wd, **_kw)
        wl = caption_words(ln["say"].split(), asr, d, **_kw)
        cap = "".join(f'<span id="w{i}_{k}">{e(w)}</span> ' for k, (w, _, _) in enumerate(wl))
        for k, (_, ws, we) in enumerate(wl):
            anim.append(f'tl.set("#w{i}_{k}",{{color:"{tk["hl"]}"}},{t + ws:.2f});tl.set("#w{i}_{k}",{{color:"{tk["capink"]}"}},{t + we:.2f});')
        stype = sc["type"]
        has_stage_pre = stype in primitives.BUILDERS or stype == "split"
        stage_html, stage_js = "", ""
        sh_i = _fit_stage(H, U, tk, sdef["caption"], ln["say"], ln["headline"], bool(ln.get("tag")) or sdef["layout"] == "split-editorial", cap_pad, side, W)
        ueff = int(min(U, sh_i * 1.85))                  # content scales with the stage it must fit (matters in 16:9)
        if stype in primitives.BUILDERS:
            stage_html, stage_js = primitives.BUILDERS[stype](ln["visual"], f"s{i}", t, d, {**g, "sh": sh_i, "U": ueff})
        elif stype == "split":
            stage_html = f'<div class="numeral">{i:02d}</div><div class="numlabel">scene {i} of {n}</div>'
        elif stype == "pullquote":
            stage_html = ""
        head = ln["headline"]
        longest = max(len(w) for w in head.split())
        base_px = U * (tk["hscale"] if has_stage_pre else tk["hero"])
        fit_px = int(min(base_px, g["sw"] / (longest * tk["cw"])))
        words = "".join(f'<span class="hw" style="display:inline-block;margin-right:.22em">{e(w)}</span>' for w in head.split()) \
            if sc["motion"] == "slam" else e(head)
        tag = ln.get("tag")
        tag_html = f'<div class="tag">{e(tag)}</div>' if tag and not re.fullmatch(r"\d+/\d+", tag) else ""
        if sdef["layout"] == "split-editorial" and not tag_html:
            tag_html = f'<div class="tag">No. {i:02d}</div>'
        has_stage = stype in primitives.BUILDERS or stype == "split"
        cls = f'scene clip L-{sdef["layout"]}{"" if has_stage else " no-stage"} T-{stype}'
        bars = '<div class="bars"><i></i><i></i></div>' if sdef["layout"] == "lower-third" else ""
        if sc["motion"] == "wipe":
            bars += f'<div class="wipebar" id="wb{i}"></div>'
        scenes.append(
            f'<div class="{cls}" id="s{i}" style="--sh:{sh_i}px;--bgcss:{sdef["grounds"][sc["ground"]]}" data-start="{t:.2f}" data-duration="{d}"><div class="bg" id="bg{i}"></div>{bars}'
            f'<div class="head">{tag_html}<h1 id="h{i}" style="font-size:{fit_px}px">{words}</h1></div>'
            f'<div class="stage" id="st{i}" style="--U:{ueff}px">{stage_html}</div>'
            f'<p class="cap cap-{sdef["caption"]}">{cap}</p></div>')
        audios.append(f'<audio id="a{i}" src="./assets/voice/{i:02d}.wav" data-start="{t:.2f}" data-duration="{d}" class="clip"></audio>')
        anim.append(_motion(sc["motion"], i, t, d, W, None) + stage_js)
        t += d
    total = round(t, 2)
    (proj / "hyperframes.json").write_text(json.dumps({"width": W, "height": H, "fps": 30, "duration": total}))
    (proj / "index.html").write_text(
        f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{e(spec["title"])}</title><script src="./gsap.min.js"></script>'
        f'<style>{typography.block(script_kind, _SEL, f"[data-script={script_kind}]")}{root_css}{CSS}</style></head><body><div id="root" data-composition-id="root" data-orient="{"port" if portrait else "land"}" data-script="{script_kind}" data-width="{W}" data-height="{H}" '
        f'data-duration="{total}">{"".join(scenes)}{"".join(audios)}</div>'
        f'<script>const tl=gsap.timeline({{paused:true}});{"".join(anim)}'
        f'window.__timelines=window.__timelines||{{}};window.__timelines["root"]=tl;</script></body></html>')
    report = planner.variety_report(pl, durs)
    if spec.get("creative_skill"):                       # which registry skill routed here (see contentos/skills)
        pl["creative_skill"] = spec["creative_skill"]
    (ctx["dir"] / "visual-plan.json").write_text(json.dumps(pl, indent=2))
    (ctx["dir"] / "variety-report.json").write_text(json.dumps(report, indent=2))
    ctx["visual_plan"], ctx["variety_report"] = pl, report
    if report["status"] == "BLOCK":
        raise RuntimeError("variety report BLOCK: " + "; ".join(c["evidence"] for c in report["checks"] if c["status"] == "BLOCK"))
    stage(ctx, lint_cmd, cwd=proj)
    return "hyperframes", [proj / "index.html", proj / "hyperframes.json", ctx["dir"] / "visual-plan.json",
                           ctx["dir"] / "variety-report.json"]
