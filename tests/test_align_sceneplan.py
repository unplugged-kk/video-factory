import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.production import align, sceneplan  # noqa: E402


def asr(words, step=0.5):
    return [{"text": w, "start": i * step, "end": i * step + 0.4} for i, w in enumerate(words)]


def test_exact_match_is_one_to_one():
    w, st = align.align_words("Your AI model never runs".split(), asr("your ai model never runs".split()))
    assert [x[1] for x in w] == [0, 0.5, 1.0, 1.5, 2.0]
    assert st["wer"] == 0 and st["match_ratio"] == 1


def test_asr_insertion_does_not_shift_later_words():
    script = "the model picks one tool".split()
    hyp = "the model um picks one tool".split()          # ASR heard an extra word
    w, st = align.align_words(script, asr(hyp))
    assert w[2][1] == 1.5 and w[3][1] == 2.0   # 'picks' and 'one' keep their true ASR times
    assert st["wer"] > 0


def test_missing_asr_word_is_interpolated_monotonic():
    w, _ = align.align_words("a b c d".split(), asr("a d".split()))
    starts = [x[1] for x in w]
    assert starts == sorted(starts) and w[0][1] == 0 and w[3][1] == 0.5


def test_wer_flags_wrong_audio():
    assert align.wer("one two three four".split(), "five six seven eight".split()) == 1.0


def test_scene_anchors_resolve_to_word_times():
    words = [(t, i * 1.0, i * 1.0 + 0.8) for i, t in enumerate("alpha beta gamma delta epsilon".split())]
    plan = {"scenes": [{"id": "a", "title": "A", "starts_at": 0}, {"id": "b", "title": "B", "starts_at": "gamma"}]}
    sc = sceneplan.resolve(plan, words, audio_end=5.0, lead=0.2, tail=2.0)
    assert sc[0]["t0"] == 0 and sc[0]["t1"] == sc[1]["t0"] == pytest.approx(1.8)
    assert sc[1]["t1"] == 7.0 and sc[1]["narration"] == "gamma delta epsilon"
    assert "| 1 A |" in sceneplan.storyboard_md(plan, sc, "t")


def test_unknown_anchor_phrase_raises():
    with pytest.raises(ValueError):
        sceneplan.resolve({"scenes": [{"id": "a", "title": "A", "starts_at": "nope"}]}, [("x", 0, 1)], 1.0)
