import hashlib
import json
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
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))
    ok = tmp_path / "ws/jobs/2026/10/a/clip.mp4"
    ok.parent.mkdir(parents=True)
    ok.touch()
    outside = tmp_path / "outside.mp4"
    outside.touch()
    spec = {**SPEC, "mpt": {"source": "local", "materials": [str(ok)]}}
    assert mpt.request(spec)["materials"] == ["/workspace/projects/2026/10/a/clip.mp4"]   # the container mounts jobs/ as /workspace/projects
    with pytest.raises(mpt.Unavailable):
        mpt.request({**SPEC, "mpt": {"source": "local", "materials": [str(outside)]}})


def test_cmd_never_bills_or_adds_music():
    req = {**mpt.request(SPEC), "audio": "/workspace/projects/t/audio/full.wav", "script": "--evil flag"}
    c = mpt.cmd(req, "tid")
    assert not any(a.startswith("--confirm-") for a in c)
    assert "--bgm-type=none" in c
    assert "--video-script=--evil flag" in c  # `=` form: argparse cannot read script text as a flag


@pytest.fixture
def local_job(tmp_path, monkeypatch):
    root = tmp_path / "ws/jobs"
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(root.parent))
    clip = root / "source/clip.mp4"
    clip.parent.mkdir(parents=True)
    clip.write_bytes(b"approved footage")
    job = root / "job"
    (job / "audio").mkdir(parents=True)
    for i in (1, 2):
        (job / f"audio/{i:02}.wav").write_bytes(b"voice take")
    spec = {**SPEC, "render": "mpt", "mpt": {"source": "local", "materials": [str(clip)]}}
    ctx = {"dir": job, "spec": spec}

    def fake_concat(argv):
        assert argv[0] == "ffmpeg"
        Path(argv[-1]).write_bytes(b"joined narration")

    monkeypatch.setattr(mpt, "_run", fake_concat)
    return ctx, clip


def staged_request(ctx):
    path = ctx["dir"] / "project/mpt-request.json"
    request = json.loads(path.read_text())
    material = request["dependencies"][0]
    return path, request, ctx["dir"] / "project" / material["path"]


def test_compose_binds_staged_bytes_and_render_passes_only_staged_paths(local_job, tmp_path, monkeypatch):
    ctx, clip = local_job
    mpt.compose(ctx)
    _, req, staged = staged_request(ctx)
    entry = req["dependencies"][0]
    assert entry["sha256"] == hashlib.sha256(staged.read_bytes()).hexdigest()
    assert entry["origin"] == "source/clip.mp4"
    assert entry["license"] == mpt.LICENSE["local"][0]
    digest = pipeline.production_digest(ctx["dir"], ctx["spec"])
    assert digest
    clip.write_bytes(b"different footage at same filename")
    assert pipeline.production_digest(ctx["dir"], ctx["spec"]) == digest
    assert staged.read_bytes() == b"approved footage"

    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "out.mp4").write_bytes(b"rendered video")
    monkeypatch.setattr(mpt, "MPT_DIR", vendor)
    calls = []

    def run(argv):
        calls.append(argv)
        return json.dumps({"result": {"videos": ["/MoneyPrinterTurbo/out.mp4"]}})

    monkeypatch.setattr(mpt, "_run", run)
    video, rights = mpt.render(ctx)
    container_material = f"/workspace/projects/job/project/{entry['path']}"
    assert calls[0][-2:] == [container_material, entry["sha256"]]
    assert f"--video-materials={container_material}" in calls[1]
    assert "--video-source=local" in calls[1]
    assert not any("/source/clip.mp4" in arg for argv in calls for arg in argv)
    assert video.read_bytes() == b"rendered video"
    assert json.loads(rights.read_text())["dependencies"] == req["dependencies"]


@pytest.mark.parametrize("change", ["replace", "delete", "symlink", "provenance", "external", "legacy", "narration", "spec"])
def test_mpt_unreviewable_dependencies_block_approval_and_render(local_job, monkeypatch, change):
    ctx, clip = local_job
    mpt.compose(ctx)
    manifest, req, staged = staged_request(ctx)
    if change == "replace":
        staged.write_bytes(b"replacement")
    elif change == "narration":
        (ctx["dir"] / "project" / mpt.NARRATION).write_bytes(b"different narration")
    elif change == "spec":
        ctx["spec"]["mpt"]["clip_seconds"] = 9
    elif change in ("delete", "symlink"):
        staged.unlink()
        if change == "symlink":
            staged.symlink_to(clip)  # Even identical bytes cannot make a link an approved staged file.
    else:
        if change == "provenance":
            del req["dependencies"][0]["origin"]
        elif change == "external":
            req["dependencies"][0]["path"] = "../../source/clip.mp4"
        else:
            del req["dependencies"]
        manifest.write_text(json.dumps(req))
    assert pipeline.production_digest(ctx["dir"], ctx["spec"]) is None
    monkeypatch.setattr(mpt, "_run", lambda argv: pytest.fail("must not invoke a subprocess"))
    with pytest.raises(mpt.Unavailable):
        mpt.render(ctx)


def test_distinct_sources_with_identical_bytes_share_staged_identity(local_job):
    ctx, clip = local_job
    other = clip.with_name("renamed.mp4")
    other.write_bytes(clip.read_bytes())
    ctx["spec"]["mpt"]["materials"].append(str(other))
    mpt.compose(ctx)
    _, req, _ = staged_request(ctx)
    a, b = req["dependencies"]
    assert (a["path"], a["sha256"]) == (b["path"], b["sha256"])
    assert [a["origin"], b["origin"]] == ["source/clip.mp4", "source/renamed.mp4"]


def test_recomposing_replaced_source_changes_review_digest(local_job):
    ctx, clip = local_job
    mpt.compose(ctx)
    before = pipeline.production_digest(ctx["dir"], ctx["spec"])
    clip.write_bytes(b"replacement footage")
    mpt.compose(ctx)
    after = pipeline.production_digest(ctx["dir"], ctx["spec"])
    assert before and after and before != after
    assert staged_request(ctx)[2].read_bytes() == b"replacement footage"


def test_source_symlink_is_not_imported(local_job):
    ctx, clip = local_job
    target = clip.rename(clip.with_name("real.mp4"))
    clip.symlink_to(target)
    with pytest.raises(mpt.Unavailable, match="without links"):
        mpt.compose(ctx)


def test_remote_selection_cannot_bypass_review(local_job, monkeypatch):
    ctx, _ = local_job
    ctx["spec"]["mpt"] = {"source": "pexels"}
    monkeypatch.setattr(mpt, "_run", lambda argv: pytest.fail("must not invoke a subprocess"))
    with pytest.raises(mpt.Unavailable, match="before approval"):
        mpt.compose(ctx)
    assert pipeline.production_digest(ctx["dir"], ctx["spec"]) is None


def test_render_blocks_when_container_mount_differs(local_job, monkeypatch):
    ctx, _ = local_job
    mpt.compose(ctx)

    def wrong_mount(argv):
        raise RuntimeError("mounted SHA differs")

    monkeypatch.setattr(mpt, "_run", wrong_mount)
    with pytest.raises(mpt.Unavailable, match="container mount"):
        mpt.render(ctx)


def test_mpt_lane_has_its_own_compose_sentinel():
    assert pipeline.artifact("compose", {"render": "mpt"}) == "project/mpt-request.json"
    assert pipeline.artifact("compose", {}) == "project/index.html"
    assert pipeline.artifact("render", {"render": "mpt"}) == "video.mp4"
