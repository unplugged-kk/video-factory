"""export-integrity/1: does an exported job's workspace video still match what was exported?

Read-only by contract: `export.divergence()` must report a mismatch and never repair one, because only a human can
decide whether a newer render is the one to ship. Every test therefore also asserts the publishing tree is untouched.
"""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contentos import export, handoff, storage  # noqa: E402
from storage_helpers import make_video  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    monkeypatch.delenv("VIDEO_FACTORY_EXPORT_MODE", raising=False)
    storage.preflight()
    return tmp_path / "ws", tmp_path / "pub"


def job(job_id="job-1", **spec):
    d, _ = storage.open_job(job_id, {"title": "What Happens When an AI Agent Uses a Tool?", "project": "Demo",
                                     "project_name": "Demo", "kind": "short", **spec})
    return d


def tree(root):
    return sorted(p.relative_to(root).as_posix() for p in Path(root).rglob("*") if p.is_file())


def exported(d, video):
    shutil.copy(video, d / "video.mp4")
    return export.export_job(d.name)


def test_a_matching_export_reports_ok_and_writes_nothing(env, tmp_path):
    ws, pub = env
    d = job()
    exported(d, make_video(tmp_path / "v.mp4", seconds=1))
    before = tree(pub)

    rep = export.divergence()
    assert rep["checked"] == 1 and [r["job_id"] for r in rep["ok"]] == ["job-1"]
    assert rep["superseded"] == []
    assert tree(pub) == before                                   # read-only: no file added, moved or replaced
    assert not list((pub / ".staging").iterdir())


def test_a_rerendered_workspace_video_is_reported_superseded(env, tmp_path):
    """The defect class: the workspace has a newer render than the one sitting in ready/."""
    ws, pub = env
    d = job()
    exported(d, make_video(tmp_path / "v1.mp4", seconds=1))
    shutil.copy(make_video(tmp_path / "v2.mp4", seconds=3), d / "video.mp4")
    before = tree(pub)

    rep = export.divergence()
    assert [r["job_id"] for r in rep["superseded"]] == ["job-1"]
    r = rep["superseded"][0]
    assert r["workspace_sha256"] != r["exported_sha256"]
    assert r["workspace_sha256"] == export.sha256_file(d / "video.mp4")
    assert tree(pub) == before                                   # it reports; it never reconciles


def test_a_missing_workspace_video_is_informational_not_superseded(env, tmp_path):
    """An adopted, legacy or cleaned job has no workspace video and is not a mismatch."""
    ws, pub = env
    d = job()
    exported(d, make_video(tmp_path / "v.mp4", seconds=1))
    (d / "video.mp4").unlink()

    rep = export.divergence()
    assert rep["superseded"] == [] and rep["ok"] == []
    assert [r["job_id"] for r in rep["workspace_video_missing"]] == ["job-1"]


def test_a_missing_sidecar_is_reported(env, tmp_path):
    """The sidecar is the ready marker; without it nothing in ready/ is publishable."""
    ws, pub = env
    d = job()
    exported(d, make_video(tmp_path / "v.mp4", seconds=1))
    next((pub / "ready").rglob("*.publish.json")).unlink()

    rep = export.divergence()
    assert [r["job_id"] for r in rep["sidecar_missing"]] == ["job-1"]
    assert rep["superseded"] == [] and rep["ok"] == []


def test_an_archived_job_is_reported_archived(env, tmp_path):
    """Handed off and archived is the expected end state, not a mismatch."""
    ws, pub = env
    d = job()
    exported(d, make_video(tmp_path / "v.mp4", seconds=1))
    handoff.claim(pub, "job-1", "scheduler")
    handoff.transition(pub, "job-1", "published", "scheduler")
    handoff.archive(pub, "job-1")

    rep = export.divergence()
    assert [r["job_id"] for r in rep["archived"]] == ["job-1"]
    assert rep["superseded"] == [] and rep["ok"] == []


def test_a_job_that_was_never_exported_is_skipped(env, tmp_path):
    ws, pub = env
    job("job-1")

    rep = export.divergence()
    assert rep["checked"] == 0
    for bucket in ("ok", "superseded", "sidecar_missing", "workspace_video_missing", "archived", "never_exported"):
        assert rep[bucket] == []


# ---- resume_blocker: the same classification, used to refuse a dishonest resume ----

def test_resume_blocker_allows_a_matching_render(env, tmp_path):
    ws, pub = env
    d = job()
    exported(d, make_video(tmp_path / "v.mp4", seconds=1))

    assert export.resume_blocker(d) is None


def test_resume_blocker_refuses_a_stale_render_and_names_both_shas(env, tmp_path):
    ws, pub = env
    d = job()
    exported(d, make_video(tmp_path / "v1.mp4", seconds=1))
    shutil.copy(make_video(tmp_path / "v2.mp4", seconds=3), d / "video.mp4")

    reason = export.resume_blocker(d)
    assert reason is not None
    assert "render changed since it was exported" in reason and "--force" in reason
    assert export.sha256_file(d / "video.mp4")[:12] in reason      # the diagnostic points at the render in question


def test_resume_blocker_reports_an_unreadable_manifest_instead_of_raising(env, tmp_path):
    ws, pub = env
    d = job()
    exported(d, make_video(tmp_path / "v.mp4", seconds=1))
    (d / "manifest.json").write_text('{"id": "legacy", "title": "not jobmanifest/1"}')
    before = tree(pub)

    reason = export.resume_blocker(d)
    assert reason is not None and "cannot be read" in reason
    assert tree(pub) == before                                     # it decides; it never writes
