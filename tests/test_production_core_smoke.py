"""Production core (ticket 07): what a failed stage means, when to try again, and what a hard kill leaves behind.

The pipeline itself is faked (`run=`), so nothing here renders, speaks or waits: backoff sleeps are recorded, not slept.
"""
import os
import sys
import time
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import ledger, pipeline, storage  # noqa: E402
from contentos.production import core  # noqa: E402

OK = ("OK", "SKIP(resume)")


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """A private ledger and project folder, so scrubbing and recording never touch the real workspace."""
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))   # ledger and jobs/ both live in the workspace
    return tmp_path


def write_spec(tmp_path, content_id="cfvg-1", **extra):
    spec = {"content_id": content_id, "title": "t", "format": "9:16", "voice": "af_heart",
            "script": [{"say": "one", "headline": "One"}], **extra}
    p = tmp_path / f"{content_id}.yaml"
    p.write_text(yaml.safe_dump(spec))
    return p


def report(*rows):
    """(stage, status) pairs as pipeline.run reports them, padded with the elapsed seconds."""
    return [(s, st, 0.0) for s, st in rows]


def scripted(*attempts):
    """A fake pipeline.run: each call returns the next scripted report."""
    queue = list(attempts)
    calls = []

    def run(spec_path, **kw):
        calls.append(kw)
        return "rid", queue.pop(0)

    run.calls = calls
    return run


def go(spec, run, **kw):
    sleeps = []
    result = core.run_until_blocked_or_done(spec, run=run, sleep=sleeps.append, log=lambda m: None, **kw)
    return result, sleeps


# ---- classification -------------------------------------------------------------------------------

@pytest.mark.parametrize("stage,status,expected", [
    ("voice", "FAIL: kokoro crashed", "transient"),
    ("compose", "FAIL: hyperframes lint timed out", "transient"),
    ("render", "FAIL: chrome died", "transient"),
    ("qa", "FAIL: QA failed: ['frozen_frames']", "output"),
    ("script", "FAIL: hookscore exploded", "output"),
    ("package", "FAIL: title tool", "output"),
    ("voice", "BLOCKED: no healthy TTS provider (run: contentos doctor)", "blocked"),
    ("render", "BLOCKED: gate PRODUCTION_APPROVED not granted", "blocked"),
])
def test_failure_classes(stage, status, expected):
    assert core.classify(stage, status) == expected


# ---- retries --------------------------------------------------------------------------------------

def test_a_clean_run_needs_one_attempt(ws):
    spec = write_spec(ws)
    result, sleeps = go(spec, scripted(report(("brief", "OK"), ("render", "OK"))))
    assert result.ok and result.attempts == 1 and sleeps == []
    assert result.as_json()["ok"] is True and result.as_json()["failureClass"] is None


def test_a_transient_failure_is_retried_after_the_backoff(ws):
    spec = write_spec(ws)
    run = scripted(report(("voice", "OK"), ("render", "FAIL: chrome died")),
                   report(("voice", "SKIP(resume)"), ("render", "OK")))
    result, sleeps = go(spec, run)
    assert result.ok and result.attempts == 2
    assert sleeps == [15]
    assert run.calls == [{"approve_private": False}] * 2


def test_transient_retries_run_out_after_three_tries(ws):
    spec = write_spec(ws)
    fail = report(("render", "FAIL: chrome died"))
    result, sleeps = go(spec, scripted(fail, fail, fail))
    assert not result.ok and result.failure_class == "transient" and result.stage == "render"
    assert result.attempts == 3 and sleeps == [15, 45]
    assert "chrome died" in result.error and "after 3 attempts" in result.error


@pytest.mark.parametrize("status,expected", [
    ("FAIL: QA failed: ['frozen_frames']", "output"),
    ("BLOCKED: gate PRODUCTION_APPROVED not granted", "blocked"),
])
def test_output_and_blocked_failures_are_not_retried(ws, status, expected):
    spec = write_spec(ws)
    stage = "qa" if expected == "output" else "render"
    result, sleeps = go(spec, scripted(report((stage, status))))
    assert not result.ok and result.failure_class == expected and result.attempts == 1 and sleeps == []


def test_the_wall_clock_cap_stops_a_retry_that_could_not_finish_in_time(ws):
    spec = write_spec(ws)
    now = iter([0.0, 10.0, 10.0, 10.0, 10.0])  # started at 0, the first failure lands at 10 s
    run = scripted(report(("render", "FAIL: chrome died")))
    sleeps = []
    result = core.run_until_blocked_or_done(spec, run=run, sleep=sleeps.append, log=lambda m: None,
                                            clock=lambda: next(now), cap=20)
    assert not result.ok and result.failure_class == "transient" and result.attempts == 1
    assert sleeps == [] and "20 s cap" in result.error


# ---- what a hard kill leaves behind ---------------------------------------------------------------

def make_project(ws, content_id="cfvg-1", with_files=("content.json", "script-lint.json", "audio/01.wav", "project/index.html",
                                                        "video.mp4", "qa.json", "metadata.yaml")):
    d = storage.job_dir(content_id)
    for rel in with_files:
        f = d / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")
    return d


def finished(content_id, *stages):
    for st in stages:
        ledger.record("rid", content_id, st, "p", "OK", time.time())


def present(d):
    return sorted(str(p.relative_to(d)) for p in d.rglob("*") if p.is_file())


def test_artifacts_the_ledger_never_finished_are_not_trusted_after_a_hard_kill(ws):
    spec = yaml.safe_load(write_spec(ws).read_text())
    d = make_project(ws)
    finished("cfvg-1", "brief", "script", "voice")  # killed during compose's lint: index.html exists, compose never recorded OK
    removed = core.scrub_interrupted("cfvg-1", spec)
    assert present(d) == ["audio/01.wav", "content.json", "script-lint.json"]
    assert "compose" in str(removed) and "render" in str(removed)


def test_an_unfinished_voice_stage_takes_everything_after_it_along(ws):
    spec = yaml.safe_load(write_spec(ws).read_text())
    d = make_project(ws)
    finished("cfvg-1", "brief", "script")
    core.scrub_interrupted("cfvg-1", spec)
    assert present(d) == ["content.json", "script-lint.json"]
    assert not (d / "audio").exists()


def test_a_finished_job_is_left_alone(ws):
    spec = yaml.safe_load(write_spec(ws).read_text())
    d = make_project(ws)
    finished("cfvg-1", "brief", "script", "voice", "compose", "render", "qa", "package", "publish")
    assert core.scrub_interrupted("cfvg-1", spec) == []
    assert len(present(d)) == 7


def test_the_scrub_runs_before_every_attempt(ws):
    spec = write_spec(ws)
    d = make_project(ws)
    finished("cfvg-1", "brief", "script", "voice")
    seen = []
    result, _ = go(spec, lambda p, **kw: (seen.append(present(d)), ("rid", report(("render", "OK"))))[1])
    assert result.ok and seen == [["audio/01.wav", "content.json", "script-lint.json"]]


def test_a_killed_render_leaves_no_work_folder_behind(ws):
    spec = yaml.safe_load(write_spec(ws).read_text())
    d = make_project(ws)
    finished("cfvg-1", "brief", "script", "voice", "compose", "render", "qa", "package", "publish")
    (d / "work-3f2a-killed-render" / "frames").mkdir(parents=True)  # hyperframes' scratch folder, left by a render that was killed
    (d / "work-3f2a-killed-render" / "frames" / "0001.png").write_bytes(b"x")
    removed = core.scrub_interrupted("cfvg-1", spec)
    assert not list(d.glob("work-*")) and any("work-3f2a-killed-render" in r for r in removed)
    assert len(present(d)) == 7, "the finished artifacts stay"


def test_an_ordinary_retry_does_not_blame_a_killed_run(ws):
    spec = write_spec(ws)
    (storage.job_dir("cfvg-1") / "audio").mkdir(parents=True)  # what a failed voice try leaves: an empty folder, not an artifact
    logs = []
    run = scripted(report(("voice", "FAIL: tts flaked")), report(("voice", "OK")))
    result = core.run_until_blocked_or_done(spec, run=run, sleep=lambda s: None, log=logs.append)
    assert result.ok
    assert not any("killed" in m for m in logs), logs


# ---- a hung tool cannot hold the lane -------------------------------------------------------------

def test_a_command_that_runs_too_long_is_killed_with_everything_under_it(tmp_path):
    pidfile = tmp_path / "grandchild.pid"
    start = time.time()
    with pytest.raises(RuntimeError, match="timed out after"):
        pipeline.sh(["sh", "-c", f"sleep 30 & echo $! > {pidfile}; wait"], timeout=0.5)
    assert time.time() - start < 10
    pid = int(pidfile.read_text())
    for _ in range(40):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        os.kill(pid, 9)
        pytest.fail("the sleep under the timed-out command is still running")
