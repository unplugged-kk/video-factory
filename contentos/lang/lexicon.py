"""Technical-term lexicon: Latin <-> Devanagari. Used (1) to transliterate Latin tokens before Hindi TTS (Hinglish strategy
`translit`) and (2) to fold scripts when scoring ASR, since Whisper writes English technical terms in Latin even when the
reference spells them in Devanagari. Small and explicit on purpose: unknown words are reported, never guessed."""
import re

# lower-case Latin -> preferred Devanagari spelling (extend per series; tests pin the benchmark vocabulary)
TERMS = {
    "kubernetes": "कुबेरनेट्स", "pod": "पॉड", "pods": "पॉड", "unit": "यूनिट", "deploy": "डिप्लॉय", "container": "कंटेनर",
    "containers": "कंटेनर", "same": "सेम", "network": "नेटवर्क", "storage": "स्टोरेज", "share": "शेयर", "fail": "फेल",
    "scheduler": "शेड्यूलर", "healthy": "हेल्दी", "node": "नोड", "start": "स्टार्ट", "server": "सर्वर", "docker": "डॉकर",
    "cluster": "क्लस्टर", "api": "एपीआई", "gpu": "जीपीयू", "model": "मॉडल", "cloud": "क्लाउड",
}
_LATIN = re.compile(r"[A-Za-z][A-Za-z\-']*")


def to_devanagari(text: str) -> tuple[str, list[str]]:
    """Replace known Latin terms; return (new text, unknown Latin words left in place)."""
    unknown = []
    def sub(m):
        w = m.group(0).lower()
        if w in TERMS:
            return TERMS[w]
        unknown.append(m.group(0))
        return m.group(0)
    return _LATIN.sub(sub, text), unknown


def fold(text: str) -> str:
    """Canonical form for scoring: known Latin terms become their Devanagari spelling (both sides get the same treatment)."""
    return to_devanagari(text)[0]


def term_hits(text: str, terms: list[str]) -> dict[str, bool]:
    t = text.lower()
    out = {}
    for term in terms:
        latin = term.lower() if term.isascii() else next((k for k, v in TERMS.items() if v == term), None)
        deva = term if not term.isascii() else TERMS.get(term.lower())
        out[term] = bool((latin and re.search(rf"\b{re.escape(latin)}s?\b", t)) or (deva and deva in text))
    return out
