"""The hand-off boundary for external schedulers (read the library, claim a video, record progress, archive it).

Ownership is split on purpose:
  * The factory owns ready/ and the sidecar (*.publish.json). A sidecar is written once at export and never rewritten.
  * A scheduler owns publish/.state/claims/<job-id>.json: its claim, status and timestamps. Scheduling state never
    flows into the factory's job state, and the factory never reads these files except to refuse replacing a video that
    has already been handed off.

Statuses: ready -> claimed -> scheduled -> published, plus failed (retryable back to ready) and the archive step.
  claim()      atomic and exclusive: only one claimant wins, so the same video is never scheduled twice.
  transition() only by the claimant, only along the allowed edges, timestamps recorded.
  archive()    moves video + sidecar from ready/ to archive/ after a recorded `published` (or force). A move is NOT a
               publication; published_at is only ever set by transition(..., "published").

Library use:  from contentos import handoff;  entries, problems = handoff.discover(publish_dir)
CLI:          python -m contentos.handoff list|claim|transition|archive|status ...   (publish dir from the usual settings)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import storage
from .export import SIDECAR_SUFFIX

STATUSES = ("ready", "claimed", "scheduled", "published", "failed")
EDGES = {
    "ready": {"claimed"},
    "claimed": {"scheduled", "published", "failed", "ready"},
    "scheduled": {"published", "failed", "ready"},
    "failed": {"ready"},
    "published": set(),
}


class HandoffError(storage.StorageError):
    pass


class AlreadyClaimed(HandoffError):
    pass


def _claims_dir(pub):
    return Path(pub) / ".state" / "claims"


def _claim_path(pub, job_id):
    return _claims_dir(pub) / f"{storage.check_job_id(job_id)}.json"


def read_claim(pub, job_id):
    p = _claim_path(pub, job_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable claim record {p}: {exc}") from exc


def _sidecars(pub, base="ready"):
    root = Path(pub) / base
    return sorted(root.rglob(f"*{SIDECAR_SUFFIX}")) if root.is_dir() else []


def discover(pub, *, project=None, status=None, platform=None, fmt=None, language=None, aspect_ratio=None, verify_hash=False):
    """Every complete video in ready/. Returns (entries, problems). A sidecar whose video is missing or has the wrong size
    (or checksum with verify_hash) is reported in `problems` and is never returned as an entry. Filters are exact matches;
    `platform` matches if it is in platform_targets, or if the targets list is empty (open to any platform)."""
    entries, problems = [], []
    for sc in _sidecars(pub):
        try:
            data = json.loads(sc.read_text(encoding="utf-8"))
            video = sc.with_name(data["video_filename"])
            if "/" in data["video_filename"] or "\\" in data["video_filename"]:
                raise ValueError("video_filename must be a bare file name")
            if not video.is_file() or video.stat().st_size != data["video_bytes"]:
                raise ValueError("video missing or its size differs from the sidecar")
            if verify_hash:
                from .export import sha256_file
                if sha256_file(video) != data["video_sha256"]:
                    raise ValueError("video checksum differs from the sidecar")
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            problems.append({"sidecar": storage.rel(sc, pub), "problem": str(exc)})
            continue
        claim = read_claim(pub, data["job_id"])
        eff = claim["status"] if claim else data.get("publishing_status", "ready")
        e = {**data, "sidecar_path": storage.rel(sc, pub), "video_path": storage.rel(video, pub),
             "effective_status": eff, "claimant": claim.get("claimant") if claim else None}
        if project and data.get("project_id") != project:
            continue
        if status and eff != status:
            continue
        if fmt and data.get("format") != fmt:
            continue
        if language and data.get("language") != language:
            continue
        if aspect_ratio and data.get("aspect_ratio") != aspect_ratio:
            continue
        if platform and data.get("platform_targets") and platform not in data["platform_targets"]:
            continue
        entries.append(e)
    return entries, problems


def _find(pub, job_id):
    entries, _ = discover(pub)
    hits = [e for e in entries if e["job_id"] == job_id]
    if not hits:
        raise HandoffError(f"no complete video for job {job_id!r} in ready/")
    return hits[0]


def claim(pub, job_id, claimant):
    """Take a ready video for scheduling. Exclusive: a second claimant gets AlreadyClaimed."""
    if not claimant or not str(claimant).strip():
        raise HandoffError("a claimant name is required")
    e = _find(pub, job_id)
    with storage.file_lock(_claims_dir(pub) / f"{job_id}.lock"):
        cur = read_claim(pub, job_id)
        if cur and cur["status"] != "ready":
            raise AlreadyClaimed(f"{job_id} is already {cur['status']} (claimant {cur.get('claimant')!r})")
        if e["effective_status"] != "ready" and not cur:
            raise HandoffError(f"{job_id} is {e['effective_status']}, not ready")
        now = storage.now_iso()
        rec = {"job_id": job_id, "status": "claimed", "claimant": str(claimant), "claimed_at": now, "updated_at": now,
               "scheduled_at": None, "published_at": None, "archived_to": None,
               "history": (cur or {}).get("history", []) + [{"status": "claimed", "by": str(claimant), "at": now}]}
        storage.write_json_atomic(_claim_path(pub, job_id), rec)
        return rec


def transition(pub, job_id, new_status, claimant, *, note=None):
    if new_status not in STATUSES:
        raise HandoffError(f"unknown status {new_status!r}")
    with storage.file_lock(_claims_dir(pub) / f"{job_id}.lock"):
        cur = read_claim(pub, job_id)
        if not cur:
            raise HandoffError(f"{job_id} has not been claimed")
        if cur.get("claimant") != claimant:
            raise HandoffError(f"{job_id} is owned by {cur.get('claimant')!r}, not {claimant!r}")
        if new_status not in EDGES[cur["status"]]:
            raise HandoffError(f"cannot go from {cur['status']} to {new_status}")
        now = storage.now_iso()
        cur.update(status=new_status, updated_at=now)
        if new_status == "scheduled":
            cur["scheduled_at"] = now
        if new_status == "published":
            cur["published_at"] = now
        cur["history"].append({"status": new_status, "by": claimant, "at": now, **({"note": str(note)[:200]} if note else {})})
        storage.write_json_atomic(_claim_path(pub, job_id), cur)
        return cur


def archive(pub, job_id, *, force=False):
    """Move a handed-off video and its sidecar to archive/<project>/YYYY/MM/. Policy: only after `published` unless
    force. The sidecar moves first, so a crash can leave an orphan video (see export.recover) but never a ready one."""
    e = _find(pub, job_id)
    with storage.file_lock(_claims_dir(pub) / f"{job_id}.lock"):
        cur = read_claim(pub, job_id)
        status = cur["status"] if cur else e["effective_status"]
        if status != "published" and not force:
            raise HandoffError(f"{job_id} is {status}; archive only after it is published (or pass force)")
        if cur is None:                                       # force-archiving something never claimed: leave a record so it is not re-exported
            now = storage.now_iso()
            cur = {"job_id": job_id, "status": status, "claimant": None, "claimed_at": None, "updated_at": now,
                   "scheduled_at": None, "published_at": None, "archived_to": None, "history": []}
        sc, vid = Path(pub) / e["sidecar_path"], Path(pub) / e["video_path"]
        created = e["created_at"]
        dest = Path(pub) / "archive" / storage.slugify(e.get("project_id"), "unassigned") / created[0:4] / created[5:7]
        dest.mkdir(parents=True, exist_ok=True)
        if (dest / vid.name).exists() or (dest / sc.name).exists():
            raise HandoffError(f"{dest / vid.name} already exists in the archive")
        os.replace(sc, dest / sc.name)
        os.replace(vid, dest / vid.name)
        storage.fsync_dir(dest)
        cur["archived_to"] = storage.rel(dest / vid.name, pub)
        cur["updated_at"] = storage.now_iso()
        cur["history"].append({"status": "archived", "at": cur["updated_at"]})
        storage.write_json_atomic(_claim_path(pub, job_id), cur)
        return cur


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m contentos.handoff", description=__doc__.split("\n")[0])
    ap.add_argument("--publish-dir", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    for f in ("project", "status", "platform", "format", "language"):
        ls.add_argument(f"--{f}")
    ls.add_argument("--verify-hash", action="store_true")
    for name in ("claim", "transition", "archive", "status"):
        p = sub.add_parser(name)
        p.add_argument("job_id")
        if name in ("claim", "transition"):
            p.add_argument("--as", dest="claimant", required=True)
        if name == "transition":
            p.add_argument("status", choices=STATUSES)
        if name == "archive":
            p.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    try:
        pub = Path(a.publish_dir) if a.publish_dir else storage.publish_root()
        if a.cmd == "list":
            entries, problems = discover(pub, project=a.project, status=a.status, platform=a.platform, fmt=a.format,
                                         language=a.language, verify_hash=a.verify_hash)
            for e in entries:
                print(f"{e['effective_status']:10} {e.get('project_id')}  {e['job_id']}  {e['video_path']}")
            for p in problems:
                print(f"PROBLEM {p['sidecar']}: {p['problem']}", file=sys.stderr)
            print(f"{len(entries)} video(s), {len(problems)} problem(s)")
            return 1 if problems else 0
        if a.cmd == "claim":
            print(json.dumps(claim(pub, a.job_id, a.claimant), indent=2))
        elif a.cmd == "transition":
            print(json.dumps(transition(pub, a.job_id, a.status, a.claimant), indent=2))
        elif a.cmd == "archive":
            print(json.dumps(archive(pub, a.job_id, force=a.force), indent=2))
        else:
            print(json.dumps(read_claim(pub, a.job_id) or {"job_id": a.job_id, "status": "ready (unclaimed)"}, indent=2))
        return 0
    except storage.StorageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(_main())
