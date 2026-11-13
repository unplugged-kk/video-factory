"""scenekit: style registry, planner rules, authored-data validation, and a hermetic compose smoke (no render, no ASR)."""
import copy
import json
import re
from pathlib import Path

import pytest
import yaml

from contentos.scenekit import compose as skc
from contentos.scenekit import planner, primitives, styles

ROOT = Path(__file__).resolve().parent.parent
KAFKA = yaml.safe_load((ROOT / "examples/styles/kafka-events.yaml").read_text())


def spec(**over):
    s = copy.deepcopy(KAFKA)
    s.update(over)
    return s


def text_only(n, **over):
    s = spec(**over)
    s["script"] = [{"say": f"Line number {i} says something plain.", "headline": f"Plain headline {i}", "tag": f"T{i}"} for i in range(n)]
    return s


# ---- styles --------------------------------------------------------------------------------------------------------

def test_registry_is_valid_and_styles_are_structurally_distinct():
    assert len(styles.STYLES) >= 5
    assert styles.validate() == []
    assert styles.distinct() == []


def test_a_recolour_cannot_pass_as_a_new_style():
    clone = copy.deepcopy(styles.STYLES["clean-explainer"])
    clone["tokens"]["accent"] = "#ff0000"
    styles.STYLES["recolour-test"] = clone
    try:
        assert any(b == "recolour-test" or a == "recolour-test" for a, b, _ in styles.distinct())
    finally:
        del styles.STYLES["recolour-test"]


@pytest.mark.parametrize("seed", [0, 1, 7, 99])
def test_grounds_cycle_so_three_scenes_use_three_grounds(seed):
    for sid in styles.STYLES:
        assert len({styles.ground_for(sid, i, seed) for i in (1, 2, 3)}) == 3


# ---- planner: validation fails closed ------------------------------------------------------------------------------

def test_stat_without_source_or_illustrative_flag_is_blocked():
    errs = planner.validate_visual({"type": "stat", "value": "3x"})
    assert any("source" in e and "illustrative" in e for e in errs)
    assert planner.validate_visual({"type": "stat", "value": "3x", "source": "benchmark X"}) == []
    assert planner.validate_visual({"type": "stat", "value": "3x", "illustrative": True}) == []


def test_diagram_edges_must_use_declared_nodes_and_labels_must_fit():
    bad = {"type": "diagram", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "edges": [["a", "zzz"]]}
    assert planner.validate_visual(bad)
    long_label = {"type": "diagram", "nodes": [{"id": "a", "label": "x" * 40}, {"id": "b", "label": "B"}], "edges": [["a", "b"]]}
    assert any("max" in e for e in planner.validate_visual(long_label))


def test_code_scene_requires_authored_code_within_limits():
    assert planner.validate_visual({"type": "code"})
    assert planner.validate_visual({"type": "code", "code": "x = 1\n" * 30})
    assert planner.validate_visual({"type": "code", "code": "x" * 80})
    assert planner.validate_visual({"type": "code", "code": "a\nb", "focus": [5]})
    assert planner.validate_visual({"type": "code", "code": "a\nb", "focus": [2]}) == []


def test_plan_refuses_a_spec_with_invalid_visuals():
    s = spec()
    s["script"][1]["visual"]["edges"] = [["prod", "nope"]]
    with pytest.raises(ValueError, match="visual validation failed"):
        planner.plan(s)


# ---- planner: choice rules -----------------------------------------------------------------------------------------

def test_text_only_spec_never_gets_data_backed_scenes():
    for sid in styles.STYLES:
        pl = planner.plan(text_only(8, visual_style=sid))
        assert not any(sc["data_backed"] for sc in pl["scenes"]), sid


def test_authored_visual_type_is_honoured():
    pl = planner.plan(spec(visual_style="clean-explainer"))
    assert [sc["type"] for sc in pl["scenes"] if sc["data_backed"]] == ["diagram", "compare", "steps"]


@pytest.mark.parametrize("sid", sorted(styles.STYLES))
@pytest.mark.parametrize("seed", [1, 5, 42])
def test_text_only_scenes_do_not_repeat_more_than_twice(sid, seed):
    s = text_only(10, visual_style={"id": sid, "seed": seed})
    pl = planner.plan(s)
    run = best = 1
    for a, b in zip(pl["scenes"], pl["scenes"][1:]):
        run = run + 1 if a["type"] == b["type"] else 1
        best = max(best, run)
    assert best <= 2, (sid, seed, [sc["type"] for sc in pl["scenes"]])
    assert planner.variety_report(pl)["longest_identical_run"] <= 2


def test_plan_is_deterministic_and_seed_is_recorded():
    a, b = planner.plan(spec(visual_style={"id": "kinetic-type", "seed": 3})), planner.plan(spec(visual_style={"id": "kinetic-type", "seed": 3}))
    assert a == b and a["style"]["seed"] == 3 and a["style"]["version"] == 1


def test_auto_selection_is_recorded_and_explicit_overrides_it():
    auto = planner.plan(spec(visual_style="auto"))
    assert auto["style"]["selection_mode"] == "auto" and auto["style"]["id"] == "blueprint-architecture"
    assert auto["style"]["recommendation"][0]["id"] == "blueprint-architecture"
    explicit = planner.plan(spec(visual_style="editorial-magazine"))
    assert explicit["style"]["selection_mode"] == "explicit" and explicit["style"]["id"] == "editorial-magazine"


def test_style_version_mismatch_and_unknown_style_are_errors():
    with pytest.raises(ValueError, match="version"):
        planner.resolve_style(spec(visual_style={"id": "clean-explainer", "version": 9}))
    with pytest.raises(ValueError, match="unknown visual style"):
        planner.resolve_style(spec(visual_style="nope"))


def test_variety_report_blocks_a_degenerate_plan():
    pl = planner.plan(text_only(6, visual_style="clean-explainer"))
    for sc in pl["scenes"]:                      # force the legacy failure mode: every scene identical
        sc.update(type="statement", motion="rise")
    rep = planner.variety_report(pl)
    assert rep["status"] == "BLOCK"
    assert {c["id"] for c in rep["checks"] if c["status"] == "BLOCK"} == {"V1.signature_diversity"}
    assert all({"id", "status", "scene", "evidence", "remediation", "human_review"} <= set(c) for c in rep["checks"])


# ---- primitives ----------------------------------------------------------------------------------------------------

G = {"sw": 940, "sh": 880, "U": 1080, "portrait": True, "tk": styles.STYLES["blueprint-architecture"]["tokens"]}


def test_diagram_is_time_addressable_and_deterministic():
    v = KAFKA["script"][1]["visual"]
    html1, js1 = primitives.diagram(v, "s2", 5.0, 6.0, G)
    html2, js2 = primitives.diagram(v, "s2", 5.0, 6.0, G)
    assert (html1, js1) == (html2, js2)
    assert "onUpdate" not in js1 and "Math.random" not in js1 and "Date" not in js1
    assert len(re.findall(r'<path id="s2e\d+"', html1)) == 4 and len(re.findall(r'<g id="s2n\d+"', html1)) == 4


def test_diagram_handles_a_cycle_without_looping_forever():
    v = {"type": "diagram", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, {"id": "c", "label": "C"}],
         "edges": [["a", "b"], ["b", "c"], ["c", "a"]]}
    html, _ = primitives.diagram(v, "s1", 0, 5, G)
    assert html.count("<path id=") == 3


def test_code_scene_escapes_html_and_shows_only_authored_lines():
    html, _ = primitives.code({"type": "code", "code": "print('<b>&')"}, "s1", 0, 5, G)
    body = html.split('class="cbody"')[1]
    assert "&lt;b&gt;&amp;" in body and "<b>" not in body


def test_stat_footer_states_source_or_illustrative():
    h1, _ = primitives.stat({"type": "stat", "value": "2x", "source": "Vendor doc"}, "s1", 0, 4, G)
    h2, _ = primitives.stat({"type": "stat", "value": "2x", "illustrative": True}, "s1", 0, 4, G)
    assert "Source: Vendor doc" in h1 and "Illustrative data" in h2


def test_stat_footer_note_overrides_default_for_non_english_videos():
    h, _ = primitives.stat({"type": "stat", "value": "2x", "illustrative": True, "note": "उदाहरण"}, "s1", 0, 4, G)
    assert "उदाहरण" in h and "Illustrative data" not in h


# ---- compose (hermetic: fake audio length, no ASR, no render) -------------------------------------------------------

def _ctx(tmp_path, s, res=(1080, 1920)):
    (tmp_path / "audio").mkdir()
    for i in range(1, len(s["script"]) + 1):
        (tmp_path / "audio" / f"{i:02d}.wav").write_bytes(b"RIFF")
    return {"id": s["content_id"], "dir": tmp_path, "spec": s, "res": res}


def _run(tmp_path, s, res=(1080, 1920)):
    ctx = _ctx(tmp_path, s, res)
    calls = []
    skc.compose(ctx, dur=lambda p: 4.0, words_for=lambda *a, **k: None,
                caption_words=lambda toks, asr, d: [(w, k * 0.3, k * 0.3 + 0.25) for k, w in enumerate(toks)],
                stage=lambda *a, **k: calls.append(a[1]), lint_cmd=["lint"])
    return ctx, calls


@pytest.mark.parametrize("res", [(1080, 1920), (1920, 1080)])
def test_compose_writes_a_valid_project_and_reports(tmp_path, res):
    ctx, calls = _run(tmp_path, spec(visual_style="clean-explainer"), res)
    html = (tmp_path / "project/index.html").read_text()
    assert len(re.findall(r'class="scene clip', html)) == 6
    assert f'data-width="{res[0]}"' in html and 'data-orient="' in html
    assert json.loads((tmp_path / "project/hyperframes.json").read_text())["width"] == res[0]
    plan = json.loads((tmp_path / "visual-plan.json").read_text())
    rep = json.loads((tmp_path / "variety-report.json").read_text())
    assert plan["style"]["id"] == "clean-explainer" and rep["status"] in ("PASS", "WARN") and calls == [["lint"]]
    assert "Math.random" not in html and "onUpdate" not in html


def test_compose_is_byte_reproducible(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    _run(a, spec(visual_style={"id": "kinetic-type", "seed": 4}))
    _run(b, spec(visual_style={"id": "kinetic-type", "seed": 4}))
    assert (a / "project/index.html").read_bytes() == (b / "project/index.html").read_bytes()


@pytest.mark.parametrize("sid", sorted(styles.STYLES))
def test_every_style_composes_the_same_script_with_distinct_markup(tmp_path, sid):
    d = tmp_path / sid
    d.mkdir()
    _run(d, spec(visual_style=sid))
    html = (d / "project/index.html").read_text()
    assert f"L-{styles.STYLES[sid]['layout']}" in html
    # grounds rotate: at least 3 distinct per-scene backgrounds are written inline (repo Rule A, ceil(6/2) = 3)
    assert len(set(re.findall(r'--bgcss:([^"]+)"', html))) >= 3


def test_composed_headlines_are_sized_to_fit_the_frame_width(tmp_path):
    # the widest word at the inline font-size the composer chose must fit the content width, in every style
    for sid, st in styles.STYLES.items():
        d = tmp_path / sid
        d.mkdir()
        s = text_only(3, visual_style=sid)
        s["script"][1]["headline"] = "Rebalancing Partitions"
        s["script"][1]["visual"] = {"type": "pullquote"}      # text-only hero size: the widest case
        _run(d, s)
        html = (d / "project/index.html").read_text()
        px = [int(x) for x in re.findall(r'<h1 id="h2" style="font-size:(\d+)px"', html)]
        assert px and px[0] * len("Rebalancing") * st["tokens"]["cw"] <= 1080 - 140 + 1, (sid, px)


def test_legacy_specs_do_not_route_to_scenekit():
    src = (ROOT / "contentos/pipeline.py").read_text()
    assert 'if ctx["spec"].get("visual_style"):' in src
