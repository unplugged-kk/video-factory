"""Inventory, migration and cleanup for the external workspace. Everything here is a DRY RUN unless apply=True.

inventory()  what exists in the old in-repo locations: size, whether Git tracks it, what references it, where it would
             go, and the risks. Read-only.
migrate()    COPIES (never moves or deletes) each item to its new place, verifies a content digest of source and copy,
             and writes a log under <workspace>/recovery/migrations/. The originals stay where they are, so recovery
             is simply "keep using the originals" or "delete the copies listed in the log".
cleanup()    removes only the scratch paths named in config retention.intermediate_paths, from jobs that were exported
             and are older than retention.intermediate_days, never from active, locked, retrying or `.keep` jobs, and
             never the final video.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

from . import storage

LEGACY_ROOT_DIRS = ("output", "state", "thumbs", "done", "queue", "work", "failed", "building", "drafts")
LEFT_ALONE = ("reference/stale-july-2025-artifacts",)


# ---- helpers ------------------------------------------------------------------------------------------------------

def tree_stats(path):
    path = Path(path)
    if path.is_file():
        return 1, path.stat().st_size
    n = b = 0
    for r, _, fs in os.walk(path):
        for f in fs:
            p = Path(r) / f
            n += 1
            with contextlib.suppress(OSError):
                b += p.lstat().st_size
    return n, b


def tree_digest(path):
    """(files, bytes, hex): SHA-256 over sorted (relative name, size, file SHA-256). Symlinks hash their target string."""
    path = Path(path)
    h = hashlib.sha256()
    files = total = 0
    entries = [path] if path.is_file() else sorted(p for p in path.rglob("*") if not p.is_dir())
    for p in entries:
        rel = p.name if path.is_file() else p.relative_to(path).as_posix()
        if p.is_symlink():
            h.update(f"L {rel} {os.readlink(p)}\n".encode())
            continue
        fh = hashlib.sha256()
        with open(p, "rb") as f:
            while block := f.read(1 << 20):
                fh.update(block)
        size = p.stat().st_size
        h.update(f"F {rel} {size} {fh.hexdigest()}\n".encode())
        files += 1
        total += size
    return files, total, h.hexdigest()


def _git_tracked(repo, relpath):
    try:
        r = subprocess.run(["git", "-C", str(repo), "ls-files", "--", relpath], capture_output=True, text=True, timeout=30)
        return len([x for x in r.stdout.splitlines() if x]) if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _ledger_refs(db_path):
    """{content_id: {"runs": n, "active": bool}} from a ledger file opened read-only; {} if there is none."""
    db_path = Path(db_path)
    if not db_path.exists():
        return {}
    refs = {}
    try:
        c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        with contextlib.closing(c):
            for cid, n in c.execute("SELECT content_id, COUNT(*) FROM runs GROUP BY content_id"):
                refs[cid] = {"runs": n, "active": False}
            for cid, st in c.execute("SELECT content_id, status FROM jobs"):
                r = refs.setdefault(cid, {"runs": 0, "active": False})
                r["active"] = r["active"] or st in ("queued", "running", "blocked")
    except sqlite3.Error:
        return {}
    return refs


def _ym_for(path, manifest=None):
    if manifest and manifest.get("created_at"):
        return manifest["created_at"][0:4], manifest["created_at"][5:7]
    t = dt.datetime.fromtimestamp(Path(path).stat().st_mtime, dt.timezone.utc)
    return f"{t.year:04d}", f"{t.month:02d}"


# ---- inventory ----------------------------------------------------------------------------------------------------

def inventory(*, repo=None, legacy=None, ws=None):
    repo = Path(repo) if repo else storage.REPO
    legacy = Path(legacy) if legacy else repo / "workspace"
    ws = Path(ws) if ws else storage.workspace_root()
    refs = _ledger_refs(legacy / "ledger.db")
    items = []

    def add(path, kind, dest, *, action="copy", refs_text="", risks=()):
        files, size = tree_stats(path) if Path(path).exists() else (0, 0)
        rel = Path(os.path.relpath(path, repo)).as_posix()
        items.append({"path": rel, "kind": kind, "bytes": size, "files": files, "tracked_files": _git_tracked(repo, rel),
                      "referenced_by": refs_text, "destination": dest, "action": action, "risks": list(risks)})

    projects = legacy / "projects"
    if projects.is_dir():
        for p in sorted(projects.iterdir()):
            if not p.is_dir() or p.name.startswith("."):
                continue
            risks = []
            ref = refs.get(p.name)
            if not storage.valid_job_id(p.name):
                risks.append("name is not a valid job id; cannot be migrated")
            mp = p / storage.MANIFEST
            if mp.exists():
                with contextlib.suppress(Exception):
                    if json.loads(mp.read_text()).get("schema") != storage.MANIFEST_SCHEMA:
                        risks.append("has its own manifest.json (kept; run `contentos storage adopt` before exporting)")
            if ref and ref["active"]:
                risks.append("job is queued/running/blocked in the ledger; skipped unless --include-active")
            risks.append("mpt Docker container must be restarted so it mounts the new jobs folder")
            ym = _ym_for(p)
            add(p, "job project", f"jobs/{ym[0]}/{ym[1]}/{p.name}",
                action="copy" if storage.valid_job_id(p.name) else "leave",
                refs_text=f"ledger: {ref['runs']} run row(s)" if ref else "no ledger rows", risks=risks)
    for name, kind in (("experiments", "experiments (scratch builds)"), ("research", "research dossiers"), ("factory-specs", "derived specs")):
        p = legacy / name
        if p.is_dir():
            add(p, kind, name, risks=["none known"] if name != "factory-specs" else ["specs are re-derived by the worker; safe to copy"])
    if (legacy / "ledger.db").exists():
        add(legacy / "ledger.db", "SQLite ledger", "ledger.db", refs_text="all runs, jobs, approvals",
            risks=["copied with the SQLite backup API; stop workers first so no job is mid-write", "queue/approval history moves with it"])
    for name in LEGACY_ROOT_DIRS:
        p = repo / name
        if p.is_dir() and any(p.iterdir()):
            add(p, "legacy exchange-style folder at repo root", f"recovery/legacy-root/{name}",
                refs_text="no code path reads it (the worker uses VIDEO_FACTORY_ROOT, never the repo root)",
                risks=["contents are old ContentForge-era videos/state; preserved, not interpreted"])
    for rel_left in LEFT_ALONE:
        p = repo / rel_left
        if p.is_dir():
            add(p, "reference artifacts", "(unchanged)", action="leave", risks=["inside a partly tracked folder; left untouched"])
    return items


def format_inventory(items):
    def mb(b):
        return f"{b / 1e6:.1f} MB"
    lines = [f"{'path':48} {'kind':34} {'size':>10} {'git':>5}  action  -> destination"]
    for i in items:
        lines.append(f"{i['path']:48} {i['kind'][:34]:34} {mb(i['bytes']):>10} {str(i['tracked_files']):>5}  {i['action']:6}  -> {i['destination']}")
        lines.append(f"    referenced: {i['referenced_by'] or '-'}; risks: {'; '.join(i['risks']) or '-'}")
    total = sum(i["bytes"] for i in items if i["action"] == "copy")
    lines.append(f"to copy: {mb(total)} in {sum(1 for i in items if i['action'] == 'copy')} item(s)")
    return "\n".join(lines)


# ---- migration ----------------------------------------------------------------------------------------------------

def _copy_item(src, dest):
    src, dest = Path(src), Path(dest)
    tmp = dest.with_name(f".{dest.name}.migrating-{uuid.uuid4().hex[:6]}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        if src.name == "ledger.db" and src.is_file():
            a = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
            b = sqlite3.connect(tmp)
            with contextlib.closing(a), contextlib.closing(b):
                a.backup(b)
            check_src = None                                  # a backup is a new file; verify it opens and counts rows instead
        elif src.is_dir():
            shutil.copytree(src, tmp, symlinks=True)
            check_src = tree_digest(src)
        else:
            shutil.copy2(src, tmp)
            check_src = tree_digest(src)
        if check_src is not None:
            got = tree_digest(tmp)
            if got != check_src:
                raise storage.StorageError(f"verification failed for {src}: copy differs from the original")
        else:
            c = sqlite3.connect(tmp)
            with contextlib.closing(c):
                c.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        os.replace(tmp, dest)
        return check_src
    finally:
        if tmp.is_dir():
            shutil.rmtree(tmp, ignore_errors=True)
        elif tmp.exists():
            tmp.unlink()


def migrate(*, apply=False, include_active=False, repo=None, legacy=None, ws=None):
    ws = Path(ws) if ws else storage.workspace_root()
    items = inventory(repo=repo, legacy=legacy, ws=ws)
    refs = _ledger_refs((Path(legacy) if legacy else (Path(repo) if repo else storage.REPO) / "workspace") / "ledger.db")
    repo = Path(repo) if repo else storage.REPO
    results = []
    if apply:
        storage.ensure_dir(ws, "workspace")
    for it in items:
        src, dest = repo / it["path"], ws / it["destination"]
        r = {"path": it["path"], "destination": it["destination"], "action": it["action"], "status": None, "note": ""}
        results.append(r)
        if it["action"] != "copy":
            r["status"] = "left in place"
            continue
        name = Path(it["path"]).name
        if it["kind"] == "job project" and refs.get(name, {}).get("active") and not include_active:
            r["status"], r["note"] = "skipped", "active job in the ledger (use --include-active after stopping workers)"
            continue
        if dest.exists():
            r["status"], r["note"] = "skipped", "destination already exists; nothing overwritten"
            continue
        if not apply:
            r["status"] = "would copy"
            continue
        try:
            dig = _copy_item(src, dest)
            r["status"] = "copied and verified"
            if dig:
                r["files"], r["bytes"], r["digest"] = dig
            if it["kind"] == "job project":
                r["note"] = _seed_manifest(dest)
        except (OSError, storage.StorageError, sqlite3.Error) as exc:
            r["status"], r["note"] = "FAILED", storage.scrub(str(exc))
    log = {"started_at": storage.now_iso(), "applied": apply, "workspace": "<workspace>", "results": results,
           "recovery": "Originals were not modified. To undo, delete the copies listed above under the workspace; "
                       "to keep going unchanged, set nothing: the old in-repo folders are still intact."}
    if apply:
        d = ws / "recovery" / "migrations"
        d.mkdir(parents=True, exist_ok=True)
        name = f"migration-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        storage.write_json_atomic(d / name, log)
        log["log_file"] = f"recovery/migrations/{name}"
    return log


def _seed_manifest(job_dir):
    """A migrated project gets a job manifest only if it has none and carries content.json from the old pipeline."""
    job_dir = Path(job_dir)
    mp = job_dir / storage.MANIFEST
    if mp.exists():
        try:
            storage.read_manifest(job_dir)
            return "already has a job manifest"
        except storage.StorageError:
            return "has a legacy manifest.json: run `contentos storage adopt` to export it"
    cj = job_dir / "content.json"
    if not cj.exists():
        return "no content.json: no manifest created; run `contentos storage adopt` to export it"
    try:
        spec = json.loads(cj.read_text(encoding="utf-8"))
        m = storage.new_manifest(job_dir.name, project_id="unassigned", content_id=storage.slugify(spec.get("title") or job_dir.name),
                                 title=spec.get("title"), description=spec.get("description", ""), tags=spec.get("tags"),
                                 renderer=spec.get("render", "hyperframes"), aspect_ratio=spec.get("format", "9:16"),
                                 now=dt.datetime.fromtimestamp(job_dir.stat().st_mtime, dt.timezone.utc))
        m["status"] = "ready" if (job_dir / "video.mp4").exists() else "created"
        m["final_output"] = "video.mp4" if (job_dir / "video.mp4").exists() else None
        m["note"] = "created by migration from content.json; validation not yet run"
        storage.write_manifest(job_dir, m)
        return "manifest created from content.json"
    except (OSError, ValueError, KeyError) as exc:
        return f"no manifest created: {exc}"


# ---- cleanup ------------------------------------------------------------------------------------------------------

def cleanup(*, apply=False, now=None, cfg=None, ws=None):
    """Report (and with apply, remove) expired scratch paths. Returns {"candidates": [...], "skipped": [...], "bytes": n}."""
    cfg = cfg or storage.config()
    pol = cfg["retention"]
    ws = Path(ws) if ws else storage.workspace_root(cfg)
    clock = now if now is not None else time.time()
    refs = _ledger_refs(ws / "ledger.db")
    out = {"applied": apply, "candidates": [], "skipped": [], "bytes": 0}
    jobs = ws / "jobs"
    for d in storage.iter_job_dirs(jobs):
        if not d.is_dir():
            continue
        def skip(why, d=d):
            out["skipped"].append({"job": d.name, "reason": why})
        try:
            m = storage.read_manifest(d)
        except storage.StorageError:
            skip("legacy manifest, not managed"); continue
        if m is None:
            skip("no manifest"); continue
        if (d / ".keep").exists():
            skip(".keep marker"); continue
        if refs.get(d.name, {}).get("active"):
            skip("queued, running or blocked in the ledger (pending retry)"); continue
        if storage.lock_is_held(d / ".manifest.lock") or storage.lock_is_held(d / ".run.lock"):
            skip("in use (lock held)"); continue
        if m["status"] == "exported":
            days, stamp = pol["intermediate_days"], (m.get("export") or {}).get("exported_at") or m["updated_at"]
        elif m["status"] == "failed" and pol.get("failed_days") is not None:
            days, stamp = pol["failed_days"], m["updated_at"]
        else:
            skip(f"status {m['status']} is not eligible"); continue
        age_days = (clock - dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()) / 86400
        if age_days < days:
            skip(f"{age_days:.0f} d old, keeping until {days} d"); continue
        final = (d / (m.get("final_output") or "video.mp4")).resolve()
        for pattern in pol["intermediate_paths"]:
            for p in sorted(d.glob(pattern)):
                rp = p.resolve()
                if not (rp != d.resolve() and d.resolve() in rp.parents) or rp == final or final in rp.parents or rp in final.parents:
                    continue
                size = tree_stats(p)[1]
                out["candidates"].append({"job": d.name, "path": p.relative_to(d).as_posix(), "bytes": size})
                out["bytes"] += size
                if apply:
                    shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()
    return out
