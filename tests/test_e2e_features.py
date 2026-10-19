"""End-to-end: each M3 fixture spec runs the real pipeline to a real MP4, with every feature on.

These are the only tests that call pipeline.run() through voice, compose, render, qa, package and
export with features enabled. They are opt-in because they need Chrome, ffmpeg and local TTS, and
they render for real:

    CONTENTOS_E2E=1 ~/.contentos/venv/bin/python -m pytest tests/test_e2e_features.py -v

Evidence from the last full run, and the wiring defects this pass found, are in
docs/E2E-VERIFICATION.md. The fixtures had no consumer before this file existed.
"""
import json
import os
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contentos import pipeline, storage  # noqa: E402
from contentos.renderers import remotion  # noqa: E402
from _pinned_skills import needs_hyperframes_bin, needs_local_tts  # noqa: E402

FIXTURES = sorted((Path(__file__).resolve().parent / "fixtures" / "m3").glob("*.yaml"))

e2e = pytest.mark.skipif(
    os.environ.get("CONTENTOS_E2E") != "1",
    reason="opt-in: set CONTENTOS_E2E=1 to run the real end-to-end renders (needs Chrome, ffmpeg and local TTS)",
)

EXTRA_CHECKS = {"extra_silence_gaps", "extra_end_hold", "extra_blank_field"}


@pytest.mark.parametrize("spec_path", FIXTURES, ids=lambda p: p.stem)
@e2e
@needs_local_tts
@needs_hyperframes_bin
def test_fixture_runs_end_to_end(spec_path, tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    spec = yaml.safe_load(spec_path.read_text())
    lane = spec.get("render", "hyperframes")
    if lane == "remotion" and not remotion.REMOTION_BIN.exists():
        pytest.skip("Remotion toolchain missing (see tests/_pinned_skills.py: needs_remotion)")

    _, report = pipeline.run(spec_path, approve_private=True)
    stages = {stage: status for stage, status, _ in report}
    assert stages, "pipeline produced no stage rows"
    assert all(s == "OK" or s.startswith("SKIP") for s in stages.values()), report

    d, _manifest = storage.open_job(spec["content_id"], spec)

    mp4 = d / "video.mp4"
    assert mp4.is_file() and mp4.stat().st_size > 0, "no rendered video"

    qa = json.loads((d / "qa.json").read_text())
    assert not [c for c in qa if c["status"] == "FAIL"], qa
    assert EXTRA_CHECKS <= {c["check"] for c in qa}, "qa_extra gates did not run"

    decision = json.loads((d / "creative-decision.json").read_text())
    assert decision["schema"] == "creative-decision/1"
    requested = spec["features"]["style_card"].get("chosen")
    assert decision["chosen"] == requested, decision["chosen"]

    if lane == "hyperframes":
        html = (d / "project" / "index.html").read_text()
        # visual_layer: backdrop rewrite plus the per-scene decor card
        assert "visual-scene" in html and 'id="decor1"' in html, "visual_layer did not run"
        assert "background:radial-gradient(circle at 50% 30%" in html, "backdrop not injected"
        # captions_hook: scaffold tags cleaned, safezone paddings applied
        assert "EXPLAINER" in html and "UP NEXT" in html, "captions_hook did not clean the tags"
        assert ">HOOK<" not in html, "raw HOOK tag survived the caption hook"
        assert "190px" in html, "captions_hook side padding not applied"
    else:
        assert (d / "project_remotion" / "src" / "Video.tsx").is_file()

    assert json.loads((d / "publish-result.json").read_text())["status"] == "DRY_RUN"
