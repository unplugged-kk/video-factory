"""supplied-audio/1: accept a voiceover or audio file the owner supplies, and record where it came from and whether it may be published.

Status: INITIAL. This slice records provenance and rights only. Nothing consumes the audio yet: `s_voice` still makes Kokoro
speech, so a job that holds a supplied-audio record STOPS at `voice` with a clear message instead of silently generating a
different voice. Wiring the supplied take into compose/captions/timeline is a later, separately approved step.

What it does (offline: ffprobe/ffmpeg only, no network, no ASR, no paid service):
  * validates the input (exists, a readable audio file with an audio stream, a known audio extension, no video stream);
  * copies the original BYTE-FOR-BYTE into <job>/supplied-audio/original/ (exclusive create, read-only, never overwritten);
  * writes <job>/supplied-audio/supplied-audio.json with SHA-256, probe facts and the rights record;
  * optionally writes a SEPARATE working copy (<job>/supplied-audio/working/*.wav, PCM, no loudness change) that records the
    hash of the original it was derived from;
  * answers "may this job be published?": rights `unknown`, a malformed record or any hash mismatch BLOCK publication
    (export to ready/ and an enabled publish). Private draft work is not blocked by rights status.

Rights: `owned` (the owner made it or holds all rights), `licensed` (a licence permits this use; the licence is named),
`unknown` (default; blocks publication). Evidence is the owner's own statement of why the status holds (a note, a licence id or
URL, a file path). This module stores it; it cannot verify it. Voice cloning, consent flows, music and SFX are out of scope.

  python -m contentos.production.supplied_audio ingest SOURCE (--job-id ID | --job-dir DIR) --rights owned|licensed|unknown
        [--evidence TEXT] [--licence TEXT] [--holder TEXT] [--working-copy]
  python -m contentos.production.supplied_audio verify (--job-id ID | --job-dir DIR)      # schema + hashes
  python -m contentos.production.supplied_audio status (--job-id ID | --job-dir DIR)      # publication blockers

Exit codes: 0 ok, 1 finding (blocked or hash/record problem), 2 unusable input. Output is JSON on stdout."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

from .. import storage
from ..qa import probe_video

SCHEMA = "supplied-audio/1"
RIGHTS = ("owned", "licensed", "unknown")
AUDIO_EXTENSIONS = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus")
SUBDIR = "supplied-audio"
RECORD_NAME = "supplied-audio.json"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class SuppliedAudioError(RuntimeError):
    """The input or record is unusable. The message says what to fix; nothing falls back to generated audio."""


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def record_path(job_dir):
    return Path(job_dir) / SUBDIR / RECORD_NAME


def has_record(job_dir):
    return record_path(job_dir).exists()


def _safe_name(name):
    base = re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name).lstrip(".")
    if not base:
        raise SuppliedAudioError(f"cannot derive a safe file name from {name!r}")
    return base


# ---- input validation -------------------------------------------------------------------------------------------------

def check_rights(status, evidence, licence):
    """Validate the rights fields as given. unknown needs nothing; owned needs evidence; licensed needs evidence and a named licence."""
    if status not in RIGHTS:
        raise SuppliedAudioError(f"rights must be one of {RIGHTS}, got {status!r}")
    evidence = (evidence or "").strip()
    licence = (licence or "").strip()
    if status in ("owned", "licensed") and not evidence:
        raise SuppliedAudioError(f"rights {status!r} needs --evidence (why the owner holds or is licensed these rights)")
    if status == "licensed" and not licence:
        raise SuppliedAudioError("rights 'licensed' needs --licence (the licence name, id or URL)")
    return evidence, licence


def probe_audio(path):
    """ffprobe facts for a usable audio input, or SuppliedAudioError. A file that also has a video stream is refused:
    footage is a different input with its own rights question."""
    p = Path(path)
    if not p.is_file():
        raise SuppliedAudioError(f"audio file not found: {p}")
    if p.stat().st_size == 0:
        raise SuppliedAudioError(f"audio file is empty: {p}")
    if p.suffix.lower() not in AUDIO_EXTENSIONS:
        raise SuppliedAudioError(f"unsupported audio file type {p.suffix!r}; use one of {AUDIO_EXTENSIONS}")
    try:
        info = probe_video(p)
    except (OSError, ValueError) as exc:
        raise SuppliedAudioError(f"ffprobe unavailable or failed on {p}: {exc}") from exc
    if not info:
        raise SuppliedAudioError(f"{p} is not a readable media file (ffprobe rejected it)")
    streams = info.get("streams", [])
    if any(s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic") for s in streams):
        raise SuppliedAudioError(f"{p} contains a video stream; supply an audio-only file")
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if a is None:
        raise SuppliedAudioError(f"{p} has no audio stream")
    try:
        duration = float(info["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        raise SuppliedAudioError(f"{p} has no readable duration") from None
    if duration <= 0:
        raise SuppliedAudioError(f"{p} has zero duration")
    return {"duration_s": round(duration, 3), "codec": a.get("codec_name"), "sample_rate": int(a.get("sample_rate") or 0) or None,
            "channels": a.get("channels")}


# ---- record validation ------------------------------------------------------------------------------------------------

def _rel_ok(rel):
    if not isinstance(rel, str) or not rel or rel.startswith("/") or ".." in Path(rel).parts:
        return False
    return Path(rel).parts[:1] == (SUBDIR,)


def validate_record(rec):
    """Schema problems in a loaded record, as a list of strings (empty = well-formed). Does not touch the files."""
    if not isinstance(rec, dict):
        return ["record is not a JSON object"]
    errs = []
    if rec.get("schema") != SCHEMA:
        errs.append(f"schema must be {SCHEMA!r}")
    if not isinstance(rec.get("job_id"), str) or not rec.get("job_id"):
        errs.append("job_id missing")
    src = rec.get("source")
    if not isinstance(src, dict) or not isinstance(src.get("filename"), str) or not SHA_RE.match(str(src.get("sha256", ""))):
        errs.append("source needs filename and a 64-hex sha256")
    orig = rec.get("original")
    if not isinstance(orig, dict) or not _rel_ok(orig.get("path")) or not SHA_RE.match(str(orig.get("sha256", ""))):
        errs.append("original needs a relative path under supplied-audio/ and a 64-hex sha256")
    elif isinstance(src, dict) and src.get("sha256") != orig.get("sha256"):
        errs.append("source.sha256 and original.sha256 differ (the stored copy is not the supplied file)")
    r = rec.get("rights")
    if not isinstance(r, dict) or r.get("status") not in RIGHTS:
        errs.append(f"rights.status must be one of {RIGHTS}")
    else:
        if r["status"] in ("owned", "licensed") and not str(r.get("evidence") or "").strip():
            errs.append(f"rights {r['status']!r} has no evidence")
        if r["status"] == "licensed" and not str(r.get("licence") or "").strip():
            errs.append("rights 'licensed' has no licence")
    pr = rec.get("probe")
    if not isinstance(pr, dict) or not isinstance(pr.get("duration_s"), (int, float)) or pr["duration_s"] <= 0:
        errs.append("probe.duration_s must be a positive number")
    wc = rec.get("working_copy")
    if wc is not None:
        if not isinstance(wc, dict) or not _rel_ok(wc.get("path")) or not SHA_RE.match(str(wc.get("sha256", ""))):
            errs.append("working_copy needs a relative path under supplied-audio/ and a 64-hex sha256")
        elif isinstance(orig, dict) and wc.get("derived_from_sha256") != orig.get("sha256"):
            errs.append("working_copy.derived_from_sha256 does not match original.sha256")
    return errs


def load_record(job_dir):
    p = record_path(job_dir)
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SuppliedAudioError(f"no supplied-audio record in {job_dir}") from None
    except (OSError, ValueError) as exc:
        raise SuppliedAudioError(f"unreadable supplied-audio record {p}: {exc}") from exc
    errs = validate_record(rec)
    if errs:
        raise SuppliedAudioError(f"malformed supplied-audio record {p}: " + "; ".join(errs))
    return rec


def verify(job_dir):
    """Re-hash the stored original (and working copy). Returns the record; raises SuppliedAudioError on any mismatch or missing file."""
    job_dir = Path(job_dir)
    rec = load_record(job_dir)
    problems = []
    for label, ent in (("original", rec["original"]), ("working copy", rec.get("working_copy"))):
        if not ent:
            continue
        f = job_dir / ent["path"]
        if not f.is_file():
            problems.append(f"{label} is missing: {ent['path']}")
        elif sha256_file(f) != ent["sha256"]:
            problems.append(f"{label} hash mismatch: {ent['path']} no longer matches the recorded SHA-256")
    if problems:
        raise SuppliedAudioError("; ".join(problems))
    return rec


def publish_blockers(job_dir):
    """Reasons this job must not be published because of its supplied audio. [] = none (including: no supplied audio at all).
    Fails closed: an unreadable/malformed record or a hash mismatch blocks too."""
    job_dir = Path(job_dir)
    if not has_record(job_dir):
        return []
    try:
        rec = verify(job_dir)
    except SuppliedAudioError as exc:
        return [str(exc)]
    status = rec["rights"]["status"]
    if status == "unknown":
        return ["supplied audio has rights status 'unknown'; record owned or licensed rights (with evidence) before publishing"]
    return []


# ---- ingest -----------------------------------------------------------------------------------------------------------

def _copy_exclusive(src, dst):
    """Copy src to dst byte-for-byte; dst must not exist. Read-only afterwards."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "rb") as fi, open(dst, "xb") as fo:
        for block in iter(lambda: fi.read(1 << 20), b""):
            fo.write(block)
        fo.flush()
        os.fsync(fo.fileno())
    os.chmod(dst, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def _make_working_copy(job_dir, original_rel, original_sha):
    src = Path(job_dir) / original_rel
    out = Path(job_dir) / SUBDIR / "working" / (Path(original_rel).stem + ".wav")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.wav")
    args = ["-vn", "-c:a", "pcm_s16le"]                                  # decode only: rate, channels and level are unchanged
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), *args, str(tmp)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        tmp.unlink(missing_ok=True)
        raise SuppliedAudioError(f"working copy failed: {exc}") from exc
    if r.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise SuppliedAudioError(f"working copy failed: ffmpeg said {r.stderr.strip()[-300:] or 'nothing'}")
    os.replace(tmp, out)
    return {"path": str(out.relative_to(job_dir)), "sha256": sha256_file(out), "bytes": out.stat().st_size,
            "derived_from_sha256": original_sha, "ffmpeg_args": args,
            "note": "decode to PCM only; the original is the record of truth"}


def ingest(source, job_dir, *, rights="unknown", evidence="", licence="", holder="", working_copy=False, job_id=None):
    """Accept `source` into the job. The source file is only read. Returns the record (also written to disk).
    Re-running with the same file is idempotent; the same file with different rights updates the rights block and keeps the
    previous one in `rights_history`; a different file is refused (the stored original is never replaced)."""
    evidence, licence = check_rights(rights, evidence, licence)
    src = Path(source).expanduser().resolve()
    probe = probe_audio(src)
    job_dir = Path(job_dir)
    if not job_dir.is_dir():
        raise SuppliedAudioError(f"job directory does not exist: {job_dir}")
    sha = sha256_file(src)
    name = _safe_name(src.name)
    original_rel = f"{SUBDIR}/original/{name}"
    dest = job_dir / original_rel
    now = storage.now_iso()
    new_rights = {"status": rights, "evidence": evidence, "licence": licence or None, "holder": (holder or "").strip() or None,
                  "recorded_at": now, "verified": False,
                  "note": "self-declared by the owner; the factory stores this but cannot verify it"}

    rec = None
    if has_record(job_dir):
        rec = load_record(job_dir)                                       # a malformed existing record stops here, explicitly
        if rec["original"]["sha256"] != sha:
            raise SuppliedAudioError("this job already holds a different supplied audio file; the stored original is never "
                                     "replaced. Use a new job id for a different take.")
        if (job_id or rec["job_id"]) != rec["job_id"]:
            raise SuppliedAudioError(f"record belongs to job {rec['job_id']!r}, not {job_id!r}")
    if dest.exists():
        if sha256_file(dest) != sha:
            raise SuppliedAudioError(f"{original_rel} already exists with different content; refusing to overwrite it")
    else:
        _copy_exclusive(src, dest)
        if sha256_file(dest) != sha:
            dest.chmod(stat.S_IWUSR | stat.S_IRUSR)
            dest.unlink()
            raise SuppliedAudioError("stored copy does not match the supplied file (SHA-256); nothing was recorded")

    if rec is None:
        rec = {"schema": SCHEMA, "job_id": job_id or job_dir.name, "created_at": now,
               "source": {"filename": src.name, "path_at_ingest": str(src), "sha256": sha, "bytes": src.stat().st_size},
               "original": {"path": original_rel, "sha256": sha, "bytes": dest.stat().st_size},
               "probe": probe, "rights": new_rights, "rights_history": [], "working_copy": None}
    else:
        old = rec["rights"]
        if (old["status"], old.get("evidence") or "", old.get("licence") or "", old.get("holder")) != \
                (rights, evidence, licence or "", new_rights["holder"]):
            rec.setdefault("rights_history", []).append(old)
            rec["rights"] = new_rights
    if working_copy and not rec.get("working_copy"):
        rec["working_copy"] = _make_working_copy(job_dir, original_rel, sha)
    elif working_copy and rec.get("working_copy"):
        wc = job_dir / rec["working_copy"]["path"]
        if not wc.is_file() or sha256_file(wc) != rec["working_copy"]["sha256"]:
            raise SuppliedAudioError("recorded working copy is missing or changed; remove it and re-ingest to rebuild")
    errs = validate_record(rec)
    if errs:                                                             # never write a record we would later reject
        raise SuppliedAudioError("internal: refusing to write a malformed record: " + "; ".join(errs))
    storage.write_json_atomic(record_path(job_dir), rec)
    _note_manifest(job_dir, rec)
    return rec


def _note_manifest(job_dir, rec):
    """Record the artifacts in the job manifest the way the pipeline does (relative paths; the manifest is a record, not a gate)."""
    try:
        if storage.read_manifest(job_dir) is None:
            return
        files = [f"{SUBDIR}/{RECORD_NAME}", rec["original"]["path"]] + ([rec["working_copy"]["path"]] if rec.get("working_copy") else [])
        storage.update_manifest(job_dir, artifacts={"supplied_audio": files})
    except (OSError, storage.StorageError):
        pass


# ---- CLI --------------------------------------------------------------------------------------------------------------

def _job_dir(a):
    if a.job_dir:
        return Path(a.job_dir)
    if a.job_id:
        return storage.job_dir(a.job_id)                                 # same resolver the pipeline uses; creates on first use
    raise SuppliedAudioError("give --job-id or --job-dir")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="supplied_audio", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ig = sub.add_parser("ingest")
    ig.add_argument("source")
    ig.add_argument("--rights", default="unknown", choices=RIGHTS)
    ig.add_argument("--evidence", default="")
    ig.add_argument("--licence", default="")
    ig.add_argument("--holder", default="")
    ig.add_argument("--working-copy", action="store_true")
    for name in ("ingest", "verify", "status"):
        p = ig if name == "ingest" else sub.add_parser(name)
        p.add_argument("--job-id")
        p.add_argument("--job-dir")
    a = ap.parse_args(argv)
    try:
        d = _job_dir(a)
        if a.cmd == "ingest":
            rec = ingest(a.source, d, rights=a.rights, evidence=a.evidence, licence=a.licence, holder=a.holder,
                         working_copy=a.working_copy, job_id=a.job_id)
            blockers = publish_blockers(d)
            print(json.dumps({"ok": True, "record": storage.rel(record_path(d), d), "rights": rec["rights"]["status"],
                              "sha256": rec["original"]["sha256"], "publish_blockers": blockers}, indent=1))
            return 0
        if a.cmd == "verify":
            rec = verify(d)
            print(json.dumps({"ok": True, "rights": rec["rights"]["status"], "original": rec["original"],
                              "working_copy": rec.get("working_copy")}, indent=1))
            return 0
        blockers = publish_blockers(d)
        print(json.dumps({"ok": not blockers, "has_record": has_record(d), "publish_blockers": blockers}, indent=1))
        return 0 if not blockers else 1
    except SuppliedAudioError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if a.cmd in ("verify", "status") else 2
    except (storage.StorageError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
