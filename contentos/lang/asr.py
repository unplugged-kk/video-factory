"""Language-aware ASR adapter over whisper.cpp (`whisper-cli`), the same engine `hyperframes transcribe` shells to.

Why not just `hyperframes transcribe`: it accepts only a fixed model list (tiny.en ... large-v3), so it cannot be pointed at the
installed `ggml-large-v3-turbo-q5_0.bin`. English keeps the unchanged legacy path (pipeline.words_for); this adapter handles the
other languages and the benchmark. It never falls back to a different model silently: a missing model is a LangError.

Word timing is whatever whisper.cpp measured with --split-on-word. Whisper timestamps are estimates (see benchmark report).
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from . import config as C
from .errors import LangError

BREW = "/opt/homebrew/bin"


def _bin():
    from shutil import which
    p = which("whisper-cli", path=f"{BREW}:{os.environ.get('PATH', '')}")
    if not p:
        raise LangError("whisper-cli not found (brew install whisper-cpp)", code="asr_binary_missing")
    return p


def transcribe(wav: str | Path, model: str | Path, language: str, timeout: float = 900) -> dict:
    """Return {words:[{text,start,end}], text, model, language, seconds, binary}. Raises LangError, never substitutes a model."""
    model, wav = Path(model).expanduser(), Path(wav)
    if not model.is_file() or model.stat().st_size < C.MIN_ASR_BYTES:
        raise LangError(f"ASR model missing or truncated: {model}", code="asr_model_missing",
                        hint="download per docs/MULTILINGUAL.md (checksum-verified) into ~/.cache/hyperframes/whisper/models")
    if not wav.is_file():
        raise LangError(f"audio not found: {wav}", code="audio_missing")
    with tempfile.TemporaryDirectory() as d:
        base = Path(d) / "out"
        cmd = [_bin(), "-m", str(model), "-f", str(wav), "-l", language, "-ml", "1", "-sow", "-oj", "-of", str(base), "-np"]
        t = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        secs = time.time() - t
        out = Path(str(base) + ".json")
        if r.returncode or not out.exists():
            raise LangError(f"whisper-cli failed (exit {r.returncode}): {(r.stderr or r.stdout)[-300:]}", code="asr_failed")
        j = json.loads(out.read_text())
    words = []
    for seg in j.get("transcription", []):
        txt = seg["text"].strip()
        if not txt or (txt.startswith("[") and txt.endswith("]")):          # [BLANK_AUDIO], [MUSIC]
            continue
        words.append({"text": txt, "start": seg["offsets"]["from"] / 1000, "end": seg["offsets"]["to"] / 1000})
    return {"words": words, "text": " ".join(w["text"] for w in words), "model": model.name, "language": language,
            "seconds": round(secs, 2), "binary": _bin()}


def valid_timestamps(words: list[dict], duration: float, tol: float = 0.5) -> list[str]:
    """Problems with a word list: non-monotonic, inverted, or past the audio end (tolerance in seconds). Empty = valid."""
    bad, prev = [], 0.0
    for i, w in enumerate(words):
        if w["end"] < w["start"]: bad.append(f"word {i} {w['text']!r}: end before start")
        if w["start"] + 0.05 < prev: bad.append(f"word {i} {w['text']!r}: starts before the previous word ended")
        if w["end"] > duration + tol: bad.append(f"word {i} {w['text']!r}: ends {w['end']:.2f}s, audio is {duration:.2f}s")
        prev = max(prev, w["end"])
    return bad


def route_transcribe(wav, route, cfg: dict) -> dict:
    """Transcribe with the model the route names. English routes are served by the legacy hyperframes path in pipeline.words_for;
    this is for the others (and for direct use). Result gains the route/model ids for the job metadata."""
    from . import config as C
    m = cfg["asr_models"][route.asr_model]
    r = transcribe(wav, C.asr_model_path(cfg, route.asr_model), route.asr_language)
    r.update({"asr_model_id": route.asr_model, "multilingual": m["multilingual"], "route_language": route.language})
    return r
