"""Design library: the seed is valid, ranking is deterministic and shows its reasons, evidence can only touch the allowed
fields, and the three concepts stay separate: AVAILABLE (exists upstream), VALIDATED (passed the required checks in a named
environment) and RECOMMENDED (fits the request; a fit score that validation cannot change)."""
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


CLOUD, MAC = "cloud-linux-swiftshader-hf0.8.114", "mac-hf0.8.114"


def test_failed_in_selected_env_is_hidden_unless_asked(lib):
    doc, entries = lib
    val = doc["validation"]
    shown = lambda **kw: [r[1] for r in designs.recommend(entries, topic="ai-ml", kinds=["shader_transition"], validation=val,
                                                          top={"shader_transition": 20}, **kw)["shader_transition"]]
    assert "shader:sdf-iris" not in shown(env=CLOUD)                     # failed in cloud
    assert "shader:sdf-iris" in shown(env=CLOUD, include_failed=True)
    assert "shader:sdf-iris" in shown(env=MAC)                           # untested on the Mac: not hidden, not validated


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
                                    "validations": [{"environment": MAC}]},
               "preset:does-not-exist": {"confidence": "preferred"}}
    _, entries = designs.load(seed, overlay=overlay)
    assert entries["preset:broadside"]["confidence"] == "experimental"
    assert entries["preset:broadside"]["topics"] != ["kids-education"]
    assert entries["preset:broadside"]["validations"] == [{"environment": MAC}]
    assert "preset:does-not-exist" not in entries


def _rec(**kw):
    r = {"environment": MAC, "level": "rendered", "result": "pass", "date": "2026-10-12", "evidence": "x", "checks": {}}
    r.update(kw)
    return r


def test_rendered_pass_needs_every_required_check(lib):
    doc, entries = lib
    e = copy.deepcopy(entries)
    e["css-transition:push-slide"]["validations"] = [_rec(checks={"hyperframes_check": True})]
    assert any("needs checks" in p for p in designs.validate(doc, e))
    e["css-transition:push-slide"]["validations"] = [_rec(checks={c: True for c in doc["validation"]["required"]["css_transition"]})]
    assert not any("push-slide" in p for p in designs.validate(doc, e))


def test_a_render_without_errors_is_not_validation(lib):
    doc, entries = lib
    e = entries["css-transition:push-slide"]
    only_check = dict(e, validations=[_rec(checks={"hyperframes_check": True})])
    assert designs.status(only_check, doc["validation"], MAC) == "partial"


def test_status_levels_and_environments(lib):
    doc, entries = lib
    val = doc["validation"]
    full = {c: True for c in val["required"]["css_transition"]}
    base = entries["css-transition:push-slide"]
    assert designs.status(base, val, CLOUD) == "validated"
    assert designs.status(base, val, MAC) == "unvalidated"                 # cloud evidence never stands in for the Mac
    assert designs.status(dict(base, validations=[_rec(level="structural")]), val, MAC) == "structural"
    assert designs.status(dict(base, validations=[_rec(checks=full)]), val, MAC) == "validated"
    assert designs.status(dict(base, validations=[_rec(checks=full), _rec(result="fail", date="2026-10-13")]), val, MAC) == "failed"


def test_reviewed_needs_a_named_reviewer(lib):
    doc, entries = lib
    e = copy.deepcopy(entries)
    full = {c: True for c in doc["validation"]["required"]["css_transition"]}
    e["css-transition:push-slide"]["validations"] = [_rec(level="reviewed", checks=full)]
    assert any("reviewer" in p for p in designs.validate(doc, e))


def test_unknown_environment_and_missing_evidence_are_reported(lib):
    doc, entries = lib
    e = copy.deepcopy(entries)
    e["css-transition:push-slide"]["validations"] = [_rec(environment="my-laptop", evidence="")]
    probs = designs.validate(doc, e)
    assert any("not a named environment" in p for p in probs) and any("evidence is required" in p for p in probs)


def test_validation_never_changes_the_fit_score(lib):
    # the old confidence bonus put a once-used transition above equally good fits; fit and validation are now separate
    _, entries = lib
    a = designs.recommend(entries, topic="ai-ml", moods=("precise",), energy="medium", kinds=["css_transition"], top={"css_transition": 40})
    e = copy.deepcopy(entries)
    e["css-transition:push-slide"]["validations"] = []
    b = designs.recommend(e, topic="ai-ml", moods=("precise",), energy="medium", kinds=["css_transition"], top={"css_transition": 40})
    sc = lambda res: {r[1]: r[0] for r in res["css_transition"]}
    assert sc(a) == sc(b)
    assert sc(a)["css-transition:push-slide"] == sc(a)["css-transition:circle-iris"] == 7


def test_require_validated_filters_and_needs_an_env(lib):
    doc, entries = lib
    rows = designs.recommend(entries, topic="ai-ml", kinds=["css_transition"], env=CLOUD, validation=doc["validation"],
                             require_validated=True)["css_transition"]
    assert {r[1] for r in rows} <= {"css-transition:push-slide", "css-transition:blur-crossfade"} and rows
    with pytest.raises(designs.DesignError):
        designs.recommend(entries, topic="ai-ml", require_validated=True)


def test_every_entry_is_available_and_no_shader_is_validated_anywhere(lib):
    doc, entries = lib
    assert all(e["available"] is True for e in entries.values())
    for e in entries.values():
        if e["kind"] == "shader_transition":
            assert not any(designs.status(e, doc["validation"], env) == "validated" for env in doc["validation"]["environments"])


def test_bad_tag_is_reported(lib):
    doc, entries = lib
    e = copy.deepcopy(entries)
    e["palette:monochrome"]["moods"] = ["spicy"]
    assert any("spicy" in p for p in designs.validate(doc, e))


def test_cli_exit_codes(tmp_path, capsys):
    assert designs.main(["validate"]) == 0
    assert designs.main(["recommend", "--topic", "ai-ml", "--aspect", "9:16"]) == 0
    assert designs.main(["recommend", "--topic", "ai-ml", "--env", "nope"]) == 2
    assert designs.main(["show", "nope"]) == 1
    assert designs.main(["--seed", str(tmp_path / "missing.json"), "validate"]) == 2


def test_shaders_are_partial_on_the_mac_and_failed_in_the_cloud(lib):
    # Mac sampler evidence exists but lacks captions/check/second render, so it is partial, never validated; cloud stays failed
    doc, entries = lib
    for e in entries.values():
        if e["kind"] == "shader_transition":
            assert designs.status(e, doc["validation"], MAC) == "partial"
            assert designs.status(e, doc["validation"], CLOUD) == "failed"
