import json
import os

import pytest

from contentos import ledger, storage, track_b, ui_api
from contentos.ui_state import job_state


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "publishing"))
    storage.preflight()
    return tmp_path


def headers():
    return {
        "Host": "127.0.0.1:4310",
        "Origin": "http://127.0.0.1:4310",
        "X-ContentOS-Token": "token",
    }


def post(path, payload=None):
    return ui_api.dispatch("POST", path, headers(), json.dumps(payload or {}).encode(), "token")


def get_job(job_id):
    response = ui_api.dispatch("GET", f"/api/v1/jobs/{job_id}", {"Host": "127.0.0.1"}, b"", "token")
    assert response.status == 200, response.body
    return response.body


def plant(job_id, *, composition=True, script=True, scene=None, video=False, track_a=False):
    directory = storage.job_dir(job_id)
    if composition:
        project = directory / "project"
        project.mkdir(exist_ok=True)
        (project / "index.html").write_text("<html><style>body{background:#111}</style></html>", encoding="utf-8")
    if script:
        (directory / "script.yaml").write_text(
            "title: Hand built\nformat: '9:16'\nscript:\n  - say: Hello from the workbench\n    headline: Hello\n",
            encoding="utf-8",
        )
    if scene is not None:
        (directory / "scene-plan.json").write_text(json.dumps(scene), encoding="utf-8")
    if video:
        (directory / "video.mp4").write_bytes(b"video")
    if track_a:
        storage.write_manifest(directory, storage.new_manifest(job_id, title="Track A", renderer="hyperframes"))
    return directory


def external_count(job_id):
    connection = ledger.db()
    try:
        return connection.execute(
            "SELECT COUNT(*) FROM runs WHERE content_id=? AND status='EXTERNAL'",
            (job_id,),
        ).fetchone()[0]
    finally:
        connection.close()


def test_track_a_job_is_unchanged_and_refuses_track_b_actions(workspace):
    plant("track-a-job", track_a=True)
    detail = job_state("track-a-job")
    assert detail["track"] == "A"
    assert detail["nextAction"]["kind"] == "run"
    assert "trackB" not in detail
    refused = post("/api/v1/jobs/track-a-job/track-b/intake")
    assert refused.status == 409
    assert refused.body["error"]["code"] == "TRACK_A_JOB"
    registered = post("/api/v1/jobs/track-a-job/track-b/register")
    assert registered.status == 409
    assert registered.body["error"]["code"] == "TRACK_A_JOB"
    capabilities = ui_api.dispatch("GET", "/api/v1/capabilities", {"Host": "127.0.0.1"}, b"", "token").body
    assert capabilities["trackB"]["compositionAuthoring"] is False
    assert capabilities["trackB"]["publish"] is False
    assert capabilities["trackB"]["allowPaid"] is False
    assert capabilities["trackB"]["approvePrivate"] is False
    assert capabilities["actions"]["publish"] is False
    run = post("/api/v1/jobs/track-a-job/run")
    assert run.body.get("error", {}).get("code") != "TRACK_B_JOB"


def test_path_traversal_and_caller_paths_are_rejected(workspace):
    plant("tb-path")
    escaped = post("/api/v1/jobs/../track-b/intake")
    assert escaped.status == 400
    assert escaped.body["error"]["code"] == "INVALID_JOB"
    forbidden = post("/api/v1/jobs/tb-path/track-b/intake", {"path": "/tmp/outside"})
    assert forbidden.status == 400
    assert forbidden.body["error"]["code"] == "FORBIDDEN_OPTION"
    assert storage.read_manifest(storage.find_job_dir("tb-path")) is None


def test_missing_composition_is_refused(workspace):
    plant("tb-missing", composition=False)
    response = post("/api/v1/jobs/tb-missing/track-b/intake")
    assert response.status == 409
    assert response.body["error"]["code"] == "MISSING_COMPOSITION"


def test_intake_before_a_video_exists(workspace):
    directory = plant("tb-intake", scene={"schema": "sceneplan/1", "scenes": [{"backdrop": "ink"}, {"backdrop": "paper"}]})
    before = (directory / "project" / "index.html").read_text(encoding="utf-8")
    response = post("/api/v1/jobs/tb-intake/track-b/intake")
    assert response.status == 200
    assert response.body["created"] is True
    again = post("/api/v1/jobs/tb-intake/track-b/intake")
    assert again.status == 200
    assert again.body["created"] is False
    manifest = storage.read_manifest(directory)
    assert manifest["track"] == "B"
    assert manifest.get("final_output") is None
    assert not (directory / "video.mp4").exists()
    assert external_count("tb-intake") == 0
    assert (directory / "project" / "index.html").read_text(encoding="utf-8") == before
    detail = get_job("tb-intake")
    assert detail["track"] == "B"
    assert detail["state"] != "RENDERED"
    assert detail["nextAction"]["kind"] == "script-review"
    assert detail["trackB"]["scenePlan"]["status"] == "PASS"
    assert detail["trackB"]["quality"]["critic"]["status"] == "NOT_RUN"


def test_invalid_scene_plan_is_refused(workspace):
    plant("tb-plan", scene={"schema": "other", "scenes": []})
    response = post("/api/v1/jobs/tb-plan/track-b/intake")
    assert response.status == 409
    assert response.body["error"]["code"] == "INVALID_SCENE_PLAN"


def test_register_after_a_valid_video_records_external_rows_once(workspace, monkeypatch):
    monkeypatch.setattr(
        "contentos.finalcheck.validate_video",
        lambda *args, **kwargs: {"status": "passed", "checks": []},
    )
    plant("tb-register", video=True)
    first = post("/api/v1/jobs/tb-register/track-b/register")
    assert first.status == 200
    assert first.body["created"] is True
    assert first.body["externalLedger"] is True
    assert external_count("tb-register") == 4
    second = post("/api/v1/jobs/tb-register/track-b/register")
    assert second.status == 200
    assert second.body["externalLedger"] is False
    assert external_count("tb-register") == 4
    detail = get_job("tb-register")
    assert detail["hasVideo"] is True
    assert detail["state"] != "RENDERED"
    render = next(stage for stage in detail["stages"] if stage["stage"] == "render")
    assert render["status"] == "EXTERNAL"


def test_intake_then_register_validates_without_replacing_a_real_render(workspace, monkeypatch):
    monkeypatch.setattr(
        "contentos.finalcheck.validate_video",
        lambda *args, **kwargs: {"status": "passed", "checks": []},
    )
    directory = plant("tb-rendered", video=True)
    assert post("/api/v1/jobs/tb-rendered/track-b/intake").status == 200
    ledger.record(ledger.new_run_id(), "tb-rendered", "render", "hyperframes", "OK", 1)
    registered = post("/api/v1/jobs/tb-rendered/track-b/register")
    assert registered.status == 200
    assert registered.body["externalLedger"] is False
    assert external_count("tb-rendered") == 0
    manifest = storage.read_manifest(directory)
    assert manifest["validation"]["status"] == "passed"
    assert manifest["final_output"] == "video.mp4"


def test_gate_order_digest_mismatch_and_render_leave_composition_untouched(workspace, monkeypatch):
    directory = plant("tb-gates")
    composition = (directory / "project" / "index.html").read_bytes()
    assert post("/api/v1/jobs/tb-gates/track-b/intake").status == 200
    blocked = post("/api/v1/jobs/tb-gates/track-b/voice")
    assert blocked.status == 409
    assert blocked.body["error"]["code"] == "GATE_REQUIRED"
    mismatch = post("/api/v1/jobs/tb-gates/approve", {"gate": "SCRIPT_APPROVED", "seenDigest": "stale"})
    assert mismatch.status == 409
    assert mismatch.body["error"]["code"] == "DIGEST_MISMATCH"
    digest = get_job("tb-gates")["approvals"]["SCRIPT_APPROVED"]["currentDigest"]
    approved = post("/api/v1/jobs/tb-gates/approve", {"gate": "SCRIPT_APPROVED", "seenDigest": digest})
    assert approved.status == 200

    def fake_voice(ctx):
        audio = ctx["dir"] / "audio"
        audio.mkdir(exist_ok=True)
        wav = audio / "01.wav"
        wav.write_bytes(b"RIFF")
        return "kokoro_local", [wav]

    monkeypatch.setattr("contentos.pipeline.s_voice", fake_voice)
    assert post("/api/v1/jobs/tb-gates/track-b/voice").status == 200
    assert (directory / "project" / "index.html").read_bytes() == composition
    monkeypatch.setattr("contentos.pipeline.words_for", lambda *args, **kwargs: [("Hello", 0.0, 0.2)])
    assert post("/api/v1/jobs/tb-gates/track-b/align").status == 200
    early = post("/api/v1/jobs/tb-gates/track-b/render")
    assert early.status == 409
    assert early.body["error"]["code"] == "GATE_REQUIRED"
    production = get_job("tb-gates")["approvals"]["PRODUCTION_APPROVED"]["currentDigest"]
    assert post("/api/v1/jobs/tb-gates/approve", {"gate": "PRODUCTION_APPROVED", "seenDigest": production}).status == 200

    def fake_render(ctx):
        video = ctx["dir"] / "video.mp4"
        video.write_bytes(b"video")
        return "hyperframes", [video]

    monkeypatch.setattr("contentos.pipeline.s_render", fake_render)
    rendered = post("/api/v1/jobs/tb-gates/track-b/render")
    assert rendered.status == 200
    assert (directory / "project" / "index.html").read_bytes() == composition
    assert post("/api/v1/jobs/tb-gates/run").status == 409
    assert post("/api/v1/jobs/tb-gates/run").body["error"]["code"] == "TRACK_B_JOB"
    assert post("/api/v1/jobs/tb-gates/rerun").body["error"]["code"] == "TRACK_B_JOB"


def test_stale_visual_evidence_and_separate_qa_results(workspace, monkeypatch):
    directory = plant("tb-qa", scene={"schema": "sceneplan/1", "scenes": [{"backdrop": "ink"}, {"backdrop": "paper"}]})
    assert post("/api/v1/jobs/tb-qa/track-b/intake").status == 200
    (directory / "video.mp4").write_bytes(b"video")
    monkeypatch.setattr("contentos.track_b.run_qa", lambda video, fmt: [("duration", "PASS", "local")])
    report = post("/api/v1/jobs/tb-qa/track-b/qa")
    assert report.status == 200
    assert report.body["technical"]["status"] == "PASS"
    assert report.body["technical"]["provenance"] == "qa.run_qa"
    assert report.body["visualPlan"]["provenance"] == "intelligence.visual.rule_a_from_plan"
    assert report.body["visualScenes"]["status"] == "NOT_RUN"
    assert report.body["critic"]["status"] == "NOT_RUN"
    (directory / "project" / "index.html").write_text("<html><style>body{background:#222}</style></html>", encoding="utf-8")
    detail = get_job("tb-qa")
    assert detail["trackB"]["quality"]["visualPlan"]["status"] == "STALE"
    assert detail["trackB"]["quality"]["critic"]["status"] == "NOT_RUN"


def test_export_refuses_when_either_grant_is_absent(workspace):
    plant("tb-export")
    assert post("/api/v1/jobs/tb-export/track-b/intake").status == 200
    (storage.find_job_dir("tb-export") / "video.mp4").write_bytes(b"video")
    missing = post("/api/v1/jobs/tb-export/export", {"confirm": True})
    assert missing.status == 409
    assert missing.body["error"]["code"] == "EXPORT_REFUSED"
    digest = get_job("tb-export")["approvals"]["SCRIPT_APPROVED"]["currentDigest"]
    assert post("/api/v1/jobs/tb-export/approve", {"gate": "SCRIPT_APPROVED", "seenDigest": digest}).status == 200
    one_gate = post("/api/v1/jobs/tb-export/export", {"confirm": True})
    assert one_gate.status == 409
    assert "PRODUCTION_APPROVED" in one_gate.body["error"]["message"]


def test_queue_cannot_send_track_b_through_production_run(workspace):
    plant("tb-queue")
    assert post("/api/v1/jobs/tb-queue/track-b/intake").status == 200
    queued = post("/api/v1/queue", {"contentId": "tb-queue"})
    assert queued.status == 409
    assert queued.body["error"]["code"] == "TRACK_B_JOB"


@pytest.mark.skipif(
    os.environ.get("CONTENTOS_TRACK_B_RENDER") != "1",
    reason="opt-in real Track B render; set CONTENTOS_TRACK_B_RENDER=1 and CONTENTOS_TRACK_B_JOB",
)
def test_opt_in_render_stops_before_publish(workspace):
    job_id = os.environ.get("CONTENTOS_TRACK_B_JOB")
    if not job_id:
        pytest.fail("CONTENTOS_TRACK_B_JOB must name an existing Track B job")
    result = track_b.render(job_id)
    assert result["status"] == "OK"
    directory = storage.find_job_dir(job_id)
    assert directory is not None
    assert not (directory / "publish-result.json").is_file()
    connection = ledger.db()
    try:
        published = connection.execute(
            "SELECT COUNT(*) FROM runs WHERE content_id=? AND stage='publish'",
            (job_id,),
        ).fetchone()[0]
    finally:
        connection.close()
    assert published == 0
