"""Design library: the seed is valid, ranking is deterministic and shows its reasons, evidence can only demote or promote
through the allowed fields, and nothing is 'validated' without a passing render."""
import copy
import json

import pytest

from contentos.intelligence import designs


@pytest.fixture(scope="module")
def lib():
    doc, entries = designs.load(overlay={})
    return doc, entries


def test_seed_is_valid(lib):
    doc, entries = lib
    assert designs.validate(doc, entries) == []


def test_seed_has_breadth(lib):
    _, entries = lib
    kinds = {}
    for e in entries.values():
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    assert kinds["frame_preset"] >= 13 and kinds["palette"] >= 9 and kinds["visual_style"] >= 8
    assert kinds["shader_transition"] >= 14 and kinds["css_transition"] >= 30


def test_every_topic_has_options_in_every_kind(lib):
    doc, entries = lib
    for topic in doc["vocabulary"]["topics"]:
        res = designs.recommend(entries, topic=topic)
        for kind in ("frame_preset", "palette", "shader_transition", "css_transition"):
            assert res[kind], f"no {kind} for topic {topic}"


def test_ai_dark_futuristic_prefers_data_drift(lib):
    _, entries = lib
    res = designs.recommend(entries, topic="ai-ml", moods=("futuristic",), register="dark", energy="medium",
                            aspect="9:16")
    assert res["visual_style"][0][1] == "style:data-drift"
    assert res["palette"][0][1] == "palette:dark-premium"


def test_reasons_add_up_to_score(lib):
    _, entries = lib
    res = designs.recommend(entries, topic="security", moods=("raw",), energy="high")
    for rows in res.values():
        for pts, _, _, why in rows:
            assert pts == sum(int(w.split()[-1]) for w in why)


def test_deterministic_order(lib):
    _, entries = lib
    a = designs.recommend(entries, topic="science", moods=("calm",))
    b = designs.recommend(dict(reversed(list(entries.items()))), topic="science", moods=("calm",))
    assert {k: [r[1] for r in v] for k, v in a.items()} == {k: [r[1] for r in v] for k, v in b.items()}


def test_unsupported_aspect_is_excluded(lib):
    _, entries = lib
    e = copy.deepcopy(entries)
    e["preset:broadside"]["aspects"] = ["16:9"]
    res = designs.recommend(e, topic="security", aspect="9:16", kinds=["frame_preset"], top={"frame_preset": 20})
    assert "preset:broadside" not in [r[1] for r in res["frame_preset"]]


def test_avoid_excludes(lib):
    _, entries = lib
    res = designs.recommend(entries, topic="ai-ml", avoid={"preset:cobalt-grid"}, kinds=["frame_preset"])
    assert "preset:cobalt-grid" not in [r[1] for r in res["frame_preset"]]


def test_failed_entries_hidden_unless_asked(lib):
    _, entries = lib
    e = copy.deepcopy(entries)
    e["shader:chromatic-split"]["verified"] = {"result": "fail", "evidence": "x"}
    shown = [r[1] for r in designs.recommend(e, topic="ai-ml", kinds=["shader_transition"])["shader_transition"]]
    assert "shader:chromatic-split" not in shown
    shown = [r[1] for r in designs.recommend(e, topic="ai-ml", kinds=["shader_transition"], include_failed=True,
                                              top={"shader_transition": 20})["shader_transition"]]
    assert "shader:chromatic-split" in shown


def test_slow_cost_penalty(lib):
    _, entries = lib
    rows = designs.recommend(entries, topic="ai-ml", kinds=["shader_transition"], prefer_fast=True,
                             top={"shader_transition": 20})["shader_transition"]
    assert rows and all("slow render -1" in r[3] for r in rows)


def test_overlay_only_touches_allowed_fields(tmp_path):
    seed = tmp_path / "seed.json"
    doc = json.loads(designs.SEED.read_text())
    seed.write_text(json.dumps(doc))
    overlay = {"preset:broadside": {"confidence": "experimental", "evidence_count": 2, "topics": ["kids-education"],
                                    "verified": {"result": "pass"}},
               "preset:does-not-exist": {"confidence": "preferred"}}
    _, entries = designs.load(seed, overlay=overlay)
    assert entries["preset:broadside"]["confidence"] == "experimental"
    assert entries["preset:broadside"]["topics"] != ["kids-education"]
    assert "preset:does-not-exist" not in entries


def test_validated_requires_a_passing_render(lib):
    doc, entries = lib
    e = copy.deepcopy(entries)
    e["preset:broadside"]["confidence"] = "validated"
    assert any("requires verified.result" in p for p in designs.validate(doc, e))
    e["preset:broadside"]["verified"] = {"result": "pass"}
    assert not any("preset:broadside" in p and "requires" in p for p in designs.validate(doc, e))


def test_bad_tag_is_reported(lib):
    doc, entries = lib
    e = copy.deepcopy(entries)
    e["palette:monochrome"]["moods"] = ["spicy"]
    assert any("spicy" in p for p in designs.validate(doc, e))


def test_cli_exit_codes(tmp_path, capsys):
    assert designs.main(["validate"]) == 0
    assert designs.main(["recommend", "--topic", "ai-ml", "--aspect", "9:16"]) == 0
    assert designs.main(["show", "nope"]) == 1
    assert designs.main(["--seed", str(tmp_path / "missing.json"), "validate"]) == 2
