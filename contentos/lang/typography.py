"""Script-aware typography shared by BOTH Track A renderers (legacy template and scenekit): one place decides the font stack and the
CSS rules for Devanagari and Odia. Indic scripts need letter-spacing 0 (spacing breaks conjuncts), no forced uppercase, and a font that has
the glyphs; `hyperframes lint` also needs an @font-face per family (local() is accepted for macOS system fonts). Latin text gets nothing."""
from __future__ import annotations

import re

RANGES = {"odia": r"[\u0B00-\u0B7F]", "deva": r"[\u0900-\u097F]"}
STACKS = {
    "deva": '"Kohinoor Devanagari","Devanagari Sangam MN","Helvetica Neue",sans-serif',
    "odia": '"Oriya Sangam MN","Noto Sans Oriya","Helvetica Neue",sans-serif',
}
FACES = {   # family -> [(weight, local font name)]  (names verified against `system_profiler SPFontsDataType` on this Mac)
    "deva": {"Kohinoor Devanagari": [(400, "Kohinoor Devanagari Regular"), (700, "Kohinoor Devanagari Bold")], "Devanagari Sangam MN": [(400, "Devanagari Sangam MN")]},
    "odia": {"Oriya Sangam MN": [(400, "Oriya Sangam MN"), (700, "Oriya Sangam MN Bold")], "Noto Sans Oriya": [(400, "Noto Sans Oriya")]},
}


def script_kind(text: str) -> str:
    """odia if any Odia letter, else deva if any Devanagari, else latin."""
    return "odia" if re.search(RANGES["odia"], text) else "deva" if re.search(RANGES["deva"], text) else "latin"


def font_faces(kind: str) -> str:
    return "".join(f'@font-face{{font-family:"{fam}";font-weight:{w};src:local("{name}")}}'
                   for fam, faces in FACES.get(kind, {}).items() for w, name in faces)


def rule(kind: str, selectors: list[str], scope: str = "") -> str:
    """CSS forcing the Indic stack on `selectors` (optionally prefixed by `scope`, e.g. '[data-script=deva]')."""
    if kind not in STACKS:
        return ""
    sel = ",".join(f"{scope} {s}".strip() for s in selectors)
    return sel + "{letter-spacing:0!important;text-transform:none!important;font-family:" + STACKS[kind] + "!important}"


def block(kind: str, selectors: list[str], scope: str = "") -> str:
    """@font-face declarations + the rule; empty string for Latin so Latin projects carry no Indic font names."""
    return font_faces(kind) + rule(kind, selectors, scope) if kind in STACKS else ""
