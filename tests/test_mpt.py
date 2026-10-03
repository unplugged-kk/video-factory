import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import mpt, pipeline  # noqa: E402

SPEC = {"content_id": "t", "script": [{"say": "First, the script.", "broll": "laptop"},
                                      {"say": "A hook, scored.", "headline": "Score it"}]}


def test_request_terms_and_subtitle_friendly_script():
    r = mpt.request(SPEC)
    assert r["script"] == "First the script. A hook, scored."  # lone opening word loses its comma, inner commas stay
    assert r["terms"] == ["laptop", "Score it"]                  # broll wins, headline is the fallback


def test_refuses_paid_source_and_missing_terms():
    with pytest.raises(mpt.Unavailable):
        mpt.request({**SPEC, "mpt": {"source": "wavespeed"}})
    with pytest.raises(mpt.Unavailable):
        mpt.request({"script": [{"say": "no terms"}]})


def test_local_materials_only_from_projects(tmp_path, monkeypatch):
    monkeypatch.setattr(mpt, "PROJECTS", tmp_path / "projects")
    ok = tmp_path / "projects/a/clip.mp4"
    ok.parent.mkdir(parents=True)
    ok.touch()
    outside = tmp_path / "outside.mp4"
    outside.touch()
    spec = {**SPEC, "mpt": {"source": "local", "materials": [str(ok)]}}
    assert mpt.request(spec)["materials"] == ["/workspace/projects/a/clip.mp4"]
    with pytest.raises(mpt.Unavailable):
        mpt.request({**SPEC, "mpt": {"source": "local", "materials": [str(outside)]}})


def test_cmd_never_bills_or_adds_music():
    req = {**mpt.request(SPEC), "audio": "/workspace/projects/t/audio/full.wav", "script": "--evil flag"}
    c = mpt.cmd(req, "tid")
    assert not any(a.startswith("--confirm-") for a in c)
    assert "--bgm-type=none" in c
    assert "--video-script=--evil flag" in c  # `=` form: argparse cannot read script text as a flag


def test_mpt_lane_has_its_own_compose_sentinel():
    assert pipeline.artifact("compose", {"render": "mpt"}) == "project/mpt-request.json"
    assert pipeline.artifact("compose", {}) == "project/index.html"
    assert pipeline.artifact("render", {"render": "mpt"}) == "video.mp4"
