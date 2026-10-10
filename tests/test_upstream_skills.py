import json
import shutil
import subprocess

import pytest

from contentos import upstream_skills as us

GIT = shutil.which("git")
pytestmark = pytest.mark.skipif(GIT is None, reason="git not installed")


def _git(cwd, *a):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def upstream(tmp_path):
    r = tmp_path / "up"
    (r / "skills/alpha/ref").mkdir(parents=True)
    (r / "skills/alpha/SKILL.md").write_text("---\nname: alpha\n---\nbody\n")
    (r / "skills/alpha/ref/a.md").write_text("A")
    (r / "skills/alpha/x.test.mjs").write_text("test only")
    (r / "skills/beta").mkdir(parents=True)
    (r / "skills/beta/SKILL.md").write_text("---\nname: beta\n---\n")
    (r / "LICENSE").write_text("Apache-2.0 text")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=r, check=True)
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "init")
    _git(r, "tag", "v1")
    commit = subprocess.run(["git", "-C", str(r), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    return r, commit


def _lock(tmp_path, repo, commit, skills=("alpha",), hashes=None):
    lock = {"schema": "upstream-skills/1", "sources": [{"id": "up", "repo": f"file://{repo}", "tag": "v1", "commit": commit,
                                                       "license": "Apache-2.0", "skills": list(skills), "tree_sha256": hashes or {}}]}
    p = tmp_path / "lock.json"
    p.write_text(json.dumps(lock))
    return p


def test_sync_installs_pinned_skill_without_tests_and_records_license(tmp_path, upstream):
    repo, commit = upstream
    dest = tmp_path / "skills"
    out = us.sync(_lock(tmp_path, repo, commit), dest)
    assert (dest / "alpha/SKILL.md").is_file() and (dest / "alpha/ref/a.md").is_file()
    assert not (dest / "alpha/x.test.mjs").exists()
    assert not (dest / "beta").exists()                                  # only what the lock lists
    assert (dest / "_upstream/up.LICENSE").read_text() == "Apache-2.0 text"
    assert "commit: " + commit in (dest / "_upstream/up.PROVENANCE.md").read_text()
    assert out["up"]["alpha"] == us.tree_hash(dest / "alpha")


def test_sync_refuses_when_commit_does_not_match_lock(tmp_path, upstream):
    repo, _ = upstream
    with pytest.raises(RuntimeError, match="refusing to install"):
        us.sync(_lock(tmp_path, repo, "0" * 40), tmp_path / "skills")
    assert not (tmp_path / "skills/alpha").exists()


def test_verify_detects_edit_and_missing_hash(tmp_path, upstream):
    repo, commit = upstream
    dest = tmp_path / "skills"
    h = us.sync(_lock(tmp_path, repo, commit), dest)["up"]
    lock = _lock(tmp_path, repo, commit, hashes=h)
    assert us.verify(lock, dest) == []
    (dest / "alpha/ref/a.md").write_text("tampered")
    assert "content differs" in us.verify(lock, dest)[0]
    assert "no tree_sha256" in us.verify(_lock(tmp_path, repo, commit), dest)[0]
    shutil.rmtree(dest / "alpha")
    assert us.verify(lock, dest) == ["alpha: not installed"]


def test_remove_deletes_only_locked_skills(tmp_path, upstream):
    repo, commit = upstream
    dest = tmp_path / "skills"
    us.sync(_lock(tmp_path, repo, commit), dest)
    (dest / "mine").mkdir()
    (dest / "mine/SKILL.md").write_text("ours")
    assert us.remove(_lock(tmp_path, repo, commit), dest) == ["alpha"]
    assert (dest / "mine/SKILL.md").is_file()
    assert not (dest / "_upstream").exists()


def test_lock_validation(tmp_path):
    bad = tmp_path / "l.json"
    base = {"schema": "upstream-skills/1", "sources": [{"id": "x", "repo": "r", "tag": "t", "commit": "abc", "license": "MIT", "skills": ["a"]}]}
    bad.write_text(json.dumps(base))
    with pytest.raises(ValueError, match="40-char"):
        us.load_lock(bad)
    base["sources"][0].update(commit="a" * 40, skills=["../evil"])
    bad.write_text(json.dumps(base))
    with pytest.raises(ValueError, match="unsafe skill name"):
        us.load_lock(bad)
    bad.write_text(json.dumps({"schema": "nope", "sources": []}))
    with pytest.raises(ValueError, match="schema"):
        us.load_lock(bad)


def test_tree_hash_changes_with_content_and_ignores_tests(tmp_path):
    d = tmp_path / "s"
    d.mkdir()
    (d / "a.md").write_text("1")
    h1 = us.tree_hash(d)
    (d / "a.test.mjs").write_text("ignored")
    assert us.tree_hash(d) == h1
    (d / "a.md").write_text("2")
    assert us.tree_hash(d) != h1
