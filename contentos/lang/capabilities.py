"""Language capability matrix: what each language can really do on this machine, with the evidence behind it.

  build()  -> dict   readiness comes from LIVE checks (model files, runtime, reference recording); everything a check cannot see
                     (rendered videos, automated tests, a native speaker's review) comes from config/language-capabilities.evidence.json
  status   -> blocked | experimental | tested | production-ready, by rule (below). An installed model alone never reaches `tested`.

Rules: blocked = no ready TTS backend. production-ready = ready + end-to-end render pass + automated tests pass + (human audio review
pass OR a documented production history). tested = ready + render pass + tests pass. Anything else ready = experimental. An evidence
entry may cap a language lower with `max_status` and a reason. The JSON snapshot (config/language-capabilities.json) is what the cloud
adapter reads; `matrix --check` fails when it is stale. The pipeline re-checks readiness at job time, so a stale snapshot can only
cause a clear Blocked, never silent wrong audio.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import config as C
from . import router as R
from . import tts as T
from .errors import LangError

ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE = ROOT / "config/language-capabilities.evidence.json"
SNAPSHOT = ROOT / "config/language-capabilities.json"
ORDER = ["blocked", "experimental", "tested", "production-ready"]
SCHEMA = "language-capabilities/1"


def _ready(route, cfg):
    try:
        T.check_ready(route, cfg)
        return {"status": "ready", "detail": f"{route.tts_backend} ready"}
    except LangError as e:
        return {"status": "blocked" if e.code == "backend_blocked" else "not-ready", "code": e.code, "detail": str(e)}


def _asr(route, cfg):
    m = cfg["asr_models"][route.asr_model]
    p = C.asr_model_path(cfg, route.asr_model)
    if p.is_file() and p.stat().st_size >= 10_000_000:
        return {"status": "ready", "model": m["file"], "detail": f"{p} ({p.stat().st_size} bytes)"}
    fb = cfg["languages"][route.language].get("timing_fallback")
    if fb:
        return {"status": "timing-fallback", "model": m["file"], "detail": f"model absent; captions use measured audio duration with {fb.replace('_', ' ')}, unverified word timing"}
    return {"status": "not-ready", "model": m["file"], "detail": f"model missing: {p}"}


def _status(tts, asr, ev) -> tuple[str, str]:
    if tts["status"] != "ready":
        return "blocked", f"TTS: {tts['detail'][:200]}"
    if asr["status"] == "not-ready":
        return "blocked", f"ASR: {asr['detail']}"
    passed = lambda k: (ev.get(k) or {}).get("status") == "pass"
    if passed("end_to_end_render") and passed("automated_tests"):
        if passed("human_audio_review") or ev.get("production_history"):
            st, why = "production-ready", "render + tests pass and " + ("native review passed" if passed("human_audio_review") else "documented production history")
        else:
            st, why = "tested", "render and automated tests pass; no human audio review yet"
    else:
        st, why = "experimental", "integration ready but end-to-end render and/or automated tests are not recorded as passing"
    cap = ev.get("max_status")
    if cap and ORDER.index(cap["status"]) < ORDER.index(st):
        st, why = cap["status"], f"capped: {cap['reason']}"
    return st, why


def build(cfg: dict | None = None) -> dict:
    cfg = cfg or C.load()
    evid = json.loads(EVIDENCE.read_text(encoding="utf-8")) if EVIDENCE.exists() else {}
    langs = {}
    for code in cfg["languages"]:
        route = R.resolve({"language": code}, None, cfg)
        be = cfg["tts_backends"][route.tts_backend]
        prof = cfg["language_profiles"][code]
        ev = evid.get(code, {})
        tts, asr = _ready(route, cfg), _asr(route, cfg)
        st, why = _status(tts, asr, ev)
        langs[code] = {
            "code": code, "name": prof["name"], "status": st, "status_reason": why,
            "tts": {"backend": route.tts_backend, "model": be.get("model", "kokoro-v1.0.onnx" if be["kind"] == "hyperframes_cli" else None), **tts},
            "asr": {"route": route.asr_model, "language": route.asr_language, **asr},
            "voices": sorted(list(be.get("voice_profiles", {})) + list(be.get("voices", []))) or [be.get("default_voice")],
            "default_voice": route.voice,
            "subtitle": {"script": prof["script"], "fonts": prof["fonts"], "unicode_ranges": prof["unicode_ranges"], "min_script_share": prof["min_script_share"], "normalization": prof["normalization"],
                         "unicode_render": (ev.get("unicode_subtitles") or {"status": "untested"})},
            "text_policy": route.text_policy, "fallback_tts": route.fallback_tts,
            "evidence": {k: ev.get(k, {"status": "not-recorded"}) for k in ("end_to_end_render", "automated_tests", "human_audio_review")},
            "limitations": ev.get("limitations", []),
        }
    src = hashlib.sha256(Path(cfg["_path"]).read_bytes() + (EVIDENCE.read_bytes() if EVIDENCE.exists() else b"")).hexdigest()
    return {"schema": SCHEMA, "source_sha256": src, "default_language": cfg["default_language"], "languages": langs}


def render_table(m: dict) -> str:
    rows = [f"{'lang':6} {'status':17} {'TTS':10} {'ASR':16} {'render':8} {'tests':8} {'human review':14} notes"]
    for c, l in m["languages"].items():
        e = l["evidence"]
        rows.append(f"{c:6} {l['status']:17} {l['tts']['status']:10} {l['asr']['status']:16} {e['end_to_end_render']['status']:8} {e['automated_tests']['status']:8} "
                    f"{e['human_audio_review']['status']:14} {l['status_reason'][:90]}")
    return "\n".join(rows)


def current(path: Path = SNAPSHOT) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def status_of(language: str, path: Path = SNAPSHOT) -> dict:
    return current(path)["languages"][language]
