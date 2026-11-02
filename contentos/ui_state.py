"""Structured read models for the local Creator Studio."""
import json
import os
import subprocess
import time
from pathlib import Path

import yaml

from . import ledger, pipeline, providers, specs, storage, track_b
from .cli import FIX
from .production import critic, platforms

_health_cache = {"at": 0.0, "value": None}
TRACK_A_REQUIRED_PROVIDERS = {"tts": "kokoro_local", "render": "hyperframes"}
JOB_VIEW_SCHEMA = "creator-studio/job/1"
CAPABILITIES_SCHEMA = "creator-studio/capabilities/1"


def _json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _qa_rows(value):
    rows = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, (list, tuple)) and len(item) >= 3:
            rows.append({"name": item[0], "status": item[1], "detail": item[2],
                         "provenance": "pipeline qa stage"})
        elif isinstance(item, dict):
            rows.append({**item, "provenance": item.get("provenance", "pipeline qa stage")})
    return rows


def _publish_state():
    try:
        enabled = bool(providers.load("youtube.yaml")["publish"]["enabled"])
    except (KeyError, OSError, TypeError, ValueError):
        return {"enabled": False, "status": "UNAVAILABLE", "actionSupported": False}
    return {
        "enabled": enabled,
        "status": "ENABLED" if enabled else "DISABLED",
        "actionSupported": False,
        "reason": None if enabled else "Publishing is disabled by configuration",
    }


def _platform_budget(manifest, spec):
    kind = spec.get("kind") or manifest.get("kind")
    if kind not in platforms.KINDS:
        return {
            "status": "NOT_AVAILABLE",
            "kind": kind,
            "reason": "Job kind is not persisted as short or long",
        }
    selected = spec.get("platform_targets") or manifest.get("platform_targets")
    if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
        selected = None
    try:
        registry = platforms.load()
        owner = platforms.owner_limits()[kind]
        value = platforms.budget(registry, kind, platforms=selected, owner_max=owner)
    except platforms.PlatformError as exc:
        return {"status": "UNAVAILABLE", "kind": kind, "reason": str(exc)}
    return {"status": "AVAILABLE", **value}


def _supervised(content_id):
    try:
        from .ui_runner import SUPERVISOR
        return SUPERVISOR.running(content_id)
    except (ImportError, AttributeError):
        return False


def _workflow_summary(content_id, state, stages, block, run_result, updated, *, now):
    attempts = [attempt for stage in stages.values() for attempt in stage.get("attempts", [])]
    run_ids = {attempt.get("runId") for attempt in attempts if attempt.get("runId")}
    latest = max(stages.values(), key=lambda row: row.get("rowId", 0), default={})
    elapsed = run_result.get("elapsedSeconds")
    if elapsed is None and latest:
        elapsed = latest.get("seconds")
    if state == "RUNNING":
        action = {"kind": None, "label": "Running",
                  "detail": "The current attempt is in progress."}
    elif state == "BLOCKED":
        action = {"kind": "review", "label": "Review required",
                  "detail": block.get("reason") or "A human approval gate is waiting.",
                  "gate": block.get("gate")}
    elif state == "FAILED":
        action = {"kind": "logs", "label": "Inspect failure",
                  "detail": (run_result.get("failure") or {}).get("error") or
                            latest.get("error") or "The latest attempt failed."}
    elif state == "STALE":
        action = {"kind": "run", "label": "Resume safely",
                  "detail": "No active run lock was reported; resume will clean interrupted artifacts."}
    elif state in ("RENDERED", "EXPORTED"):
        action = {"kind": "review", "label": "Review output",
                  "detail": "The pipeline attempt completed.", "gate": "PRODUCTION_APPROVED"}
    else:
        action = {"kind": "run", "label": "Run job",
                  "detail": "Start or resume at the next incomplete stage."}
    return {
        "activeRun": state == "RUNNING",
        "attempts": len(run_ids) or run_result.get("attempts", 0),
        "retries": run_result.get("retries", 0),
        "retryReason": (run_result.get("failure") or {}).get("error"),
        "elapsedSeconds": elapsed,
        "stale": state == "STALE",
        "updated": updated,
        "nextAction": action,
        "serverNow": now,
    }


def capabilities_state():
    """Read-only product capabilities backed by the canonical registries."""
    try:
        registry = platforms.load()
        owner = platforms.owner_limits()
        registry_metadata = _json(platforms.DEFAULT_PATH, {})
        platform_rows = [{
            "id": platform_id,
            "name": value["name"],
            "defaultEnabled": bool(value["default_enabled"]),
            "availableInIndia": bool(value["available_in_india"]),
            "formats": {
                kind: {
                    key: details.get(key)
                    for key in ("label", "max_seconds", "max_mb", "aspect_range",
                                "preferred_aspect", "confidence", "requires")
                    if details.get(key) is not None
                }
                for kind, details in value["formats"].items()
            },
        } for platform_id, value in registry.items()]
        budgets = {
            kind: platforms.budget(registry, kind, owner_max=owner[kind])
            for kind in platforms.KINDS
        }
        platform_state = {
            "status": "AVAILABLE",
            "checked": registry_metadata.get("checked"),
            "ownerLimits": owner,
            "platforms": platform_rows,
            "budgets": budgets,
        }
    except platforms.PlatformError as exc:
        platform_state = {
            "status": "UNAVAILABLE", "ownerLimits": {}, "platforms": {},
            "budgets": {}, "reason": str(exc),
        }
    return {
        "schema": CAPABILITIES_SCHEMA,
        "schemaVersion": 1,
        "voices": list(json.loads(specs.VOICE_IDS_FILE.read_text(encoding="utf-8"))),
        "platformLimits": platform_state,
        "renderLanes": ["hyperframes"],
        "actions": {
            "validateSpec": True,
            "createSpec": True,
            "runOrResume": True,
            "preview": True,
            "readStageLog": True,
            "approveScript": True,
            "approveProduction": True,
            "publish": False,
            "allowPaid": False,
            "cancel": False,
            "oneStageRerun": True,
            "rerunQa": True,
            "export": True,
        },
        "trackB": {
            "intake": True,
            "register": True,
            "voice": True,
            "align": True,
            "render": True,
            "qa": True,
            "compositionAuthoring": False,
            "publish": False,
            "allowPaid": False,
            "approvePrivate": False,
        },
        "publish": _publish_state(),
    }


def authoring_summary(spec, report):
    narration = report.get("narration", {})
    budget = _platform_budget({}, spec)
    issues = [
        {"level": "error", "path": item.get("path"), "message": item.get("message")}
        for item in report.get("errors", [])
    ]
    maximum = budget.get("max_seconds") if budget.get("status") == "AVAILABLE" else None
    estimate = narration.get("estimated_seconds")
    if maximum is not None and estimate is not None and estimate > maximum:
        issues.append({
            "level": "warning", "path": "script",
            "message": f"Estimated narration is {estimate:.1f}s; selected platforms allow {maximum}s.",
        })
    return {
        "status": "FAIL" if report.get("errors") else ("WARNING" if issues else "PASS"),
        "narration": narration,
        "platformBudget": budget,
        "issues": issues,
    }


def _tool(name):
    try:
        result = subprocess.run([name, "-version"], capture_output=True, text=True, timeout=10)
        detail = (result.stderr or result.stdout).splitlines()
        return {"status": "PASS" if result.returncode == 0 else "NOT_INSTALLED",
                "detail": detail[0] if detail else f"{name} exited {result.returncode}"}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "NOT_INSTALLED", "detail": f"{type(exc).__name__}: {exc}"}


def _root_health(label, getter):
    try:
        path = getter()
        healthy = path.is_dir() and os.access(path, os.W_OK)
        return {"label": label, "path": str(path), "writable": healthy,
                "status": "PASS" if healthy else "NOT_INSTALLED"}
    except (OSError, storage.StorageError) as exc:
        return {"label": label, "path": None, "writable": False,
                "status": "NOT_INSTALLED", "detail": str(exc)}


def _run_readiness(capabilities, tools, roots):
    blockers = []
    for capability, provider_id in TRACK_A_REQUIRED_PROVIDERS.items():
        group = next((item for item in capabilities if item["name"] == capability), None)
        provider = next(
            (item for item in (group or {}).get("candidates", []) if item["id"] == provider_id),
            None,
        )
        if not provider or not provider["healthy"]:
            blockers.append({
                "kind": "provider", "id": provider_id, "label": provider_id,
                "detail": (provider or {}).get("detail", f"{provider_id} is not configured"),
                "fix": (provider or {}).get("fix"),
            })
    ffmpeg = tools["ffmpeg"]
    if ffmpeg["status"] != "PASS":
        blockers.append({
            "kind": "tool", "id": "ffmpeg", "label": "ffmpeg",
            "detail": ffmpeg.get("detail"), "fix": ffmpeg.get("fix"),
        })
    for root in roots:
        if not root["writable"]:
            blockers.append({
                "kind": "storage", "id": root["label"], "label": root["label"],
                "detail": root.get("detail") or root.get("path"),
            })
    return {
        "profile": "track-a/hyperframes",
        "ready": not blockers,
        "blockers": blockers,
        "requiredProviders": dict(TRACK_A_REQUIRED_PROVIDERS),
        "requiredTools": ["ffmpeg"],
        "requiredStorage": ["workspace", "publishing"],
        "notes": {
            "stt": "optional: word timing falls back to even spacing",
            "publishing": "OAuth is not required: publishing is disabled and the publish stage is a dry run",
        },
    }


def health_state(*, refresh=False, clock=time.time):
    now = clock()
    if not refresh and _health_cache["value"] is not None and now - _health_cache["at"] <= 60:
        return _health_cache["value"]
    capabilities = []
    for capability in providers.load("providers.yaml")["capabilities"]:
        candidates = providers.candidates(capability)
        selected = next((candidate["id"] for candidate in candidates if candidate["healthy"]), None)
        rows = []
        for candidate in candidates:
            paid = candidate["tier"] in ("paid_api", "low_cost_api")
            status = "PASS" if candidate["healthy"] else ("OPTIONAL" if paid else "NOT_INSTALLED")
            rows.append({**candidate, "status": status,
                         "fix": None if paid else FIX.get(candidate["id"]),
                         "requiredForRun": candidate["id"] == TRACK_A_REQUIRED_PROVIDERS.get(capability)})
        capabilities.append({"name": capability, "selected": selected, "candidates": rows,
                             "requiredForRun": capability in TRACK_A_REQUIRED_PROVIDERS,
                             "status": "PASS" if selected else "NOT_INSTALLED",
                             "detail": f"selected: {selected}" if selected else "No healthy local provider"})
    tools = {"ffmpeg": {**_tool("ffmpeg"), "fix": FIX["ffmpeg"], "requiredForRun": True}}
    roots = [
        {**_root_health("workspace", storage.workspace_root), "requiredForRun": True},
        {**_root_health("publishing", storage.publish_root), "requiredForRun": True},
    ]
    value = {
        "checkedAt": now,
        "checked_at": now,
        "capabilities": capabilities,
        "tools": tools,
        "storage": roots,
        "publish": {"enabled": _publish_state()["enabled"]},
        "runReadiness": _run_readiness(capabilities, tools, roots),
    }
    _health_cache.update(at=now, value=value)
    return value


def _runs_and_approvals():
    with ledger.db() as connection:
        runs = connection.execute(
            "SELECT rowid,run_id,content_id,stage,provider,status,start,end,error,retries "
            "FROM runs ORDER BY rowid"
        ).fetchall()
        approvals = connection.execute(
            "SELECT content_id,gate,by,at,note,subject_sha256 FROM approvals ORDER BY at"
        ).fetchall()
    return runs, approvals


def _job_rows(now=None):
    now = time.time() if now is None else now
    runs, approvals = _runs_and_approvals()
    by_job = {}
    for rowid, run_id, cid, stage, provider, status, started, ended, error, retries in runs:
        row = {"rowId": rowid, "runId": run_id, "stage": stage, "provider": provider,
               "status": status, "started": started, "ended": ended,
               "seconds": round((ended or now) - started, 1), "error": error or "",
               "retries": retries or 0}
        stages = by_job.setdefault(cid, {})
        history = list(stages.get(stage, {}).get("attempts", []))
        history.append(dict(row))
        row["attempts"] = history
        row["attemptCount"] = len(history)
        stages[stage] = row
    approval_rows = {}
    for cid, gate, by, at, note, digest in approvals:
        approval_rows.setdefault(cid, {}).setdefault(gate, []).append(
            {"by": by, "at": at, "note": note, "digest": digest}
        )
    return by_job, approval_rows


def _status(stages, directory, now):
    latest = max(stages.values(), key=lambda row: row["rowId"], default=None)
    if latest:
        status = latest["status"]
        if status == "RUNNING" and now - latest["started"] > 600:
            status = "RUNNING" if storage.lock_is_held(directory / ".run.lock") else "STALE"
        if status == "BLOCKED":
            return "BLOCKED"
        if status == "FAIL":
            return "FAILED"
        if status in ("RUNNING", "STALE"):
            return status
    manifest = storage.read_manifest(directory) or {}
    if manifest.get("status") == "exported":
        return "EXPORTED"
    if manifest.get("status") == "ready" or stages.get("render", {}).get("status") == "OK":
        return "RENDERED"
    return "PENDING"


def jobs_state(*, now=None):
    now = time.time() if now is None else now
    by_job, approvals = _job_rows(now)
    result = []
    for directory in storage.iter_job_dirs():
        manifest = storage.read_manifest(directory) or {}
        cid = directory.name
        stages = by_job.get(cid, {})
        latest = max(stages.values(), key=lambda row: row["rowId"], default={})
        state = _status(stages, directory, now)
        if _supervised(cid):
            state = "RUNNING"
        block = _block_state(stages)
        run_result = _ui_run_result(directory)
        updated = latest.get("ended") or latest.get("started") or directory.stat().st_mtime
        workflow = _workflow_summary(cid, state, stages, block, run_result, updated, now=now)
        track = "B" if manifest.get("track") == "B" else "A"
        if track == "B" and state != "RUNNING":
            workflow = {**workflow, "nextAction": track_b.next_action(cid, directory)}
        result.append({
            "schema": JOB_VIEW_SCHEMA, "schemaVersion": 1,
            "id": cid,
            "track": track,
            "title": manifest.get("title") or cid,
            "format": manifest.get("aspect_ratio"),
            "state": state,
            "draft": False,
            "updated": updated,
            "hasVideo": (directory / "video.mp4").is_file(),
            "stages": stage_rows(directory, stages, manifest),
            "approvals": approvals.get(cid, {}),
            "block": block,
            "blocked_reason": block["reason"],
            "gate": block["gate"],
            **workflow,
            "recovery": _recovery_hint(state, block, run_result.get("failure")),
        })
    known = {job["id"] for job in result}
    specs_dir = storage.workspace_root() / "specs"
    for path in sorted(specs_dir.glob("*.yaml")) if specs_dir.is_dir() else []:
        spec = _json_or_yaml(path)
        cid = spec.get("content_id") if isinstance(spec, dict) else None
        if not cid or cid in known or not storage.valid_job_id(cid):
            continue
        draft_state = "RUNNING" if _supervised(cid) else "DRAFT"
        workflow = _workflow_summary(
            cid, draft_state, {}, {}, {"attempts": 0, "retries": 0}, path.stat().st_mtime, now=now
        )
        result.append({
            "schema": JOB_VIEW_SCHEMA, "schemaVersion": 1,
            "id": cid, "track": "A", "title": spec.get("title") or cid, "format": spec.get("format"),
            "state": draft_state, "updated": path.stat().st_mtime, "updated_at": path.stat().st_mtime,
            "draft": True, "hasVideo": False,
            "stages": [{"stage": stage, "status": "PENDING", "attempts": [], "attemptCount": 0}
                       for stage in pipeline.STAGES],
            "approvals": {}, "block": {"blocked": False, "stage": None, "gate": None, "reason": None},
            "blocked_reason": None, "gate": None, **workflow,
            "recovery": _recovery_hint("DRAFT", {}, None),
        })
    result.sort(key=lambda job: (-job["updated"], job["id"]))
    return result


def stage_rows(directory, rows, manifest=None):
    manifest = manifest or storage.read_manifest(directory) or {}
    result = []
    for stage in pipeline.STAGES:
        row = dict(rows.get(stage) or {})
        declared = (manifest.get("artifacts") or {}).get(stage, [])
        recorded = isinstance(declared, list) and bool(declared)
        present = recorded and all(_artifact_path(directory, name) is not None for name in declared)
        row.update(
            stage=stage,
            status=row.get("status") or ("DONE" if present else "PENDING"),
            attempts=row.get("attempts", []),
            attemptCount=row.get("attemptCount", 0),
            artifactRecorded=recorded,
            artifactPresent=present,
        )
        result.append(row)
    return result


def _artifact_path(directory, relative):
    if not isinstance(relative, str) or not relative:
        return None
    try:
        source = directory / relative
        if source.is_symlink():
            return None
        candidate = source.resolve()
        candidate.relative_to(directory.resolve())
    except (OSError, ValueError):
        return None
    return candidate if candidate.is_file() and not candidate.is_symlink() else None


def _artifacts(directory, manifest):
    records = {}
    declared = manifest.get("artifacts")
    if isinstance(declared, dict):
        for stage, names in declared.items():
            if not isinstance(stage, str) or not isinstance(names, list):
                continue
            for name in names:
                path = _artifact_path(directory, name)
                if path is not None:
                    records[name] = {
                        "name": Path(name).name, "path": name, "stage": stage,
                        "size": path.stat().st_size, "status": "AVAILABLE",
                        "provenance": "job manifest",
                    }
    for name in ("script.md", "script-lint.json", "video.mp4", "qa.json", "metadata.yaml",
                 "look.json", "critic-report.json", "delivery/critic-report.json",
                 "publish-result.json", "export-result.json", "logs/ui-run-result.json"):
        path = _artifact_path(directory, name)
        if path is not None and name not in records:
            records[name] = {
                "name": Path(name).name, "path": name, "stage": None,
                "size": path.stat().st_size, "status": "AVAILABLE",
                "provenance": "workspace artifact",
            }
    return list(records.values())


def _ui_run_result(directory):
    path = directory / "logs" / "ui-run-result.json"
    if not path.is_file() or path.is_symlink():
        return {
            "status": "NOT_RUN", "attempts": 0, "retries": 0,
            "failure": None, "provenance": None,
        }
    value = _json(path, None)
    if not isinstance(value, dict) or not isinstance(value.get("status", value.get("ok")), (str, bool)):
        return {
            "status": "INVALID", "attempts": 0, "retries": 0,
            "failure": {"class": "invalid-result", "stage": None,
                        "error": "ui-run-result.json is malformed"},
            "provenance": "logs/ui-run-result.json",
        }
    attempts = value.get("attempts", 1)
    attempts = attempts if isinstance(attempts, int) and attempts > 0 else 1
    ok = value.get("ok")
    process_error = value.get("status") == "PROCESS_ERROR"
    failure = None
    if ok is False or process_error:
        failure = {
            "class": value.get("failureClass") or ("process" if process_error else None),
            "stage": value.get("stage"),
            "error": value.get("error"),
            "returncode": value.get("returncode"),
        }
    return {
        "status": "SUCCEEDED" if ok is True else ("FAILED" if failure else "COMPLETED"),
        "ok": ok,
        "attempts": attempts,
        "retries": max(0, attempts - 1),
        "elapsedSeconds": value.get("elapsedS"),
        "failure": failure,
        "provenance": "logs/ui-run-result.json",
    }


def _visual_quality(directory):
    path = directory / "look.json"
    value = _json(path, None) if path.is_file() and not path.is_symlink() else None
    if not isinstance(value, dict) or value.get("schema") != "look/1":
        return {"status": "NOT_RUN", "provenance": None}
    verdict = value.get("verdict")
    if not isinstance(verdict, dict) or not isinstance(verdict.get("ok"), bool):
        return {
            "status": "INVALID", "provenance": "look.json",
            "detail": "Persisted look report is malformed",
        }
    return {
        "status": "PASS" if verdict["ok"] else "FAIL",
        "provenance": "look.json (persisted visual-language check)",
        "detail": value.get("reason"),
        "schema": value["schema"],
        "verdict": verdict,
    }


def _critic_quality(directory):
    for relative in ("delivery/critic-report.json", "critic-report.json"):
        path = directory / relative
        if not path.is_file() or path.is_symlink():
            continue
        value = _json(path, None)
        if not isinstance(value, dict):
            return {
                "status": "INVALID", "provenance": relative,
                "detail": "Persisted critic report is malformed",
            }
        checked = critic.check(value)
        return {
            "status": "INVALID" if not checked["ok"] else
                      ("PASS" if value.get("verdict") == "pass" else
                       ("FAIL" if value.get("verdict") == "reject" else "WARNING")),
            "provenance": relative,
            "verdict": value.get("verdict"),
            "computedVerdict": checked.get("computed_verdict"),
            "valid": checked["ok"],
            "problems": checked["problems"],
        }
    return {"status": "NOT_RUN", "provenance": None}


def _export_state(directory, manifest):
    recorded = manifest.get("export")
    result = _json(directory / "export-result.json", None)
    if manifest.get("status") == "exported" and isinstance(recorded, dict):
        return {"status": "EXPORTED", "record": recorded, "provenance": "job manifest"}
    if isinstance(recorded, dict) and recorded.get("status") == "failed":
        return {"status": "FAILED", "record": recorded, "provenance": "job manifest"}
    if isinstance(result, dict):
        return {"status": str(result.get("status") or "RECORDED").upper(),
                "record": result, "provenance": "export-result.json"}
    return {
        "status": "READY" if (manifest.get("status") == "ready" and
                              _artifact_path(directory, "video.mp4")) else "NOT_READY",
        "record": None, "provenance": None,
    }


def _block_state(rows):
    latest = max(rows.values(), key=lambda row: row["rowId"], default=None)
    if not latest or latest["status"] != "BLOCKED":
        return {"blocked": False, "stage": None, "gate": None, "reason": None}
    stage = latest["stage"]
    return {
        "blocked": True,
        "stage": stage,
        "gate": pipeline.GATE_OF.get(stage),
        "reason": latest.get("error") or "Pipeline stage is blocked",
    }


def _recovery_hint(state, block, failure):
    can_resume = state in ("DRAFT", "PENDING", "BLOCKED", "FAILED", "STALE", "RENDERED")
    if state == "STALE":
        message = "No run lock is held; resume will scrub interrupted artifacts before continuing"
    elif state == "BLOCKED":
        message = "Resolve the blocking gate or prerequisite, then resume"
    elif state == "FAILED":
        message = "Inspect the failure before resuming through the production core"
    else:
        message = "Run or resume from the next incomplete stage" if can_resume else None
    return {
        "canResume": can_resume,
        "cleanupOnResume": state == "STALE",
        "message": message,
        "blockedStage": block.get("stage"),
        "failedStage": (failure or {}).get("stage"),
    }


def _spec_for(manifest):
    source = manifest.get("source_spec")
    if not source:
        return {}
    try:
        value = yaml.safe_load(Path(source).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def _json_or_yaml(path):
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def _draft_spec_record(content_id):
    root = storage.workspace_root() / "specs"
    for suffix in (".yaml", ".yml", ".json"):
        path = root / f"{content_id}{suffix}"
        if path.is_file():
            spec = _json_or_yaml(path)
            if spec.get("content_id") == content_id:
                return spec, path
    return None, None


def _draft_spec(content_id):
    return _draft_spec_record(content_id)[0]


def job_state(content_id, *, now=None):
    if not storage.valid_job_id(content_id):
        return None
    directory = storage.find_job_dir(content_id)
    if directory is None:
        spec, spec_path = _draft_spec_record(content_id)
        if spec is None:
            return None
        updated = spec_path.stat().st_mtime
        publish = _publish_state()
        platform_budget = _platform_budget({}, spec)
        state = "RUNNING" if _supervised(content_id) else "DRAFT"
        workflow = _workflow_summary(
            content_id, state, {}, {}, {"attempts": 0, "retries": 0}, updated, now=now or time.time()
        )
        return {
            "schema": JOB_VIEW_SCHEMA, "schemaVersion": 1,
            "id": content_id, "track": "A", "title": spec.get("title") or content_id, "format": spec.get("format"),
            "state": state, "draft": True, "updated": updated, "updated_at": updated,
            "manifest": {"status": "draft", "title": spec.get("title"), "renderer": "hyperframes",
                         "aspect_ratio": spec.get("format")},
            "stages": [
                {"stage": stage, "status": "PENDING", "attempts": [], "attemptCount": 0,
                 "artifactRecorded": False, "artifactPresent": False}
                for stage in pipeline.STAGES
            ],
            "approvals": {
                "SCRIPT_APPROVED": {"state": "none", "currentDigest": None, "approved": False},
                "PRODUCTION_APPROVED": {"state": "none", "currentDigest": None, "approved": False},
            },
            "approvalHistory": {}, "spec": spec, "script": spec.get("script", []),
            "scriptMarkdown": None, "scriptLint": None, "script_lint": None, "qa": [],
            "quality": {"pipeline": [], "visualGate": {"status": "NOT_RUN"},
                        "critic": {"status": "NOT_RUN"}},
            "artifacts": [], "previews": [], "preview": {"frames": []}, "hasVideo": False,
            "block": {"blocked": False, "stage": None, "gate": None, "reason": None},
            "blocked_reason": None, "gate": None,
            "uiRunResult": {"status": "NOT_RUN", "attempts": 0, "retries": 0,
                            "failure": None, "provenance": None},
            **workflow,
            "failure": None,
            "recovery": _recovery_hint("DRAFT", {}, None),
            "platformBudget": platform_budget,
            "publishing": publish,
            "export": {"status": "NOT_READY", "record": None, "provenance": None},
            "artifactState": {"available": 0, "hasVideo": False, "exportStatus": "NOT_READY"},
        }
    now = time.time() if now is None else now
    by_job, approvals = _job_rows(now)
    rows = by_job.get(content_id, {})
    manifest = storage.read_manifest(directory) or {}
    track = "B" if manifest.get("track") == "B" else "A"
    spec = _spec_for(manifest)
    if track == "B":
        live = track_b.script_spec(directory)
        if live.get("script"):
            spec = live
    script_digest = pipeline.script_digest(spec) if spec.get("script") else None
    production_digest = pipeline.production_digest(directory, spec) if spec else None
    approval_state = {}
    for gate, digest in (("SCRIPT_APPROVED", script_digest), ("PRODUCTION_APPROVED", production_digest)):
        state, bound = ledger.check_gate(content_id, gate, digest)
        approval_state[gate] = {"state": state, "currentDigest": digest, "approvedDigests": bound}
        approval_state[gate].update(approved=state == "ok", digest=bound[-1] if bound else None)
    qa = _qa_rows(_json(directory / "qa.json", []))
    artifacts = _artifacts(directory, manifest)
    preview_dir = directory / "previews"
    previews = [path.name for path in sorted(preview_dir.glob("*.png"))] if preview_dir.is_dir() else []
    state = _status(rows, directory, now)
    if _supervised(content_id):
        state = "RUNNING"
    block = _block_state(rows)
    run_result = _ui_run_result(directory)
    latest = max(rows.values(), key=lambda row: row["rowId"], default={})
    failure = run_result.get("failure")
    if failure is None and latest.get("status") == "FAIL":
        failure = {
            "class": None, "stage": latest.get("stage"),
            "error": latest.get("error"), "provenance": "run ledger",
        }
    if failure is None and isinstance(manifest.get("failure"), dict):
        failure = {**manifest["failure"], "provenance": "job manifest"}
    visual_quality = _visual_quality(directory)
    critic_quality = _critic_quality(directory)
    export_state = _export_state(directory, manifest)
    has_video = _artifact_path(directory, "video.mp4") is not None
    updated = latest.get("ended") or latest.get("started") or 0
    workflow = _workflow_summary(content_id, state, rows, block, run_result, updated, now=now)
    if track == "B" and state != "RUNNING":
        workflow = {**workflow, "nextAction": track_b.next_action(content_id, directory)}
    return {
        "schema": JOB_VIEW_SCHEMA,
        "schemaVersion": 1,
        "id": content_id,
        "track": track,
        "title": manifest.get("title") or content_id,
        "format": manifest.get("aspect_ratio"),
        "state": state,
        "draft": False,
        "updated": updated,
        "updated_at": updated,
        "manifest": {key: manifest.get(key) for key in
                     ("status", "title", "renderer", "aspect_ratio", "final_output", "failure")},
        "stages": stage_rows(directory, rows, manifest),
        "approvals": approval_state,
        "approvalHistory": approvals.get(content_id, {}),
        "spec": {key: spec.get(key) for key in
                 ("content_id", "title", "format", "render", "voice", "kind",
                  "platform_targets", "script")},
        "script": spec.get("script", []),
        "scriptMarkdown": (directory / "script.md").read_text(encoding="utf-8") if (directory / "script.md").is_file() else None,
        "scriptLint": _json(directory / "script-lint.json", None),
        "script_lint": _json(directory / "script-lint.json", None),
        "qa": qa,
        "quality": {
            "pipeline": qa,
            "visualGate": visual_quality,
            "critic": critic_quality,
        },
        "artifacts": artifacts,
        "previews": previews,
        "preview": {"frames": previews},
        "hasVideo": has_video,
        "block": block,
        "blocked_reason": block["reason"],
        "gate": block["gate"],
        "uiRunResult": run_result,
        **workflow,
        "failure": failure,
        "recovery": _recovery_hint(state, block, failure),
        "platformBudget": _platform_budget(manifest, spec),
        "publishing": _publish_state(),
        "export": export_state,
        **({"trackB": track_b.evidence(directory, manifest)} if track == "B" else {}),
        "artifactState": {
            "available": len(artifacts),
            "hasVideo": has_video,
            "exportStatus": export_state["status"],
        },
    }
