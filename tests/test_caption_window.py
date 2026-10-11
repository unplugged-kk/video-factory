"""The Mac harness's caption-text check must tell glyphs on a light plate from a bright blob and from a dark scene."""
import importlib.util
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "docs" / "video-intelligence" / "mac-experiment" / "caption_window.py"
spec = importlib.util.spec_from_file_location("caption_window", SRC)
cw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cw)
W, H = 300, 40


def frame(fill, plate=None, glyphs=(), blob=None):
    rows = []
    for y in range(H):
        row = [fill] * W
        if plate and plate[1] <= y < plate[3]:
            for x in range(plate[0], plate[2]):
                row[x] = 250
        if blob and blob[1] <= y < blob[3]:
            for x in range(blob[0], blob[2]):
                row[x] = 255
        for gx, gy0, gy1 in glyphs:
            if gy0 <= y < gy1:
                row[gx:gx + 4] = [20] * 4
        rows.append(bytes(row))
    return b"".join(rows)


def test_glyphs_on_plate_score_high():
    g = [(60 + 20 * i, 10, 30) for i in range(8)]
    assert cw.plate_text_score(frame(24, plate=(30, 5, 270, 35), glyphs=g), W, H) >= 8 * 4 * 20


def test_empty_dark_scene_scores_zero():
    assert cw.plate_text_score(frame(24), W, H) == 0


def test_bright_blob_without_text_scores_zero():
    assert cw.plate_text_score(frame(24, blob=(0, 0, 150, 40)), W, H) == 0


def test_plate_without_text_scores_zero():
    assert cw.plate_text_score(frame(24, plate=(30, 5, 270, 35)), W, H) == 0


def test_dark_stroke_with_light_on_one_side_only_is_not_text():
    f = bytearray(frame(24, blob=(0, 0, 100, 40)))
    for y in range(40):
        f[y * W + 101: y * W + 105] = bytes([20] * 4)           # just outside the blob edge: light only on the left
    assert cw.plate_text_score(bytes(f), W, H) == 0


def test_light_glyphs_on_dark_plate_score_high_in_light_on_dark_mode():
    g = [(60 + 20 * i, 10, 30) for i in range(8)]
    rows = []
    for y in range(H):
        row = [24] * W
        if 5 <= y < 35:
            for x in range(30, 270):
                row[x] = 42
        for gx, gy0, gy1 in g:
            if gy0 <= y < gy1:
                row[gx:gx + 4] = [250] * 4
        rows.append(bytes(row))
    buf = b"".join(rows)
    assert cw.plate_text_score(buf, W, H, "light-on-dark") >= 8 * 4 * 20
    # the two modes are mirror images, so each one is only meaningful for its own plate; run.sh picks the mode per arm


def test_white_blob_without_text_scores_zero_on_dark_plate_mode():
    rows = []
    for y in range(H):
        row = [24] * W
        for x in range(0, 150):
            row[x] = 255
        rows.append(bytes(row))
    assert cw.plate_text_score(b"".join(rows), W, H, "light-on-dark") == 0
