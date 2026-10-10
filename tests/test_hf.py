"""The pinned HyperFrames CLI is called by absolute path, so a job folder outside the repo still uses the repo's version."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import hf, pipeline  # noqa: E402
from contentos.production import preview  # noqa: E402


def test_env_override_wins(monkeypatch):
    monkeypatch.setenv("HYPERFRAMES_BIN", "/opt/custom/hyperframes")
    assert hf.command("lint") == ["/opt/custom/hyperframes", "lint"]


def test_uses_repo_binary_by_absolute_path(monkeypatch):
    monkeypatch.delenv("HYPERFRAMES_BIN", raising=False)
    local = hf.ROOT / "node_modules" / ".bin" / "hyperframes"
    if not local.exists():
        pytest.skip("node_modules not installed")
    cmd = hf.command("render", "-o", Path("/x/video.mp4"))
    assert cmd == [str(local), "render", "-o", "/x/video.mp4"] and Path(cmd[0]).is_absolute()


def test_falls_back_to_npx_when_not_installed(monkeypatch, tmp_path):
    monkeypatch.delenv("HYPERFRAMES_BIN", raising=False)
    monkeypatch.setattr(hf, "ROOT", tmp_path)
    assert hf.command("lint") == ["npx", "--no-install", "hyperframes", "lint"]


def test_runs_from_a_folder_outside_the_repo(monkeypatch, tmp_path):
    """The regression: with cwd outside the repo the CLI must still resolve to the pinned version."""
    monkeypatch.delenv("HYPERFRAMES_BIN", raising=False)
    if not (hf.ROOT / "node_modules" / ".bin" / "hyperframes").exists():
        pytest.skip("node_modules not installed")
    r = subprocess.run(hf.command("--version"), cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and r.stdout.strip()


def test_pipeline_and_preview_never_use_bare_npx(monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERFRAMES_BIN", "/pinned/hyperframes")
    seen = []
    monkeypatch.setattr(pipeline, "sh", lambda cmd, cwd=None, timeout=None: seen.append(cmd) or "")
    ctx = {"dir": tmp_path, "spec": {}}
    (tmp_path / "project").mkdir()
    pipeline.sh(hf.command("lint"), cwd=tmp_path)
    pipeline.s_render(ctx)
    monkeypatch.setattr(preview, "_run", lambda cmd, cwd=None, timeout=300: seen.append(cmd) or "")
    preview.snapshot(tmp_path, [1.0], tmp_path / "o")
    assert seen and all(c[0] == "/pinned/hyperframes" for c in seen)
