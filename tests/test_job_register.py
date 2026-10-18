"""W1 / G-01: `contentos job register` brings a hand-built (Track B) job under the manifest, ledger and export discipline
without touching anything already in its folder. Hermetic: scratch workspace and publish dir, tiny ffmpeg videos."""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contentos import cli, export, ledger, storage  # noqa: E402
from storage_helpers import make_video  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    storage.preflight()
    d = storage.job_dir("tb1")
    make_video(d / "video.mp4", seconds=1)
    (d / "tools").mkdir()
    (d / "tools" / "chain.sh").write_text("hyperframes render\n")
    (d / "script.txt").write_text("hand written\n")
    return SimpleNamespace(dir=d, pub=tmp_path / "pub", tmp=tmp_path)


def snapshot(d):
    return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(d).rglob("*")) if p.is_file()}


def register(d, **kw):
    args = dict(path=str(d), track="B", title=None, project=None, project_name=None)
    args.update(kw)
    return cli.cmd_job_register(SimpleNamespace(**args))


def approve_both():
    for g in ("SCRIPT_APPROVED", "PRODUCTION_APPROVED"):
        ledger.approve("tb1", g, by="owner")


def test_register_creates_only_manifest_json(env):
    before = snapshot(env.dir)
    assert "manifest.json" not in before
    assert register(env.dir) == 0
    after = snapshot(env.dir)
    assert set(after) - set(before) == {"manifest.json"}
    assert {k: v for k, v in after.items() if k != "manifest.json"} == before         # every original byte untouched
    m = storage.read_manifest(env.dir)
    assert m["job_id"] == "tb1" and m["track"] == "B" and m["status"] == "created"
    assert m["validation"]["status"] == "passed"
    assert m["final_output"] == "video.mp4"


def test_register_takes_metadata_from_flags(env):
    register(env.dir, title="Hand Built", project="Your AI Buddy", project_name="Your AI Buddy")
    m = storage.read_manifest(env.dir)
    assert m["title"] == "Hand Built" and m["project_id"] == "your-ai-buddy"


def test_register_is_idempotent(env):
    register(env.dir)
    first = (env.dir / "manifest.json").read_bytes()
    n = ledger.db().execute("SELECT count(*) FROM runs WHERE content_id='tb1'").fetchone()[0]
    assert register(env.dir) == 0
    assert (env.dir / "manifest.json").read_bytes() == first                            # not even updated_at moves
    assert ledger.db().execute("SELECT count(*) FROM runs WHERE content_id='tb1'").fetchone()[0] == n


def test_register_records_external_ledger_rows(env):
    register(env.dir)
    rows = ledger.db().execute("SELECT stage, status FROM runs WHERE content_id='tb1'").fetchall()
    assert rows and all(status == "EXTERNAL" for _, status in rows)
    assert {"script", "voice", "compose", "render"} <= {stage for stage, _ in rows}


def test_register_grants_no_approval(env):
    register(env.dir)
    assert ledger.db().execute("SELECT count(*) FROM approvals").fetchone()[0] == 0


def test_export_refuses_until_both_gates_exist_then_exports_once(env):
    register(env.dir)
    with pytest.raises(export.ExportRefused, match="SCRIPT_APPROVED.*PRODUCTION_APPROVED"):
        export.export_job("tb1")
    ledger.approve("tb1", "SCRIPT_APPROVED", by="owner")
    with pytest.raises(export.ExportRefused, match="PRODUCTION_APPROVED"):
        export.export_job("tb1")
    assert not list((env.pub / "ready").rglob("*.mp4"))
    ledger.approve("tb1", "PRODUCTION_APPROVED", by="owner")
    assert export.export_job("tb1")["status"] == "exported"
    assert export.export_job("tb1")["status"] == "already_exported"
    assert len(list((env.pub / "ready").rglob("*.mp4"))) == 1
    assert register(env.dir) == 0                                                       # registering after export changes nothing
    assert storage.read_manifest(env.dir)["status"] == "exported"


def test_publish_is_never_granted_by_registering_or_exporting(env):
    register(env.dir)
    approve_both()
    export.export_job("tb1")
    assert not ledger.approved("tb1", "PUBLISH_APPROVED")


def test_unregistered_directory_still_cannot_export(env):
    with pytest.raises(storage.StorageError, match="no manifest"):
        export.export_job("tb1")


def test_track_a_export_is_unchanged(env):
    """A pipeline job has no track marker, so the new gate check does not apply to it."""
    d, _ = storage.open_job("pj", {"title": "Pipeline Job", "project": "Demo"})
    make_video(d / "video.mp4", seconds=1)
    assert export.export_job("pj")["status"] == "exported"


def test_register_refuses_missing_video(env):
    (env.dir / "video.mp4").unlink()
    with pytest.raises(storage.StorageError, match="video.mp4"):
        register(env.dir)
    assert not (env.dir / "manifest.json").exists()


def test_register_refuses_a_directory_outside_the_jobs_root(env):
    outside = env.tmp / "elsewhere" / "tb2"
    make_video(outside / "video.mp4", seconds=1)
    with pytest.raises(storage.StorageError, match="jobs"):
        register(outside)
    assert not (outside / "manifest.json").exists()


def test_register_refuses_a_legacy_manifest_and_leaves_it_alone(env):
    (env.dir / "manifest.json").write_text(json.dumps({"schema": "contentos-project-manifest/1", "title": "old"}))
    before = snapshot(env.dir)
    with pytest.raises(storage.StorageError, match="adopt"):
        register(env.dir)
    assert snapshot(env.dir) == before


def test_register_does_not_convert_a_track_a_job(env):
    d, _ = storage.open_job("pj", {"title": "Pipeline Job"})
    make_video(d / "video.mp4", seconds=1)
    before = snapshot(d)
    with pytest.raises(storage.StorageError, match="Track A"):
        register(d)
    assert snapshot(d) == before


def test_cli_parses_job_register(env, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["contentos", "job", "register", str(env.dir), "--track", "B"])
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 0
    assert storage.read_manifest(env.dir)["track"] == "B"


def test_cli_rejects_other_tracks(env, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["contentos", "job", "register", str(env.dir), "--track", "A"])
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code != 0
    assert not (env.dir / "manifest.json").exists()
