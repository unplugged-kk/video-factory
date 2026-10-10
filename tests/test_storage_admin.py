"""Migration, retention cleanup and legacy compatibility. Everything runs on temp copies; originals are never touched."""
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import ledger, storage, storage_admin  # noqa: E402

LEDGER_DDL = ledger.DDL


@pytest.fixture
def world(tmp_path, monkeypatch):
    repo, ws = tmp_path / "repo", tmp_path / "ws"
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(ws))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    legacy = repo / "workspace"
    (legacy / "projects" / "old-job" / "audio").mkdir(parents=True)
    (legacy / "projects" / "old-job" / "video.mp4").write_bytes(b"V" * 4096)
    (legacy / "projects" / "old-job" / "audio" / "a.wav").write_bytes(b"A" * 1024)
    (legacy / "projects" / "old-job" / "content.json").write_text(json.dumps({"title": "Old Job", "format": "9:16"}))
    (legacy / "projects" / "pilot-001").mkdir()
    (legacy / "projects" / "pilot-001" / "manifest.json").write_text(json.dumps({"id": "pilot-001", "slides": []}))
    (legacy / "projects" / "busy").mkdir()
    (legacy / "projects" / "busy" / "f").write_text("x")
    (legacy / "research").mkdir(); (legacy / "research" / "r.md").write_text("notes")
    db = sqlite3.connect(legacy / "ledger.db")
    db.executescript(LEDGER_DDL)
    db.execute("insert into runs(content_id,status) values ('old-job','done'), ('busy','running')")
    db.execute("insert into jobs(content_id,status) values ('old-job','done'), ('busy','running')")
    db.commit(); db.close()
    (repo / "output").mkdir(); (repo / "output" / "legacy.mp4").write_bytes(b"L" * 100)
    return repo, ws


def snap(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in Path(root).rglob("*") if p.is_file()}


def test_inventory_is_read_only_and_flags_risks(world):
    repo, ws = world
    before = snap(repo)
    items = {i["path"]: i for i in storage_admin.inventory(repo=repo, ws=ws)}
    assert snap(repo) == before and not ws.exists()
    assert items["workspace/projects/old-job"]["action"] == "copy"
    assert any("own manifest" in r for r in items["workspace/projects/pilot-001"]["risks"])
    assert any("queued/running" in r for r in items["workspace/projects/busy"]["risks"])
    assert "output" in items and items["output"]["destination"] == "recovery/legacy-root/output"


def test_dry_run_copies_nothing(world):
    repo, ws = world
    log = storage_admin.migrate(repo=repo, ws=ws)
    assert not ws.exists() and any(r["status"] == "would copy" for r in log["results"])


def test_apply_copies_verifies_never_deletes_and_is_rerunnable(world):
    repo, ws = world
    before = snap(repo)
    log = storage_admin.migrate(apply=True, repo=repo, ws=ws)
    assert snap(repo) == before                                           # originals untouched
    st = {r["path"]: r["status"] for r in log["results"]}
    assert st["workspace/projects/old-job"] == "copied and verified"
    assert st["workspace/projects/busy"] == "skipped"                     # active job
    dest = next(ws.glob("jobs/*/*/old-job"))
    assert (dest / "video.mp4").read_bytes() == b"V" * 4096 and (dest / "audio" / "a.wav").exists()
    assert storage.read_manifest(dest)["status"] == "ready"               # seeded from content.json, not validated
    assert sqlite3.connect(ws / "ledger.db").execute("select count(*) from runs").fetchone()[0] == 2
    assert (ws / "recovery" / "legacy-root" / "output" / "legacy.mp4").exists()
    assert list((ws / "recovery" / "migrations").glob("migration-*.json"))
    again = storage_admin.migrate(apply=True, repo=repo, ws=ws)
    assert not any(r["status"] == "copied and verified" for r in again["results"])         # nothing overwritten on re-run
    assert next(ws.glob("jobs/*/*/old-job")) == dest


def test_foreign_manifest_survives_migration_and_adopts(world):
    repo, ws = world
    storage_admin.migrate(apply=True, repo=repo, ws=ws)
    d = next(ws.glob("jobs/*/*/pilot-001"))
    assert json.loads((d / "manifest.json").read_text())["id"] == "pilot-001"
    storage.adopt(d)
    assert (d / "metadata" / "legacy-manifest.json").exists() and storage.read_manifest(d)["job_id"] == "pilot-001"


def test_include_active_flag(world):
    repo, ws = world
    storage_admin.migrate(apply=True, include_active=True, repo=repo, ws=ws)
    assert list(ws.glob("jobs/*/*/busy"))


def test_migration_failure_is_reported_and_leaves_source(world, monkeypatch):
    repo, ws = world
    def boom(src, dest):
        raise OSError("disk full")
    monkeypatch.setattr(storage_admin, "_copy_item", boom)
    log = storage_admin.migrate(apply=True, repo=repo, ws=ws)
    assert any(r["status"] == "FAILED" for r in log["results"]) and (repo / "workspace/projects/old-job/video.mp4").exists()


def _exported_job(ws, job_id, age_days, status="exported"):
    d, m = storage.open_job(job_id, {"title": job_id})
    (d / "temporary").mkdir(); (d / "temporary" / "t.bin").write_bytes(b"t" * 500)
    (d / "video.mp4").write_bytes(b"final")
    import datetime as dt
    stamp = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=age_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    storage.update_manifest(d, status=status, export={"status": "exported", "exported_at": stamp}, final_output="video.mp4")
    mm = storage.read_manifest(d); mm["updated_at"] = stamp; storage.write_json_atomic(d / "manifest.json", mm)
    return d


def test_cleanup_dry_run_then_apply_keeps_final_and_recent(world):
    repo, ws = world
    storage.preflight()
    old, new = _exported_job(ws, "old", 40), _exported_job(ws, "new", 2)
    fail = _exported_job(ws, "failed-one", 400, status="failed")
    keep = _exported_job(ws, "pinned", 400); (keep / ".keep").write_text("")
    dry = storage_admin.cleanup()
    assert [c["job"] for c in dry["candidates"]] == ["old"] and (old / "temporary" / "t.bin").exists()
    reasons = {s["job"]: s["reason"] for s in dry["skipped"]}
    assert "keeping" in reasons["new"] and ".keep" in reasons["pinned"] and "not eligible" in reasons["failed-one"]
    storage_admin.cleanup(apply=True)
    assert not (old / "temporary").exists() and (old / "video.mp4").exists()
    assert (new / "temporary" / "t.bin").exists() and (fail / "temporary").exists() and (keep / "temporary").exists()


def test_cleanup_skips_locked_and_active(world):
    repo, ws = world
    storage.preflight()
    d = _exported_job(ws, "old", 90)
    with storage.file_lock(d / ".manifest.lock"):
        r = storage_admin.cleanup()
    assert any("in use" in s["reason"] for s in r["skipped"])
    db = sqlite3.connect(ws / "ledger.db"); db.executescript(LEDGER_DDL)
    db.execute("insert into jobs(content_id,status) values ('old','queued')"); db.commit(); db.close()
    assert not storage_admin.cleanup()["candidates"]


def test_cleanup_ignores_paths_outside_job_via_symlink(world):
    repo, ws = world
    storage.preflight()
    d = _exported_job(ws, "old", 90)
    outside = ws.parent / "precious"; outside.mkdir(); (outside / "keep.txt").write_text("k")
    os.symlink(outside, d / "temporary" / "link")
    storage_admin.cleanup(apply=True)
    assert (outside / "keep.txt").exists()
