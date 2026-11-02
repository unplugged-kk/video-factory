"""Non-interactive process supervision for Creator Studio runs."""
import json
import os
import shlex
import subprocess
import threading
from pathlib import Path

from . import storage
from .ui_security import redact_text


class RunConflict(RuntimeError):
    pass


def _last_json(text):
    for line in reversed(text.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


class RunSupervisor:
    def __init__(self, popen=subprocess.Popen):
        self._popen = popen
        self._guard = threading.Lock()
        self._reserved = set()
        self._processes = {}

    def running(self, content_id):
        with self._guard:
            process = self._processes.get(content_id)
            return content_id in self._reserved or (process is not None and process.poll() is None)

    def start(self, content_id, spec_path, *, only=None, force=False):
        if not storage.valid_job_id(content_id):
            raise ValueError("invalid content id")
        directory = storage.find_job_dir(content_id)
        if directory is not None and storage.lock_is_held(directory / ".run.lock"):
            return {"contentId": content_id, "status": "ALREADY_RUNNING", "active": True}
        with self._guard:
            process = self._processes.get(content_id)
            if content_id in self._reserved or (process is not None and process.poll() is None):
                return {
                    "contentId": content_id, "status": "ALREADY_RUNNING", "active": True,
                    "pid": getattr(process, "pid", None),
                }
            self._reserved.add(content_id)
        try:
            override = os.environ.get("CONTENTOS_UI_RUNNER")
            if override:
                command = shlex.split(override)
            elif only:
                from .pipeline import STAGES
                if only not in STAGES:
                    raise ValueError("unknown pipeline stage")
                command = [str(Path(__file__).resolve().parent.parent / "contentos.sh"), "pipeline", "run"]
            else:
                command = [str(Path(__file__).resolve().parent.parent / "contentos.sh"), "production", "run"]
            command.append(str(spec_path))
            if only and not override:
                command.extend(["--only", only])
                if force:
                    command.append("--force")
            process = self._popen(
                command,
                cwd=Path(__file__).resolve().parent.parent,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            with self._guard:
                self._processes[content_id] = process
                self._reserved.discard(content_id)
            threading.Thread(
                target=self._collect, args=(content_id, process), daemon=True,
                name=f"contentos-ui-{content_id}"
            ).start()
            return {"contentId": content_id, "pid": process.pid, "status": "STARTED", "active": True}
        except Exception:
            with self._guard:
                self._reserved.discard(content_id)
            raise

    def _collect(self, content_id, process):
        stdout, stderr = process.communicate()
        directory = storage.find_job_dir(content_id)
        if directory is not None:
            logs = directory / "logs"
            logs.mkdir(parents=True, exist_ok=True)
            result = _last_json(stdout)
            if process.returncode != 0 or result is None:
                result = {
                    "status": "PROCESS_ERROR",
                    "returncode": process.returncode,
                    "error": redact_text((stderr or stdout)[-4000:]),
                }
            temporary = logs / ".ui-run-result.json.tmp"
            temporary.write_text(json.dumps(result, indent=2), encoding="utf-8")
            temporary.replace(logs / "ui-run-result.json")
        with self._guard:
            self._processes.pop(content_id, None)


SUPERVISOR = RunSupervisor()
