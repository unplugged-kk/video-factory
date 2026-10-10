"""Word timing for captions: align the SCRIPT words to ASR (whisper.cpp) word timestamps.
Captions always show the script's own spelling; ASR only supplies timing. Unlike a proportional index map, this uses a
sequence alignment, so an ASR insertion/deletion shifts only the words around it instead of every later caption.
Also reports a word error rate so a bad transcript (wrong audio, wrong script) fails loudly rather than drifting."""
import difflib
import re


def norm(w):
    return re.sub(r"[^a-z0-9']+", "", w.lower())


def wer(ref, hyp):
    """Word error rate (Levenshtein over normalised words), 0.0 = identical."""
    a, b = [norm(w) for w in ref if norm(w)], [norm(w) for w in hyp if norm(w)]
    if not a:
        return 0.0 if not b else 1.0
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1] / len(a)


def align_words(script_words, asr):
    """script_words: list[str]. asr: list of {text,start,end} (hyperframes transcript.json).
    Returns (words, stats): words = [(word, start, end)] monotonic, one per script word."""
    a = [norm(w) for w in script_words]
    b = [norm(x["text"]) for x in asr]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    t = [None] * len(a)
    matched = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            matched += i2 - i1
            for k in range(i2 - i1):
                t[i1 + k] = (asr[j1 + k]["start"], asr[j1 + k]["end"])
        elif tag == "replace" and i2 > i1 and j2 > j1:
            s, e = asr[j1]["start"], asr[j2 - 1]["end"]
            step = (e - s) / (i2 - i1)
            for k in range(i2 - i1):
                t[i1 + k] = (s + k * step, s + (k + 1) * step)
    # fill words with no ASR counterpart by interpolating between the nearest timed neighbours
    for i in range(len(t)):
        if t[i] is None:
            lo = next((j for j in range(i - 1, -1, -1) if t[j]), None)
            hi = next((j for j in range(i + 1, len(t)) if t[j]), None)
            s = t[lo][1] if lo is not None else (asr[0]["start"] if asr else 0.0)
            e = t[hi][0] if hi is not None else (asr[-1]["end"] if asr else s + 0.3)
            n = (hi if hi is not None else len(t)) - (lo + 1 if lo is not None else 0)
            k = i - (lo + 1 if lo is not None else 0)
            step = max(e - s, 0.05 * n) / n
            t[i] = (s + k * step, s + (k + 1) * step)
    out, last = [], 0.0
    for w, (s, e) in zip(script_words, t):
        s = max(s, last)
        e = max(e, s + 0.05)
        out.append((w, round(s, 3), round(e, 3)))
        last = s
    stats = {"script_words": len(a), "asr_words": len(b), "matched": matched,
             "match_ratio": round(matched / len(a), 4) if a else 1.0,
             "wer": round(wer(script_words, [x["text"] for x in asr]), 4)}
    return out, stats
