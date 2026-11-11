import http.client
import json
import threading
from contextlib import contextmanager

import pytest

from contentos import dashboard, ledger, specs, storage, ui_api, ui_state
from contentos.production import critic


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "publishing"))
    storage.preflight()
    ui_state._health_cache.update(at=0, value=None)
    return tmp_path


@contextmanager
def server():
    instance = dashboard.make_server(0)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield instance, instance.server_address[1]
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=2)


def request(port, method, path, *, headers=None, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response, data


def write_headers(token="token"):
    return {"Host": "127.0.0.1:4310", "Origin": "http://127.0.0.1:4310",
            "X-ContentOS-Token": token}


def valid_spec(content_id="ui-spec"):
    return {
        "content_id": content_id, "title": "Local creator job", "format": "9:16",
        "voice": "af_heart", "render": "hyperframes",
        "script": [{"headline": "Start", "say": "This stays on the local machine."}],
    }


def test_health_treats_dead_ffmpeg_as_unavailable(workspace, monkeypatch):
    monkeypatch.setattr(ui_state.providers, "load", lambda name: {
        "capabilities": {"render": {}}
    } if name == "providers.yaml" else {"publish": {"enabled": False}})
    monkeypatch.setattr(ui_state.providers, "candidates", lambda capability: [])

    def dead(*args, **kwargs):
        raise OSError(86, "Bad CPU type in executable")

    monkeypatch.setattr(ui_state.subprocess, "run", dead)
    health = ui_state.health_state(refresh=True)
    assert health["tools"]["ffmpeg"]["status"] == "NOT_INSTALLED"
    assert {item["id"] for item in health["runReadiness"]["blockers"]} == {
        "kokoro_local", "hyperframes", "ffmpeg",
    }
    assert health["publish"] == {"enabled": False}
    assert health["storage"][0]["writable"] is True


def test_track_a_readiness_ignores_unneeded_capabilities_and_fallbacks(workspace, monkeypatch):
    capability_names = ("tts", "stt", "render", "llm", "youtube_read", "publish_youtube", "decision")
    candidates = {
        "tts": [
            {"id": "kokoro_local", "tier": "local_oss", "rank": 0, "quality": 3,
             "healthy": True, "detail": "ready"},
            {"id": "chatterbox_mlx", "tier": "local_oss", "rank": 0, "quality": 4,
             "healthy": False, "detail": "optional fallback missing"},
        ],
        "render": [
            {"id": "hyperframes", "tier": "local_oss", "rank": 0, "quality": 4,
             "healthy": True, "detail": "ready"},
            {"id": "mpt", "tier": "local_oss", "rank": 0, "quality": 3,
             "healthy": False, "detail": "unused lane missing"},
        ],
    }
    monkeypatch.setattr(ui_state.providers, "load", lambda name: {
        "capabilities": {name: {} for name in capability_names}
    } if name == "providers.yaml" else {"publish": {"enabled": False}})
    monkeypatch.setattr(
        ui_state.providers, "candidates",
        lambda capability: candidates.get(capability, []),
    )
    monkeypatch.setattr(ui_state, "_tool", lambda name: {"status": "PASS", "detail": "ready"})

    health = ui_state.health_state(refresh=True)
    assert health["runReadiness"]["ready"] is True
    assert health["runReadiness"]["blockers"] == []
    assert health["runReadiness"]["requiredProviders"] == {
        "tts": "kokoro_local", "render": "hyperframes",
    }
    assert next(item for item in health["capabilities"] if item["name"] == "stt")["requiredForRun"] is False


def test_track_a_readiness_requires_hyperframes_not_an_alternate_render_lane(workspace, monkeypatch):
    monkeypatch.setattr(ui_state.providers, "load", lambda name: {
        "capabilities": {"tts": {}, "render": {}}
    } if name == "providers.yaml" else {"publish": {"enabled": False}})
    monkeypatch.setattr(ui_state.providers, "candidates", lambda capability: {
        "tts": [{"id": "kokoro_local", "tier": "local_oss", "rank": 0, "quality": 3,
                 "healthy": True, "detail": "ready"}],
        "render": [
            {"id": "hyperframes", "tier": "local_oss", "rank": 0, "quality": 4,
             "healthy": False, "detail": "missing"},
            {"id": "mpt", "tier": "local_oss", "rank": 0, "quality": 3,
             "healthy": True, "detail": "ready"},
        ],
    }[capability])
    monkeypatch.setattr(ui_state, "_tool", lambda name: {"status": "PASS", "detail": "ready"})

    readiness = ui_state.health_state(refresh=True)["runReadiness"]
    assert readiness["ready"] is False
    assert [item["id"] for item in readiness["blockers"]] == ["hyperframes"]


def test_track_a_readiness_requires_both_pipeline_storage_roots():
    capabilities = [
        {"name": "tts", "candidates": [{"id": "kokoro_local", "healthy": True}]},
        {"name": "render", "candidates": [{"id": "hyperframes", "healthy": True}]},
    ]
    tools = {"ffmpeg": {"status": "PASS"}}
    roots = [
        {"label": "workspace", "writable": True},
        {"label": "publishing", "writable": False, "detail": "directory is not writable"},
    ]
    readiness = ui_state._run_readiness(capabilities, tools, roots)
    assert readiness["ready"] is False
    assert readiness["blockers"] == [{
        "kind": "storage", "id": "publishing", "label": "publishing",
        "detail": "directory is not writable",
    }]


def test_dispatch_rejects_invalid_host_and_cross_origin_write(workspace):
    assert ui_api.dispatch("GET", "/api/v1/jobs", {"Host": "attacker.test"}, b"", "token").status == 421
    denied = ui_api.dispatch(
        "POST", "/api/v1/specs/validate",
        {"Host": "127.0.0.1:4310", "Origin": "http://localhost:4310",
         "X-ContentOS-Token": "token"},
        b"{}", "token",
    )
    assert denied.status == 403


def test_dashboard_serves_shell_injects_token_and_keeps_legacy_state(workspace, monkeypatch):
    monkeypatch.setattr(dashboard, "_health", lambda: ({}, {}))
    with server() as (instance, port):
        response, body = request(port, "GET", "/")
        assert response.status == 200
        assert instance.ui_token.encode() in body
        assert b"__CONTENTOS_TOKEN__" not in body
        response, body = request(port, "GET", "/ui/styles.css")
        assert response.status == 200
        assert b"--bg:" in body

        response, body = request(port, "GET", "/api/state")
        assert response.status == 200
        assert "contents" in json.loads(body)


def test_dashboard_rejects_host_header_and_traversal(workspace):
    with server() as (_, port):
        response, _ = request(port, "GET", "/api/v1/jobs", headers={"Host": "evil.example"})
        assert response.status == 421
        response, _ = request(port, "GET", "/media/../video.mp4")
        assert response.status == 404


def test_media_streams_valid_ranges_and_rejects_unsatisfiable_ranges(workspace):
    directory = storage.job_dir("range-test")
    (directory / "video.mp4").write_bytes(b"0123456789")
    with server() as (_, port):
        response, body = request(port, "GET", "/media/range-test/video.mp4",
                                 headers={"Range": "bytes=2-5"})
        assert response.status == 206
        assert response.getheader("Content-Range") == "bytes 2-5/10"
        assert body == b"2345"

        response, body = request(port, "GET", "/media/range-test/video.mp4",
                                 headers={"Range": "bytes=99-"})
        assert response.status == 416
        assert body == b""


def test_write_requires_exact_token_and_origin(workspace):
    with server() as (instance, port):
        headers = {
            "Origin": f"http://127.0.0.1:{port}",
            "X-ContentOS-Token": instance.ui_token,
            "Content-Type": "application/json",
        }
        response, body = request(port, "POST", "/api/v1/specs/validate",
                                 headers=headers, body=b"{")
        assert response.status == 400
        assert json.loads(body)["error"]["code"] == "INVALID_JSON"


def test_jobs_state_skips_a_legacy_project_manifest(workspace):
    legacy = storage.job_dir("legacy-pilot")
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "manifest.json").write_text(json.dumps({"schema": "project-manifest/1", "title": "Pilot"}))
    real = storage.job_dir("real-job")
    real.mkdir(parents=True, exist_ok=True)
    storage.write_manifest(real, storage.new_manifest("real-job", title="Real job"))
    assert [job["id"] for job in ui_state.jobs_state()] == ["real-job"]


def test_spec_validate_create_collision_and_draft_read_model(workspace):
    payload = json.dumps(valid_spec()).encode()
    validated = ui_api.dispatch("POST", "/api/v1/specs/validate", write_headers(), payload, "token")
    assert validated.status == 200
    assert validated.body["valid"] is True

    created = ui_api.dispatch("POST", "/api/v1/specs", write_headers(), payload, "token")
    assert created.status == 201
    assert created.body["status"] == "SAVED"
    assert any(job["id"] == "ui-spec" and job["state"] == "DRAFT" for job in ui_state.jobs_state())
    draft = ui_state.job_state("ui-spec")
    assert draft["script"][0]["headline"] == "Start"
    assert draft["schema"] == "creator-studio/job/1"
    assert draft["state"] == "DRAFT"
    assert draft["draft"] is True
    assert draft["updated_at"] > 0
    assert draft["publishing"]["status"] == "DISABLED"
    assert draft["platformBudget"]["status"] == "NOT_AVAILABLE"

    changed = valid_spec()
    changed["title"] = "Changed"
    collision = ui_api.dispatch("POST", "/api/v1/specs", write_headers(),
                                json.dumps(changed).encode(), "token")
    assert collision.status == 409
    assert collision.body["error"]["details"] == {
        "contentId": "ui-spec", "recoverable": True,
    }


def test_authoring_validation_returns_canonical_budget_and_lint_summary(workspace):
    spec = {
        **valid_spec("budgeted-job"),
        "kind": "short",
        "platform_targets": ["youtube", "instagram"],
    }
    response = ui_api.dispatch(
        "POST", "/api/v1/specs/validate", write_headers(),
        json.dumps(spec).encode(), "token",
    )
    assert response.status == 200
    assert response.body["valid"] is True
    assert response.body["summary"]["status"] == "PASS"
    assert response.body["summary"]["narration"]["word_count"] == 6
    from contentos.production import platforms
    expected = platforms.budget(
        platforms.load(), "short", platforms=["youtube", "instagram"],
        owner_max=platforms.owner_limits()["short"],
    )
    assert response.body["summary"]["platformBudget"]["max_seconds"] == expected["max_seconds"]


def test_job_progress_event_is_an_invalidation_hint(workspace):
    specs.save_spec(valid_spec("event-job"))
    with server() as (_, port):
        response, body = request(port, "GET", "/api/v1/jobs/event-job/events?once=1")
    assert response.status == 200
    assert response.getheader("Content-Type") == "text/event-stream; charset=utf-8"
    assert b"event: progress\n" in body
    payload = json.loads(next(
        line.removeprefix(b"data: ") for line in body.splitlines()
        if line.startswith(b"data: ")
    ))
    assert payload["contentId"] == "event-job"
    assert payload["state"] == "DRAFT"
    assert payload["activeRun"] is False
    assert set(payload) == {
        "contentId", "state", "updated", "activeRun", "nextAction", "revision",
    }


def test_approval_is_digest_bound_and_publish_gate_is_not_exposed(workspace):
    spec = valid_spec("approval-job")
    path = specs.save_spec(spec)
    directory, _ = storage.open_job("approval-job", spec)
    storage.update_manifest(directory, source_spec=str(path))
    (directory / "script.md").write_text("# reviewed", encoding="utf-8")
    digest = ui_state.job_state("approval-job")["approvals"]["SCRIPT_APPROVED"]["currentDigest"]

    mismatch = ui_api.dispatch(
        "POST", "/api/v1/jobs/approval-job/approve", write_headers(),
        json.dumps({"gate": "SCRIPT_APPROVED", "seenDigest": "old"}).encode(), "token",
    )
    assert mismatch.status == 409
    approved = ui_api.dispatch(
        "POST", "/api/v1/jobs/approval-job/approve", write_headers(),
        json.dumps({"gate": "SCRIPT_APPROVED", "seenDigest": digest}).encode(), "token",
    )
    assert approved.status == 200
    assert ui_state.job_state("approval-job")["approvals"]["SCRIPT_APPROVED"]["approved"] is True

    publish = ui_api.dispatch(
        "POST", "/api/v1/jobs/approval-job/approve", write_headers(),
        json.dumps({"gate": "PUBLISH_APPROVED", "seenDigest": digest}).encode(), "token",
    )
    assert publish.status == 400


def test_stage_log_is_bounded_and_scrubs_secrets(workspace, monkeypatch):
    monkeypatch.setenv("UI_TEST_SECRET_TOKEN", "never-return-this-secret")
    spec = valid_spec("log-job")
    directory, _ = storage.open_job("log-job", spec)
    logs = directory / "logs"
    logs.mkdir()
    (logs / "script.log").write_text(
        "x" * 210_000 + "\nauthorization: never-return-this-secret\nBearer another-secret\n",
        encoding="utf-8",
    )
    response = ui_api.dispatch("GET", "/api/v1/jobs/log-job/stages/script/log",
                               {"Host": "localhost"}, b"", "token")
    assert response.status == 200
    assert len(response.body["text"]) <= 200_000
    assert "never-return-this-secret" not in response.body["text"]
    assert "another-secret" not in response.body["text"]


def test_run_route_uses_saved_workspace_spec_without_approval_shortcuts(workspace, monkeypatch):
    path = specs.save_spec(valid_spec("run-job"))
    captured = {}

    class StubSupervisor:
        def start(self, content_id, spec_path):
            captured.update(content_id=content_id, spec_path=spec_path)
            return {"contentId": content_id, "status": "STARTED", "pid": 7}

    monkeypatch.setattr(ui_api, "SUPERVISOR", StubSupervisor())
    response = ui_api.dispatch("POST", "/api/v1/jobs/run-job/run", write_headers(), b"{}", "token")
    assert response.status == 202
    assert captured == {"content_id": "run-job", "spec_path": path}


def test_preview_is_bounded_and_records_only_job_local_evidence(workspace, monkeypatch):
    spec = valid_spec("preview-job")
    directory, _ = storage.open_job("preview-job", spec)
    (directory / "video.mp4").write_bytes(b"fixture")
    captured = {}

    def fake_frames(video, times, output, prefix):
        captured.update(video=video, times=times, output=output, prefix=prefix)
        frame = output / "frame-001.png"
        frame.write_bytes(b"png")
        return [frame]

    monkeypatch.setattr(ui_api.preview, "video_frames", fake_frames)
    response = ui_api.dispatch(
        "POST", "/api/v1/jobs/preview-job/preview", write_headers(),
        json.dumps({"times": [0, 2.5]}).encode(), "token",
    )
    assert response.status == 200
    assert captured["output"] == directory / "previews"
    assert response.body == {"previews": ["frame-001.png"]}

    excessive = ui_api.dispatch(
        "POST", "/api/v1/jobs/preview-job/preview", write_headers(),
        json.dumps({"times": list(range(13))}).encode(), "token",
    )
    assert excessive.status == 400


def test_qa_rows_include_pipeline_provenance_and_absent_checks_are_not_run(workspace):
    spec = valid_spec("qa-job")
    directory, _ = storage.open_job("qa-job", spec)
    (directory / "qa.json").write_text(
        json.dumps([["render_integrity", "PASS", "12.0s"]]), encoding="utf-8"
    )
    detail = ui_state.job_state("qa-job")
    assert detail["qa"] == [{
        "name": "render_integrity", "status": "PASS", "detail": "12.0s",
        "provenance": "pipeline qa stage",
    }]
    assert detail["quality"]["visualGate"]["status"] == "NOT_RUN"
    assert detail["quality"]["critic"]["status"] == "NOT_RUN"


def test_capabilities_are_read_only_and_use_canonical_registries(workspace):
    response = ui_api.dispatch(
        "GET", "/api/v1/capabilities", {"Host": "localhost"}, b"", "token"
    )
    assert response.status == 200
    body = response.body
    assert body["schema"] == "creator-studio/capabilities/1"
    assert body["voices"] == json.loads(specs.VOICE_IDS_FILE.read_text(encoding="utf-8"))
    assert body["renderLanes"] == ["hyperframes"]
    assert body["actions"]["runOrResume"] is True
    assert body["actions"]["publish"] is False
    assert body["actions"]["allowPaid"] is False
    assert body["publish"]["status"] == "DISABLED"
    assert body["platformLimits"]["status"] == "AVAILABLE"
    assert body["platformLimits"]["budgets"]["short"]["max_seconds"] == 140


def test_job_state_transitions_do_not_infer_success_from_file_presence(workspace):
    spec = valid_spec("transition-job")
    directory, _ = storage.open_job("transition-job", spec)
    now = 10_000

    assert ui_state._status({}, directory, now) == "PENDING"
    (directory / "video.mp4").write_bytes(b"not evidence of a successful render")
    assert ui_state._status({}, directory, now) == "PENDING"
    assert ui_state._status({
        "render": {"rowId": 1, "status": "OK", "started": now - 1}
    }, directory, now) == "RENDERED"
    assert ui_state._status({
        "render": {"rowId": 1, "status": "RUNNING", "started": now - 1}
    }, directory, now) == "RUNNING"
    assert ui_state._status({
        "render": {"rowId": 1, "status": "RUNNING", "started": now - 700}
    }, directory, now) == "STALE"
    assert ui_state._status({
        "voice": {"rowId": 1, "status": "BLOCKED", "started": now - 1}
    }, directory, now) == "BLOCKED"
    assert ui_state._status({
        "qa": {"rowId": 1, "status": "FAIL", "started": now - 1}
    }, directory, now) == "FAILED"
    storage.update_manifest(directory, status="exported")
    assert ui_state._status({}, directory, now) == "EXPORTED"


def test_job_read_model_exposes_block_retries_recovery_quality_and_export(workspace):
    spec = valid_spec("read-model-job")
    path = specs.save_spec(spec)
    directory, _ = storage.open_job("read-model-job", spec)
    storage.update_manifest(
        directory,
        source_spec=str(path),
        kind="short",
        platform_targets=["youtube", "instagram"],
        artifacts={"qa": ["qa.json"], "render": ["video.mp4"]},
        export={"status": "failed", "reason": "validation failed"},
    )
    (directory / "video.mp4").write_bytes(b"fixture")
    (directory / "qa.json").write_text(
        json.dumps([["render_integrity", "PASS", "fixture"]]), encoding="utf-8"
    )
    (directory / "look.json").write_text(json.dumps({
        "schema": "look/1",
        "verdict": {"ok": True, "duplicates": [], "refused": None},
        "reason": None,
    }), encoding="utf-8")
    scores = {dimension: 9 for dimension in critic.DIMENSIONS}
    (directory / "critic-report.json").write_text(json.dumps({
        "critic": "independent", "verdict": "pass", "scores": scores,
        "hard_failures": [], "notes": [],
    }), encoding="utf-8")
    logs = directory / "logs"
    logs.mkdir()
    (logs / "ui-run-result.json").write_text(json.dumps({
        "ok": False, "failureClass": "blocked", "stage": "voice",
        "error": "voice blocked: SCRIPT_APPROVED gate not granted",
        "attempts": 3, "elapsedS": 4.5,
    }), encoding="utf-8")
    ledger.record(
        ledger.new_run_id(), "read-model-job", "voice", "kokoro", "FAIL", 90,
        error="temporary renderer failure", retries=1,
    )
    ledger.record(
        ledger.new_run_id(), "read-model-job", "voice", "-", "BLOCKED", 100,
        error="SCRIPT_APPROVED gate not granted",
    )

    detail = ui_state.job_state("read-model-job", now=200)
    assert detail["state"] == "BLOCKED"
    assert detail["block"] == {
        "blocked": True, "stage": "voice", "gate": "SCRIPT_APPROVED",
        "reason": "SCRIPT_APPROVED gate not granted",
    }
    assert detail["uiRunResult"]["attempts"] == 3
    assert detail["uiRunResult"]["retries"] == 2
    voice_stage = next(stage for stage in detail["stages"] if stage["stage"] == "voice")
    assert voice_stage["attemptCount"] == 2
    assert [attempt["status"] for attempt in voice_stage["attempts"]] == ["FAIL", "BLOCKED"]
    assert detail["failure"]["class"] == "blocked"
    assert detail["recovery"]["canResume"] is True
    assert detail["platformBudget"]["max_seconds"] == 180
    assert detail["quality"]["pipeline"][0]["provenance"] == "pipeline qa stage"
    assert detail["quality"]["visualGate"]["provenance"].startswith("look.json")
    assert detail["quality"]["critic"]["provenance"] == "critic-report.json"
    assert detail["export"]["status"] == "FAILED"
    assert detail["artifactState"]["hasVideo"] is True
    assert {item["path"] for item in detail["artifacts"]} >= {
        "video.mp4", "qa.json", "look.json", "critic-report.json",
        "logs/ui-run-result.json",
    }


def test_optional_persisted_reports_fail_closed_when_malformed(workspace):
    spec = valid_spec("malformed-reports")
    path = specs.save_spec(spec)
    directory, _ = storage.open_job("malformed-reports", spec)
    storage.update_manifest(directory, source_spec=str(path))
    (directory / "critic-report.json").write_text("{", encoding="utf-8")
    logs = directory / "logs"
    logs.mkdir()
    (logs / "ui-run-result.json").write_text("[]", encoding="utf-8")

    detail = ui_state.job_state("malformed-reports")
    assert detail["quality"]["critic"]["status"] == "INVALID"
    assert detail["uiRunResult"]["status"] == "INVALID"
    assert detail["uiRunResult"]["failure"]["class"] == "invalid-result"


def test_rerun_preview_and_confirmation_fail_closed(workspace, monkeypatch):
    spec = valid_spec("rerun-api")
    specs.save_spec(spec)
    storage.open_job("rerun-api", spec)
    captured = {}

    class StubSupervisor:
        def start(self, content_id, spec_path, only=None, force=False):
            captured.update(content_id=content_id, only=only, force=force)
            return {"contentId": content_id, "status": "STARTED", "pid": 9}

    monkeypatch.setattr(ui_api, "SUPERVISOR", StubSupervisor())
    preview = ui_api.dispatch("GET", "/api/v1/jobs/rerun-api/rerun?stage=render", {"Host": "127.0.0.1"}, b"", "token")
    assert preview.status == 200
    assert "qa" in preview.body["removesDownstream"]
    assert preview.body["revokesApprovals"] == []
    missing = ui_api.dispatch("POST", "/api/v1/jobs/rerun-api/rerun", write_headers(), b"{}", "token")
    assert missing.body["error"]["code"] == "CONFIRMATION_REQUIRED"
    publish = ui_api.dispatch(
        "POST", "/api/v1/jobs/rerun-api/rerun", write_headers(),
        json.dumps({"stage": "publish", "confirm": True, "force": True}).encode(), "token",
    )
    assert publish.body["error"]["code"] == "UNKNOWN_STAGE"
    started = ui_api.dispatch(
        "POST", "/api/v1/jobs/rerun-api/rerun", write_headers(),
        json.dumps({"stage": "compose", "confirm": True, "force": True}).encode(), "token",
    )
    assert started.status == 202
    assert captured == {"content_id": "rerun-api", "only": "compose", "force": True}
    assert started.body["revokesApprovals"] == ["PRODUCTION_APPROVED"]


def test_queue_and_export_reject_unconfirmed_or_forbidden_options(workspace, monkeypatch):
    spec = valid_spec("queue-api")
    specs.save_spec(spec)
    storage.open_job("queue-api", spec)
    denied = ui_api.dispatch("POST", "/api/v1/queue", {"Host": "127.0.0.1"}, b"{}", "token")
    assert denied.status == 403
    added = ui_api.dispatch(
        "POST", "/api/v1/queue", write_headers(),
        json.dumps({"contentId": "queue-api"}).encode(), "token",
    )
    assert added.status == 202
    duplicate = ui_api.dispatch(
        "POST", "/api/v1/queue", write_headers(),
        json.dumps({"contentId": "queue-api", "approvePrivate": True}).encode(), "token",
    )
    assert duplicate.body["error"]["code"] == "FORBIDDEN_OPTION"
    listed = ui_api.dispatch("GET", "/api/v1/queue", {"Host": "127.0.0.1"}, b"", "token")
    assert listed.body["jobs"][0]["contentId"] == "queue-api"
    unconfirmed = ui_api.dispatch("POST", "/api/v1/jobs/queue-api/export", write_headers(), b"{}", "token")
    assert unconfirmed.body["error"]["code"] == "CONFIRMATION_REQUIRED"
    def dead_qa(*_args, **_kwargs):
        raise OSError("ffmpeg missing")

    monkeypatch.setattr(ui_api, "run_qa", dead_qa)
    (storage.find_job_dir("queue-api") / "video.mp4").write_bytes(b"video")
    qa = ui_api.dispatch("POST", "/api/v1/jobs/queue-api/qa", write_headers(), b"{}", "token")
    assert qa.body["error"]["code"] == "QA_FAILED"


def test_new_routes_fail_closed_for_traversal_and_a_held_run_lock(workspace, monkeypatch):
    specs.save_spec(valid_spec("locked-job"))
    storage.open_job("locked-job", valid_spec("locked-job"))
    missing = ui_api.dispatch(
        "GET", "/api/v1/jobs/..%2Fsecret/rerun?stage=render",
        {"Host": "127.0.0.1"}, b"", "token",
    )
    assert missing.status == 404
    monkeypatch.setattr(storage, "lock_is_held", lambda _path: True)
    held = ui_api.dispatch("POST", "/api/v1/jobs/locked-job/run", write_headers(), b"{}", "token")
    assert held.status == 202
    assert held.body["status"] == "ALREADY_RUNNING"
    assert "pid" not in held.body or held.body["status"] == "ALREADY_RUNNING"
