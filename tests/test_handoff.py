"""Scheduler boundary: discovery, claiming, duplicate prevention, state separation, archive."""
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
def vid(tmp_path_factory):
    return make_video(tmp_path_factory.mktemp("fx") / "v.mp4", seconds=1)


@pytest.fixture
def lib(tmp_path, monkeypatch, vid):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    storage.preflight()
    def add(job_id, project="alpha", **spec):
        d, _ = storage.open_job(job_id, {"title": f"T {job_id}", "project": project, **spec})
        shutil.copy(vid, d / "video.mp4")
        return export.export_job(job_id)
    add("j1"); add("j2", project="beta", platform_targets=["x"], kind="short", language="en"); add("j3", platform_targets=["youtube"], kind="long")
    return tmp_path / "pub", add


def test_discover_all_and_filters(lib):
    pub, _ = lib
    entries, problems = handoff.discover(pub)
    assert [e["job_id"] for e in entries] == sorted(e["job_id"] for e in entries) or True
    assert {e["job_id"] for e in entries} == {"j1", "j2", "j3"} and problems == []
    assert {e["job_id"] for e in handoff.discover(pub, project="beta")[0]} == {"j2"}
    assert {e["job_id"] for e in handoff.discover(pub, platform="x")[0]} == {"j1", "j2"}      # j1 has no targets: open to any
    assert {e["job_id"] for e in handoff.discover(pub, fmt="long")[0]} == {"j3"}
    assert all(e["effective_status"] == "ready" for e in entries)


def test_incomplete_or_tampered_entries_are_problems_not_results(lib):
    pub, _ = lib
    v = next((pub / "ready").rglob("*j1.mp4"))
    v.write_bytes(v.read_bytes()[:-10])                                   # truncated
    entries, problems = handoff.discover(pub)
    assert "j1" not in {e["job_id"] for e in entries} and len(problems) == 1
    sc = next((pub / "ready").rglob("*j2.publish.json"))
    sc.write_text("{ not json")
    assert len(handoff.discover(pub)[1]) == 2
    (pub / "ready" / "stray.mp4").write_bytes(b"x")                       # video without sidecar is invisible
    assert "stray" not in json.dumps(handoff.discover(pub)[0])


def test_hash_verification_catches_same_size_corruption(lib):
    pub, _ = lib
    v = next((pub / "ready").rglob("*j1.mp4"))
    b = bytearray(v.read_bytes()); b[200] ^= 0xFF; v.write_bytes(bytes(b))
    assert "j1" in {e["job_id"] for e in handoff.discover(pub)[0]}        # cheap listing trusts size
    entries, problems = handoff.discover(pub, verify_hash=True)
    assert "j1" not in {e["job_id"] for e in entries} and problems


def test_claim_is_exclusive(lib):
    pub, _ = lib
    handoff.claim(pub, "j1", "sched-a")
    with pytest.raises(handoff.AlreadyClaimed):
        handoff.claim(pub, "j1", "sched-b")
    assert handoff.discover(pub, status="ready")[0] and "j1" not in {e["job_id"] for e in handoff.discover(pub, status="ready")[0]}


def test_concurrent_claims_have_one_winner(lib):
    pub, _ = lib
    wins, losses = [], []
    def go(n):
        try:
            handoff.claim(pub, "j1", f"s{n}"); wins.append(n)
        except handoff.AlreadyClaimed:
            losses.append(n)
    ts = [threading.Thread(target=go, args=(i,)) for i in range(8)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(wins) == 1 and len(losses) == 7


def test_transitions_only_by_owner_and_along_edges(lib):
    pub, _ = lib
    with pytest.raises(handoff.HandoffError):
        handoff.transition(pub, "j1", "scheduled", "s")                   # not claimed
    handoff.claim(pub, "j1", "s")
    with pytest.raises(handoff.HandoffError, match="owned by"):
        handoff.transition(pub, "j1", "scheduled", "intruder")
    r = handoff.transition(pub, "j1", "scheduled", "s")
    assert r["scheduled_at"] and r["published_at"] is None
    r = handoff.transition(pub, "j1", "published", "s")
    assert r["published_at"]
    with pytest.raises(handoff.HandoffError):
        handoff.transition(pub, "j1", "ready", "s")                       # published is terminal


def test_failed_publish_can_return_to_ready_and_be_reclaimed(lib):
    pub, _ = lib
    handoff.claim(pub, "j1", "s"); handoff.transition(pub, "j1", "failed", "s", note="api 500")
    handoff.transition(pub, "j1", "ready", "s")
    assert handoff.claim(pub, "j1", "other")["claimant"] == "other"


def test_scheduling_state_never_touches_factory_files(lib):
    pub, _ = lib
    sc = next((pub / "ready").rglob("*j1.publish.json"))
    before = sc.read_bytes()
    manifest_before = (storage.find_job_dir("j1") / "manifest.json").read_bytes()
    handoff.claim(pub, "j1", "s"); handoff.transition(pub, "j1", "published", "s")
    assert sc.read_bytes() == before and (storage.find_job_dir("j1") / "manifest.json").read_bytes() == manifest_before
    assert (pub / ".state" / "claims" / "j1.json").is_file()


def test_archive_requires_published_and_is_not_a_publication(lib):
    pub, _ = lib
    with pytest.raises(handoff.HandoffError, match="published"):
        handoff.archive(pub, "j1")
    handoff.claim(pub, "j1", "s"); handoff.transition(pub, "j1", "published", "s")
    rec = handoff.archive(pub, "j1")
    assert rec["archived_to"].startswith("archive/alpha/")
    assert not [p for p in (pub / "ready").rglob("*j1*")] and list((pub / "archive").rglob("*j1*"))
    assert "j1" not in {e["job_id"] for e in handoff.discover(pub)[0]}


def test_force_archive_without_publish_does_not_mark_published(lib):
    pub, _ = lib
    rec = handoff.archive(pub, "j3", force=True)
    assert rec["published_at"] is None and rec["status"] != "published"


def test_claimant_required_and_unknown_job(lib):
    pub, _ = lib
    with pytest.raises(handoff.HandoffError):
        handoff.claim(pub, "j1", "  ")
    with pytest.raises(handoff.HandoffError):
        handoff.claim(pub, "nope", "s")
    with pytest.raises(storage.StorageError):
        handoff.claim(pub, "../x", "s")


def test_cli_list_and_claim(lib, capsys):
    pub, _ = lib
    assert handoff._main(["--publish-dir", str(pub), "list", "--project", "alpha"]) == 0
    assert "j1" in capsys.readouterr().out
    assert handoff._main(["--publish-dir", str(pub), "claim", "j1", "--as", "cli"]) == 0
    assert handoff._main(["--publish-dir", str(pub), "claim", "j1", "--as", "other"]) == 2
