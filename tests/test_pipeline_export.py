"""The pipeline's export stage: a validated render reaches ready/; a bad one never does; retries add nothing."""
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contentos import pipeline, storage  # noqa: E402
from storage_helpers import make_video  # noqa: E402


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    spec = tmp_path / "spec.yaml"
    spec.write_text(yaml.safe_dump({"content_id": "pj", "title": "Pipeline Job", "project": "Demo", "script": [{"say": "Hi there."}]}))
    return spec, tmp_path / "pub"


def stage(spec, video):
    storage.preflight()
    d, _ = storage.open_job("pj", yaml.safe_load(spec.read_text()))
    shutil.copy(video, d / "video.mp4")
    return d


def test_export_stage_publishes_and_is_idempotent(setup, tmp_path):
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "ok.mp4", seconds=1))
    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "OK")
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1
    pipeline.run(spec, only="export", force=True)                      # forced re-run: still one copy
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1
    assert storage.read_manifest(d)["status"] == "exported"


def test_export_stage_failure_is_recorded_and_ready_stays_empty(setup, tmp_path):
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "bad.mp4", w=320, h=240, seconds=1))
    _, report = pipeline.run(spec, only="export")
    assert report[0][1].startswith("FAIL")
    assert list((pub / "ready").rglob("*")) == []
    assert storage.read_manifest(d)["status"] == "failed"


def test_stage_order_has_export_before_publish():
    assert pipeline.STAGES.index("package") < pipeline.STAGES.index("export") < pipeline.STAGES.index("publish")
