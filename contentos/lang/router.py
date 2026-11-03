"""Central language routing. Pure decisions, no model is loaded here.

resolve(spec, line) -> Route. Order: line `lang` > spec `language` > config default. `auto` needs reliable metadata, never a guess.
Unsupported or unconfigured languages raise LangError listing what is supported. Nothing falls back silently.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from . import config as C
from .errors import LangError

_DEVA = re.compile(r"[\u0900-\u097F]")
_LATIN = re.compile(r"[A-Za-z]")


@dataclass(frozen=True)
class Route:
    language: str                 # resolved: en | hi | hi-en
    requested: str                # what the spec asked for (may be auto)
    tts_backend: str
    voice: str | None
    asr_model: str
    asr_language: str
    text_policy: str
    fallback_tts: str | None

    def to_dict(self):
        return asdict(self)


def script_hint(text: str) -> dict:
    """A SUGGESTION from Unicode blocks, never used by `auto` on its own: Devanagari share and Latin share of letters."""
    d, l = len(_DEVA.findall(text)), len(_LATIN.findall(text))
    tot = max(d + l, 1)
    guess = "en" if d == 0 else ("hi" if l == 0 else "hi-en")
    return {"devanagari_share": round(d / tot, 3), "latin_share": round(l / tot, 3), "suggestion": guess,
            "reliable": False, "note": "script is not language identification; declare language_metadata to use auto"}


def _auto(spec: dict, cfg: dict) -> str:
    md = spec.get("language_metadata") or {}
    a = cfg.get("auto", {})
    lang = md.get("language")
    ok = (md.get("source") == "declared" and a.get("accept_declared", True)) or (
        md.get("source") == "detected" and float(md.get("confidence", 0)) >= float(a.get("min_detected_confidence", 0.9)))
    if not lang or not ok:
        raise LangError("language: auto needs reliable metadata (spec.language_metadata = {language, source: declared|detected, confidence})",
                        code="auto_needs_metadata", hint="declare the language explicitly: language: en | hi | hi-en")
    return lang


def resolve(spec: dict, line: dict | None = None, cfg: dict | None = None) -> Route:
    cfg = cfg or C.load()
    requested = (line or {}).get("lang") or spec.get("language") or cfg["default_language"]
    lang = _auto(spec, cfg) if requested == "auto" else requested
    if lang not in cfg["languages"]:
        raise LangError(f"unsupported language {lang!r}; supported: {', '.join(sorted(cfg['languages']))} (and auto with metadata)",
                        code="unsupported_language", hint="see docs/MULTILINGUAL.md for the supported languages and their status (python -m contentos.lang matrix)")
    r = cfg["languages"][lang]
    be = cfg["tts_backends"][r["tts"]]
    spec_lang = spec.get("language") or cfg["default_language"]
    # a voice is tied to a language: the spec-level voice applies to the spec's own language; a line may carry its own `voice`
    spec_voice = (line or {}).get("voice") or (spec.get("voice") if (line is None or lang == spec_lang or requested == spec_lang) else None)
    if lang == "en":                         # English: the spec voice is a Kokoro id, validated by specs.validate_spec as before
        voice = spec_voice or be.get("default_voice")
    else:
        valid = list(be.get("voice_profiles", {})) + list(be.get("voices", []))
        if spec_voice and spec_voice not in valid:
            raise LangError(f"voice {spec_voice!r} is not valid for {lang} ({r['tts']}); valid: {', '.join(valid)}", code="invalid_voice",
                            hint="use a voice_profile from config/language.yaml or omit `voice` for the default")
        voice = spec_voice or be.get("default_voice")
    return Route(lang, requested, r["tts"], voice, r["asr"], r["asr_language"], r["text_policy"], r.get("fallback_tts"))


def video_language(spec: dict, cfg: dict | None = None) -> str:
    """The language that decides the ASR model for the whole video (per-line overrides still route their own TTS)."""
    return resolve(spec, None, cfg).language


def is_legacy(spec: dict) -> bool:
    """True when the spec is plain English with no per-line overrides: such a job must take the untouched original path."""
    langs = {spec.get("language", "en")} | {ln.get("lang", "en") for ln in spec.get("script", [])}
    return langs <= {"en"}
