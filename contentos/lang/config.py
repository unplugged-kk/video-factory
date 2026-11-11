"""Load and validate config/language.yaml. CONTENTOS_LANGUAGE_CONFIG overrides the path (tests, experiments)."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

from .errors import LangError

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT = ROOT / "config" / "language.yaml"
MODES = ("en", "hi", "hi-en", "or", "auto")
MIN_ASR_BYTES = 10_000_000          # a real whisper model is far larger; a truncated file must never read as ready


def load(path: str | Path | None = None) -> dict:
    p = Path(path or os.environ.get("CONTENTOS_LANGUAGE_CONFIG") or DEFAULT)
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    problems = validate(cfg)
    if problems:
        raise LangError("invalid language config " + str(p) + ": " + "; ".join(problems), code="config_invalid")
    cfg["_path"] = str(p)
    return cfg


def validate(cfg: dict) -> list[str]:
    errs = []
    for k in ("default_language", "paths", "languages", "tts_backends", "asr_models"):
        if k not in cfg:
            errs.append(f"missing key {k}")
    if errs:
        return errs
    if cfg["default_language"] not in cfg["languages"]:
        errs.append("default_language is not a configured language")
    for lang, r in cfg["languages"].items():
        if lang not in MODES or lang == "auto":
            errs.append(f"language {lang!r} is not one of en, hi, hi-en, or")
        if lang not in cfg.get("language_profiles", {}):
            errs.append(f"{lang}: missing language_profiles entry")
        if r.get("tts") not in cfg["tts_backends"]:
            errs.append(f"{lang}: unknown tts backend {r.get('tts')!r}")
        if r.get("asr") not in cfg["asr_models"]:
            errs.append(f"{lang}: unknown asr model {r.get('asr')!r}")
        if r.get("fallback_tts") and r["fallback_tts"] not in cfg["tts_backends"]:
            errs.append(f"{lang}: unknown fallback_tts {r['fallback_tts']!r}")
        if r.get("tts") in cfg["tts_backends"] and lang not in cfg["tts_backends"][r["tts"]].get("languages", []):
            errs.append(f"{lang}: backend {r['tts']} does not declare support for it")
        if r.get("text_policy") not in ("as_is", "translit_known", "mixed"):
            errs.append(f"{lang}: bad text_policy")
        if r.get("timing_fallback") not in (None, "even_spacing"):
            errs.append(f"{lang}: bad timing_fallback")
    return errs


def path(cfg: dict, key: str) -> Path:
    return Path(os.path.expanduser(cfg["paths"][key]))


def asr_model_path(cfg: dict, key: str) -> Path:
    return path(cfg, "whisper_models") / cfg["asr_models"][key]["file"]
