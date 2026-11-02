"""Track B workbench operations.

Intake records a hand-built HyperFrames job before a video exists. Registration
adopts a finished video. Voice, alignment, render, and QA call the existing
local operations and leave project/index.html untouched.
"""
import json
import time
from pathlib import Path

import yaml

from . import export, ledger, pipeline, storage
from .intelligence import visual
from .production import critic
from .qa import run_qa

SCRIPT_FILES = ("script.yaml", "script.yml", "script.json", "spec.yaml", "spec.yml", "spec.json", "track-b.yaml")
SCENE_PLAN_FILES = ("scene-plan.json", "sceneplan.json")
MAX_TEXT = 1_048_576


class TrackBError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _job(job_id):
    if not storage.valid_job_id(str(job_id)):
        raise TrackBError(400, "INVALID_JOB", "Job id is not valid")
    directory = storage.find_job_dir(job_id)
    if directory is None:
        raise TrackBError(404, "NOT_FOUND", "Job not found")
    return directory.resolve()


def _inside(directory, path):
    resolved = Path(path).resolve()
    resolved.relative_to(directory.resolve())
    return resolved


def _read_text(directory, path):
    if path.is_symlink():
        raise TrackBError(409, "UNSAFE_ARTIFACT", "Job files must stay inside the job directory")
    try:
        _inside(directory, path)
    except ValueError as exc:
        raise TrackBError(409, "UNSAFE_ARTIFACT", "Job files must stay inside the job directory") from exc
    if path.stat().st_size > MAX_TEXT:
        raise TrackBError(413, "BODY_TOO_LARGE", "A Track B text file exceeds 1 MiB")
    return path.read_text(encoding="utf-8")


def _load_document(directory, path):
    text = _read_text(directory, path)
    try:
        value = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise TrackBError(409, "INVALID_SCRIPT", f"{path.name} is not valid") from exc
    if not isinstance(value, dict):
        raise TrackBError(409, "INVALID_SCRIPT", f"{path.name} must contain a script")
    return value


def _lines(document):
    rows = document.get("script")
    if not isinstance(rows, list) or not rows:
        return None
    lines = []
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("say") or "").strip():
            return None
        line = {"say": str(row["say"]), "headline": str(row.get("headline") or "")}
        if row.get("tts"):
            line["tts"] = str(row["tts"])
        lines.append(line)
    return lines


def discover_script(directory):
    directory = Path(directory)
    for name in SCRIPT_FILES:
        path = directory / name
        if not path.is_file():
            continue
        document = _load_document(directory, path)
        lines = _lines(document)
        if lines is None:
            raise TrackBError(409, "INVALID_SCRIPT", f"{name} needs spoken lines")
        return {
            "content_id": directory.name,
            "title": str(document.get("title") or directory.name),
            "format": str(document.get("format") or "9:16"),
            "voice": str(document.get("voice") or "af_heart"),
            "render": "hyperframes",
            "script": lines,
        }
    return None


def script_spec(directory):
    try:
        return discover_script(directory) or {}
    except TrackBError:
        return {}


def scene_plan_state(directory):
    directory = Path(directory)
    for name in SCENE_PLAN_FILES:
        path = directory / name
        if not path.is_file():
            continue
        try:
            document = json.loads(_read_text(directory, path))
        except (TrackBError, json.JSONDecodeError):
            return {"status": "INVALID", "path": name, "provenance": name, "detail": "Scene plan is not valid JSON"}
        scenes = document.get("scenes") if isinstance(document, dict) else None
        if not isinstance(document, dict) or document.get("schema") != "sceneplan/1" or not isinstance(scenes, list):
            return {"status": "INVALID", "path": name, "provenance": name, "detail": "Scene plan must use schema sceneplan/1"}
        return {"status": "PASS", "path": name, "provenance": name, "scenes": len(scenes)}
    return {"status": "NOT_RUN", "provenance": None}


def _composition(directory):
    path = directory / "project" / "index.html"
    if not path.is_file() or path.is_symlink():
        return None
    try:
        return _inside(directory, path)
    except (TrackBError, ValueError):
        return None


def _manifest(directory):
    manifest = storage.read_manifest(directory)
    if manifest is None or manifest.get("track") != "B":
        raise TrackBError(409, "NEEDS_INTAKE", "This job is not a Track B intake")
    return manifest


def _spec_for_job(directory):
    spec = discover_script(directory)
    if spec is None:
        raise TrackBError(409, "MISSING_SCRIPT", "The job directory has no spoken script")
    return spec


def _require_gate(job_id, gate, digest):
    if not digest:
        raise TrackBError(409, "ARTIFACT_NOT_READY", f"{gate} has no current artifact digest")
    state, _bound = ledger.check_gate(job_id, gate, digest)
    if state != "ok":
        raise TrackBError(409, "GATE_REQUIRED", f"{gate} is required for the current digest")


def _log(directory):
    folder = directory / "logs"
    folder.mkdir(exist_ok=True)
    return folder / "track-b.log"


def _context(directory, spec):
    return {
        "dir": directory,
        "spec": {**spec, "render": "hyperframes"},
        "allow_paid": False,
        "log_path": _log(directory),
    }


def _record(job_id, stage, provider, status, start, artifacts=(), error=""):
    ledger.record(ledger.new_run_id(), job_id, stage, provider, status, start, artifacts=artifacts, error=error[-1000:])


def _composition_sha(directory):
    path = _composition(directory)
    return export.sha256_file(path) if path else None


def _write_report(directory, name, payload):
    folder = directory / "reports"
    folder.mkdir(exist_ok=True)
    target = folder / name
    if target.is_symlink():
        raise TrackBError(409, "UNSAFE_ARTIFACT", "Report path must stay inside the job directory")
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _stored_report(directory, name):
    path = directory / "reports" / name
    if not path.is_file() or path.is_symlink():
        return {"status": "NOT_RUN", "provenance": None}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "INVALID", "provenance": f"reports/{name}", "detail": "Persisted report is malformed"}
    if not isinstance(value, dict):
        return {"status": "INVALID", "provenance": f"reports/{name}"}
    current = _composition_sha(directory)
    if value.get("compositionSha256") and value.get("compositionSha256") != current:
        return {**value, "status": "STALE", "detail": "The composition changed after this report was written"}
    return value


def critic_state(directory):
    for relative in ("delivery/critic-report.json", "critic-report.json"):
        path = directory / relative
        if not path.is_file() or path.is_symlink():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"status": "INVALID", "provenance": relative, "detail": "Persisted critic report is malformed"}
        if not isinstance(value, dict):
            return {"status": "INVALID", "provenance": relative, "detail": "Persisted critic report is malformed"}
        checked = critic.check(value)
        verdict = value.get("verdict")
        status = "INVALID" if not checked["ok"] else ("PASS" if verdict == "pass" else ("FAIL" if verdict == "reject" else "WARNING"))
        return {
            "status": status,
            "provenance": relative,
            "verdict": verdict,
            "computedVerdict": checked.get("computed_verdict"),
            "valid": checked["ok"],
            "problems": checked["problems"],
        }
    return {"status": "NOT_RUN", "provenance": None}


def _technical(directory):
    path = directory / "qa.json"
    if not path.is_file() or path.is_symlink():
        return {"status": "NOT_RUN", "provenance": None}
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "INVALID", "provenance": "qa.json"}
    failed = [item.get("check") for item in rows if isinstance(item, dict) and item.get("status") == "FAIL"] if isinstance(rows, list) else []
    return {"status": "FAIL" if failed else "PASS", "provenance": "qa.run_qa", "failed": failed}


def _audio(directory):
    folder = directory / "audio"
    if not folder.is_dir():
        return []
    return [{"name": path.name, "path": f"audio/{path.name}"} for path in sorted(folder.glob("*.wav")) if path.is_file() and not path.is_symlink()]


def _timing(directory):
    path = directory / "timing.json"
    if not path.is_file() or path.is_symlink():
        return {"status": "NOT_RUN", "provenance": None}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "INVALID", "path": "timing.json", "provenance": "timing.json"}
    if not isinstance(value, dict) or value.get("schema") != "word-timing/1":
        return {"status": "INVALID", "path": "timing.json", "provenance": "timing.json"}
    return {"status": "PASS", "path": "timing.json", "provenance": "timing.json", "lines": len(value.get("lines") or [])}


def evidence(directory, manifest):
    directory = Path(directory)
    composition = _composition(directory)
    spec = script_spec(directory)
    return {
        "composition": {
            "path": "project/index.html" if composition else None,
            "present": composition is not None,
        },
        "script": {
            "present": bool(spec.get("script")),
            "lines": len(spec.get("script") or []),
            "digest": pipeline.script_digest(spec) if spec.get("script") else None,
        },
        "scenePlan": scene_plan_state(directory),
        "timing": _timing(directory),
        "audio": _audio(directory),
        "registration": {
            "status": (manifest.get("validation") or {}).get("status", "NOT_RUN") if isinstance(manifest.get("validation"), dict) else "NOT_RUN",
            "finalOutput": manifest.get("final_output"),
        },
        "quality": {
            "technical": _technical(directory),
            "visualPlan": _stored_report(directory, "visual-plan.json"),
            "visualCheck": _stored_report(directory, "visual-check.json"),
            "visualScenes": _stored_report(directory, "visual-scenes.json"),
            "critic": critic_state(directory),
        },
    }


def next_action(job_id, directory):
    directory = Path(directory)
    manifest = storage.read_manifest(directory) or {}
    if manifest.get("track") != "B":
        return None
    spec = script_spec(directory)
    if _composition(directory) is None or not spec.get("script"):
        return {
            "kind": "intake",
            "label": "Finish intake",
            "detail": "Track B intake needs project/index.html and a spoken script in the job directory.",
        }
    script_state, _bound = ledger.check_gate(job_id, "SCRIPT_APPROVED", pipeline.script_digest(spec))
    if script_state != "ok":
        return {
            "kind": "script-review",
            "label": "Review the script",
            "detail": "Voice waits until this script digest is approved.",
            "gate": "SCRIPT_APPROVED",
            "href": f"#/jobs/{job_id}/script",
        }
    if not _audio(directory):
        return {
            "kind": "track-b-voice",
            "label": "Generate voice",
            "detail": "Kokoro reads the approved script. The composition file stays as written.",
        }
    if _timing(directory)["status"] != "PASS":
        return {
            "kind": "track-b-align",
            "label": "Align words",
            "detail": "Word timing has not been written for the current audio takes.",
        }
    production = pipeline.production_digest(directory, spec)
    production_state, _bound = ledger.check_gate(job_id, "PRODUCTION_APPROVED", production)
    if production_state != "ok":
        return {
            "kind": "production-review",
            "label": "Review the composition",
            "detail": "Render waits until this production digest is approved.",
            "gate": "PRODUCTION_APPROVED",
            "href": f"#/jobs/{job_id}/review",
        }
    if not (directory / "video.mp4").is_file():
        return {
            "kind": "track-b-render",
            "label": "Render HyperFrames",
            "detail": "Render writes video.mp4 from the existing project directory.",
        }
    if _technical(directory)["status"] == "NOT_RUN":
        return {
            "kind": "track-b-qa",
            "label": "Run diagnostics",
            "detail": "Technical QA, visual checks, and the critic reader are recorded separately.",
        }
    return {
        "kind": "export",
        "label": "Export",
        "detail": "Export copies the validated video into the ready library. Publishing stays off.",
        "href": f"#/jobs/{job_id}/files",
    }


def intake(job_id):
    directory = _job(job_id)
    existing = storage.read_manifest(directory)
    if existing is not None and existing.get("track") != "B":
        raise TrackBError(409, "TRACK_A_JOB", "A Track A job is not converted to Track B")
    if _composition(directory) is None:
        raise TrackBError(409, "MISSING_COMPOSITION", "Intake needs project/index.html inside the job directory")
    spec = discover_script(directory)
    if spec is None:
        raise TrackBError(409, "MISSING_SCRIPT", "Intake needs a script file with spoken lines inside the job directory")
    plan = scene_plan_state(directory)
    if plan["status"] == "INVALID":
        raise TrackBError(409, "INVALID_SCENE_PLAN", plan.get("detail") or "Scene plan must use schema sceneplan/1")
    created = False
    if existing is None:
        written = directory / "track-b.yaml"
        written.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
        manifest = storage.new_manifest(
            job_id, title=spec["title"], renderer="hand-built",
            aspect_ratio=spec["format"], content_id=job_id,
        )
        manifest["track"] = "B"
        manifest["source_spec"] = str(written.resolve())
        manifest["final_output"] = None
        manifest["note"] = "Track B intake. The composition stays hand-built."
        storage.write_manifest(directory, manifest)
        created = True
    return {"status": "INTAKE", "created": created, "jobId": job_id, "scenePlan": plan["status"]}


def _recorded_stages(job_id):
    connection = ledger.db()
    try:
        rows = connection.execute(
            "SELECT stage, status FROM runs WHERE content_id=? AND status IN ('OK', 'EXTERNAL') ORDER BY rowid",
            (job_id,),
        ).fetchall()
    finally:
        connection.close()
    return {stage: status for stage, status in rows}


def _record_external(job_id):
    latest = _recorded_stages(job_id)
    if latest.get("render") in ("OK", "EXTERNAL"):
        return False
    started = time.time()
    run_id = ledger.new_run_id()
    wrote = False
    for stage in ("script", "voice", "compose", "render"):
        if latest.get(stage) in ("OK", "EXTERNAL"):
            continue
        ledger.record(run_id, job_id, stage, "external:track-B", "EXTERNAL", started)
        wrote = True
    return wrote


def register(job_id):
    directory = _job(job_id)
    existing = storage.read_manifest(directory)
    if existing is not None and existing.get("track") != "B":
        raise TrackBError(409, "TRACK_A_JOB", "A Track A job is not converted to Track B")
    video = directory / "video.mp4"
    if not video.is_file() or video.is_symlink():
        raise TrackBError(409, "ARTIFACT_NOT_READY", "Register needs video.mp4 inside the job directory")
    try:
        _inside(directory, video)
    except ValueError as exc:
        raise TrackBError(409, "UNSAFE_ARTIFACT", "video.mp4 must stay inside the job directory") from exc
    if existing is None:
        spec = script_spec(directory)
        storage.adopt_external(directory, title=spec.get("title") or job_id)
        return {"status": "REGISTERED", "created": True, "externalLedger": _record_external(job_id)}
    from . import finalcheck
    manifest = storage.read_manifest(directory)
    result = finalcheck.validate_video(
        video, manifest.get("aspect_ratio") or "9:16", require_audio=manifest.get("require_audio", True),
    )
    if result.get("status") != "passed":
        storage.update_manifest(directory, validation=result)
        raise TrackBError(422, "VIDEO_INVALID", "The finished video did not pass validation")
    storage.update_manifest(directory, validation=result, final_output="video.mp4", failure=None)
    return {"status": "REGISTERED", "created": False, "externalLedger": _record_external(job_id)}


def voice(job_id):
    directory = _job(job_id)
    _manifest(directory)
    spec = _spec_for_job(directory)
    _require_gate(job_id, "SCRIPT_APPROVED", pipeline.script_digest(spec))
    started = time.time()
    try:
        provider, artifacts = pipeline.s_voice(_context(directory, spec))
    except pipeline.Blocked as exc:
        raise TrackBError(409, "VOICE_BLOCKED", str(exc)) from exc
    except (OSError, RuntimeError) as exc:
        _record(job_id, "voice", "kokoro_local", "FAIL", started, error=str(exc))
        raise TrackBError(422, "VOICE_FAILED", str(exc)[-1000:]) from exc
    _record(job_id, "voice", provider, "OK", started, artifacts=artifacts)
    return {"status": "OK", "provider": provider, "takes": len(artifacts)}


def align(job_id):
    directory = _job(job_id)
    _manifest(directory)
    spec = _spec_for_job(directory)
    lines = []
    for index, line in enumerate(spec["script"], 1):
        wav = directory / "audio" / f"{index:02d}.wav"
        if not wav.is_file() or wav.is_symlink():
            raise TrackBError(409, "ARTIFACT_NOT_READY", f"Alignment needs audio/{index:02d}.wav")
        asr = pipeline.words_for(wav, directory / "work" / f"align-{index:02d}", _log(directory))
        tokens = line["say"].split()
        duration = 1.0 if asr else pipeline.dur(wav)
        timed = pipeline.caption_words(tokens, asr, duration) if tokens else []
        lines.append({
            "say": line["say"],
            "words": [{"text": word, "start": start, "end": end} for word, start, end in timed],
        })
    payload = {"schema": "word-timing/1", "lines": lines}
    target = directory / "timing.json"
    if target.is_symlink():
        raise TrackBError(409, "UNSAFE_ARTIFACT", "timing.json must stay inside the job directory")
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    storage.update_manifest(directory, artifacts={"align": "timing.json"})
    return {"status": "OK", "path": "timing.json", "lines": len(lines)}


def render(job_id):
    directory = _job(job_id)
    _manifest(directory)
    spec = _spec_for_job(directory)
    _require_gate(job_id, "PRODUCTION_APPROVED", pipeline.production_digest(directory, spec))
    if _composition(directory) is None:
        raise TrackBError(409, "MISSING_COMPOSITION", "Render needs project/index.html")
    started = time.time()
    try:
        provider, artifacts = pipeline.s_render(_context(directory, spec))
    except pipeline.Blocked as exc:
        raise TrackBError(409, "RENDER_BLOCKED", str(exc)) from exc
    except (OSError, RuntimeError) as exc:
        _record(job_id, "render", "hyperframes", "FAIL", started, error=str(exc))
        raise TrackBError(422, "RENDER_FAILED", str(exc)[-1000:]) from exc
    _record(job_id, "render", provider, "OK", started, artifacts=artifacts)
    return {"status": "OK", "provider": provider}


def _visual_plan(directory, digest):
    plan = None
    for name in SCENE_PLAN_FILES:
        path = directory / name
        if path.is_file() and not path.is_symlink():
            try:
                plan = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                plan = None
            break
    if not isinstance(plan, dict) or plan.get("schema") != "sceneplan/1":
        return {"status": "NOT_RUN", "provenance": None}
    try:
        result = visual.rule_a_from_plan(plan)
    except visual.VisualError as exc:
        return _write_report(directory, "visual-plan.json", {
            "status": "NOT_RUN", "provenance": "intelligence.visual.rule_a_from_plan",
            "compositionSha256": digest, "detail": str(exc),
        })
    return _write_report(directory, "visual-plan.json", {
        "status": "PASS" if result.get("ok") else "FAIL",
        "provenance": "intelligence.visual.rule_a_from_plan",
        "compositionSha256": digest,
        "result": result,
    })


def _visual_check(directory, job_id, digest):
    composition = _composition(directory)
    if composition is None or digest is None:
        return {"status": "NOT_RUN", "provenance": None}
    try:
        signature, _basis = visual.signature_for(visual._css_text(composition), None)
        result = visual.rule_b(signature, visual.ledger(), content_id=job_id)
    except (OSError, ValueError, visual.VisualError) as exc:
        return _write_report(directory, "visual-check.json", {
            "status": "ERROR", "provenance": "intelligence.visual.rule_b",
            "compositionSha256": digest, "detail": str(exc),
        })
    return _write_report(directory, "visual-check.json", {
        "status": "PASS" if result.get("ok") else "FAIL",
        "provenance": "intelligence.visual.rule_b",
        "compositionSha256": digest,
        "result": result,
    })


def _scene_timing(directory):
    for name in ("scene-timing.json", "scenes.json"):
        path = directory / name
        if path.is_file() and not path.is_symlink():
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
            return value if isinstance(value, dict) else None
    return None


def _visual_scenes(directory, digest):
    video = directory / "video.mp4"
    timing = _scene_timing(directory)
    if not video.is_file() or video.is_symlink() or timing is None or digest is None:
        return {"status": "NOT_RUN", "provenance": None}
    try:
        starts, total = visual.starts_from_timing(timing, video)
        result = visual.rule_a_from_video(video, starts, total)
    except (OSError, RuntimeError, ValueError, visual.VisualError) as exc:
        return _write_report(directory, "visual-scenes.json", {
            "status": "ERROR", "provenance": "intelligence.visual.rule_a_from_video",
            "compositionSha256": digest, "detail": str(exc),
        })
    return _write_report(directory, "visual-scenes.json", {
        "status": "PASS" if result.get("ok") else "FAIL",
        "provenance": "intelligence.visual.rule_a_from_video",
        "compositionSha256": digest,
        "result": result,
    })


def qa(job_id):
    directory = _job(job_id)
    manifest = _manifest(directory)
    spec = script_spec(directory) or {"format": manifest.get("aspect_ratio") or "9:16"}
    video = directory / "video.mp4"
    technical = {"status": "NOT_RUN", "provenance": None}
    if video.is_file() and not video.is_symlink():
        rows = run_qa(video, spec.get("format") or "9:16")
        target = directory / "qa.json"
        target.write_text(json.dumps(
            [{"check": name, "status": status, "detail": text} for name, status, text in rows], indent=2,
        ), encoding="utf-8")
        failed = [name for name, status, _text in rows if status == "FAIL"]
        technical = {"status": "FAIL" if failed else "PASS", "provenance": "qa.run_qa", "failed": failed}
    digest = _composition_sha(directory)
    return {
        "technical": technical,
        "visualPlan": _visual_plan(directory, digest),
        "visualCheck": _visual_check(directory, job_id, digest),
        "visualScenes": _visual_scenes(directory, digest),
        "critic": critic_state(directory),
    }
