"""Capability probe: what is actually installed here, checked at call time (no installs, no network, no model download).

Each capability returns {"ok": bool, "evidence": str}. Evidence is what was checked, so a skill's status can cite it.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BREW = "/opt/homebrew/bin"          # contentos.sh puts arm64 tools first; the x86 ones in /usr/local/bin die with "bad CPU type"


def _which(name):
    return shutil.which(name, path=f"{BREW}:{os.environ.get('PATH', '')}")


def _py(mod):
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError):
        return False


def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout or r.stderr).strip().splitlines()[:1]
    except (OSError, subprocess.SubprocessError) as e:
        return False, [type(e).__name__]


def _whisper_models():
    d = Path(os.environ.get("HYPERFRAMES_HOME", Path.home() / ".cache/hyperframes")) / "whisper/models"
    return sorted(p.name for p in d.glob("ggml-*.bin")) if d.is_dir() else []


def probe() -> dict[str, dict]:
    out: dict[str, dict] = {}

    def put(cap, ok, ev):
        out[cap] = {"ok": bool(ok), "evidence": ev}

    hf = ROOT / "node_modules/.bin/hyperframes"
    put("render.hyperframes", hf.exists(), f"{hf.relative_to(ROOT)} {'present' if hf.exists() else 'missing'} (pinned 0.8.114)")
    put("media.ffmpeg", _which("ffmpeg") and _which("ffprobe"), f"ffmpeg={_which('ffmpeg')}")
    models = _whisper_models()
    en_only = [m for m in models if ".en." in m]
    multi = [m for m in models if ".en." not in m]
    put("asr.word_timing_en", _which("whisper-cli") and en_only, f"whisper-cli={_which('whisper-cli')}; models={models or 'none'}")
    put("asr.word_timing_multilingual", _which("whisper-cli") and multi, f"multilingual models: {multi or 'none (only English-only models installed)'}")
    put("align.forced_mms", _py("torchaudio"), "python module torchaudio " + ("importable" if _py("torchaudio") else "not installed"))
    put("tts.kokoro_en", _py("kokoro_onnx"), "python module kokoro_onnx " + ("importable" if _py("kokoro_onnx") else "missing"))
    try:
        from ..lang import config as lc, router as lr, tts as lt
        cfg = lc.load()
        lt.check_ready(lr.resolve({"language": "hi"}, None, cfg), cfg)
        put("tts.hindi", True, "Chatterbox Multilingual v3 (MLX) ready: venv, reference recording and cached weights present (python -m contentos.lang doctor)")
    except Exception as e:                                  # LangError carries the exact fix; any other failure is also "not ready"
        put("tts.hindi", False, f"Hindi TTS not ready: {e}")
    seg = [m for m in ("mediapipe", "rembg", "cv2") if _py(m)]
    put("cv.person_matte", seg, f"segmentation libs importable: {seg or 'none (mediapipe, rembg, cv2 all missing)'}")
    put("cv.face_detect", [m for m in ("mediapipe", "cv2") if _py(m)], "face detection needs mediapipe or cv2: " + ("present" if any(_py(m) for m in ("mediapipe", "cv2")) else "missing"))
    put("audio.beat_detect", _py("librosa"), "python module librosa " + ("importable" if _py("librosa") else "missing; numpy/scipy exist but no onset code is wired"))
    put("audio.stem_separation", _py("demucs"), "python module demucs " + ("importable" if _py("demucs") else "missing"))
    put("3d.blender", _which("blender"), f"blender={_which('blender') or 'not on PATH'}")
    wa = ROOT / "node_modules/world-atlas"
    put("data.world_atlas", wa.exists(), f"node_modules/world-atlas {'present' if wa.exists() else 'missing (npm package, MIT/ISC not yet vetted)'}")
    y = _which("yt-dlp")
    ok, ev = _run([y, "--version"]) if y else (False, ["not on PATH"])
    put("net.yt_dlp", ok, f"yt-dlp --version -> {ev[0] if ev else ''}")
    put("render.remotion", False, "intentionally not a lane (AGENTS.md section 3): only hyperframes and mpt exist")
    put("image.generate_paid", False, "no paid generation; AGENTS.md section 1 forbids paid services")
    put("media.supplied_audio_ingest", (ROOT / "contentos/production/supplied_audio.py").exists(), "contentos/production/supplied_audio.py (rights record + probe)")
    put("render.scenekit", (ROOT / "contentos/scenekit/compose.py").exists(), "contentos/scenekit (6 styles, 5 data-backed scene types)")
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(probe(), indent=1))
