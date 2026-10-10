import shutil
import subprocess

import pytest

from contentos.production import motion_audit as ma

HTML = '''tl.fromTo("#a",{opacity:0},{opacity:1,ease:"power3.out"},0);
tl.fromTo("#b",{scale:.6},{scale:1,ease: 'back.out(2)'},1);
tl.to("#c",{x:5,ease:"elastic.out(1,.3)"},2);tl.to("#d",{y:5,yoyo:true,repeat:1,ease:"sine.inOut"},3);
tl.to("#e",{y:5,repeat:-1,ease:"none"},4);'''


def test_ease_inventory_counts_families_and_flags():
    inv = ma.ease_inventory(HTML)
    assert inv["total"] == 5
    assert inv["overshoot"] == 2                      # back + elastic
    assert inv["by_ease"]["power3.out"] == 1
    assert inv["repeat_infinite"] == 1
    assert inv["yoyo"] == 1


def test_ease_inventory_ignores_non_ease_text():
    assert ma.ease_inventory("<p>please ease into it</p>")["total"] == 0


def test_parse_ydif():
    text = "frame:0 pts:0\nlavfi.signalstats.YDIF=0.000\nframe:1\nlavfi.signalstats.YDIF=1.5\n"
    assert ma.parse_ydif(text) == [0.0, 1.5]


def test_motion_stats_still_and_pop():
    series = [0.0] * 30 + [0.4, 0.5, 0.4] + [0.0] * 10 + [9.0] + [0.1] * 5      # one isolated spike at frame 44
    s = ma.motion_stats(series, fps=30)
    assert s["frames"] == len(series)
    assert s["longest_still_s"] == 1.0                                         # first 30 frames
    assert s["pop_count"] == 1 and s["pops"] == [round(43 / 30, 3)]
    assert 0 < s["still_fraction"] < 1


def test_smooth_move_is_not_a_pop():
    s = ma.motion_stats([0.0, 2.0, 2.2, 2.1, 2.0, 0.0], fps=30)
    assert s["pop_count"] == 0                                                 # plateau, not a one-frame jump


def test_motion_stats_empty():
    assert ma.motion_stats([], 30) == {"frames": 0}


def test_compare_rows():
    rows = ma.compare({"a": 5, "b": "x"}, {"a": 2, "b": "y"}, ["a", "b", "c"])
    assert rows[0]["delta"] == -3 and rows[1]["delta"] is None and rows[2]["control"] is None


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg not installed")
def test_video_ydif_on_synthetic_clip(tmp_path):
    mp4 = tmp_path / "t.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10:duration=2", "-pix_fmt", "yuv420p",
                    str(mp4)], check=True)
    series, fps = ma.video_ydif(mp4, width=80)
    assert fps == 10.0 and len(series) == 20
    assert max(series) > 0
