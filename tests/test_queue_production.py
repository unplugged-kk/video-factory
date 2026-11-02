"""Queue execution uses the production core and can stop its own process group."""
import json
import subprocess

import yaml

from contentos import ledger, queue, storage


def test_queue_run_uses_production_result_and_kills_on_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "publishing"))
    storage.preflight()
    spec = tmp_path / "job.yaml"
    spec.write_text(yaml.safe_dump({"content_id": "queue-job", "title": "Queue"}))
    job_id = queue.add([spec])[0]
    calls = []

    class Process:
        pid = 4321
        returncode = 1

        def communicate(self, timeout=None):
            calls.append(timeout)
            if timeout is not None:
                raise subprocess.TimeoutExpired(cmd="production", timeout=timeout)
            return ('{"ok": false}\n', "")

        def wait(self, timeout=None):
            return 1

        def kill(self):
            calls.append("kill")

    monkeypatch.setattr(queue.subprocess, "Popen", lambda cmd, **kwargs: calls.append((cmd, kwargs)) or Process())
    monkeypatch.setattr(queue.os, "killpg", lambda pid, sig: calls.append(("killpg", pid, sig)))
    queue._run((job_id, str(spec), "queue-job", 0))
    command, options = next(item for item in calls if isinstance(item, tuple) and item and isinstance(item[0], list))
    assert command[1:3] == ["production", "run"]
    assert options["start_new_session"] is True
    assert ("killpg", 4321, queue.signal.SIGTERM) in calls
    status, error = ledger.db().execute("SELECT status, error FROM jobs WHERE id=?", (job_id,)).fetchone()
    assert status == "failed"
    assert "timed out" in error


def test_production_json_marks_gate_wait_as_blocked(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "publishing"))
    storage.preflight()
    spec = tmp_path / "job.yaml"
    spec.write_text(yaml.safe_dump({"content_id": "blocked-job", "title": "Blocked"}))
    job_id = queue.add([spec])[0]

    class Process:
        pid = 44
        returncode = 1

        def communicate(self, timeout=None):
            return (json.dumps({"ok": False, "failureClass": "blocked", "error": "gate waiting"}) + "\n", "")

    monkeypatch.setattr(queue.subprocess, "Popen", lambda *_args, **_kwargs: Process())
    queue._run((job_id, str(spec), "blocked-job", 0))
    status, error = ledger.db().execute("SELECT status, error FROM jobs WHERE id=?", (job_id,)).fetchone()
    assert status == "blocked"
    assert error == "gate waiting"
