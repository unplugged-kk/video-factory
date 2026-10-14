"""The legacy `contentos-project-manifest/1` shape: refused, reported, and what `storage adopt` does to it.

Built from the real shape of `pilot-001-agent-tool-use` (a pre-`contentos` pilot): a 30-entry `files[]` provenance
ledger, `status: READY_FOR_HUMAN_REVIEW`, two format masters under `renders/` and no `video.mp4`. Everything here runs in
a tmp workspace, so the real job is never read, adopted or modified.

These tests deliberately pin two things that are *consequences*, not bugs to be discovered later: `adopt()` derives
`content_id` from the title (which drifts from the id the Rule B shipped-look ledger records), and a legacy job is
ineligible for cleanup both before and after adoption.
"""
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contentos import export, ledger, pipeline, storage, storage_admin  # noqa: E402
from contentos.production import core  # noqa: E402
from storage_helpers import make_video  # noqa: E402

JOB = "pilot-001-agent-tool-use"
TITLE = "What Happens When an AI Agent Uses a Tool?"

LEGACY = {
    "schema": "contentos-project-manifest/1",
    "project": JOB,
    "title": TITLE,
    "generated": "2026-10-10 22:33:31",
    "status": "READY_FOR_HUMAN_REVIEW",
    "published": False,
    "gates": {"PUBLISH_APPROVED": "NOT GRANTED - nothing uploaded or published"},
    "durations_s": {"narration": 44.62, "video": 48.2, "lead": 0.35},
    "formats": {"landscape": "1920x1080 30fps h264+aac", "portrait": "1080x1920 30fps h264+aac"},
    "toolchain": {"renderer": "hyperframes 0.8.114 (repo-pinned)"},
    "estimated_external_cost_usd": 0.0,
    "files": [{"path": "renders/pilot-001-portrait-master.mp4", "role": "9:16 master",
               "bytes": 1, "sha256": "0" * 64}],
}


@pytest.fixture
def legacy(tmp_path, monkeypatch):
    """A synthetic legacy job: month-level layout, legacy manifest, masters under renders/ and no video.mp4."""
    ws, pub = tmp_path / "ws", tmp_path / "pub"
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(ws))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(pub))
    monkeypatch.delenv("VIDEO_FACTORY_EXPORT_MODE", raising=False)
    storage.preflight()
    d = ws / "jobs" / "2026" / "10" / JOB                       # the pre-day-folder layout
    (d / "renders").mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps(LEGACY, indent=1))
    make_video(d / "renders" / "pilot-001-portrait-master.mp4", seconds=1)
    return d, pub


def tree(root):
    return sorted(p.relative_to(root).as_posix() for p in Path(root).rglob("*") if p.is_file())


def test_read_manifest_and_open_job_both_refuse_a_legacy_manifest(legacy):
    d, _ = legacy
    with pytest.raises(storage.StorageError, match="jobmanifest/1"):
        storage.read_manifest(d)
    with pytest.raises(storage.StorageError, match="jobmanifest/1"):
        storage.open_job(JOB, {"title": TITLE})                 # the unhandled-traceback path in pipeline.run


def test_divergence_reports_it_as_unreadable_manifest(legacy):
    d, _ = legacy
    rep = export.divergence()
    assert rep["unreadable_manifest"] == [JOB]
    assert rep["checked"] == 0                                  # it is never evaluated for an export relationship


def test_cleanup_skips_a_legacy_job_as_not_managed(legacy):
    d, _ = legacy
    r = storage_admin.cleanup()
    assert r["candidates"] == []
    assert any(s["job"] == JOB and "legacy manifest, not managed" in s["reason"] for s in r["skipped"])


def test_adopt_preserves_the_original_bytes_and_records_what_it_cannot_know(legacy):
    d, pub = legacy
    original = (d / "manifest.json").read_bytes()
    before = tree(pub)

    m = storage.adopt(d)
    assert m is not None
    assert (d / "metadata" / "legacy-manifest.json").read_bytes() == original    # byte-for-byte, not re-serialised

    got = storage.read_manifest(d)
    assert got["schema"] == "jobmanifest/1" and got["job_id"] == JOB
    assert got["title"] == TITLE                                 # the only field adopt reads
    assert got["status"] == "created"                            # READY_FOR_HUMAN_REVIEW is not a job status
    assert got["project_id"] == "unassigned"                     # the legacy `project` field is ignored
    assert got["content_id"] == "what-happens-when-an-ai-agent-uses-a-tool"
    assert got["content_id"] != JOB                              # WARNING: drifts from the Rule B ledger's id
    assert got["aspect_ratio"] is None and got["export"] is None  # unknown values are never invented
    assert tree(pub) == before                                   # adoption touches no published artifact

    assert storage.adopt(d) is None                              # idempotent
    assert (d / "metadata" / "legacy-manifest.json").read_bytes() == original


def test_after_adoption_the_job_is_managed_but_still_not_exportable(legacy):
    """Adoption buys management, not a route to shipping: there is still no video.mp4."""
    d, pub = legacy
    storage.adopt(d)
    before = tree(pub)

    rep = export.divergence()
    assert rep["unreadable_manifest"] == []                      # the noise is gone
    # ...but it is not compared either: divergence() only looks at jobs that have an export record or status
    # "exported", and an adopted job has neither. So the integrity check has nothing to say about it - it is managed,
    # not verified. That is the honest outcome, and why adoption is not a route to shipping this job.
    assert rep["checked"] == 0
    for bucket in ("ok", "superseded", "sidecar_missing", "workspace_video_missing", "archived", "never_exported"):
        assert rep[bucket] == []

    r = storage_admin.cleanup()
    assert r["candidates"] == []                                 # being managed does not make it deletable
    assert any(s["job"] == JOB and "status created is not eligible" in s["reason"] for s in r["skipped"])

    ready_before = tree(pub / "ready")
    with pytest.raises(export.ExportRefused, match="final video is missing"):
        export.export_job(JOB)                                   # the masters are renders/*-master.mp4, not video.mp4
    assert tree(pub / "ready") == ready_before                   # nothing published was touched
    # the only side effect anywhere under the library is the export lock, which export_job takes before it refuses
    assert set(tree(pub)) - set(before) == {f".state/locks/{JOB}.lock"}


# ---- how pipeline.run reports it: a blocked row, not a traceback ----


def spec_file(tmp_path, **over):
    sp = tmp_path / "spec.yaml"
    sp.write_text(yaml.safe_dump({"content_id": JOB, "title": TITLE, "project": "Demo",
                                  "script": [{"say": "Hi there."}], **over}))
    return sp


def test_run_reports_a_legacy_manifest_as_blocked_instead_of_raising(legacy, tmp_path):
    """Before this, the StorageError escaped pipeline.run uncaught and reached the CLI as a raw traceback."""
    d, _ = legacy
    rid, report = pipeline.run(spec_file(tmp_path), only="export")

    assert rid and len(report) == 1                              # it stops before any stage runs
    stage, status, _ = report[0]
    assert stage == "manifest" and status.startswith("BLOCKED")
    assert "jobmanifest/1" in status and "adopt" in status        # the actionable message survives verbatim
    assert not (d / "metadata").exists()                         # reporting it never adopts it

    with ledger.db() as c:
        row = c.execute("select stage, status, error from runs where content_id=? order by rowid desc limit 1",
                        (JOB,)).fetchone()
    assert row and row[0] == "manifest" and row[1] == "BLOCKED" and "adopt" in row[2]


def test_the_blocked_manifest_row_is_not_retried(legacy, tmp_path):
    """core.classify() must not call it transient, or the worker would loop on something only an operator can fix."""
    _, report = pipeline.run(spec_file(tmp_path), only="export")

    assert core.classify(report[0][0], report[0][1]) == "blocked"
    assert "manifest" not in core.TRANSIENT_STAGES


def test_run_still_raises_for_an_unrelated_storage_error(tmp_path, monkeypatch):
    """The catch is scoped to open_job alone: a preflight failure must surface as itself, not become a BLOCKED row."""
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(storage.REPO / "workspace"))   # inside the repo: preflight refuses

    with pytest.raises(storage.StorageError, match="inside the repository"):
        pipeline.run(spec_file(tmp_path), only="export")
