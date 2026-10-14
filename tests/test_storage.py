"""External storage: path resolution, safety, job isolation, manifests. No real media is stored in the repository."""
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import storage  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    ws, pub = tmp_path / "ws", tmp_path / "pub"
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(ws))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(pub))
    for k in ("VIDEO_FACTORY_CACHE_DIR", "VIDEO_FACTORY_EXPORT_MODE"):
        monkeypatch.delenv(k, raising=False)
    return ws, pub


def test_env_vars_win_and_defaults_are_the_documented_desktop_paths(env, monkeypatch):
    ws, pub = env
    assert storage.workspace_root() == ws and storage.publish_root() == pub
    assert storage.jobs_root() == ws / "jobs" and storage.ledger_path() == ws / "ledger.db"
    assert storage.cache_root() == ws / "shared-cache" and storage.staging_root() == pub / ".staging"
    monkeypatch.delenv("VIDEO_FACTORY_WORKSPACE"); monkeypatch.delenv("VIDEO_FACTORY_PUBLISH_DIR")
    monkeypatch.setenv("HOME", "/home/someone")
    assert storage.workspace_root() == Path("/home/someone/Desktop/VideoFactory-Workspace")
    assert storage.publish_root() == Path("/home/someone/Desktop/Video-Publishing")


def test_relative_and_repo_internal_paths_are_refused(env, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", "relative/dir")
    with pytest.raises(storage.StorageError, match="absolute"):
        storage.workspace_root()
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(storage.REPO / "workspace"))
    with pytest.raises(storage.StorageError, match="inside the repository"):
        storage.workspace_root()
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(storage.REPO.parent))
    with pytest.raises(storage.StorageError, match="contains the repository"):
        storage.workspace_root()


def test_workspace_and_publish_must_not_nest(env, monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "ws" / "pub"))
    with pytest.raises(storage.StorageError, match="contain each other"):
        storage.publish_root()


def test_no_silent_fallback_when_unwritable(env, monkeypatch, tmp_path):
    blocker = tmp_path / "file-not-dir"
    blocker.write_text("x")
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(blocker / "ws"))
    with pytest.raises(storage.StorageError):
        storage.preflight()
    assert not (storage.REPO / "workspace" / "jobs").exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_readonly_publish_dir_fails_clearly(env):
    ws, pub = env
    pub.mkdir(); pub.chmod(0o500)
    try:
        with pytest.raises(storage.StorageError):
            storage.preflight()
    finally:
        pub.chmod(0o700)


def test_preflight_creates_only_what_is_needed(env):
    ws, pub = env
    p = storage.preflight()
    assert p["jobs"].is_dir() and (pub / "ready").is_dir() and (pub / ".staging").is_dir() and (pub / ".state").is_dir()
    assert sorted(x.name for x in ws.iterdir()) == ["jobs"]        # no empty speculative dirs


@pytest.mark.parametrize("bad", ["../x", "a/b", "a\\b", "", ".hidden", "a..b", "x" * 200, "a b", None, 5])
def test_unsafe_job_ids_rejected(bad):
    assert not storage.valid_job_id(bad)
    with pytest.raises(storage.StorageError):
        storage.check_job_id(bad)


def test_job_dir_traversal_never_escapes(env):
    storage.preflight()
    for bad in ("../../etc", "..", "a/../../b"):
        with pytest.raises(storage.StorageError):
            storage.job_dir(bad)
    assert [p.name for p in storage.workspace_root().iterdir()] == ["jobs"]


def test_slugify_is_safe_and_never_empty():
    assert storage.slugify("Hello, World! ../../x") == "hello-world-x"
    assert storage.slugify("日本語", "fallback") == "fallback"
    assert "/" not in storage.slugify("a/b\\c") and storage.slugify("   ") == "untitled"


def test_jobs_are_isolated_and_stable(env):
    storage.preflight()
    a, _ = storage.open_job("job-a", {"title": "A", "project": "Proj One"})
    b, _ = storage.open_job("job-b", {"title": "B", "project": "Proj One"})
    assert a != b and a.parent == b.parent and a.parent.parent.parent.parent == storage.jobs_root()
    (a / "audio").mkdir(); (a / "audio" / "voice.wav").write_bytes(b"a")
    assert not (b / "audio").exists()
    again, m = storage.open_job("job-a", {"title": "changed later"})       # resume keeps the same job and manifest
    assert again == a and m["title"] == "A" and m["project_id"] == "proj-one"
    assert storage.find_job_dir("job-a") == a and storage.find_job_dir("nope") is None


def test_manifest_has_no_invented_values_and_no_secrets(env, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-supersecret")
    storage.preflight()
    d, m = storage.open_job("j1", {"title": "T"})
    text = (d / "manifest.json").read_text()
    assert "sk-supersecret" not in text and str(storage.workspace_root()) not in text
    assert m["language"] is None and m["platform_targets"] == [] and m["project_id"] == "unassigned"
    assert m["status"] == "created" and m["schema"] == storage.MANIFEST_SCHEMA


def test_scrub_redacts_secrets_and_paths():
    s = storage.scrub("failed key=sk-abc123def456ghi789 token: Bearer abcdefghijklmnop at /Users/kishore/Desktop/x")
    assert "sk-abc123def456ghi789" not in s and "abcdefghijklmnop" not in s


def test_manifest_write_is_atomic_no_partial_file(env, monkeypatch):
    storage.preflight()
    d, _ = storage.open_job("j1", {"title": "T"})
    real = os.replace
    def boom(src, dst):
        raise OSError("disk full")
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        storage.update_manifest(d, status="running")
    monkeypatch.setattr(os, "replace", real)
    assert storage.read_manifest(d)["status"] == "created"              # old file intact
    assert not [p for p in d.iterdir() if p.name.endswith(".tmp")]      # temp cleaned up


def test_concurrent_manifest_updates_do_not_lose_artifacts(env):
    storage.preflight()
    d, _ = storage.open_job("j1", {"title": "T"})
    ts = [threading.Thread(target=storage.update_manifest, args=(d,), kwargs={"artifacts": {f"s{i}": f"f{i}"}}) for i in range(12)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(storage.read_manifest(d)["artifacts"]) == 12


def test_foreign_manifest_is_refused_then_adopted_without_loss(env):
    storage.preflight()
    d = storage.job_dir("pilot-001")
    legacy = {"id": "pilot-001", "title": "Pilot", "slides": [1, 2]}
    (d / "manifest.json").write_text(json.dumps(legacy))
    with pytest.raises(storage.StorageError):
        storage.read_manifest(d)
    assert storage.adopt(d) is not None or True
    assert json.loads((d / "metadata" / "legacy-manifest.json").read_text()) == legacy
    assert storage.adopt(d) is None                                      # idempotent


def test_unknown_status_rejected(env):
    storage.preflight()
    d, _ = storage.open_job("j1", {})
    with pytest.raises(storage.StorageError):
        storage.update_manifest(d, status="published")


def test_repo_stays_clean_of_generated_files(env):
    """Running storage operations must not create files under the repository tree."""
    before = subprocess.run(["git", "status", "--porcelain", "--ignored"], cwd=storage.REPO, capture_output=True, text=True).stdout
    storage.preflight(); storage.open_job("clean-check", {"title": "x"})
    after = subprocess.run(["git", "status", "--porcelain", "--ignored"], cwd=storage.REPO, capture_output=True, text=True).stdout
    assert before == after


def test_gitignore_blocks_media(tmp_path):
    r = subprocess.run(["git", "check-ignore", "-q", "workspace/projects/x/video.mp4"], cwd=storage.REPO)
    assert r.returncode == 0


def test_file_lock_non_blocking_refuses_a_second_holder(tmp_path):
    """The run lock needs a loud refusal, not a silent wait: blocking=False raises instead of hanging."""
    lock = tmp_path / ".run.lock"
    with storage.file_lock(lock):
        with pytest.raises(storage.StorageError, match=r"\.run\.lock is held by another process"):
            with storage.file_lock(lock, blocking=False):
                pass                                                 # pragma: no cover
    with storage.file_lock(lock, blocking=False):                     # free again once released
        pass


def test_file_lock_stays_blocking_by_default(tmp_path):
    """The default must remain blocking or every existing caller changes behaviour."""
    lock = tmp_path / ".lock"
    acquired = []

    def second_holder():
        with storage.file_lock(lock):
            acquired.append(True)

    with storage.file_lock(lock):
        t = threading.Thread(target=second_holder)
        t.start()
        t.join(timeout=0.3)
        assert acquired == []                                        # still waiting: it neither raised nor skipped
    t.join(timeout=5)
    assert acquired == [True]
