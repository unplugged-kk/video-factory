"""timeline/1 in shadow mode: derive, validate and compare against the legacy data. No renderer, no ASR, no pipeline.py.
A final test runs against the real Ep3 project artifacts when they are present (they live in the git-ignored workspace)."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.production import timeline  # noqa: E402


def make(sources=None, cue_word=2):
    lines = [
        {"id": "a", "title": "A", "t0": 0.0, "t1": 3.0, "words": [("one", 0.1, 0.5), ("two", 0.6, 1.0), ("three", 1.1, 2.0)],
         "sources": sources or ["matched", "matched", "matched"]},
        {"id": "b", "title": "B", "t0": 3.0, "t1": 6.0, "words": [("four", 3.1, 3.5), ("five", 3.6, 4.4)], "sources": ["matched", "span"]},
    ]
    return timeline.build_timeline("job", 30, 6.0, lines, [{"scene": "a", "word": cue_word, "do": "x"}, {"scene": "b", "word": 3, "do": "y"}],
                                   alignment={"match_ratio": 1.0, "wer": 0.0})


def codes(tl, level=None):
    return [i["code"] for i in timeline.validate(tl) if level in (None, i["level"])]


def legacy_of(tl):
    return {"duration": tl["duration_s"],
            "scenes": [{"id": s["id"], "start": s["t0"], "dur": round(s["t1"] - s["t0"], 3)} for s in tl["scenes"]],
            "captions": {s["id"]: [[w["text"], w["t0"], w["t1"]] for w in tl["words"][s["w0"]:s["w1"] + 1]] for s in tl["scenes"]},
            "cues": {s["id"]: [c["t"] for c in tl["cues"] if c["scene"] == s["id"]] for s in tl["scenes"]}}


def test_clean_timeline_validates_and_carries_the_unverified_label():
    tl = make()
    assert codes(tl) == []
    assert tl["schema"] == "timeline/1" and tl["alignment"]["timing_trust"] == "asr-derived-unverified"
    assert tl["alignment"]["verified_anchors"] == [] and tl["audio"]["rights"]["status"] == "unassessed"
    assert [c["t"] for c in tl["cues"]] == [1.1, 3.1]      # a cue's time is the start of its anchor word (three, four)
    assert [c["id"] for c in tl["cues"]] == ["c01-a", "c02-b"]


def test_word_order_and_negative_duration_are_errors():
    tl = make()
    tl["words"][1]["t0"] = 0.0                                    # starts before word 0 (0.1)
    tl["words"][2]["t1"] = 0.5                                    # ends before it starts (1.1)
    assert {"word_order", "word_negative"} <= set(codes(tl, "error"))


def test_scene_gap_and_bad_end_are_errors():
    tl = make()
    tl["scenes"][1]["t0"] = 3.5
    assert "scene_gap" in codes(tl, "error")
    tl = make()
    tl["duration_s"] = 7.0
    assert "end" in codes(tl, "error")


def test_word_outside_its_scene_is_an_error():
    tl = make()
    tl["words"][2]["t1"] = 3.4                                    # runs into scene b
    assert "word_outside_scene" in codes(tl, "error")


def test_scene_below_min_hold_is_reported_not_changed():
    tl = make()
    tl["scenes"][0]["min_hold_s"] = 4.0
    assert "min_hold" in codes(tl, "warning")
    assert tl["scenes"][0]["t1"] == 3.0                           # untouched


def test_cue_on_interpolated_word_is_flagged_and_bad_anchors_are_errors():
    tl = make(sources=["matched", "interpolated", "matched"], cue_word=1)
    assert "cue_on_interpolated_word" in codes(tl, "warning")
    tl = make()
    tl["cues"][0]["at"]["word"] = 99
    assert "cue_word" in codes(tl, "error")
    tl = make()
    tl["cues"][0]["at"]["word"] = 4                               # a real word, but in scene b
    assert "cue_not_in_scene" in codes(tl, "error")


def test_timing_trust_cannot_be_upgraded_without_anchors():
    tl = make()
    tl["alignment"]["timing_trust"] = "verified"
    assert "trust" in codes(tl, "error")
    tl["alignment"]["verified_anchors"] = [{"word": 0, "t": 0.1}]
    assert "trust" not in codes(tl)


def test_word_sources_label_matched_span_and_interpolated():
    assert timeline.word_sources(["a", "spellchecker", "flags"], ["a", "spell", "checker", "flags"]) == ["matched", "span", "matched"]
    assert timeline.word_sources(["a", "b", "c", "d"], ["a", "d"]) == ["matched", "interpolated", "interpolated", "matched"]
    assert timeline.word_sources(["Humans", "beat"], ["humans", "beat!"]) == ["matched", "matched"]


def test_legacy_comparison_passes_and_catches_a_one_frame_shift():
    tl = make()
    assert timeline.compare_legacy(tl, legacy_of(tl))["ok"]
    T = legacy_of(tl)
    T["captions"]["a"][1][1] += 0.034                             # one frame at 30 fps
    res = timeline.compare_legacy(tl, T)
    assert not res["ok"] and any("two" in d for d in res["diffs"])
    T = legacy_of(tl)
    T["cues"]["b"] = [3.0]
    assert not timeline.compare_legacy(tl, T)["ok"]
    T = legacy_of(tl)
    T["scenes"][1]["start"] = 3.2
    assert not timeline.compare_legacy(tl, T)["ok"]


def test_the_module_does_not_import_the_pipeline_or_a_renderer():
    src = Path(timeline.__file__).read_text(encoding="utf-8")
    for banned in ("pipeline", "hyperframes", "subprocess", "requests", "urllib"):
        assert f"import {banned}" not in src and f"from . import {banned}" not in src and f"from .{banned}" not in src


EP3 = Path(__file__).resolve().parent.parent / "workspace/projects/ep3-what-is-generative-ai"


@pytest.mark.skipif(not (EP3 / "audio/timing.json").exists(), reason="Ep3 workspace artifacts not present (git-ignored)")
def test_real_ep3_project_builds_validates_and_matches_legacy():
    tl = timeline.build_from_project(EP3)
    assert [i for i in timeline.validate(tl) if i["level"] == "error"] == []
    legacy = json.loads((EP3 / "project/timings.js").read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";"))
    cmp = timeline.compare_legacy(tl, legacy)
    assert cmp["ok"], cmp["diffs"][:3]
    assert len(tl["words"]) == 130 and len(tl["scenes"]) == 6
    spans = [w["text"] for w in tl["words"] if w["source"] == "span"]
    assert spans == ["spellchecker", "favourite"]                 # whisper split one and respelled the other; both timed from the ASR span
