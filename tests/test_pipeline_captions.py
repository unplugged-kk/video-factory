"""Track A caption timing: script words timed by sequence alignment to the ASR words.

Captions used to be timed by a proportional index into the ASR list (pipeline.py: `asr[int(k * n / len(toks))]`), so a single
ASR insertion or deletion shifted every later caption on that line. These tests pin the aligned behaviour, the even-spacing
fallback when ASR is unavailable, and the fact that the compose path still calls the helper rather than a proportional map.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import pipeline  # noqa: E402

STEP = 0.5


def asr(words, step=STEP):
    """words_for returns [(text, start, end)]; a take costs `step` seconds per word."""
    return [(w, round(i * step, 3), round(i * step + step - 0.1, 3)) for i, w in enumerate(words)]


def starts(wl):
    return [round(x[1], 3) for x in wl]


def test_asr_insertion_keeps_later_captions_on_their_own_onset():
    toks = "the model picks one tool".split()
    heard = asr("the model um picks one tool".split())          # whisper heard an extra word
    wl = pipeline.caption_words(toks, heard, d=5.0)
    assert [w for w, _, _ in wl] == toks                        # the caption shows the script's words
    # 'picks', 'one' and 'tool' keep their true ASR onsets; a proportional index map would put them at 1.0, 1.5 and 2.0
    assert starts(wl) == [0.0, 0.5, 1.5, 2.0, 2.5]


def test_missing_asr_words_are_interpolated_and_stay_monotonic():
    wl = pipeline.caption_words("a b c d e".split(), asr(["a", "e"]), d=5.0)
    st = starts(wl)
    # 'b', 'c' and 'd' were not in the transcript: they land between the two spoken onsets, in order
    assert st == [0.0, 0.4, 0.45, 0.5, 0.5]
    assert st == sorted(st) and all(w[2] > w[1] for w in wl)


def test_no_asr_falls_back_to_even_spacing_over_the_take():
    toks = "five words in this line".split()
    wl = pipeline.caption_words(toks, None, d=3.35)             # dur(wav) + 0.35, as s_compose passes it
    assert starts(wl) == [0.0, 0.6, 1.2, 1.8, 2.4]
    assert all(round(w[2] - w[1], 3) == 0.6 for w in wl)


def test_empty_asr_also_falls_back():
    assert starts(pipeline.caption_words("one two".split(), [], d=1.35)) == [0.0, 0.5]


def test_script_spelling_survives_a_case_insensitive_match():
    wl = pipeline.caption_words(["Humans", "beat", "machines"], asr(["humans", "beat", "machines"]), d=2.0)
    assert [w for w, _, _ in wl] == ["Humans", "beat", "machines"]
    assert starts(wl) == [0.0, 0.5, 1.0]


def test_compose_uses_the_aligned_helper():
    src = pipeline.s_compose.__wrapped__ if hasattr(pipeline.s_compose, "__wrapped__") else pipeline.s_compose
    body = __import__("inspect").getsource(src)
    assert "caption_words(toks, asr, d)" in body
    assert "len(asr)" not in body                               # the proportional index map is gone
