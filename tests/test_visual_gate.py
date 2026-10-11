"""visual_gate: regression tests for KF-004 (shader transitions that are hard cuts or black) and KF-005 (captions hidden by
opaque scene backgrounds), on small synthetic videos made with ffmpeg, so no media is committed.

Each real failure was first seen on the ep3 spike (see docs/video-intelligence/04-visual-reliability-gate.md); these fixtures
reproduce the *shape* of each failure, not the exact pixels."""
import shutil
import subprocess

import pytest

from contentos.production import visual_gate as g

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

SIZE = "108x192"


def _ff(args, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-pix_fmt", "yuv420p", "-r", "10", str(out)], check=True)


def _colour(c, d, size=SIZE):
    return ["-f", "lavfi", "-t", str(d), "-i", f"color=c={c}:s={size}:r=10"]


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("gate")
    out = {}
    # red 1.0s -> blue 1.0s, real cross-fade over 0.5s starting at t=0.75 (blend window 0.75..1.25)
    out["blend"] = d / "blend.mp4"
    _ff(_colour("red", 1.5) + _colour("blue", 1.5) + ["-filter_complex", "[0][1]xfade=transition=fade:duration=0.5:offset=1.0"], out["blend"])
    # same colours, hard cut at 1.5s
    out["cut"] = d / "cut.mp4"
    _ff(_colour("red", 1.5) + _colour("blue", 1.5) + ["-filter_complex", "[0][1]concat=n=2:v=1:a=0"], out["cut"])
    # red -> 0.8s of black -> blue : the black texture failure shape
    out["black"] = d / "black.mp4"
    _ff(_colour("red", 1.2) + _colour("black", 0.8) + _colour("blue", 1.2) + ["-filter_complex", "[0][1][2]concat=n=3:v=1:a=0"], out["black"])
    # dark (but not black) neighbours around a blackout: a dark scene must not stop black being detected
    out["darkblack"] = d / "darkblack.mp4"
    _ff(_colour("0x0c0c3a", 1.2) + _colour("black", 0.8) + _colour("0x0c3a3a", 1.2) + ["-filter_complex", "[0][1][2]concat=n=3:v=1:a=0"], out["darkblack"])
    # identical neighbours: nothing to detect
    out["same"] = d / "same.mp4"
    _ff(_colour("red", 3.0), out["same"])
    # captions: dark gradient background; ink = white strips in the caption region only between 0.5s and 2.5s
    region_filter = "drawbox=x=10:y=150:w=88:h=6:color=white:t=fill:enable='between(t,0.5,2.5)',drawbox=x=20:y=165:w=60:h=6:color=white:t=fill:enable='between(t,0.5,2.5)'"
    base = ["-f", "lavfi", "-t", "3", "-i", f"gradients=s={SIZE}:r=10:c0=0x101820:c1=0x182030:x0=0:y0=0:x1=0:y1=192,format=yuv420p"]
    out["captions"] = d / "captions.mp4"
    _ff(base + ["-vf", region_filter], out["captions"])
    out["nocaptions"] = d / "nocaptions.mp4"
    _ff(base, out["nocaptions"])
    return out


# ---- KF-004: transitions ------------------------------------------------------------------------------------------

def test_real_blend_is_a_blend(clips):
    r = g.check_transition(clips["blend"], 1.0, 0.5, "css")
    assert r["verdict"] == "blend" and r["ok"]


def test_hard_cut_is_reported_as_hard_cut(clips):
    r = g.check_transition(clips["cut"], 1.25, 0.5, "shader")
    assert r["verdict"] == "hard_cut" and not r["ok"]
    assert r["intermediate_samples"] == 0


def test_black_window_is_reported_as_black_not_blend(clips):
    r = g.check_transition(clips["black"], 1.2, 0.8, "shader")
    assert r["verdict"] == "black" and not r["ok"]
    assert r["black_fraction"] > g.MAX_BLACK_FRACTION


def test_black_dip_accepted_only_when_declared(clips):
    assert g.check_transition(clips["black"], 1.2, 0.8, allow_dip=True)["verdict"] != "black"


def test_blackout_covering_the_window_edge_is_still_black(clips):
    # regression: the first version took its 'before' frame 0.05s outside the window. Here that frame is already black, so
    # black matched black and the gate called a black texture a hard cut. Neighbours are now taken further out.
    r = g.check_transition(clips["black"], 1.5, 0.4, "shader")
    assert r["verdict"] == "black" and not r["ok"]


def test_black_is_detected_next_to_a_dark_scene(clips):
    # regression: neighbours had to be brighter than 0.08 luma, so a legitimate dark scene (pure blue is 0.072) hid a blackout
    r = g.check_transition(clips["darkblack"], 1.5, 0.4, "shader")
    assert r["verdict"] == "black", r["neighbour_luma"]


def test_identical_neighbours_are_inconclusive(clips):
    assert g.check_transition(clips["same"], 1.0, 0.5)["verdict"] == "inconclusive"


# ---- KF-004: render log -------------------------------------------------------------------------------------------

FALLBACK_LOG = ('"hasShaderTransitions":true ... [Browser:WARN] [HyperShader] page-side compositing requested but '
                'drawElementImage/WebGL is not available; falling back to opacity-flip mode (Node-side layered pipeline will handle the blend).')


def test_log_flags_shader_fallback_and_suggests_css():
    f = g.scan_render_log(FALLBACK_LOG)
    codes = {x["code"] for x in f}
    assert {"shader_fallback_opacity_flip", "page_side_compositing_unavailable"} <= codes
    plan = g.fallback_plan(f)
    assert plan["action"] == "use_css_transition" and "css-transition:push-slide" in plan["suggest"]


def test_log_ignores_shader_lines_when_no_shaders_used():
    assert not [x for x in g.scan_render_log("falling back to opacity-flip mode", uses_shaders=False) if x["severity"] == "error"]


def test_log_flags_failed_render_and_compile_failure():
    codes = {x["code"] for x in g.scan_render_log('Render failed\nStreaming encoder exited before frame 361', uses_shaders=False)}
    assert {"render_failed", "encoder_exited"} <= codes
    assert "shader_compile_failed" in {x["code"] for x in g.scan_render_log("[HyperShader] Shader \"x\" failed to compile", uses_shaders=True)}


def test_clean_log_has_no_errors_but_that_is_not_proof():
    # documented limit: a black-texture render logs nothing alarming; only the frame check catches it
    f = g.scan_render_log('"hasShaderTransitions":true\nLow-memory render profile active', uses_shaders=True)
    assert all(x["severity"] == "info" for x in f)


# ---- KF-005: captions, rendered ---------------------------------------------------------------------------------

REGION = (0, 140, 108, 40)
CANVAS = (108, 192)


def test_captions_visible_when_ink_present(clips):
    r = g.check_captions(clips["captions"], [(1.0, 1.0001), (1.5, 1.5001), (2.0, 2.0001)], CANVAS, REGION)
    assert r["ok"] and r["visible_ratio"] == 1.0


def test_captions_hidden_are_reported(clips):
    r = g.check_captions(clips["nocaptions"], [(1.0, 1.0001), (1.5, 1.5001), (2.0, 2.0001)], CANVAS, REGION)
    assert not r["ok"] and r["visible_ratio"] == 0.0


def test_narration_gaps_do_not_fail_the_gate(clips):
    # 2 of 3 samples inside the ink window (0.5..2.5s) and 1 after it: 0.67 < 0.70 fails, 3 of 4 passes
    wins = [(1.0, 1.0001), (1.5, 1.5001), (2.0, 2.0001), (2.8, 2.8001)]
    assert g.check_captions(clips["captions"], wins, CANVAS, REGION)["ok"]


# ---- KF-005: layer order, static ---------------------------------------------------------------------------------

HTML = ('<div id="root"><section class="scene" id="s-a" style="z-index:1"></section>'
        '<section class="scene" id="s-b" style="z-index:2"></section><div id="captions"></div></div>')


def test_opaque_scenes_above_unlayered_captions_are_an_error():
    css = ".scene{position:absolute} #s-a{background:#111} #s-b{background:linear-gradient(#222,#333)} #captions{position:absolute}"
    r = g.check_caption_layering(css, HTML)
    assert not r["ok"] and r["findings"][0]["code"] == "opaque_scene_above_captions"
    assert r["rendered_check_required"]


def test_captions_above_scenes_are_fine():
    css = ".scene{position:absolute} #s-a{background:#111} #s-b{background:#222} #captions{z-index:20;position:absolute}"
    assert g.check_caption_layering(css, HTML)["ok"]


def test_transparent_scenes_never_hide_captions():
    css = ".scene{position:absolute;background:rgba(255,255,255,.05)} #captions{position:absolute}"
    assert g.check_caption_layering(css, HTML)["ok"]


def test_default_scene_background_counts():
    css = ".scene{position:absolute;background-color:#0a0e18} #captions{position:absolute}"
    assert not g.check_caption_layering(css, HTML)["ok"]


def test_declared_intent_is_allowed_but_demands_a_rendered_check():
    html = HTML.replace('id="captions"', 'id="captions" data-captions-intent="behind"')
    css = "#s-a{background:#111} #s-b{background:#222} #captions{position:absolute}"
    r = g.check_caption_layering(css, html)
    assert r["ok"] and r["findings"][0]["severity"] == "declared" and r["rendered_check_required"]


def test_equal_z_later_in_dom_wins():
    html = ('<section class="scene" id="s-a" style="z-index:3"></section><div id="captions"></div>')
    assert g.check_caption_layering("#s-a{background:#111} #captions{z-index:3;position:absolute}", html)["ok"]
    html2 = ('<div id="captions"></div><section class="scene" id="s-a" style="z-index:3"></section>')
    assert not g.check_caption_layering("#s-a{background:#111} #captions{z-index:3;position:absolute}", html2)["ok"]


def test_comments_in_css_are_ignored():
    css = "/* #s-a{background:#111} */ #captions{position:absolute}"
    assert g.check_caption_layering(css, HTML)["ok"]


def test_caption_region_from_css():
    css = "#captions{position:absolute;left:70px;right:140px;bottom:332px;height:214px}"
    assert g.caption_region_from_css(css, (1080, 1920)) == (70, 1374, 870, 214)
    assert g.caption_region_from_css("#x{}", (1080, 1920)) is None


# ---- CLI ----------------------------------------------------------------------------------------------------------

def test_cli_exit_codes(clips, tmp_path):
    assert g.main(["transitions", str(clips["blend"]), "--at", "1.0:0.5:css"]) == 0
    assert g.main(["transitions", str(clips["cut"]), "--at", "1.25:0.5:shader"]) == 1
    assert g.main(["transitions", str(tmp_path / "missing.mp4"), "--at", "1:1"]) == 2
    log = tmp_path / "r.log"
    log.write_text(FALLBACK_LOG)
    assert g.main(["log", str(log)]) == 1
    assert g.main(["log", str(tmp_path / "nope.log")]) == 2
