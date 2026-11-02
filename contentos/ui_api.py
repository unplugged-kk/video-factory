"""Versioned local-only JSON API used by Creator Studio."""
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

from . import export, ledger, pipeline, queue, storage, track_b
from .export import ExportRefused
from .production import preview
from .qa import run_qa
from .ui_runner import RunConflict, SUPERVISOR
from .ui_security import redact_text
from .ui_state import authoring_summary, capabilities_state, health_state, job_state, jobs_state

MAX_BODY = 1_048_576
_LOCAL_HOST = re.compile(r"^(localhost|127\.0\.0\.1)(:\d+)?$", re.IGNORECASE)


@dataclass
class Response:
    status: int
    body: object
    headers: dict = field(default_factory=dict)


def error(status, code, message, details=None):
    value = {"error": {"code": code, "message": message}}
    if details is not None:
        value["error"]["details"] = details
    return Response(status, value)


def valid_host(value):
    return bool(_LOCAL_HOST.fullmatch(value or ""))


def write_authorized(headers, token):
    host = headers.get("host", "")
    origin = headers.get("origin", "")
    parsed = urlsplit(origin)
    return (
        valid_host(host)
        and parsed.scheme == "http"
        and parsed.netloc.lower() == host.lower()
        and headers.get("x-contentos-token") == token
    )


def _payload(raw):
    if len(raw) > MAX_BODY:
        raise OverflowError
    value = json.loads(raw.decode("utf-8") or "{}")
    if not isinstance(value, dict):
        raise ValueError
    return value


def _spec_path(content_id, detail=None):
    if detail:
        directory = storage.find_job_dir(content_id)
        if directory is not None:
            manifest = storage.read_manifest(directory) or {}
            source = manifest.get("source_spec")
            if source and Path(source).is_file():
                return Path(source)
    root = storage.workspace_root() / "specs"
    for suffix in (".yaml", ".yml", ".json"):
        candidate = root / f"{content_id}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def _approve(content_id, payload):
    gate = payload.get("gate")
    if gate not in ("SCRIPT_APPROVED", "PRODUCTION_APPROVED"):
        return error(400, "UNSUPPORTED_GATE", "Only script and production approval are available")
    detail = job_state(content_id)
    if detail is None:
        return error(404, "NOT_FOUND", "Job not found")
    current = detail["approvals"][gate]["currentDigest"]
    if not current:
        return error(409, "ARTIFACT_NOT_READY", "The review artifact is not ready")
    if payload.get("seenDigest") != current:
        return error(409, "DIGEST_MISMATCH", "The artifact changed after it was reviewed",
                     {"currentDigest": current})
    ledger.approve(content_id, gate, by="creator-studio",
                   note=str(payload.get("note") or "")[:500], subject_sha256=current)
    return Response(200, {"status": "APPROVED", "gate": gate, "digest": current})


def _preview(content_id, payload):
    detail = job_state(content_id)
    directory = storage.find_job_dir(content_id)
    if detail is None or directory is None:
        return error(404, "NOT_FOUND", "Job not found")
    raw_times = payload.get("times", [2])
    if not isinstance(raw_times, list) or not 1 <= len(raw_times) <= 12:
        return error(400, "INVALID_TIMES", "Provide between 1 and 12 timestamps")
    try:
        times = [float(value) for value in raw_times]
    except (TypeError, ValueError):
        return error(400, "INVALID_TIMES", "Timestamps must be numbers")
    if any(value < 0 or value > 86_400 for value in times):
        return error(400, "INVALID_TIMES", "Timestamps must be between 0 and 86400 seconds")
    output = directory / "previews"
    if output.is_symlink():
        return error(409, "UNSAFE_ARTIFACT", "Preview directory must not be a symlink")
    output.mkdir(parents=True, exist_ok=True)
    video = directory / "video.mp4"
    project = directory / "project"
    try:
        output.resolve().relative_to(directory.resolve())
        if video.exists():
            video.resolve().relative_to(directory.resolve())
        if project.exists():
            project.resolve().relative_to(directory.resolve())
    except ValueError:
        return error(409, "UNSAFE_ARTIFACT", "Review artifacts must stay inside the job directory")
    try:
        paths = preview.video_frames(video, times, output, prefix="frame") if video.is_file() else (
            preview.snapshot(project, times, output) if (project / "index.html").is_file() else []
        )
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        return error(422, "PREVIEW_FAILED", str(exc)[-1000:])
    if not paths:
        return error(409, "ARTIFACT_NOT_READY", "No video or composition is ready to preview")
    return Response(200, {"previews": [Path(path).name for path in paths]})


def _spec_operation(payload, create):
    try:
        from . import specs
    except ImportError:
        return error(501, "NOT_IMPLEMENTED", "Spec authoring is unavailable")
    for forbidden in ("allowPaid", "approvePrivate", "path", "outputPath"):
        if payload.get(forbidden):
            return error(400, "FORBIDDEN_OPTION", f"{forbidden} is not accepted")
    render = payload.get("render")
    if render and render not in ("hyperframes",):
        return error(400, "UNSUPPORTED_RENDERER", "Creator Studio supports HyperFrames only")
    try:
        if create:
            path = specs.save_spec(payload)
            result = {"contentId": payload["content_id"], "path": str(path), "status": "SAVED"}
        else:
            report = specs.validate_spec(payload)
            result = {**report, "valid": report["ok"],
                      "summary": authoring_summary(payload, report)}
    except specs.SpecValidationError as exc:
        return error(422, "INVALID_SPEC", "Spec validation failed", exc.errors)
    except specs.SpecCollisionError as exc:
        return error(409, "SPEC_COLLISION", str(exc),
                     {"contentId": payload.get("content_id"), "recoverable": True})
    except (specs.SpecError, ValueError, OSError, yaml.YAMLError) as exc:
        return error(422, "INVALID_SPEC", str(exc))
    return Response(201 if create else 200, result)


def _rerun_preview(content_id, stage):
    if stage not in pipeline.STAGES or stage == "publish":
        return error(400, "UNKNOWN_STAGE", "Choose a pipeline stage other than publish")
    detail = job_state(content_id)
    if detail is None:
        return error(404, "NOT_FOUND", "Job not found")
    later, gates = pipeline.rerun_plan(stage)
    return Response(200, {
        "contentId": content_id, "stage": stage, "force": True,
        "removesDownstream": later, "revokesApprovals": gates,
        "confirmRequired": True,
    })


def _rerun(content_id, payload):
    stage = payload.get("stage")
    if payload.get("confirm") is not True:
        return error(400, "CONFIRMATION_REQUIRED", "Confirm the downstream invalidation before rerunning")
    if stage not in pipeline.STAGES or stage == "publish":
        return error(400, "UNKNOWN_STAGE", "Choose a pipeline stage other than publish")
    if payload.get("force") is False:
        return error(400, "FORCE_REQUIRED", "A one-stage rerun must invalidate stale downstream results")
    detail = job_state(content_id)
    spec_path = _spec_path(content_id, detail)
    if spec_path is None:
        return error(404, "SPEC_NOT_FOUND", "No saved spec exists for this job")
    try:
        started = SUPERVISOR.start(content_id, spec_path, only=stage, force=True)
    except RunConflict as exc:
        return error(409, "RUN_CONFLICT", str(exc))
    except ValueError as exc:
        return error(400, "UNKNOWN_STAGE", str(exc))
    later, gates = pipeline.rerun_plan(stage)
    return Response(202, {**started, "stage": stage, "removesDownstream": later, "revokesApprovals": gates})


def _rerun_qa(content_id):
    directory = storage.find_job_dir(content_id)
    detail = job_state(content_id)
    if directory is None or detail is None:
        return error(404, "NOT_FOUND", "Job not found")
    video = directory / "video.mp4"
    if not video.is_file():
        return error(409, "ARTIFACT_NOT_READY", "QA needs a rendered video")
    try:
        video.resolve().relative_to(directory.resolve())
        rows = run_qa(video, (detail.get("spec") or {}).get("format") or "9:16")
    except ValueError:
        return error(409, "UNSAFE_ARTIFACT", "The video must stay inside the job directory")
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        return error(422, "QA_FAILED", str(exc)[-1000:])
    target = directory / "qa.json"
    target.write_text(json.dumps([{"check": name, "status": status, "detail": text} for name, status, text in rows], indent=2), encoding="utf-8")
    failed = [name for name, status, _text in rows if status == "FAIL"]
    return Response(200, {"status": "FAIL" if failed else "PASS", "failed": failed, "checks": len(rows)})


def _export_preview(content_id):
    directory = storage.find_job_dir(content_id)
    if directory is None:
        return error(404, "NOT_FOUND", "Job not found")
    manifest = storage.read_manifest(directory)
    video = directory / "video.mp4"
    if manifest is None or not video.is_file():
        return error(409, "ARTIFACT_NOT_READY", "Export needs a rendered video and a job manifest")
    try:
        paths = storage.preflight(publish=True)
        destination, dest_video, dest_sidecar = export.locations(paths["publish"], manifest, storage.export_mode())
        existing = export._existing(paths["publish"], manifest)
    except (OSError, storage.StorageError, ExportRefused, KeyError, ValueError) as exc:
        return error(409, "EXPORT_UNAVAILABLE", str(exc))
    return Response(200, {
        "contentId": content_id,
        "source": "video.mp4",
        "bytes": video.stat().st_size,
        "sha256": export.sha256_file(video),
        "destination": str(dest_video.relative_to(paths["publish"])),
        "sidecar": str(dest_sidecar.relative_to(paths["publish"])),
        "destinationDirectory": str(destination.relative_to(paths["publish"])),
        "existing": None if existing is None else "already-exported",
        "publishEnabled": False,
    })


def _export(content_id, payload):
    if payload.get("confirm") is not True:
        return error(400, "CONFIRMATION_REQUIRED", "Confirm the export destination before copying the video")
    for forbidden in ("allowPaid", "publish", "destination", "path"):
        if payload.get(forbidden):
            return error(400, "FORBIDDEN_OPTION", f"{forbidden} is not accepted")
    if job_state(content_id) is None:
        return error(404, "NOT_FOUND", "Job not found")
    try:
        result = export.export_job(content_id, force=bool(payload.get("force")))
    except ExportRefused as exc:
        return error(409, "EXPORT_REFUSED", str(exc))
    except storage.StorageError as exc:
        return error(409, "EXPORT_UNAVAILABLE", str(exc))
    return Response(200, {"status": result.get("status"), "video": result.get("video"), "sidecar": result.get("sidecar"), "sha256": result.get("sha256")})


def _track_a_only(content_id):
    detail = job_state(content_id)
    if detail and detail.get("track") == "B":
        return error(409, "TRACK_B_JOB", "Track B jobs use their own voice, render, and QA actions")
    return None


def _track_b(content_id, action, payload):
    for forbidden in ("path", "destination", "allowPaid", "approvePrivate", "publish"):
        if payload.get(forbidden):
            return error(400, "FORBIDDEN_OPTION", f"{forbidden} is not accepted")
    operation = {
        "intake": track_b.intake,
        "register": track_b.register,
        "voice": track_b.voice,
        "align": track_b.align,
        "render": track_b.render,
        "qa": track_b.qa,
    }.get(action)
    if operation is None:
        return error(404, "NOT_FOUND", "Route not found")
    try:
        return Response(200, operation(content_id))
    except track_b.TrackBError as exc:
        return error(exc.status, exc.code, exc.message)
    except storage.StorageError as exc:
        return error(409, "TRACK_B_REFUSED", str(exc))


def _queue_add(payload):
    content_id = payload.get("contentId")
    if not storage.valid_job_id(str(content_id or "")):
        return error(400, "INVALID_JOB", "A saved job id is required")
    if payload.get("approvePrivate") or payload.get("allowPaid"):
        return error(400, "FORBIDDEN_OPTION", "Queue entries cannot grant approvals or enable paid work")
    refused = _track_a_only(content_id)
    if refused:
        return refused
    spec_path = _spec_path(content_id, job_state(content_id))
    if spec_path is None:
        return error(404, "SPEC_NOT_FOUND", "No saved spec exists for this job")
    ids = queue.add([spec_path], approve_private=False)
    if not ids:
        return error(409, "QUEUE_CONFLICT", "This job is already queued or running")
    return Response(202, {"id": ids[0], "contentId": content_id, "status": "queued"})


def _queue_requeue(raw_id):
    if not str(raw_id).isdigit():
        return error(400, "INVALID_JOB", "Queue ids are integers")
    before = ledger.db().execute("SELECT status FROM jobs WHERE id=?", (int(raw_id),)).fetchone()
    if before is None:
        return error(404, "NOT_FOUND", "Queue job not found")
    if before[0] not in ("failed", "blocked"):
        return error(409, "QUEUE_CONFLICT", "Only a failed or blocked queue job can be requeued")
    queue.requeue(int(raw_id))
    return Response(200, {"id": int(raw_id), "status": "queued"})


def dispatch(method, path, headers, raw_body, token):
    headers = {key.lower(): value for key, value in headers.items()}
    parsed_path = urlsplit(path)
    path = parsed_path.path
    query = parse_qs(parsed_path.query)
    if not valid_host(headers.get("host")):
        return error(421, "INVALID_HOST", "Creator Studio only accepts loopback hosts")
    if not path.startswith("/api/v1/"):
        return error(404, "NOT_FOUND", "Route not found")
    if method not in ("GET", "HEAD") and not write_authorized(headers, token):
        return error(403, "WRITE_FORBIDDEN", "A same-origin session token is required")
    try:
        payload = _payload(raw_body) if method not in ("GET", "HEAD") else {}
    except OverflowError:
        return error(413, "BODY_TOO_LARGE", "Request body exceeds 1 MiB")
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return error(400, "INVALID_JSON", "Request body must be a JSON object")

    if method == "GET" and path == "/api/v1/health":
        return Response(200, health_state(refresh=query.get("refresh") == ["1"]))
    if method == "GET" and path == "/api/v1/capabilities":
        return Response(200, capabilities_state())
    if method == "GET" and path == "/api/v1/jobs":
        return Response(200, {"jobs": jobs_state()})
    if method == "POST" and path == "/api/v1/specs/validate":
        return _spec_operation(payload, False)
    if method == "POST" and path == "/api/v1/specs":
        return _spec_operation(payload, True)

    match = re.fullmatch(r"/api/v1/jobs/([^/]+)", path)
    if match and method == "GET":
        detail = job_state(match.group(1))
        return Response(200, detail) if detail else error(404, "NOT_FOUND", "Job not found")
    match = re.fullmatch(r"/api/v1/jobs/([^/]+)/run", path)
    if match and method == "POST":
        content_id = match.group(1)
        if payload.get("only") or payload.get("force"):
            return error(400, "UNSUPPORTED_RUN_OPTION", "Use the rerun route for a forced one-stage run")
        refused = _track_a_only(content_id)
        if refused:
            return refused
        detail = job_state(content_id)
        spec_path = _spec_path(content_id, detail)
        if spec_path is None:
            return error(404, "SPEC_NOT_FOUND", "No saved spec exists for this job")
        try:
            started = SUPERVISOR.start(content_id, spec_path)
            return Response(202, started)
        except RunConflict as exc:
            return error(409, "RUN_CONFLICT", str(exc))
    match = re.fullmatch(r"/api/v1/jobs/([^/]+)/rerun", path)
    if match and method == "GET":
        refused = _track_a_only(match.group(1))
        return refused or _rerun_preview(match.group(1), query.get("stage", [""])[0])
    if match and method == "POST":
        refused = _track_a_only(match.group(1))
        return refused or _rerun(match.group(1), payload)
    match = re.fullmatch(r"/api/v1/jobs/([^/]+)/track-b/([a-z]+)", path)
    if match and method == "POST":
        return _track_b(match.group(1), match.group(2), payload)
    match = re.fullmatch(r"/api/v1/jobs/([^/]+)/qa", path)
    if match and method == "POST":
        return _rerun_qa(match.group(1))
    match = re.fullmatch(r"/api/v1/jobs/([^/]+)/export", path)
    if match and method == "GET":
        return _export_preview(match.group(1))
    if match and method == "POST":
        return _export(match.group(1), payload)
    if method == "GET" and path == "/api/v1/queue":
        return Response(200, queue.view())
    if method == "POST" and path == "/api/v1/queue":
        return _queue_add(payload)
    match = re.fullmatch(r"/api/v1/queue/([^/]+)/requeue", path)
    if match and method == "POST":
        return _queue_requeue(match.group(1))
    match = re.fullmatch(r"/api/v1/jobs/([^/]+)/approve", path)
    if match and method == "POST":
        return _approve(match.group(1), payload)
    match = re.fullmatch(r"/api/v1/jobs/([^/]+)/preview", path)
    if match and method == "POST":
        return _preview(match.group(1), payload)
    match = re.fullmatch(r"/api/v1/jobs/([^/]+)/stages/([^/]+)/log", path)
    if match and method == "GET":
        content_id, stage = match.groups()
        if stage not in pipeline.STAGES or not storage.valid_job_id(content_id):
            return error(404, "NOT_FOUND", "Stage log not found")
        directory = storage.find_job_dir(content_id)
        log_path = directory / "logs" / f"{stage}.log" if directory else None
        if log_path is None or not log_path.is_file():
            return Response(200, {"stage": stage, "status": "NOT_RUN", "text": ""})
        text = redact_text(log_path.read_text(encoding="utf-8", errors="replace")[-200_000:])
        return Response(200, {"stage": stage, "status": "AVAILABLE", "text": text})
    return error(404, "NOT_FOUND", "Route not found")
