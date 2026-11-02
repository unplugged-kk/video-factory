import threading

from contentos import storage
from contentos.ui_runner import RunSupervisor


class BlockingProcess:
    pid = 4321

    def __init__(self):
        self.done = threading.Event()
        self.returncode = None

    def poll(self):
        return self.returncode

    def communicate(self):
        self.done.wait(timeout=3)
        self.returncode = 0
        return ('{"ok": true}\n', "")


def test_supervisor_reserves_content_id_before_process_collection(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "publishing"))
    storage.preflight()
    process = BlockingProcess()
    supervisor = RunSupervisor(popen=lambda *args, **kwargs: process)
    spec = tmp_path / "job.yaml"
    spec.write_text("content_id: exactly-once", encoding="utf-8")

    started = supervisor.start("exactly-once", spec)
    assert started["status"] == "STARTED"
    repeated = supervisor.start("exactly-once", spec)
    assert repeated == {
        "contentId": "exactly-once", "status": "ALREADY_RUNNING",
        "active": True, "pid": 4321,
    }
    process.done.set()
