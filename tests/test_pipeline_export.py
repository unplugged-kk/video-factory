"""The pipeline's export stage: a validated render reaches ready/; a bad one never does; retries add nothing.
Also: `--force` must reach export, and two runs of one job must not interleave."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contentos import export, handoff, pipeline, storage  # noqa: E402
from contentos.production import supplied_audio  # noqa: E402
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


# ---- --force must reach export (it used to dead-end there) and must not go too far ----

def test_forced_rerun_replaces_superseded_export(setup, tmp_path):
    """A re-render that changes the bytes must be exportable with --force. This is the case that used to fail."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v1.mp4", seconds=1))
    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "OK")
    first = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())

    shutil.copy(make_video(tmp_path / "v2.mp4", seconds=3), d / "video.mp4")
    _, report = pipeline.run(spec, only="export", force=True)
    assert report[0][:2] == ("export", "OK")
    sidecars = list((pub / "ready").rglob("*.publish.json"))
    assert len(sidecars) == 1                                        # replaced in place, not duplicated
    second = json.loads(sidecars[0].read_text())
    assert second["video_sha256"] == export.sha256_file(d / "video.mp4")
    assert second["video_sha256"] != first["video_sha256"]
    assert storage.read_manifest(d)["status"] == "exported"


def test_rerun_without_force_refuses_superseded_export(setup, tmp_path):
    """Without --force the old refusal stands, and the already-exported video is left untouched.

    The export stage's resume sentinel is removed first to reach the stage at all - see the skip test below for why a
    plain re-run never gets this far.
    """
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v1.mp4", seconds=1))
    pipeline.run(spec, only="export")
    shutil.copy(make_video(tmp_path / "v2.mp4", seconds=3), d / "video.mp4")
    (d / "export-result.json").unlink()          # the sentinel the pipeline itself deletes when a stage fails

    _, report = pipeline.run(spec, only="export")
    assert report[0][1].startswith("FAIL")
    assert "force" in report[0][1]
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1
    sc = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    assert sc["video_sha256"] != export.sha256_file(d / "video.mp4")  # nothing was replaced


# ---- a resumed export is only "done" when the render still matches what was exported ----

def test_a_matching_render_still_resumes_silently(setup, tmp_path):
    """Normal resume must be untouched: same render, so the skip is honest."""
    spec, pub = setup
    stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    pipeline.run(spec, only="export")

    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "SKIP(resume)")


def test_a_stale_render_blocks_the_resume_instead_of_reporting_success(setup, tmp_path):
    """The gap this closes: a re-render must not be reported as a successful export resume."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v1.mp4", seconds=1))
    pipeline.run(spec, only="export")
    first = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    shutil.copy(make_video(tmp_path / "v2.mp4", seconds=3), d / "video.mp4")

    _, report = pipeline.run(spec, only="export")
    assert report[0][0] == "export" and report[0][1].startswith("BLOCKED")
    assert "render changed since it was exported" in report[0][1]
    assert "--force" in report[0][1]
    assert (d / "export-result.json").exists()                    # the sentinel is kept, so no later run self-authorises
    sc = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    assert sc["video_sha256"] == first["video_sha256"]            # ready/ still holds the older, exported render
    assert [r["job_id"] for r in export.divergence()["superseded"]] == ["pj"]

    _, report = pipeline.run(spec, only="export", force=True)      # the explicit path still replaces it
    assert report[0][:2] == ("export", "OK")
    sc = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    assert sc["video_sha256"] == export.sha256_file(d / "video.mp4")


def test_a_claimed_export_that_still_matches_resumes(setup, tmp_path):
    """A claim protects replacement without adding a false block: an unchanged render still resumes."""
    spec, pub = setup
    stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    pipeline.run(spec, only="export")
    handoff.claim(pub, "pj", "scheduler")

    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "SKIP(resume)")


def test_a_resume_that_cannot_be_verified_is_blocked(setup, tmp_path):
    """Lost export metadata must block with a diagnostic, never resume as a pass and never re-export."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    pipeline.run(spec, only="export")
    next((pub / "ready").rglob("*.publish.json")).unlink()
    (pub / ".state" / "exports" / "pj.json").unlink()
    before = sorted(p.relative_to(pub).as_posix() for p in pub.rglob("*") if p.is_file())

    _, report = pipeline.run(spec, only="export")
    assert report[0][0] == "export" and report[0][1].startswith("BLOCKED")
    assert "cannot verify" in report[0][1] and "--force" in report[0][1]
    assert (d / "export-result.json").exists()
    assert sorted(p.relative_to(pub).as_posix() for p in pub.rglob("*") if p.is_file()) == before


# Not covered here: a manifest that is not jobmanifest/1. `run()` calls `storage.open_job` before the stage loop and that
# raises StorageError, so a legacy job never reaches the resume guard; its own handling of that input is covered by
# tests/test_export_divergence.py, which calls resume_blocker directly and asserts a diagnostic rather than a raise.
# (Out of scope for this change: the pre-existing open_job failure, whose documented remedy is `contentos storage adopt`.)


def test_an_archived_job_and_a_job_without_a_video_still_resume(setup, tmp_path):
    """Neither is a stale export: an archived job was handed off deliberately, and a job with no workspace video has
    nothing to compare. Blocking either would be noise and would mark the archived job failed."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    pipeline.run(spec, only="export")
    handoff.claim(pub, "pj", "scheduler")
    handoff.transition(pub, "pj", "published", "scheduler")
    handoff.archive(pub, "pj")

    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "SKIP(resume)")            # archived

    (d / "video.mp4").unlink()                                   # nothing to compare
    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "SKIP(resume)")


def test_forced_rerun_cannot_replace_a_claimed_export(setup, tmp_path):
    """force supersedes an unclaimed export only. A scheduler's claim must still refuse."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v1.mp4", seconds=1))
    pipeline.run(spec, only="export")
    handoff.claim(pub, "pj", "scheduler")
    shutil.copy(make_video(tmp_path / "v2.mp4", seconds=3), d / "video.mp4")

    _, report = pipeline.run(spec, only="export", force=True)
    assert report[0][1].startswith("FAIL")
    assert "claimed" in report[0][1]
    sc = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    assert sc["video_sha256"] != export.sha256_file(d / "video.mp4")


def test_forced_rerun_of_identical_video_is_a_no_op(setup, tmp_path):
    """force must not rewrite an export that is already current."""
    spec, pub = setup
    stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    pipeline.run(spec, only="export")
    snapshot = sorted(p.relative_to(pub).as_posix() for p in pub.rglob("*") if p.is_file())

    _, report = pipeline.run(spec, only="export", force=True)
    assert report[0][:2] == ("export", "OK")
    assert sorted(p.relative_to(pub).as_posix() for p in pub.rglob("*") if p.is_file()) == snapshot


def test_second_run_refuses_while_the_run_lock_is_held(setup, tmp_path):
    """Two runs of one job must not interleave: the second is refused by name, before any stage runs."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    with storage.file_lock(d / ".run.lock"):
        with pytest.raises(storage.StorageError, match=r"\.run\.lock is held by another process"):
            pipeline.run(spec, only="export")
    _, report = pipeline.run(spec, only="export")                    # free again once the holder released it
    assert report[0][:2] == ("export", "OK")


def test_force_does_not_bypass_a_supplied_audio_blocker(setup, tmp_path):
    """force replaces an export; it must never carry rights-unclear audio into ready/."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    take = tmp_path / "take.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(take)], check=True)
    supplied_audio.ingest(take, d, rights="unknown")

    _, report = pipeline.run(spec, only="export", force=True)
    assert report[0][1].startswith("BLOCKED")
    assert "supplied audio" in report[0][1]
    assert list((pub / "ready").rglob("*.mp4")) == []
