"""Export a finished, validated job into the publishing library (Video-Publishing/ready/...).

Order of events, all under a per-job lock so concurrent or repeated calls cannot duplicate or interleave:
  1. If this job was already exported with the same video, return it unchanged (idempotent).
  2. Validate the final video (contentos.finalcheck). A failed video never leaves the workspace; diagnostics stay put.
  3. Copy it into publish/.staging/<job>-<id>/, fsync, and verify size and SHA-256.
  4. Write the sidecar into staging, then promote with os.replace (atomic on one filesystem): the video first and the
     sidecar LAST. A video without a sidecar is, by contract, not ready; the sidecar is the "ready" marker.
  5. Verify the promoted files, record the export in the job manifest and publish/.state/exports/, remove staging.
Any failure removes the staging folder and anything promoted by this call, so nothing publishable is left behind.
A scheduler that has already claimed the job (publish/.state/claims/) makes a replacement impossible."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import shutil
import time
import uuid
from pathlib import Path

from . import finalcheck, storage
from .production import supplied_audio

SIDECAR_SUFFIX = ".publish.json"
SIDECAR_SCHEMA_VERSION = 1
INTEGRITY_SCHEMA = "export-integrity/1"


class ExportRefused(storage.StorageError):
    """The job must not be exported (failed validation, conflicting earlier export, or already handed off)."""


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def _copy(src, dst):
    """Streaming copy with fsync. A separate function so tests can simulate a failure halfway through."""
    with open(src, "rb") as r, open(dst, "wb") as w:
        shutil.copyfileobj(r, w, 1 << 20)
        w.flush()
        os.fsync(w.fileno())


def names(manifest):
    project = storage.slugify(manifest.get("project_id"), "unassigned")
    content = storage.slugify(manifest.get("content_id") or manifest.get("title") or manifest["job_id"], storage.slugify(manifest["job_id"]))
    job = manifest["job_id"]
    created = dt.datetime.strptime(manifest["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    return project, content, job, f"{created.year:04d}", f"{created.month:02d}"


def locations(pub, manifest, mode):
    """(directory, video path, sidecar path) for the chosen export mode."""
    project, content, job, yyyy, mm = names(manifest)
    base = Path(pub) / "ready"
    d = base / project / yyyy / mm if mode == "nested" else base
    stem = f"{content}__{job}"
    return d, d / f"{stem}.mp4", d / f"{stem}{SIDECAR_SUFFIX}"


def _state(pub, job):
    return Path(pub) / ".state" / "exports" / f"{job}.json"


def _claim(pub, job):
    return Path(pub) / ".state" / "claims" / f"{job}.json"


def _existing(pub, manifest):
    """Where this job was exported before, in either mode: (video, sidecar) or None."""
    st = _state(pub, manifest["job_id"])
    if st.exists():
        with contextlib.suppress(Exception):
            rec = json.loads(st.read_text(encoding="utf-8"))
            return Path(pub) / rec["video"], Path(pub) / rec["sidecar"]
    for mode in storage.EXPORT_MODES:
        _, v, s = locations(pub, manifest, mode)
        if s.exists() or v.exists():
            return v, s
    return None


def build_sidecar(m, validation, video_name, sha, size, exported_at):
    return {
        "schema_version": SIDECAR_SCHEMA_VERSION,
        "project_id": m.get("project_id"), "project_name": m.get("project_name"),
        "content_id": storage.slugify(m.get("content_id") or m.get("title") or m["job_id"], m["job_id"]),
        "job_id": m["job_id"], "title": m.get("title"), "description": m.get("description") or "",
        "platform_targets": list(m.get("platform_targets") or []), "tags": list(m.get("tags") or []),
        "language": m.get("language"), "format": m.get("kind"), "aspect_ratio": m.get("aspect_ratio"),
        "duration_seconds": validation.get("duration_seconds"),
        "video_filename": video_name, "video_sha256": sha, "video_bytes": size,
        "created_at": m["created_at"], "exported_at": exported_at,
        "validation_status": validation["status"], "validation": finalcheck.summary(validation),
        "publishing_status": "ready", "scheduled_at": None, "published_at": None,
    }


def export_job(job_id, *, force=False, mode=None, cfg=None, jobs=None):
    cfg = cfg or storage.config()
    paths = storage.preflight(publish=True, cfg=cfg)
    pub = paths["publish"]
    d = storage.find_job_dir(job_id, jobs)
    if d is None:
        raise storage.StorageError(f"no job directory for {job_id!r}")
    m = storage.read_manifest(d)
    if m is None:
        raise storage.StorageError(f"job {job_id!r} has no manifest.json")
    if m.get("track") == "B":                                # hand-built jobs have no pipeline gates, so the ledger must hold both before export
        from . import ledger
        missing = [g for g in ("SCRIPT_APPROVED", "PRODUCTION_APPROVED") if not ledger.approved(job_id, g)]
        if missing:
            raise ExportRefused(f"{job_id}: hand-built job is not exported until {' and '.join(missing)} {'is' if len(missing) == 1 else 'are'} granted: "
                                + "; ".join(f"contentos approve {job_id} {g}" for g in missing))
    mode = mode or storage.export_mode(cfg)
    with storage.file_lock(pub / ".state" / "locks" / f"{job_id}.lock"):
        return _export_locked(d, m, pub, mode, force, cfg)


def _fail(d, reason):
    storage.update_manifest(d, export={"status": "failed", "reason": storage.scrub(reason), "at": storage.now_iso()})


def _export_locked(d, m, pub, mode, force, cfg):
    job = m["job_id"]
    video = d / "video.mp4"
    if not video.is_file():
        raise ExportRefused(f"{job}: final video is missing; nothing to export")
    blockers = supplied_audio.publish_blockers(d)           # unknown rights, a malformed record or a hash mismatch: nothing reaches ready/
    if blockers:
        raise ExportRefused(f"{job}: not exported, supplied audio blocks publication: " + "; ".join(blockers))
    sha, size = sha256_file(video), video.stat().st_size
    prior = _existing(pub, m)
    prior_sidecar = None
    if not (prior and (prior[0].exists() or prior[1].exists())) and _claim(pub, job).exists():
        try:
            archived = json.loads(_claim(pub, job).read_text(encoding="utf-8")).get("archived_to")
        except (OSError, ValueError):
            archived = None
        if archived:
            raise ExportRefused(f"{job}: already handed off and archived ({archived}); not re-exporting into ready/")
    if prior:
        pv, ps = prior
        if ps.exists():
            prior_sidecar = json.loads(ps.read_text(encoding="utf-8"))
            if prior_sidecar.get("job_id") != job:
                raise ExportRefused(f"{ps.name} belongs to another job ({prior_sidecar.get('job_id')!r})")
            if prior_sidecar.get("video_sha256") == sha and pv.exists() and pv.stat().st_size == size:
                return {"status": "already_exported", "job_id": job, "video": storage.rel(pv, pub),
                        "sidecar": storage.rel(ps, pub), "sha256": sha}
            if _claim(pub, job).exists():
                raise ExportRefused(f"{job}: a different video was exported earlier and a scheduler has already claimed it; not replacing")
            if not force:
                raise ExportRefused(f"{job}: a different video was already exported for this job; re-run with force to replace the unclaimed one")

    validation = finalcheck.validate_video(video, m.get("aspect_ratio") or "9:16", require_audio=m.get("require_audio", True))
    if validation["status"] != "passed":
        fails = [c["check"] for c in validation["checks"] if c["status"] == "FAIL"]
        storage.update_manifest(d, validation=validation, status="failed",
                                failure={"stage": "validation", "reason": f"failed checks: {fails}", "at": storage.now_iso()})
        raise ExportRefused(f"{job}: final video failed validation ({fails}); it stays in the workspace and is not exported")
    storage.update_manifest(d, validation=validation, status="ready", failure=None, final_output="video.mp4")

    dest_dir, dest_video, dest_sidecar = locations(pub, m, mode)
    stage = storage.staging_root(cfg) / f"{job}-{uuid.uuid4().hex[:10]}"
    promoted = []
    try:
        stage.mkdir(parents=True)
        s_video, s_sidecar = stage / dest_video.name, stage / dest_sidecar.name
        _copy(video, s_video)
        if s_video.stat().st_size != size or sha256_file(s_video) != sha:
            raise storage.StorageError("staged copy does not match the rendered video (size or checksum)")
        exported_at = storage.now_iso()
        sidecar = build_sidecar(m, validation, dest_video.name, sha, size, exported_at)
        storage.write_json_atomic(s_sidecar, sidecar)
        dest_dir.mkdir(parents=True, exist_ok=True)
        if prior and prior[1].exists():                      # un-publish the old sidecar first; a crash then leaves "not ready"
            os.replace(prior[1], stage / "replaced.publish.json")
        os.replace(s_video, dest_video)
        promoted.append(dest_video)
        os.replace(s_sidecar, dest_sidecar)                  # last: this is what makes the video "ready"
        promoted.append(dest_sidecar)
        storage.fsync_dir(dest_dir)
        if not dest_video.is_file() or dest_video.stat().st_size != size or sha256_file(dest_video) != sha:
            raise storage.StorageError("promoted video does not match the expected output")
        rec = {"job_id": job, "video": storage.rel(dest_video, pub), "sidecar": storage.rel(dest_sidecar, pub),
               "sha256": sha, "bytes": size, "mode": mode, "exported_at": exported_at}
        storage.write_json_atomic(_state(pub, job), rec)
        storage.update_manifest(d, status="exported", export={"status": "exported", **{k: rec[k] for k in ("video", "sidecar", "sha256", "bytes", "mode", "exported_at")}})
        if prior and prior[0] != dest_video and prior[0].exists():
            prior[0].unlink()                                # mode changed with force: remove the old copy so there is one
        return {"status": "exported", "job_id": job, "video": rec["video"], "sidecar": rec["sidecar"], "sha256": sha}
    except BaseException as exc:
        for p in reversed(promoted):
            with contextlib.suppress(OSError):
                p.unlink()
        with contextlib.suppress(Exception):
            _fail(d, f"export failed: {exc}")
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def recover(*, apply=False, cfg=None, now=None):
    """Find leftovers of an interrupted export. Dry run unless apply=True; never touches a job whose lock is held.
    stale staging: folders older than retention.staging_stale_minutes (removed with apply)
    orphan videos: an .mp4 in ready/ with no sidecar (moved to .state/orphans/ with apply, never deleted)."""
    cfg = cfg or storage.config()
    pub = storage.publish_root(cfg)
    stale_after = cfg["retention"]["staging_stale_minutes"] * 60
    clock = now if now is not None else time.time()
    report = {"stale_staging": [], "orphan_videos": [], "applied": apply}
    stage_root = storage.staging_root(cfg)
    if stage_root.is_dir():
        for p in sorted(stage_root.iterdir()):
            job = p.name.rsplit("-", 1)[0]
            if p.is_dir() and clock - p.stat().st_mtime > stale_after and not storage.lock_is_held(pub / ".state" / "locks" / f"{job}.lock"):
                report["stale_staging"].append(p.name)
                if apply:
                    shutil.rmtree(p, ignore_errors=True)
    ready = pub / "ready"
    if ready.is_dir():
        for v in sorted(ready.rglob("*.mp4")):
            if not v.with_suffix("").with_name(v.stem + SIDECAR_SUFFIX).exists():
                job = v.stem.rsplit("__", 1)[-1]
                if storage.lock_is_held(pub / ".state" / "locks" / f"{job}.lock"):
                    continue
                report["orphan_videos"].append(storage.rel(v, pub))
                if apply:
                    q = pub / ".state" / "orphans"
                    q.mkdir(parents=True, exist_ok=True)
                    os.replace(v, q / f"{uuid.uuid4().hex[:8]}-{v.name}")
    return report


def classify(d, m, pub):
    """Where a job's current render stands against its recorded export. Read-only: writes nothing.

    `d` is the job directory, `m` its manifest and `pub` the publishing root. Returns `(kind, record)`, where kind is one
    of `ok`, `superseded`, `sidecar_missing`, `workspace_video_missing`, `archived` or `never_exported`, decided in that
    order. Only `superseded` means a render exists that differs from the one that was exported.

    This is the single source of truth for that comparison: `divergence()` reports on it and `resume_blocker()` refuses a
    resume on it. What to *do* about a finding stays `_export_locked`'s job.
    """
    job = m["job_id"]
    rec = {"job_id": job, "workspace_video": None, "exported_video": None, "sidecar": None,
           "workspace_sha256": None, "exported_sha256": None, "exported_at": None}
    claim = _claim(pub, job)
    if claim.exists():
        archived = None
        with contextlib.suppress(OSError, ValueError):
            archived = json.loads(claim.read_text(encoding="utf-8")).get("archived_to")
        if archived:
            rec["archived_to"] = archived
            return "archived", rec                             # handed off on purpose: not a stale export
    prior = _existing(pub, m)
    if prior is None:
        return "never_exported", rec                           # nothing recorded anywhere: nothing to compare
    pv, ps = prior
    rec["exported_video"] = storage.rel(pv, pub)
    rec["sidecar"] = storage.rel(ps, pub)
    sidecar = None
    with contextlib.suppress(OSError, ValueError):
        sidecar = json.loads(ps.read_text(encoding="utf-8")) if ps.exists() else None
    if sidecar is None:
        return "sidecar_missing", rec                          # gone or unreadable: the sidecar is the "ready" marker
    rec["exported_sha256"] = sidecar.get("video_sha256")
    rec["exported_at"] = sidecar.get("exported_at")
    video = Path(d) / "video.mp4"
    if not video.is_file():
        return "workspace_video_missing", rec                  # the export stands on its own; not a mismatch
    rec["workspace_video"] = storage.rel(video, d)
    rec["workspace_sha256"] = sha256_file(video)
    return ("ok" if rec["workspace_sha256"] == rec["exported_sha256"] else "superseded"), rec


def divergence(*, cfg=None, jobs=None):
    """Does each exported job still match the video sitting in its workspace? (`export-integrity/1`)

    Read-only: writes nothing, creates no directory and never calls preflight(), so it is safe to run against the real
    publishing library. It REPORTS a mismatch and never repairs one - replacing an exported video stays an explicit
    `contentos storage export <job> --force`, because only a human can judge whether the new render is the one to ship.

    Buckets the jobs by `classify()`: archived, sidecar_missing, workspace_video_missing (normal for an adopted, legacy
    or cleaned job - not a mismatch), never_exported, ok, or superseded. Only `superseded` is a mismatch.
    """
    cfg = cfg or storage.config()
    pub = storage.publish_root(cfg)
    out = {"schema": INTEGRITY_SCHEMA, "checked": 0, "ok": [], "superseded": [], "sidecar_missing": [],
           "workspace_video_missing": [], "archived": [], "never_exported": [], "unreadable_manifest": []}
    if not (pub / ".state").is_dir():                        # nothing has ever been exported into this library
        return out
    for d in storage.iter_job_dirs(jobs):
        try:
            m = storage.read_manifest(d)
        except storage.StorageError:
            out["unreadable_manifest"].append(d.name)
            continue
        if m is None or not (m.get("export") or m.get("status") == "exported"):
            continue
        out["checked"] += 1
        kind, rec = classify(d, m, pub)
        out[kind].append(rec)
    return out


# A resume is honest when there is nothing to compare (no workspace video) or the export was deliberately handed off.
RESUME_SAFE = ("ok", "archived", "workspace_video_missing")


def resume_blocker(job_dir, *, cfg=None):
    """None when a resumed export may be reported as done, otherwise the reason it must not be.

    A resume that reports success while `ready/` holds an older render is a false success, so the render is checked
    against the sha the sidecar recorded. Blocking is reported by the caller as a BLOCKED stage (an operator decision),
    never as a pass; a job that cannot be verified - a missing sidecar, a lost export record, an unreadable manifest -
    blocks too, with a diagnostic that names the recovery command. Nothing here writes, and it never repairs.
    """
    d = Path(job_dir)
    try:
        m = storage.read_manifest(d)
    except storage.StorageError as exc:
        return (f"export resume refused: {d.name}/manifest.json cannot be read ({exc}); "
                f"re-export explicitly with 'contentos storage export {d.name} --force'")
    if m is None:
        return (f"export resume refused: {d.name} has no manifest.json to verify this render against; "
                f"re-export explicitly with 'contentos storage export {d.name} --force'")
    try:
        pub = storage.publish_root(cfg or storage.config())
    except storage.StorageError as exc:
        return (f"export resume refused: the publishing library cannot be resolved ({exc}); "
                f"nothing was verified, so this render is not reported as exported")
    kind, rec = classify(d, m, pub)
    if kind in RESUME_SAFE:
        return None
    if kind == "superseded":
        return (f"export resume refused: the render changed since it was exported "
                f"(workspace {str(rec['workspace_sha256'])[:12]} != exported {str(rec['exported_sha256'])[:12]}); "
                f"re-run with --force to replace it, or inspect with 'contentos storage ready --check'")
    what = {"sidecar_missing": "its .publish.json sidecar is missing or unreadable",
            "never_exported": "no export record or sidecar was found"}.get(kind, f"it is {kind}")
    return (f"export resume refused: cannot verify this render against its export record because {what}; "
            f"re-export explicitly with 'contentos storage export {d.name} --force'")
