"""Unattended local setup for the languages this Mac can actually run.

English, Hindi, and Hinglish are installed here. Odia is not. Its models are gated and need a PyTorch
environment the owner has not approved. A successful setup still prints Odia as NOT READY.
"""
from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from . import config as C
from .errors import LangError

MLX_PIN = "mlx-audio==0.6.4"


def apple_silicon(system: str | None = None, machine: str | None = None) -> bool:
    return (system or sys.platform) == "darwin" and (machine or platform.machine()) == "arm64"


def required_languages(system: str | None = None, machine: str | None = None) -> tuple[str, ...]:
    """Hindi and Hinglish need MLX on Apple Silicon. Every other host can only be set up for English."""
    return ("en", "hi", "hi-en") if apple_silicon(system, machine) else ("en",)


def artifact_ok(path: Path, size: int, sha: str | None = None) -> bool:
    if size <= 0 or not path.is_file() or path.stat().st_size != size:
        return False
    if not sha:
        return True
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == sha


def ensure_asr_models(cfg: dict, languages=None) -> list[str]:
    """Download ASR files for `languages` (all configured when None). Returns what changed."""
    from . import router as R
    needed = None if languages is None else {R.resolve({"language": lang}, None, cfg).asr_model for lang in languages}
    done = []
    for key, spec in cfg["asr_models"].items():
        if needed is not None and key not in needed:
            continue
        source = spec.get("source")
        size = int(spec.get("size_bytes") or 0)
        if not source or size <= 0:
            continue
        dest = C.asr_model_path(cfg, key)
        if artifact_ok(dest, size, spec.get("sha256")):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".partial")
        try:
            urllib.request.urlretrieve(source, tmp)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise LangError(f"could not download {key} from {source}: {exc}", code="asr_download_failed") from exc
        if not artifact_ok(tmp, size, spec.get("sha256")):
            tmp.unlink(missing_ok=True)
            raise LangError(f"downloaded {key} from {source} but size or sha256 did not match config/language.yaml", code="asr_download_bad")
        tmp.replace(dest)
        done.append(key)
    return done


def ensure_mlx(cfg: dict) -> str:
    py = C.path(cfg, "mlx_python")
    if py.exists() and subprocess.run([str(py), "-c", "import mlx_audio"], capture_output=True).returncode == 0:
        return "present"
    if not shutil.which("uv"):
        raise LangError("uv is not on PATH; install it with `brew install uv` and rerun setup", code="runtime_missing")
    try:
        py.parent.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["uv", "venv", "--python", "3.12", str(py.parent.parent)], check=True)
        subprocess.run(["uv", "pip", "install", "--python", str(py), MLX_PIN], check=True)
    except (subprocess.CalledProcessError, OSError) as exc:
        raise LangError(f"could not prepare the MLX runtime at {py}: {exc}", code="runtime_missing") from exc
    return "installed"


def ensure_storage() -> None:
    from contentos import storage
    try:
        for root in (storage.workspace_root(), storage.publish_root()):
            root.mkdir(parents=True, exist_ok=True)
        storage.preflight()
    except storage.StorageError as exc:
        raise LangError(str(exc), code="storage_not_ready") from exc


def _weights_dir(cfg: dict) -> Path:
    from . import router as R
    from . import tts as T
    route = R.resolve({"language": "hi"}, None, cfg)
    return T.weights_dir(cfg, cfg["tts_backends"][route.tts_backend])


def _weights_cached(cfg: dict) -> bool:
    from . import tts as T
    return T.weights_cached(_weights_dir(cfg))


def _make_reference(cfg: dict, dest: Path) -> None:
    import json
    import time
    from . import router as R
    from . import tts as T
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = json.loads((Path(__file__).resolve().parents[2] / "tests/fixtures/multilingual/benchmark.json").read_text(encoding="utf-8"))["reference_voice_text_hi"]
    route = R.Route("hi", "hi", "kokoro_hindi", "hf_alpha", "whisper_turbo_q5", "hi", "as_is", None)
    res = T._kokoro(text, route, dest, cfg, time.time())
    print(f"wrote {dest} ({res.duration} s, synthetic Kokoro hf_alpha; no real person's voice)")


def _download_tts(cfg: dict) -> None:
    from . import router as R
    from . import tts as T
    route = R.resolve({"language": "hi"}, None, cfg)
    be = cfg["tts_backends"][route.tts_backend]
    py = C.path(cfg, "mlx_python")
    code = ("from huggingface_hub import snapshot_download as s;"
            f"print(s({be['model']!r}));print(s('mlx-community/S3TokenizerV2'))")
    run = subprocess.run([str(py), "-c", code], env=T._env(cfg), capture_output=True, text=True)
    print(run.stdout.strip() or run.stderr[-400:])
    if run.returncode != 0:
        raise LangError("Chatterbox download failed", code="weights_missing")


def language_issues(cfg: dict) -> dict[str, list[str]]:
    from . import router as R
    from . import tts as T
    out = {}
    for lang in cfg["languages"]:
        route = R.resolve({"language": lang}, None, cfg)
        issues = []
        try:
            T.check_ready(route, cfg)
        except LangError as exc:
            issues.append(str(exc))
        model = C.asr_model_path(cfg, route.asr_model)
        if not model.is_file() or model.stat().st_size < C.MIN_ASR_BYTES:
            issues.append(f"asr model missing or truncated: {model}")
        out[lang] = issues
    return out


def setup(cfg: dict | None = None) -> int:
    """Install the languages this host can run. Apple Silicon includes Hindi and Hinglish. Other hosts stop at English."""
    cfg = cfg or C.load()
    needed = required_languages()
    if apple_silicon():
        print(f"mlx runtime: {ensure_mlx(cfg)}")
    else:
        print("mlx runtime: skipped. Hindi and Hinglish need Apple Silicon. This host is set up for English only.")
    changed = ensure_asr_models(cfg, needed)
    print("asr models: " + (", ".join(changed) if changed else "already present"))
    ensure_storage()
    print("storage: workspace and publishing library are writable")
    if apple_silicon():
        ref = Path(os.path.expanduser(cfg["tts_backends"]["chatterbox_v3"]["voice_profiles"]["hindi-default"]["reference"]))
        if not ref.is_file():
            _make_reference(cfg, ref)
        else:
            print(f"reference voice: {ref}")
        if not _weights_cached(cfg):
            _download_tts(cfg)
        else:
            print(f"tts weights: {_weights_dir(cfg)}")
    issues = language_issues(cfg)
    failed = [lang for lang in needed if issues[lang]]
    for lang, rows in issues.items():
        print(f"{lang:6} {'READY' if not rows else 'NOT READY'}")
        for row in rows:
            print("       " + row)
    if failed:
        print("setup incomplete: " + ", ".join(failed))
        return 1
    ready = ", ".join(needed)
    print(f"setup ok: {ready} ready. Odia (or) stays blocked until the owner approves a gated model and a PyTorch environment.")
    return 0
