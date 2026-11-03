"""Edit-distance metrics for the benchmark (no jiwer dependency). WER on whitespace tokens, CER on characters, after
normalisation that drops punctuation, lowercases Latin and folds Devanagari nukta forms, so scoring sees words, not marks."""
import re
import unicodedata

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower()
    s = s.replace("\u093c", "")                      # nukta: ज़ vs ज are scored as one letter (ASR rarely keeps it)
    s = s.replace("।", " ")
    return re.sub(r"\s+", " ", _PUNCT.sub(" ", s)).strip()


def _lev(a, b) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def wer(ref: str, hyp: str) -> float:
    r, h = normalize(ref).split(), normalize(hyp).split()
    return _lev(r, h) / max(len(r), 1)


def cer(ref: str, hyp: str) -> float:
    r, h = normalize(ref).replace(" ", ""), normalize(hyp).replace(" ", "")
    return _lev(r, h) / max(len(r), 1)
