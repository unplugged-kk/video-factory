"""A forced one-stage rerun must not leave later evidence or stale approvals looking current."""
from contentos import ledger, pipeline, storage


def test_compose_rerun_removes_downstream_evidence_and_revokes_production_grant(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "publishing"))
    storage.preflight()
    spec = {
        "content_id": "rerun-job", "title": "Rerun", "format": "9:16",
        "script": [{"say": "Stay local."}],
    }
    directory, _manifest = storage.open_job("rerun-job", spec)
    (directory / "project").mkdir()
    (directory / "project" / "index.html").write_text("<html></html>", encoding="utf-8")
    (directory / "video.mp4").write_bytes(b"video")
    (directory / "qa.json").write_text("[]", encoding="utf-8")
    ledger.approve("rerun-job", "SCRIPT_APPROVED", subject_sha256="script")
    ledger.approve("rerun-job", "PRODUCTION_APPROVED", subject_sha256="production")

    result = pipeline.invalidate_downstream(directory, spec, "compose")

    assert not (directory / "video.mp4").exists()
    assert not (directory / "qa.json").exists()
    assert (directory / "project" / "index.html").is_file()
    assert result["revokedApprovals"] == ["PRODUCTION_APPROVED"]
    assert ledger.check_gate("rerun-job", "PRODUCTION_APPROVED", "production")[0] == "none"
    assert ledger.check_gate("rerun-job", "SCRIPT_APPROVED", "script")[0] == "ok"
