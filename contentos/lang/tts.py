"""TTS adapters behind one contract. Both return audio the pipeline already expects: 24 kHz mono 16-bit WAV, loudnorm -14 LUFS.

  synthesize(text, route, out_wav, cfg) -> TTSResult      (one segment)
  synthesize_lines(spec, out_dir, cfg)  -> list[TTSResult] (a whole script; Chatterbox loads its model ONCE for all lines)

No silent substitution: a failure raises LangError unless the language config names `fallback_tts`, in which case the fallback is
logged in the result (`fallback_from`, `warnings`) so it is visible in the job metadata. Models are lazy: nothing heavy is touched
until a line actually routes to it, so English-only jobs never import or spawn the MLX stack.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import config as C
from . import lexicon
from .errors import LangError
from .router import Route, resolve

ROOT = Path(__file__).resolve().parent.parent.parent
WORKER = Path(__file__).with_name("chatterbox_worker.py")
LOUDNORM = "loudnorm=I=-14:TP=-1.5:LRA=11"


@dataclass
class TTSResult:
    text: str
    language: str
    backend: str
    model: str
    voice: str | None
    path: str
    sample_rate: int
    channels: int
    codec: str
    duration: float
    gen_seconds: float
    text_policy: str = "as_is"
    spoken_text: str = ""                 # what was actually sent to the model (after the text policy)
    chunks: list = field(default_factory=list)   # chunk offsets inside the file (Chatterbox); empty = single chunk
    word_timestamps: str = "none"         # never claimed here: timing comes from ASR (measured) or is absent
    fallback_from: str | None = None
    warnings: list = field(default_factory=list)
    reference: str | None = None

    def to_dict(self):
        return asdict(self)


def prepare_text(text: str, policy: str) -> tuple[str, list[str]]:
    """Apply the language's text policy. Returns (text for the model, warnings)."""
    if policy == "translit_known":
        out, unknown = lexicon.to_devanagari(text)
        return out, ([f"unknown Latin words passed through unchanged: {sorted(set(unknown))}"] if unknown else [])
    return text, []


def _ffmpeg(*a):
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *a], capture_output=True, text=True, env=_env())
    if r.returncode:
        raise LangError(f"ffmpeg failed: {r.stderr[-300:]}", code="audio_postprocess_failed")


def _env(cfg=None):
    e = {**os.environ, "PATH": "/opt/homebrew/bin:" + os.environ.get("PATH", "")}
    e.setdefault("HYPERFRAMES_PYTHON", os.path.expanduser("~/.contentos/venv/bin/python"))
    if cfg:
        e["HF_HOME"] = str(C.path(cfg, "hf_home"))
    return e


def _probe(p: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=sample_rate,channels,codec_name", "-of", "json", str(p)],
                       capture_output=True, text=True, env=_env())
    if r.returncode:
        raise LangError(f"cannot probe generated audio {p}: {r.stderr[-200:]}", code="audio_invalid")
    j = json.loads(r.stdout)
    s = j["streams"][0]
    return {"duration": round(float(j["format"]["duration"]), 3), "sample_rate": int(s["sample_rate"]), "channels": int(s["channels"]), "codec": s["codec_name"]}


def _normalise(raw: Path, out: Path):
    _ffmpeg("-i", str(raw), "-af", LOUDNORM, "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(out))


# ---- readiness (explicit, actionable errors) -------------------------------------------------------------------------

def weights_dir(cfg: dict, be: dict) -> Path:
    return C.path(cfg, "hf_home") / "hub" / ("models--" + be["model"].replace("/", "--"))


def weights_cached(hub: Path) -> bool:
    """A cache directory is not a complete download: huggingface_hub creates it before the blobs finish.

    Treat an in-progress blob or an empty `snapshots/` as missing so a retry actually retries instead of reporting
    Hindi READY and failing later at model load.
    """
    if not hub.is_dir() or any(hub.rglob("*.incomplete")):
        return False
    snapshots = hub / "snapshots"
    return snapshots.is_dir() and any(snapshots.iterdir())


def check_ready(route: Route, cfg: dict):
    be = cfg["tts_backends"][route.tts_backend]
    if be.get("blocked"):
        raise LangError(f"TTS backend {route.tts_backend} ({be.get('model')}) is not available: {be['blocked']}", code="backend_blocked",
                        hint="see docs/MULTILINGUAL.md section 'Odia' for the exact approval and install steps")
    if be["kind"] not in ("hyperframes_cli", "mlx_worker"):
        raise LangError(f"no adapter implemented for backend kind {be['kind']!r} ({route.tts_backend})", code="adapter_not_implemented")
    if be["kind"] == "mlx_worker":
        py = C.path(cfg, "mlx_python")
        if not py.exists():
            raise LangError(f"mlx-audio runtime missing: {py}", code="runtime_missing",
                            hint="create the isolated venv: uv venv --python 3.12 ~/.contentos/venv-mlx-audio && uv pip install --python ~/.contentos/venv-mlx-audio/bin/python mlx-audio==0.6.4")
        prof = be.get("voice_profiles", {}).get(route.voice)
        if not prof:
            raise LangError(f"voice profile {route.voice!r} not defined for {route.tts_backend}", code="invalid_voice")
        ref = Path(os.path.expanduser(prof["reference"]))
        if not ref.is_file():
            raise LangError(f"reference recording missing: {ref}; Chatterbox v3 (MLX) has no default voice", code="reference_missing",
                            hint="python -m contentos.lang reference --make   (synthetic Kokoro reference) or supply your own recording with consent")
        hub = weights_dir(cfg, be)
        if not weights_cached(hub):
            raise LangError(f"model weights not in cache: {be['model']} ({hub})", code="weights_missing",
                            hint="first use downloads ~3 GB: python -m contentos.lang download-tts   (needs network)")


# ---- backends ----------------------------------------------------------------------------------------------------------

def _kokoro(text, route, out, cfg, t0) -> TTSResult:
    be = cfg["tts_backends"][route.tts_backend]
    from .. import hf
    raw = out.with_suffix(".raw.wav")
    cmd = hf.command("tts", text, "-v", route.voice or be["default_voice"], "-o", str(raw))
    if be.get("lang_arg"):
        cmd += ["--lang", be["lang_arg"]]
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, env=_env())
    if r.returncode or not raw.exists():
        raise LangError(f"kokoro generation failed: {(r.stdout + r.stderr)[-300:]}", code="generation_failed")
    _normalise(raw, out); raw.unlink()
    p = _probe(out)
    return TTSResult(text, route.language, route.tts_backend, "kokoro-v1.0.onnx", route.voice, str(out), p["sample_rate"], p["channels"], p["codec"],
                     p["duration"], round(time.time() - t0, 2), route.text_policy, text)


def _run_worker(jobs: list[dict], route: Route, cfg: dict) -> dict:
    be = cfg["tts_backends"][route.tts_backend]
    prof = be["voice_profiles"][route.voice]
    with tempfile.TemporaryDirectory() as d:
        jf = Path(d) / "jobs.json"
        jf.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
        cmd = [str(C.path(cfg, "mlx_python")), str(WORKER), "--batch", str(jf), "--lang", be["lang_code"], "--ref", os.path.expanduser(prof["reference"]),
               "--model", be["model"], "--exaggeration", str(be.get("exaggeration", 0.5))]
        r = subprocess.run(cmd, capture_output=True, text=True, env=_env(cfg))
    lines = [l for l in r.stdout.strip().splitlines() if l.startswith("{")]
    if not lines:
        raise LangError(f"chatterbox worker produced no result (exit {r.returncode}): {r.stderr[-300:]}", code="generation_failed")
    j = json.loads(lines[-1])
    if not j.get("ok"):
        raise LangError(f"chatterbox failed: {j.get('error')}", code="generation_failed")
    return j


def _chatterbox_many(items: list[tuple[str, Route, Path]], cfg: dict) -> list[TTSResult]:
    route = items[0][1]
    be = cfg["tts_backends"][route.tts_backend]
    prof = be["voice_profiles"][route.voice]
    spoken, warns = [], []
    for text, rt, _ in items:
        s, w = prepare_text(text, rt.text_policy)
        spoken.append(s); warns.append(w)
    t0 = time.time()
    j = _run_worker([{"text": s, "out": str(o.with_suffix(".raw.wav"))} for s, (_, _, o) in zip(spoken, items)], route, cfg)
    if len(j.get("items", [])) != len(items):
        raise LangError(f"chatterbox returned {len(j.get('items', []))} results for {len(items)} line(s)", code="generation_failed")
    res = []
    for (text, rt, out), s, w, it in zip(items, spoken, warns, j["items"]):
        raw = out.with_suffix(".raw.wav")
        _normalise(raw, out); raw.unlink()
        p = _probe(out)
        res.append(TTSResult(text, rt.language, rt.tts_backend, j["model"], rt.voice, str(out), p["sample_rate"], p["channels"], p["codec"], p["duration"],
                             round(it.get("gen_seconds", 0), 2), rt.text_policy, s, it.get("chunks", []), "none", None, w, prof["provenance"]))
    res[0].warnings.append(f"model loaded once for {len(items)} line(s): load {j.get('load_seconds')} s, mlx peak {j.get('peak_memory_gb')} GB")
    return res


# ---- public API ----------------------------------------------------------------------------------------------------------

def synthesize_lines(spec: dict, out_dir: Path, cfg: dict | None = None, names=None) -> list[TTSResult]:
    """Generate every script line to out_dir/NN.wav (24 kHz mono, -14 LUFS), writing NN.tts.json metadata next to each."""
    cfg = cfg or C.load()
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = []
    for i, ln in enumerate(spec["script"], 1):
        rt = resolve(spec, ln, cfg)
        plan.append((i, ln.get("tts", ln["say"]), rt, out_dir / f"{i:02d}.wav"))
    results: dict[int, TTSResult] = {}
    groups: dict[str, list] = {}
    for i, text, rt, out in plan:
        groups.setdefault(rt.tts_backend, []).append((i, text, rt, out))
    for backend, items in groups.items():
        todo = []
        for i, t, rt, o in items:
            meta = _load_meta(o) if o.exists() else None
            if meta is None:
                todo.append((i, t, rt, o))     # a wav without metadata is a half-finished take: regenerate it
            else:
                results[i] = meta
        if not todo:
            continue
        try:
            check_ready(todo[0][2], cfg)
            kind = cfg["tts_backends"][backend]["kind"]
            if kind == "mlx_worker":
                for (i, *_), r in zip(todo, _chatterbox_many([(t, rt, o) for i, t, rt, o in todo], cfg)):
                    results[i] = r
            else:
                for i, t, rt, o in todo:
                    t0 = time.time()
                    results[i] = _kokoro(prepare_text(t, rt.text_policy)[0], rt, o, cfg, t0)
        except LangError as e:
            fb = todo[0][2].fallback_tts
            if not fb or e.code in ("unsupported_language", "invalid_voice"):
                raise
            for i, t, rt, o in todo:                       # explicit, configured fallback: logged in the metadata
                frt = Route(rt.language, rt.requested, fb, cfg["tts_backends"][fb].get("default_voice"), rt.asr_model, rt.asr_language, "as_is", None)
                r = _kokoro(t, frt, o, cfg, time.time())
                r.fallback_from = backend
                r.warnings.append(f"FALLBACK from {backend} to {fb}: {e}")
                results[i] = r
    out = []
    for i, text, rt, o in plan:
        r = results[i]
        if r is not None:
            Path(o.with_suffix(".tts.json")).write_text(json.dumps(r.to_dict(), indent=1, ensure_ascii=False), encoding="utf-8")
            out.append(r)
    return out


def _load_meta(wav: Path):
    m = wav.with_suffix(".tts.json")
    if m.exists():
        d = json.loads(m.read_text(encoding="utf-8"))
        return TTSResult(**d)
    return None


def synthesize(text: str, route: Route, out: Path, cfg: dict | None = None) -> TTSResult:
    spec = {"script": [{"say": text, "lang": route.language}], "voice": route.voice if route.language != "en" else None}
    out = Path(out)
    tmp = out.parent / f"__one_{out.stem}"
    res = synthesize_lines(spec, tmp, cfg)[0]
    out.parent.mkdir(parents=True, exist_ok=True)
    Path(res.path).replace(out)
    res.path = str(out)
    for f in tmp.glob("*"):
        f.unlink()
    tmp.rmdir()
    return res
