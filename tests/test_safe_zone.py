"""visual_gate safezone (G6): hard-edged content inside the platform-UI zones of a 9:16 render is flagged.

Synthetic ffmpeg clips only, so no media is committed. The default zones are conservative heuristics, not platform specs;
these tests prove the detector, not any platform's real UI."""
import shutil
import subprocess

import pytest

from contentos.production import visual_gate as g

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

W, H = 270, 480                      # 9:16; default zones: top 37px, bottom 87px, right 45px wide from y=250 to y=392
CANVAS = (W, H)
BASE = f"gradients=s={W}x{H}:r=10:c0=0x101820:c1=0x182030:x0=0:y0=0:x1=0:y1={H},format=yuv420p"


def _clip(path, boxes, base=BASE):
    vf = ",".join(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=white:t=fill" for x, y, w, h in boxes) or "null"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", "2", "-i", base, "-vf", vf, "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("sz")
    mid = (30, 200, 210, 14)                                    # a caption-like bar in the safe middle
    return {
        "clean": _clip(d / "clean.mp4", [mid]),
        "plain": _clip(d / "plain.mp4", []),                    # smooth gradient only: no hard edges anywhere
        "top": _clip(d / "top.mp4", [mid, (20, 8, 230, 18)]),
        "bottom": _clip(d / "bottom.mp4", [mid, (20, 420, 230, 20)]),
        "right": _clip(d / "right.mp4", [mid, (232, 300, 30, 60)]),
        "landscape": _clip(d / "landscape.mp4", [(30, 100, 210, 14)], base=f"gradients=s={H}x{W}:r=10:c0=0x101820:c1=0x182030,format=yuv420p"),
    }


def test_clean_9_16_passes(clips):
    r = g.check_safe_zones(clips["clean"], [0.5, 1.0, 1.5], CANVAS)
    assert r["ok"] and r["applicable"] and not r["flagged"]


def test_smooth_background_is_not_content(clips):
    assert g.check_safe_zones(clips["plain"], [1.0], CANVAS)["ok"]


@pytest.mark.parametrize("name", ["top", "bottom", "right"])
def test_content_in_each_zone_is_flagged(clips, name):
    r = g.check_safe_zones(clips[name], [1.0], CANVAS)
    assert not r["ok"]
    assert [f["zone"] for f in r["flagged"]] == [name]            # only the zone that was intruded


def test_landscape_video_with_matching_canvas_has_no_default_zones(clips):
    r = g.check_safe_zones(clips["landscape"], [1.0], (H, W))                 # a real 480x270 clip, canvas 480x270
    assert r["ok"] is False and r["applicable"] is False and r["status"] == "not_applicable"      # nothing checked is not a pass
    assert g.main(["safezone", str(clips["landscape"]), "--canvas", f"{H}x{W}", "--times", "1.0"]) == 3


def test_custom_zone_overrides_defaults(clips):
    r = g.check_safe_zones(clips["clean"], [1.0], CANVAS, zones=[("mid", 0, 190, W, 40)])
    assert not r["ok"] and r["flagged"][0]["zone"] == "mid"


def test_cli_exit_codes(clips, capsys):
    assert g.main(["safezone", str(clips["clean"]), "--canvas", f"{W}x{H}", "--times", "1.0"]) == 0
    assert g.main(["safezone", str(clips["top"]), "--canvas", f"{W}x{H}", "--times", "1.0"]) == 1
    assert g.main(["safezone", str(clips["top"]), "--canvas", f"{W}x{H}"]) == 2          # no times given
    capsys.readouterr()


# ---- canvas validation: syntax, positive size, and agreement with the real video --------------------------------------

@pytest.mark.parametrize("text", ["abc", "1080", "1080x", "x1920", "1080*1920", "10.5x20", "-1080x1920", "1080x-1920", "0x1920", "1080x0", "0x0", ""])
def test_malformed_or_non_positive_canvas_is_rejected(text):
    with pytest.raises(g.GateError, match="--canvas"):
        g.parse_canvas(text)


@pytest.mark.parametrize("text, want", [("1080x1920", (1080, 1920)), ("1920X1080", (1920, 1080)), (" 270 x 480 ", (270, 480))])
def test_valid_canvas_parses(text, want):
    assert g.parse_canvas(text) == want


def test_canvas_larger_than_video_is_an_error_not_a_result(clips):
    with pytest.raises(g.GateError, match="does not match the video's actual size 270x480"):
        g.check_safe_zones(clips["clean"], [1.0], (1080, 1920))


def test_canvas_with_wrong_orientation_is_not_hidden_behind_not_applicable(clips):
    with pytest.raises(g.GateError, match="does not match"):
        g.check_safe_zones(clips["clean"], [1.0], (480, 270))                  # portrait clip, landscape canvas


def test_portrait_canvas_on_landscape_video_is_an_error(clips):
    with pytest.raises(g.GateError, match="does not match"):
        g.check_safe_zones(clips["landscape"], [1.0], CANVAS)


def test_function_rejects_non_positive_canvas(clips):
    with pytest.raises(g.GateError, match="positive"):
        g.check_safe_zones(clips["clean"], [1.0], (W, 0))


def test_configured_canvas_is_never_silently_replaced(clips):
    with pytest.raises(g.GateError):
        g.check_safe_zones(clips["clean"], [1.0], (W, H + 1))                    # off by one is still a mismatch


def test_unreadable_video_is_a_clear_error(tmp_path):
    bad = tmp_path / "nope.mp4"
    with pytest.raises(g.GateError, match="cannot read video dimensions"):
        g.check_safe_zones(bad, [1.0], CANVAS)


def test_cli_canvas_errors_exit_2_with_a_message(clips, capsys):
    base = ["safezone", str(clips["clean"]), "--times", "1.0"]
    assert g.main(base + ["--canvas", "abc"]) == 2
    assert "--canvas must look like" in capsys.readouterr().err
    assert g.main(base + ["--canvas", f"{W}x0"]) == 2
    assert g.main(base + ["--canvas", "1080x1920"]) == 2
    assert "does not match the video's actual size" in capsys.readouterr().err


# ---- custom zones: every invalid category fails before ffmpeg runs a measurement --------------------------------------

@pytest.mark.parametrize("spec, message", [
    ("foo", "expected name:x,y,w,h"),                 # no colon
    (":0,0,10,10", "expected name:x,y,w,h"),          # empty name
    ("bad name:0,0,10,10", "expected name:x,y,w,h"),  # illegal characters in the name
    ("a:", "exactly 4 numbers"),                      # no fields
    ("a:1,2,3", "exactly 4 numbers"),                 # missing field
    ("a:1,2,3,4,5", "exactly 4 numbers"),             # extra field
    ("a:x,y,w,h", "whole numbers"),                   # non-integer
    ("a:1.5,2,3,4", "whole numbers"),                 # float
    ("a:1,2,3,", "whole numbers"),                    # empty field
])
def test_malformed_zone_specs_are_rejected_with_a_message(spec, message):
    with pytest.raises(g.GateError, match=message):
        g.parse_zone(spec)


@pytest.mark.parametrize("zone, message", [
    (("a", -1, 0, 10, 10), "must not be negative"),
    (("a", 0, -5, 10, 10), "must not be negative"),
    (("a", 0, 0, 0, 10), "must be positive"),
    (("a", 0, 0, 10, 0), "must be positive"),
    (("a", 0, 0, -10, 10), "must be positive"),
    (("a", 0, 0, W + 1, 10), "extends outside"),
    (("a", W, 0, 10, 10), "extends outside"),
    (("a", 0, H - 5, 10, 10), "extends outside"),
    (("a", 5000, 5000, 100, 100), "extends outside"),
])
def test_invalid_zone_geometry_is_rejected_against_the_real_video(clips, zone, message):
    with pytest.raises(g.GateError, match=message):
        g.check_safe_zones(clips["clean"], [1.0], CANVAS, zones=[zone])


def test_duplicate_zone_names_are_rejected(clips):
    with pytest.raises(g.GateError, match="more than once"):
        g.check_safe_zones(clips["clean"], [1.0], CANVAS, zones=[("a", 0, 0, 10, 10), ("a", 20, 20, 10, 10)])


def test_zone_exactly_filling_the_canvas_is_valid(clips):
    r = g.check_safe_zones(clips["plain"], [1.0], CANVAS, zones=[("all", 0, 0, W, H)])
    assert r["ok"] and r["applicable"]


def test_valid_custom_zone_syntax_still_works(clips):
    name, x, y, w, h = g.parse_zone("mid:0,190,270,40")
    assert (name, x, y, w, h) == ("mid", 0, 190, 270, 40)
    r = g.check_safe_zones(clips["clean"], [1.0], CANVAS, zones=[(name, x, y, w, h)])
    assert not r["ok"] and r["flagged"][0]["zone"] == "mid"


def test_cli_invalid_zones_exit_2_without_tracebacks(clips, capsys):
    base = ["safezone", str(clips["clean"]), "--canvas", f"{W}x{H}", "--times", "1.0"]
    for spec in ("foo", "a:1,2,3", "a:x,y,w,h", "a:-1,0,10,10", "a:0,0,0,10", "a:0,0,9999,10"):
        assert g.main(base + ["--zone", spec]) == 2, spec
        err = capsys.readouterr().err
        assert err.startswith("error: ") and "Traceback" not in err and "ffmpeg" not in err.lower(), (spec, err)
    assert g.main(base + ["--zone", "mid:0,190,270,40"]) == 1                  # valid zone, content present: a finding, not an input error
    capsys.readouterr()


def test_calibration_constants_are_unchanged():
    assert g.MAX_ZONE_EDGE_FRACTION == 0.01 and g.EDGE_JUMP == 0.08
    assert g.default_zones((1080, 1920)) == [("top", 0, 0, 1080, 150), ("bottom", 0, 1570, 1080, 350), ("right", 900, 1000, 180, 570)]
