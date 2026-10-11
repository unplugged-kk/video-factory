"""Builds three 9:16 test compositions (cut / css / shader) from one code-editorial-styled template. Only the 2->3 s boundary differs."""
import sys
from pathlib import Path
here = Path(__file__).parent
SCENES = [("s1", "A rule, then a machine", "#141413", "#FAF9F5"), ("s2", "Learned, not written", "#EFE9DE", "#141413")]
WORDS = [["A", "rule,", "then", "a", "machine"], ["Learned,", "not", "written"]]
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
#captions{position:absolute;left:70px;right:140px;bottom:332px;height:214px;z-index:20;display:flex;align-items:center;justify-content:center}
.cap{position:absolute;padding:22px 34px;border-radius:12px;background:#FAF9F5;border:1px solid rgba(20,20,19,.2);box-shadow:0 4px 16px rgba(20,20,19,.12);font-family:"EB Garamond",serif;font-size:64px;color:#141413;opacity:0}
'''
def page(arm):
    OV = ' data-layout-allow-overlap' if arm == 'shader' else ''
    sc = "\n".join(f'<section class="scene" id="{i}"{OV} style="z-index:{n+1};background-color:{bg};color:{fg}"><div class="kicker"{OV}>0{n+1} · code editorial</div><div class="h"{OV}>{t}</div><div class="card"{OV}>if (rule) {{ output = fixed; }}<br>else {{ output = learned; }}</div></section>'
                   for n, (i, t, bg, fg) in enumerate(SCENES))
    caps = "\n".join(f'<div class="cap" id="c{n}">{" ".join(w)}</div>' for n, w in enumerate(WORDS))
    cap_js = "".join(f'tl.set("#c{n}",{{opacity:1}},{n*6+0.3}); tl.set("#c{n}",{{opacity:0}},{n*6+5.9});\n' for n in range(2))
    scripts = '<script src="./gsap.min.js"></script>' + ('<script src="./shader-transitions.js"></script>' if arm == "shader" else "")
    if arm == "shader":
        js = ('var tl = HyperShader.init({bgColor:"#181715",accentColor:"#CC785C",compositionId:"root",scenes:["s1","s2"],'
              'transitions:[{time:5.7,shader:"sdf-iris",duration:0.6}]});\n')
    else:
        js = 'gsap.set("#s2",{opacity:0});\nvar tl = gsap.timeline({paused:true});\n'
        if arm == "css":
            js += ('tl.set("#s2",{opacity:1},5.55); tl.fromTo("#s1",{x:0},{x:-1080,duration:0.45,ease:"power2.inOut"},5.55);'
                   'tl.fromTo("#s2",{x:1080},{x:0,duration:0.45,ease:"power2.inOut"},5.55); tl.set("#s1",{opacity:0},6.01);\n')
        else:
            js += 'tl.set("#s2",{opacity:1},6.0); tl.set("#s1",{opacity:0},6.0);\n'
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>mac experiment {arm}</title>{scripts}<style>{CSS}</style></head><body>\n'
            f'<div id="root" data-composition-id="root" data-start="0" data-width="1080" data-height="1920" data-duration="12">\n{sc}\n<div id="captions">\n{caps}\n</div>\n</div>\n'
            f'<script>\n{js}{cap_js}window.__timelines=window.__timelines||{{}};window.__timelines["root"]=tl;\n</script></body></html>')
for arm in ("cut", "css", "shader"):
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
print("built", [p.name for p in here.iterdir()])
