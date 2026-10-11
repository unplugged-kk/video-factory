"""Timeline-labelled contact sheet: frame selection and labels are pure functions; the drawing path is checked on a synthetic video
(skipped when ffmpeg has no drawtext or no font file is found)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.production import sheet  # noqa: E402


def tl():
    words = [{"i": i, "text": t, "t0": round(0.5 * i, 3), "t1": round(0.5 * i + 0.4, 3), "source": s}
             for i, (t, s) in enumerate([("one", "matched"), ("two", "matched"), ("three", "span"), ("four", "matched"), ("five", "matched"), ("six", "matched")])]
    return {"schema": "timeline/1", "job": "j", "fps": 10, "duration_s": 3.0,
            "alignment": {"timing_trust": "asr-derived-unverified"}, "words": words,
            "scenes": [{"id": "a", "t0": 0.0, "t1": 1.5, "w0": 0, "w1": 2}, {"id": "b", "t0": 1.5, "t1": 3.0, "w0": 3, "w1": 5}],
            "cues": [{"id": "c01-a", "scene": "a", "t": 0.5, "do": "the headline lands", "at": {"word": 1}},
                     {"id": "c02-b", "scene": "b", "t": 2.0, "do": "x" * 80, "at": {"word": 4}}]}


def test_pick_times_covers_scene_edges_and_cues_inside_the_video():
    pts = sheet.pick_times(tl())
    ts = [t for t, _ in pts]
    assert ts == sorted(ts) and all(0 <= t <= 3.0 - 0.1 for t in ts)
    reasons = [r for _, rs in pts for r in rs]
    assert reasons.count("scene-start") == 2 and reasons.count("scene-end") == 2
    assert "cue c01-a" in reasons and "cue c02-b" in reasons
    assert any(abs(t - 0.65) < 1e-6 for t in ts)                  # cue at 0.5 + settle 0.15


def test_close_points_merge_and_keep_every_reason():
    t = tl()
    t["cues"][0]["t"] = 0.0                                       # cue 0 + settle lands within min_gap of the scene start frame (0.1)
    pts = sheet.pick_times(t, settle_s=0.15, min_gap_s=0.3)
    assert pts[0][0] == pytest.approx(0.1) and {"scene-start", "cue c01-a"} <= set(pts[0][1])


def test_describe_names_scene_word_and_cue_and_marks_non_exact_words():
    t = tl()
    d = sheet.describe(t, 0.65, ["cue c01-a"])
    assert d["scene"] == "a" and d["word"]["text"] == "two" and d["cues"] == ["c01-a"]
    assert d["label"].splitlines()[0].strip().startswith("0.65s")
    d = sheet.describe(t, 1.05, ["x"])
    assert d["word"] == {"i": 2, "text": "three", "source": "span"} and "(span)" in d["label"]
    d = sheet.describe(t, 0.45, ["gap"])                          # between words 0 (ends 0.4) and 1 (starts 0.5)
    assert d["word"] is None and "no word spoken" in d["label"]


def test_labels_are_shortened_to_fit_but_the_full_text_is_kept():
    d = sheet.describe(tl(), 2.15, ["cue c02-b"], max_chars=30)
    assert all(len(line) <= 30 for line in d["label"].splitlines()) and d["label"].endswith("…")
    assert "x" * 80 in d["label_full"]


def test_find_font_uses_the_explicit_path_then_the_environment(tmp_path, monkeypatch):
    f = tmp_path / "f.ttf"
    f.write_bytes(b"x")
    assert sheet.find_font(str(f)) == str(f)
    monkeypatch.setenv("CONTENTOS_SHEET_FONT", str(f))
    assert sheet.find_font() == str(f)


def drawing_ok():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return False
    return sheet._drawtext_available() and sheet.find_font() is not None


def synth(path):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x336699:size=270x480:rate=10:duration=3", "-pix_fmt", "yuv420p", str(path)], check=True)


def test_missing_font_fails_closed_unless_unlabelled_is_allowed(tmp_path, monkeypatch):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not available")
    synth(tmp_path / "v.mp4")
    monkeypatch.setattr(sheet, "find_font", lambda explicit=None: None)
    with pytest.raises(sheet.SheetError):
        sheet.build_sheet(tmp_path / "v.mp4", tl(), tmp_path / "o1")
    m = sheet.build_sheet(tmp_path / "v.mp4", tl(), tmp_path / "o2", allow_unlabelled=True)
    assert m["labelled"] is False and (tmp_path / "o2/sheet.png").exists() and all(t["label_full"] for t in m["tiles"])


@pytest.mark.skipif(not drawing_ok(), reason="ffmpeg drawtext or a font file is not available")
def test_labelled_sheet_really_draws_text_and_writes_the_manifest(tmp_path):
    synth(tmp_path / "v.mp4")
    m = sheet.build_sheet(tmp_path / "v.mp4", tl(), tmp_path / "labelled", cols=3, tile_h=240)
    assert m["labelled"] is True and m["timing_trust"] == "asr-derived-unverified" and (tmp_path / "labelled/sheet.png").stat().st_size > 1000
    on_disk = json.loads((tmp_path / "labelled/sheet.json").read_text())
    assert on_disk["schema"] == "sheet/1" and len(on_disk["tiles"]) == len(m["tiles"]) >= 6
    # the label box (bottom-left, clear of the video's own headline) darkens the bottom-left corner of the first labelled tile, which is a flat 0x336699 colour in the source frame
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp_path / "labelled" / m["tiles"][0]["frame"]), "-vf", "crop=4:4:6:in_h-10,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp_path / "labelled/frames" / f"raw_{m['tiles'][0]['t']:07.2f}.png"), "-vf", "crop=4:4:6:in_h-10,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    assert len(out) == len(raw) == 16 and sum(out) < sum(raw) * 0.8


def test_the_module_stays_local_and_imports_no_renderer():
    src = Path(sheet.__file__).read_text(encoding="utf-8")
    for banned in ("requests", "urllib", "hyperframes", "PIL"):
        assert f"import {banned}" not in src and f"from {banned}" not in src
