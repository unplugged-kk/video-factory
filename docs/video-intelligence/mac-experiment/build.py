"""Builds five 9:16 test compositions from one code-editorial-styled template. Only the 2->3 s boundary (and, for the shader
variants, where the captions live) differs:
  cut         hard-cut control
  css         CSS push-slide (the validated path)
  shader      sdf-iris, captions at root with z-index 20      (the arrangement that lost its captions on the Mac)
  shader-zi   sdf-iris, captions at root with z-index 200      (above the shader canvas, which HyperShader injects at z-index 100)
  shader-in   sdf-iris, each caption inside its own scene      (captured into the transition texture)
  *-dark      the final experiment: same as cut / css / shader-in but with a DARK caption plate (#2b2a27, light text), so the
              iris flash has less to wash out. cut-dark and css-dark are the matched controls for shader-in-dark.
The caption text, plate geometry, fonts and scene content are identical in every arm."""
import sys
from pathlib import Path
here = Path(__file__).parent
SCENES = [("s1", "A rule, then a machine", "#141413", "#FAF9F5"), ("s2", "Learned, not written", "#EFE9DE", "#141413")]
WORDS = [["A", "rule,", "then", "a", "machine"], ["Learned,", "not", "written"]]
ARMS = ("cut", "css", "shader", "shader-zi", "shader-in", "cut-dark", "css-dark", "shader-in-dark")
CSS = '''
@font-face{font-family:"EB Garamond";src:url("./fonts/EBGaramond-400.woff2") format("woff2");font-weight:400}
@font-face{font-family:"EB Garamond";src:url("./fonts/EBGaramond-700.woff2") format("woff2");font-weight:700}
@font-face{font-family:"Inter";src:url("./fonts/Inter-400.woff2") format("woff2");font-weight:400}
@font-face{font-family:"Inter";src:url("./fonts/Inter-700.woff2") format("woff2");font-weight:700}
@font-face{font-family:"JetBrains Mono";src:url("./fonts/JetBrainsMono-400.woff2") format("woff2");font-weight:400}
@font-face{font-family:"JetBrains Mono";src:url("./fonts/JetBrainsMono-700.woff2") format("woff2");font-weight:700}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#181715}
#root{position:relative;width:1080px;height:1920px;background:#181715}
.scene{position:absolute;left:0;top:0;width:1080px;height:1920px;padding:150px 90px;font-family:"Inter",sans-serif}
.kicker{font-family:"JetBrains Mono",monospace;font-weight:700;font-size:30px;letter-spacing:5px;text-transform:uppercase;color:#CC785C}
#s2 .kicker{color:#9E4F36}
.h{margin-top:40px;font-family:"EB Garamond",serif;font-weight:400;font-size:132px;line-height:1.04;letter-spacing:-2px}
.card{margin-top:90px;padding:40px;border-radius:12px;border:1px solid rgba(128,128,128,.35);font-family:"JetBrains Mono",monospace;font-size:34px;line-height:1.6}
.capbox{position:absolute;left:70px;right:140px;bottom:332px;height:214px;display:flex;align-items:center;justify-content:center}
#captions{z-index:20}
.cap{position:absolute;padding:22px 34px;border-radius:12px;background:#FAF9F5;border:1px solid rgba(20,20,19,.2);box-shadow:0 4px 16px rgba(20,20,19,.12);font-family:"EB Garamond",serif;font-size:64px;color:#141413;opacity:0}
'''


def page(arm):
    dark = arm.endswith("-dark")
    base = arm[:-5] if dark else arm
    shader = base.startswith("shader")
    in_scene = base == "shader-in"
    OV = ' data-layout-allow-overlap' if shader else ''
    def cap(n):
        return f'<div class="cap" id="c{n}"{OV}>{" ".join(WORDS[n])}</div>'
    sc_parts = []
    for n, (i, t, bg, fg) in enumerate(SCENES):
        inner = (f'<div class="kicker"{OV}>0{n+1} · code editorial</div><div class="h"{OV}>{t}</div>'
                 f'<div class="card"{OV}>if (rule) {{ output = fixed; }}<br>else {{ output = learned; }}</div>')
        if in_scene:
            inner += f'<div class="capbox"{OV}>{cap(n)}</div>'
        sc_parts.append(f'<section class="scene" id="{i}"{OV} style="z-index:{n+1};background-color:{bg};color:{fg}">{inner}</section>')
    sc = "\n".join(sc_parts)
    root_caps = "" if in_scene else f'<div id="captions" class="capbox"{OV}>\n{cap(0)}\n{cap(1)}\n</div>'
    if in_scene:
        # each caption lives and dies with its scene (visible from the start of its scene's life)
        cap_js = 'tl.set("#c0",{opacity:1},0.3); tl.set("#c1",{opacity:1},0);\n'
    else:
        # contiguous: chunk 0 on 0.3-6.0 s, chunk 1 on 6.0-12 s, so any gap seen around the boundary is the renderer's, not the script's
        cap_js = 'tl.set("#c0",{opacity:1},0.3); tl.set("#c0",{opacity:0},6.0); tl.set("#c1",{opacity:1},6.0); tl.set("#c1",{opacity:0},12.0);\n'
    css = CSS + ('#captions{z-index:200}\n' if base == "shader-zi" else '')
    if dark:
        css += '.cap{background:#2b2a27;border:1px solid rgba(250,249,245,.28);box-shadow:0 4px 16px rgba(0,0,0,.35);color:#FAF9F5}\n'
    scripts = '<script src="./gsap.min.js"></script>' + ('<script src="./shader-transitions.js"></script>' if shader else "")
    if shader:
        js = ('var tl = HyperShader.init({bgColor:"#181715",accentColor:"#CC785C",compositionId:"root",scenes:["s1","s2"],'
              'transitions:[{time:5.7,shader:"sdf-iris",duration:0.6}]});\n')
    else:
        js = 'gsap.set("#s2",{opacity:0});\nvar tl = gsap.timeline({paused:true});\n'
        if base == "css":
            js += ('tl.set("#s2",{opacity:1},5.55); tl.fromTo("#s1",{x:0},{x:-1080,duration:0.45,ease:"power2.inOut"},5.55);'
                   'tl.fromTo("#s2",{x:1080},{x:0,duration:0.45,ease:"power2.inOut"},5.55); tl.set("#s1",{opacity:0},6.01);\n')
        else:
            js += 'tl.set("#s2",{opacity:1},6.0); tl.set("#s1",{opacity:0},6.0);\n'
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>mac experiment {arm}</title>{scripts}<style>{css}</style></head><body>\n'
            f'<div id="root" data-composition-id="root" data-start="0" data-width="1080" data-height="1920" data-duration="12">\n{sc}\n{root_caps}\n</div>\n'
            f'<script>\n{js}{cap_js}window.__timelines=window.__timelines||{{}};window.__timelines["root"]=tl;\n</script></body></html>')


if __name__ == "__main__":
    for arm in ARMS:
        d = here / arm
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(page(arm))
        (d / "hyperframes.json").write_text('{ "width": 1080, "height": 1920, "fps": 30, "duration": 12 }')
        for f in ("gsap.min.js", "shader-transitions.js"):
            (d / f).write_bytes((here / "common" / f).read_bytes())
        fd = d / "fonts"
        fd.mkdir(exist_ok=True)
        for f in (here / "common" / "fonts").glob("*.woff2"):
            (fd / f.name).write_bytes(f.read_bytes())
    print("built", list(ARMS))
