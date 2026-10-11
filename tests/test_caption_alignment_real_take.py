"""Track A caption timing on a real whisper transcript (Ep3 line 3, `audio/tx03/transcript.json`, trimmed to text/start/end).

Complements tests/test_pipeline_captions.py (synthetic cases): the real take has a repeated word ('a' x3, 'A' x2), the ASR split
'spellchecker' into 'spell'+'checker', and a leading 'A' that shares a boundary with the next word. The expected onsets are the
transcript's own onsets for every word it heard, so a proportional index map (the old behaviour) fails them by up to 1.1 s."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import pipeline  # noqa: E402

LINE = ("A spellchecker flags a mistake. A generative AI assistant can write your entire email from a simple instruction. "
        "Same computer, a completely different capability.")
ASR = [("A", 0.03, 0.09), ("spell", 0.09, 0.55), ("checker", 0.55, 1.19), ("flags", 1.19, 1.65), ("a", 1.65, 1.74),
       ("mistake.", 1.74, 2.42), ("A", 2.45, 2.5), ("generative", 2.5, 3.25), ("AI", 3.39, 3.55), ("assistant", 3.55, 4.3),
       ("can", 4.3, 4.55), ("write", 4.86, 4.88), ("your", 4.88, 5.02), ("entire", 5.02, 5.56), ("email", 5.62, 6.06),
       ("from", 6.09, 6.36), ("a", 6.36, 6.43), ("simple", 6.43, 6.88), ("instruction.", 6.88, 7.95), ("Same", 7.99, 8.29),
       ("computer,", 8.29, 9.12), ("a", 9.12, 9.17), ("completely", 9.17, 9.73), ("different", 9.74, 9.88),
       ("capability.", 10.41, 11.05)]
TOKS = LINE.split()


def old_proportional(toks, asr):
    """The behaviour before the fix (verbatim formula from pipeline.s_compose at HEAD), kept only to prove the test discriminates."""
    n = len(asr)
    return [(w, asr[min(int(k * n / len(toks)), n - 1)][1], asr[min(int((k + 1) * n / len(toks)), n) - 1][2]) for k, w in enumerate(toks)]


def test_every_heard_word_keeps_its_asr_onset():
    wl = pipeline.caption_words(TOKS, ASR, d=11.3)
    onset = {1: 0.09, 2: 1.19, 3: 1.65, 4: 1.74, 5: 2.45, 6: 2.5, 7: 3.39, 8: 3.55, 9: 4.3, 10: 4.86, 11: 4.88, 12: 5.02,
             13: 5.62, 14: 6.09, 15: 6.36, 16: 6.43, 17: 6.88, 18: 7.99, 19: 8.29, 20: 9.12, 21: 9.17, 22: 9.74, 23: 10.41}
    assert len(wl) == len(TOKS) == 24
    for k, t in onset.items():
        assert wl[k][1] == t, (TOKS[k], wl[k][1], t)


def test_a_split_word_is_timed_over_both_asr_pieces():
    wl = dict((w, (s, e)) for w, s, e in pipeline.caption_words(TOKS, ASR, d=11.3)[:2])
    assert wl["spellchecker"] == (0.09, 1.19)                   # 'spell' start .. 'checker' end


def test_order_is_monotonic_and_repeated_words_are_not_swapped():
    wl = pipeline.caption_words(TOKS, ASR, d=11.3)
    starts = [s for _, s, _ in wl]
    assert starts == sorted(starts)
    assert [w for w, _, _ in wl] == TOKS
    a_onsets = [s for w, s, _ in wl if w.lower() == "a"]          # 'A' (x2 at line start/mid) and 'a' (x3)
    assert a_onsets == [0.03, 1.65, 2.45, 6.36, 9.12]


def test_the_old_proportional_map_is_off_by_up_to_a_second_on_this_take():
    """Guards the guard: the same inputs through the old formula must fail the onsets above, otherwise the tests prove nothing."""
    old = old_proportional(TOKS, ASR)
    new = pipeline.caption_words(TOKS, ASR, d=11.3)
    errs = [abs(o[1] - n[1]) for o, n in zip(old, new)]
    assert max(errs) > 1.0 and sum(e > 0.15 for e in errs) >= 16


def test_end_of_line_extra_asr_word_does_not_move_earlier_words():
    heard = ASR + [("thanks", 11.1, 11.4)]                       # trailing hallucination
    wl = pipeline.caption_words(TOKS, heard, d=11.7)
    base = pipeline.caption_words(TOKS, ASR, d=11.3)
    assert [s for _, s, _ in wl] == [s for _, s, _ in base]


def test_leading_asr_noise_does_not_shift_the_line():
    heard = [("uh", 0.0, 0.03)] + ASR
    wl = pipeline.caption_words(TOKS, heard, d=11.3)
    base = pipeline.caption_words(TOKS, ASR, d=11.3)
    assert [s for _, s, _ in wl] == [s for _, s, _ in base]
