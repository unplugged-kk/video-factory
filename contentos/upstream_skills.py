"""Pinned, verifiable, removable installs of third-party Claude Code skills.

A lock file (config/upstream-skills.lock.json) names each source repo, the exact tag and commit, the license, and the
skill folders we use. `sync` clones that tag, refuses anything whose commit differs from the lock, and copies only the
listed skill folders (minus test files) into a project skills directory. `verify` re-hashes the installed folders so a
silent edit or a half-update is caught. `remove` deletes exactly the folders the lock lists, nothing else.

Nothing from the upstream repo is executed here. Network is used only by `sync`, and only for `git clone`."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

EXCLUDE = ("*.test.mjs", "*.test.js", "__pycache__", ".DS_Store")
UPSTREAM_DIR = "_upstream"            # holds the license copy + provenance note; has no SKILL.md so it is never loaded as a skill


def _skip(rel: Path) -> bool:
    return any(fnmatch.fnmatch(part, pat) for part in rel.parts for pat in EXCLUDE)


def tree_hash(folder: Path) -> str:
    """Deterministic SHA-256 over relative paths + file bytes (sorted), ignoring EXCLUDE patterns."""
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder)
        if p.is_file() and not _skip(rel):
            h.update(rel.as_posix().encode() + b"\0")
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def load_lock(path: Path) -> dict:
    lock = json.loads(Path(path).read_text())
    if lock.get("schema") != "upstream-skills/1":
        raise ValueError(f"unsupported lock schema: {lock.get('schema')!r}")
    for s in lock["sources"]:
        for k in ("id", "repo", "tag", "commit", "license", "skills"):
            if k not in s:
                raise ValueError(f"source missing {k!r}: {s}")
        if len(s["commit"]) != 40:
            raise ValueError(f"{s['id']}: commit must be a full 40-char sha")
        for name in s["skills"]:
            if "/" in name or name.startswith("."):
                raise ValueError(f"{s['id']}: unsafe skill name {name!r}")
    return lock


def clone_at_tag(repo: str, tag: str, dest: Path) -> str:
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0")
    subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", tag, repo, str(dest)], check=True, env=env,
                   capture_output=True, text=True)
    return subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def _copy_skill(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if _skip(Path(n))])


def sync(lock_path: Path, skills_dir: Path, source_id: str | None = None, clone=clone_at_tag) -> dict:
    """Install every listed skill at its pinned commit. Returns {source_id: {skill: tree_sha256}}; the caller records hashes."""
    lock, out = load_lock(lock_path), {}
    for s in lock["sources"]:
        if source_id and s["id"] != source_id:
            continue
        with tempfile.TemporaryDirectory(prefix="upstream-skills-") as tmp:
            work = Path(tmp) / "src"
            head = clone(s["repo"], s["tag"], work)
            if head != s["commit"]:
                raise RuntimeError(f"{s['id']}: tag {s['tag']} resolves to {head}, lock pins {s['commit']}; refusing to install")
            out[s["id"]] = {}
            for name in s["skills"]:
                src = work / "skills" / name
                if not (src / "SKILL.md").is_file():
                    raise RuntimeError(f"{s['id']}: skills/{name}/SKILL.md missing at {s['tag']}")
                _copy_skill(src, skills_dir / name)
                out[s["id"]][name] = tree_hash(skills_dir / name)
            up = skills_dir / UPSTREAM_DIR
            up.mkdir(parents=True, exist_ok=True)
            shutil.copy(work / "LICENSE", up / f"{s['id']}.LICENSE")
            (up / f"{s['id']}.PROVENANCE.md").write_text(
                f"# {s['id']}\n\nrepo: {s['repo']}\ntag: {s['tag']}\ncommit: {s['commit']}\nlicense: {s['license']}\n"
                f"skills: {', '.join(s['skills'])}\nfiles excluded: {', '.join(EXCLUDE)}\n"
                "Installed by contentos.upstream_skills; do not edit in place (verify will fail). Remove with the same module.\n")
    return out


def verify(lock_path: Path, skills_dir: Path) -> list[str]:
    """Problems found (empty = all installed skills match the lock). A lock entry with no recorded hash is reported."""
    problems = []
    for s in load_lock(lock_path)["sources"]:
        for name in s["skills"]:
            d = skills_dir / name
            want = (s.get("tree_sha256") or {}).get(name)
            if not (d / "SKILL.md").is_file():
                problems.append(f"{name}: not installed")
            elif not want:
                problems.append(f"{name}: lock has no tree_sha256")
            elif tree_hash(d) != want:
                problems.append(f"{name}: content differs from lock (edited or different version)")
    return problems


def remove(lock_path: Path, skills_dir: Path) -> list[str]:
    """Delete exactly the folders the lock lists (and the license/provenance notes). Returns what was removed."""
    gone = []
    lock = load_lock(lock_path)
    for s in lock["sources"]:
        for name in s["skills"]:
            d = skills_dir / name
            if d.is_dir():
                shutil.rmtree(d)
                gone.append(name)
        for suffix in (".LICENSE", ".PROVENANCE.md"):
            f = skills_dir / UPSTREAM_DIR / f"{s['id']}{suffix}"
            if f.is_file():
                f.unlink()
    up = skills_dir / UPSTREAM_DIR
    if up.is_dir() and not any(up.iterdir()):
        up.rmdir()
    return gone
