"""Export lifecycle: validation gate, staging, atomic promotion, idempotency, concurrency, failure and recovery."""
import json
import shutil
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contentos import export, handoff, storage  # noqa: E402
from storage_helpers import make_video  # noqa: E402


@pytest.fixture(scope="module")
def good_video(tmp_path_factory):
    return make_video(tmp_path_factory.mktemp("fx") / "good.mp4")


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    monkeypatch.delenv("VIDEO_FACTORY_EXPORT_MODE", raising=False)
    storage.preflight()
    return tmp_path / "ws", tmp_path / "pub"


def job(good_video, job_id="job-1", video=True, **spec):
    d, _ = storage.open_job(job_id, {"title": "What Happens When an AI Agent Uses a Tool?", "project": "AI Explained",
                                     "project_name": "AI Explained", "platform_targets": ["youtube_shorts"],
                                     "language": "en", "kind": "short", "tags": ["ai"], **spec})
    (d / "temporary").mkdir(exist_ok=True)
    (d / "temporary" / "scratch.bin").write_bytes(b"x" * 100)
    if video is True:
        shutil.copy(good_video, d / "video.mp4")
    elif video:
        shutil.copy(video, d / "video.mp4")
    return d


def tree(root):
    return sorted(p.relative_to(root).as_posix() for p in Path(root).rglob("*") if p.is_file())


def test_success_nested_layout_and_sidecar(env, good_video):
    ws, pub = env
    d = job(good_video)
    r = export.export_job("job-1")
    assert r["status"] == "exported"
    ym = storage.read_manifest(d)["created_at"]
    video = pub / "ready" / "ai-explained" / ym[:4] / ym[5:7] / "what-happens-when-an-ai-agent-uses-a-tool__job-1.mp4"
    assert video.is_file() and video.with_suffix("").with_name(video.stem + ".publish.json").is_file()
    sc = json.loads(video.with_suffix("").with_name(video.stem + ".publish.json").read_text())
    for k in ("schema_version", "project_id", "content_id", "job_id", "title", "video_filename", "video_sha256", "video_bytes",
              "duration_seconds", "validation_status", "publishing_status", "created_at", "exported_at"):
        assert k in sc
    assert sc["validation_status"] == "passed" and sc["publishing_status"] == "ready"
    assert sc["scheduled_at"] is None and sc["published_at"] is None            # never invented
    assert sc["video_sha256"] == export.sha256_file(video) and sc["video_bytes"] == video.stat().st_size
    assert str(ws) not in json.dumps(sc) and str(pub) not in json.dumps(sc)       # no absolute paths
    assert not list((pub / ".staging").iterdir())
    assert [p for p in tree(pub / "ready") if not p.endswith((".mp4", ".publish.json"))] == []   # nothing but video + sidecar
    m = storage.read_manifest(d)
    assert m["status"] == "exported" and m["export"]["sha256"] == sc["video_sha256"] and m["validation"]["status"] == "passed"
    assert (d / "temporary" / "scratch.bin").exists()                              # workspace intermediates untouched


def test_flat_mode(env, good_video):
    ws, pub = env
    job(good_video)
    r = export.export_job("job-1", mode="flat")
    assert Path(r["video"]).parent.as_posix() == "ready"


def test_two_projects_do_not_collide(env, good_video):
    job(good_video, "job-1", project="Alpha"); job(good_video, "job-2", project="Beta")
    a, b = export.export_job("job-1"), export.export_job("job-2")
    assert a["video"].split("/")[1] == "alpha" and b["video"].split("/")[1] == "beta"


def test_same_content_two_jobs_get_distinct_files(env, good_video):
    job(good_video, "job-1", content="intro"); job(good_video, "job-2", content="intro")
    assert export.export_job("job-1")["video"] != export.export_job("job-2")["video"]


def test_retry_is_idempotent_no_duplicates(env, good_video):
    ws, pub = env
    job(good_video)
    first = export.export_job("job-1")
    snapshot = tree(pub)
    second = export.export_job("job-1")
    assert second["status"] == "already_exported" and second["video"] == first["video"]
    assert tree(pub) == snapshot


def test_different_video_for_same_job_needs_force(env, good_video, tmp_path):
    ws, pub = env
    d = job(good_video)
    export.export_job("job-1")
    other = make_video(tmp_path / "other.mp4", seconds=3)
    shutil.copy(other, d / "video.mp4")
    with pytest.raises(export.ExportRefused, match="force"):
        export.export_job("job-1")
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1
    r = export.export_job("job-1", force=True)
    assert r["status"] == "exported" and len(list((pub / "ready").rglob("*.mp4"))) == 1
    sc = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    assert sc["video_sha256"] == export.sha256_file(d / "video.mp4")


def test_claimed_video_is_never_replaced(env, good_video, tmp_path):
    ws, pub = env
    d = job(good_video)
    export.export_job("job-1")
    handoff.claim(pub, "job-1", "sched")
    shutil.copy(make_video(tmp_path / "o.mp4", seconds=3), d / "video.mp4")
    with pytest.raises(export.ExportRefused, match="claimed"):
        export.export_job("job-1", force=True)


def test_archived_job_is_not_reexported(env, good_video):
    ws, pub = env
    job(good_video)
    export.export_job("job-1")
    handoff.claim(pub, "job-1", "s"); handoff.transition(pub, "job-1", "published", "s"); handoff.archive(pub, "job-1")
    assert not list((pub / "ready").rglob("*.mp4"))
    with pytest.raises(export.ExportRefused, match="archived"):
        export.export_job("job-1")
    assert not list((pub / "ready").rglob("*.mp4"))


def test_failed_validation_never_reaches_ready(env, good_video, tmp_path):
    ws, pub = env
    bad = make_video(tmp_path / "bad.mp4", w=640, h=360)
    d = job(good_video, video=bad)
    with pytest.raises(export.ExportRefused, match="validation"):
        export.export_job("job-1")
    assert tree(pub / "ready") == [] and list((pub / ".staging").iterdir()) == []
    m = storage.read_manifest(d)
    assert m["status"] == "failed" and m["failure"]["stage"] == "validation" and m["validation"]["status"] == "failed"
    assert (d / "video.mp4").exists()                                               # diagnostics stay in the workspace


def test_black_video_and_missing_audio_fail(env, good_video, tmp_path):
    ws, pub = env
    job(good_video, "j-black", video=make_video(tmp_path / "k.mp4", black=True))
    with pytest.raises(export.ExportRefused):
        export.export_job("j-black")
    job(good_video, "j-mute", video=make_video(tmp_path / "m.mp4", audio=False))
    with pytest.raises(export.ExportRefused):
        export.export_job("j-mute")
    job(good_video, "j-mute-ok", video=make_video(tmp_path / "m2.mp4", audio=False), require_audio=False)
    assert export.export_job("j-mute-ok")["status"] == "exported"
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1


def test_missing_empty_corrupt_video(env, good_video, tmp_path):
    ws, pub = env
    job(good_video, "j-none", video=False)
    with pytest.raises(export.ExportRefused, match="missing"):
        export.export_job("j-none")
    empty = tmp_path / "empty.mp4"; empty.write_bytes(b"")
    job(good_video, "j-empty", video=empty)
    with pytest.raises(export.ExportRefused):
        export.export_job("j-empty")
    junk = tmp_path / "junk.mp4"; junk.write_bytes(b"not a video" * 100)
    job(good_video, "j-junk", video=junk)
    with pytest.raises(export.ExportRefused):
        export.export_job("j-junk")
    assert tree(pub / "ready") == []


def test_unknown_job_and_unsafe_id(env):
    with pytest.raises(storage.StorageError):
        export.export_job("ghost")
    with pytest.raises(storage.StorageError):
        export.export_job("../escape")


def test_partial_copy_leaves_nothing_publishable_and_retry_works(env, good_video, monkeypatch):
    ws, pub = env
    d = job(good_video)
    real = export._copy
    def half(src, dst):
        with open(src, "rb") as r, open(dst, "wb") as w:
            w.write(r.read(5000))
        raise OSError("disk full mid-copy")
    monkeypatch.setattr(export, "_copy", half)
    with pytest.raises(OSError):
        export.export_job("job-1")
    assert tree(pub / "ready") == [] and list((pub / ".staging").iterdir()) == []
    assert (d / "video.mp4").exists()
    assert storage.read_manifest(d)["export"]["status"] == "failed"
    monkeypatch.setattr(export, "_copy", real)
    assert export.export_job("job-1")["status"] == "exported"
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1


def test_corrupt_staged_copy_is_caught(env, good_video, monkeypatch):
    ws, pub = env
    job(good_video)
    def corrupt(src, dst):
        shutil.copy(src, dst)
        with open(dst, "r+b") as f:
            f.seek(100); f.write(b"\x00\x01\x02")
    monkeypatch.setattr(export, "_copy", corrupt)
    with pytest.raises(storage.StorageError, match="does not match"):
        export.export_job("job-1")
    assert tree(pub / "ready") == []


def test_crash_between_video_and_sidecar_leaves_orphan_not_ready(env, good_video, monkeypatch):
    ws, pub = env
    job(good_video)
    real = export.os.replace
    calls = {"n": 0}
    def flaky(src, dst):
        calls["n"] += 1
        if str(dst).endswith(".publish.json"):
            raise OSError("power cut")
        return real(src, dst)
    monkeypatch.setattr(export.os, "replace", flaky)
    with pytest.raises(OSError):
        export.export_job("job-1")
    monkeypatch.setattr(export.os, "replace", real)
    entries, _ = handoff.discover(pub)
    assert entries == []                                                             # never discoverable without a sidecar
    assert tree(pub / "ready") == []                                                 # rolled back
    assert export.export_job("job-1")["status"] == "exported"


def test_recover_finds_orphans_and_stale_staging(env, good_video):
    ws, pub = env
    orphan = pub / "ready" / "p" / "2026" / "10" / "x__job-9.mp4"
    orphan.parent.mkdir(parents=True); orphan.write_bytes(b"v")
    stale = pub / ".staging" / "job-7-abc"; stale.mkdir(); (stale / "f").write_bytes(b"1")
    import os, time
    old = time.time() - 7200
    os.utime(stale, (old, old))
    dry = export.recover()
    assert dry["orphan_videos"] and dry["stale_staging"] and orphan.exists() and stale.exists()
    export.recover(apply=True)
    assert not orphan.exists() and not stale.exists()
    assert list((pub / ".state" / "orphans").iterdir())                              # quarantined, never deleted


def test_concurrent_exports_produce_one_copy(env, good_video):
    ws, pub = env
    job(good_video)
    results, errors = [], []
    def go():
        try:
            results.append(export.export_job("job-1")["status"])
        except Exception as exc:                                                     # pragma: no cover
            errors.append(exc)
    ts = [threading.Thread(target=go) for _ in range(6)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert not errors
    assert sorted(results).count("exported") == 1 and results.count("already_exported") == 5
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1 and len(list((pub / "ready").rglob("*.publish.json"))) == 1


def test_concurrent_different_jobs(env, good_video):
    ws, pub = env
    for i in range(4):
        job(good_video, f"job-{i}")
    ts = [threading.Thread(target=export.export_job, args=(f"job-{i}",)) for i in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(list((pub / "ready").rglob("*.mp4"))) == 4


def test_two_processes_one_copy(env, good_video, tmp_path):
    import subprocess, os
    ws, pub = env
    job(good_video)
    code = "from contentos import export; print(export.export_job('job-1')['status'])"
    envv = {**os.environ, "PYTHONPATH": str(storage.REPO), "PYTHONDONTWRITEBYTECODE": "1"}
    ps = [subprocess.Popen([sys.executable, "-c", code], env=envv, stdout=subprocess.PIPE, text=True) for _ in range(3)]
    outs = sorted(p.communicate()[0].strip() for p in ps)
    assert outs == ["already_exported", "already_exported", "exported"]
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1


def test_manifest_and_sidecar_agree(env, good_video):
    ws, pub = env
    d = job(good_video)
    export.export_job("job-1")
    m = storage.read_manifest(d)
    sc = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    for a, b in (("job_id", "job_id"), ("title", "title"), ("project_id", "project_id"), ("created_at", "created_at"),
                 ("tags", "tags"), ("platform_targets", "platform_targets"), ("language", "language")):
        assert m[a] == sc[b]
    assert m["export"]["sha256"] == sc["video_sha256"] and m["export"]["exported_at"] == sc["exported_at"]


def test_no_secrets_in_manifest_or_sidecar(env, good_video, monkeypatch):
    ws, pub = env
    monkeypatch.setenv("ELEVENLABS_API_KEY", "xi-very-secret-value-123456")
    d = job(good_video)
    export.export_job("job-1")
    blob = (d / "manifest.json").read_text() + next((pub / "ready").rglob("*.publish.json")).read_text()
    assert "xi-very-secret-value-123456" not in blob


def test_publish_dir_unavailable_fails_not_falls_back(env, good_video, monkeypatch, tmp_path):
    job(good_video)
    f = tmp_path / "blocker"; f.write_text("x")
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(f / "pub"))
    with pytest.raises(storage.StorageError):
        export.export_job("job-1")
    assert not (storage.REPO / "Video-Publishing").exists()
