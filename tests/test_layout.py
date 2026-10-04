import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from contentos import pipeline  # noqa: E402

LONG = ("Why the sky is blue: air scatters short blue wavelengths of sunlight far more than long red ones, "
        "and at sunset the light crosses more air, so the sky turns orange.")


def chrome():
    r = subprocess.run(["npx", "--no-install", "hyperframes", "browser", "path"], cwd=ROOT, capture_output=True, text=True)
    lines = r.stdout.strip().splitlines() if r.returncode == 0 else []
    return lines[-1] if lines and Path(lines[-1]).exists() else None


@pytest.mark.parametrize("res", [(1080, 1920), (1920, 1080)], ids=["9:16", "16:9"])
def test_long_caption_never_overlaps_the_headline(tmp_path, monkeypatch, res):
    exe = chrome()
    if not (exe and shutil.which("ffmpeg") and shutil.which("node")):
        pytest.skip("needs ffmpeg, node and the hyperframes Chrome")
    for i in (1, 2):  # three seconds of silence per line
        (tmp_path / "audio").mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3",
                        str(tmp_path / "audio" / f"{i:02d}.wav")], check=True)
    monkeypatch.setattr(pipeline, "words_for", lambda *a, **k: [])
    monkeypatch.setattr(pipeline, "sh", lambda *a, **k: "")  # skip hyperframes lint
    spec = {"title": "t", "script": [{"say": LONG, "headline": "Why the sky is blue: air scatters short", "tag": "LONG"},
                                     {"say": "Short line.", "headline": "Short", "tag": "SHORT"}]}
    pipeline.s_compose({"spec": spec, "res": res, "dir": tmp_path, "id": "t"})
    probe = ROOT / "tests/layout_probe.mjs"
    out = subprocess.run(["node", str(probe), str(tmp_path / "project/index.html"), str(res[0]), str(res[1]), exe],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    for s in json.loads(out):
        # the caption must take part in the layout: a floating (absolute) caption grows over the headline when
        # it wraps to more lines, and the font that wraps it is not the one this probe measures with
        assert s["capPosition"] != "absolute", f"caption floats over the headline: {s}"
        assert s["cap"]["top"] - s["h1"]["bottom"] >= 24, f"headline is not clear of the caption: {s}"
        assert s["cap"]["bottom"] <= res[1], f"caption runs off the frame: {s}"
        assert 0 <= s["h1"]["left"] and s["h1"]["right"] <= res[0], f"headline runs off the frame: {s}"
