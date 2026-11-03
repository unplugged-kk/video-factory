"""Script validation per language: Unicode normalisation and script share. Pure functions, no model.

validate(language, lines) returns a list of problems (empty = ok). normalise(text) returns NFC text. The thresholds live in
config/language.yaml (language_profiles.<lang>.min_script_share) so there is no per-language branching here.
"""
from __future__ import annotations

import re
import unicodedata

from . import config as C

_CTRL = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u200b\ufeff\ufffd]")   # control chars, BOM, zero-width space, replacement char


def normalise(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _ranges(profile):
    return [tuple(int(x, 16) for x in r.split("-")) for r in profile.get("unicode_ranges", [])]


def letters(text: str):
    return [c for c in text if unicodedata.category(c)[0] in "LM"]       # base letters and combining marks (matras)


def script_share(text: str, profile: dict) -> float:
    rs = _ranges(profile)
    ls = letters(text)
    if not ls or not rs:
        return 0.0
    return sum(any(a <= ord(c) <= b for a, b in rs) for c in ls) / len(ls)


def validate(language: str, lines: list[str], cfg: dict | None = None) -> list[str]:
    cfg = cfg or C.load()
    prof = cfg["language_profiles"].get(language)
    if not prof:
        return [f"no language profile for {language!r}"]
    out = []
    for i, t in enumerate(lines, 1):
        if not isinstance(t, str) or not t.strip():
            out.append(f"line {i}: empty"); continue
        if _CTRL.search(t):
            out.append(f"line {i}: contains a control, zero-width, BOM or U+FFFD character (usually an encoding problem)")
        if normalise(t) != t:
            out.append(f"line {i}: not NFC-normalised (run it through unicodedata.normalize('NFC', ...))")
        if prof["min_script_share"] > 0:
            sh = script_share(t, prof)
            if sh < prof["min_script_share"] and letters(t):
                out.append(f"line {i}: only {sh:.0%} of the letters are {prof['script']} script; {prof['name']} needs at least {prof['min_script_share']:.0%}"
                           + (f" ({prof['note']})" if prof.get("note") else ""))
        elif language == "en":
            other = re.search(r"[\u0900-\u097F\u0B00-\u0B7F]", t)
            if other and script_share(t, {"unicode_ranges": ["0900-097F", "0B00-0B7F"]}) > 0.5:
                out.append(f"line {i}: mostly Indic script but the video language is English; set `language`")
    return out
