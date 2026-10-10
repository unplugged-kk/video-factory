import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.production import direction as dr  # noqa: E402
from contentos.production import director as dd  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures"
PLAN_FIX = FIX / "m2-dryrun-scene-plan.json"
SCRIPT_FIX = FIX / "m2-dryrun-script.txt"
PILOT_FIX = FIX / "pilot-001-scene-plan.json"
WORK = REPO / "workspace/experiments/m2-director-dryrun-001"
REGISTRY = REPO / "config/capabilities.json"


def entry(cid, kind="rule", status="installed", path="skills/x.md", **kw):
    e = {"id": cid, "name": cid, "kind": kind, "status": status, "purpose": "p", "path": path, "context": ["hyperframes"],
         "requires": [], "offline": True, "paid": False, "limitations": [], "fallback": None}
    if status != "installed":
        e["status_reason"] = f"{status} because of a test reason"
    e.update(kw)
    return e


def small_registry(tmp_path, extra=()):
    entries = [
        entry("hf.native:html-svg-css", kind="native"),
        entry("hf.rule:svg-path-draw"),
        entry("hf.rule:gone", path="skills/missing.md"),
        entry("opt:tool", status="available", path=None, fallback="hf.native:html-svg-css"),
        entry("cand:p5", kind="treatment", status="candidate", path=None, fallback="hf.native:html-svg-css"),
        entry("nope:filter", kind="treatment", status="unavailable", path=None),
        entry("lane:video", kind="lane", status="available", path=None),
        entry("paid:thing", kind="treatment", path=None, paid=True),
        entry("renderer:hyperframes", kind="renderer"),
    ] + list(extra)
    root = tmp_path / "repo"
    (root / "skills").mkdir(parents=True)
    (root / "skills/x.md").write_text("x", encoding="utf-8")
    (root / "config").mkdir()
    (root / "config/capabilities.json").write_text(json.dumps({"schema": "capabilities/1", "capabilities": entries}), encoding="utf-8")
    return dr.load_registry(root / "config/capabilities.json", root)


@pytest.fixture(scope="module")
def real_reg():
    return dr.load_registry(REGISTRY, REPO)


@pytest.fixture()
def plan():
    return json.loads(PLAN_FIX.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def script():
    return SCRIPT_FIX.read_text(encoding="utf-8")


# ---- select_capability --------------------------------------------------------------------------------------------

def test_installed_preference_is_chosen_without_substitution(tmp_path):
    s = dd.select_capability(small_registry(tmp_path), ["hf.rule:svg-path-draw"])
    assert (s.chosen, s.status, s.substituted_from, s.needs_review) == ("hf.rule:svg-path-draw", "installed", None, False)


def test_available_needs_opt_in(tmp_path):
    reg = small_registry(tmp_path)
    s = dd.select_capability(reg, ["opt:tool"])
    assert s.chosen == "hf.native:html-svg-css" and s.substituted_from == "opt:tool" and "opted in" in s.reason
    assert dd.select_capability(reg, ["opt:tool"], opt_in=["opt:tool"]).chosen == "opt:tool"


def test_candidate_is_not_selected_for_production(tmp_path):
    reg = small_registry(tmp_path)
    for kw in ({}, {"mode": "experimental"}, {"experimental": True}):
        s = dd.select_capability(reg, ["cand:p5"], **kw)
        assert s.chosen == "hf.native:html-svg-css" and s.substituted_from == "cand:p5", kw
    assert dd.select_capability(reg, ["cand:p5"], mode="experimental", experimental=True).chosen == "cand:p5"


def test_unavailable_is_always_rejected(tmp_path):
    reg = small_registry(tmp_path)
    s = dd.select_capability(reg, ["nope:filter"], mode="experimental", experimental=True, opt_in=["nope:filter"])
    assert s.chosen == "hf.native:html-svg-css" and s.substituted_from == "nope:filter"


def test_substitution_is_recorded_with_reason(tmp_path):
    s = dd.select_capability(small_registry(tmp_path), ["cand:p5"])
    assert s.substituted_from == "cand:p5" and "candidate" in s.reason and not s.needs_review


def test_nothing_usable_asks_for_review(tmp_path):
    reg = small_registry(tmp_path)
    # an unusable explicit fallback does not block the default fallback
    assert dd.select_capability(reg, ["nope:filter"], fallback="hf.rule:gone").chosen == "hf.native:html-svg-css"
    # with the default fallback also gone, nothing verified remains
    reg.entries.pop("hf.native:html-svg-css")
    s = dd.select_capability(reg, ["nope:filter"], fallback="hf.rule:gone")
    assert s.chosen is None and s.needs_review and s.substituted_from == "nope:filter"


def test_paid_blocked_without_approval(tmp_path):
    reg = small_registry(tmp_path)
    assert dd.select_capability(reg, ["paid:thing"]).chosen == "hf.native:html-svg-css"
    assert dd.select_capability(reg, ["paid:thing"], allow_paid=True).chosen == "paid:thing"


def test_whole_video_lane_is_not_a_scene_technique(tmp_path):
    reg = small_registry(tmp_path)
    ok, why = dd.usable(reg, "lane:video", opt_in=["lane:video"])
    assert not ok and "not a scene technique" in why


def test_unknown_id_and_missing_file_are_not_usable(tmp_path):
    reg = small_registry(tmp_path)
    assert dd.usable(reg, "no:such")[0] is False
    ok, why = dd.usable(reg, "hf.rule:gone")
    assert not ok and "does not exist" in why


def test_empty_preference_list_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        dd.select_capability(small_registry(tmp_path), [])


# ---- the dry-run plan ---------------------------------------------------------------------------------------------

def test_dry_run_plan_passes_m1_validator(plan, real_reg):
    assert dr.validate_plan(plan, real_reg, mode="production") == []


def test_dry_run_check_is_ok(plan, real_reg, script):
    r = dd.check(plan, real_reg, script)
    assert r["ok"], r
    assert 45 <= r["estimated_seconds"] <= 60


def test_all_selected_capabilities_exist_in_registry(plan, real_reg):
    for sc in plan["scenes"]:
        for cid in sc["direction"]["technique"]:
            assert cid in real_reg, cid
        fb = sc["direction"].get("fallback")
        if fb:
            assert fb in real_reg and real_reg.get(fb)["status"] == "installed"


def test_dry_run_selects_only_installed_capabilities(plan, real_reg):
    rep = dd.capability_report(plan, real_reg)
    assert rep["summary"]["non_installed_used"] == []
    assert rep["summary"]["paid_used"] == []
    assert rep["summary"]["by_status"].keys() == {"installed"}


def test_dry_run_records_its_substitution(plan, real_reg):
    subs = dd.capability_report(plan, real_reg)["summary"]["substitutions"]
    assert [s["scene"] for s in subs] == ["menu"]
    assert subs[0]["preferred"] == "treatment:handdrawn-p5brush"
    assert real_reg.get("treatment:handdrawn-p5brush")["status"] == "candidate"
    menu = next(s for s in plan["scenes"] if s["id"] == "menu")
    assert menu["direction"]["why"]


def test_motion_is_not_required_in_every_scene(plan):
    static = [s["id"] for s in plan["scenes"] if dd.is_static(s["direction"])]
    assert static == ["menu", "next"]
    assert len(static) < len(plan["scenes"])


def test_ambient_and_camera_are_quiet(plan):
    for sc in plan["scenes"]:
        d = sc["direction"]
        assert d.get("motion", {}).get("ambient", "none") == "none"
        assert d.get("camera", "hold") == "hold"


def test_every_scene_has_both_aspect_notes(plan):
    for sc in plan["scenes"]:
        assert set(sc["direction"]["reframe"]) == {"16:9", "9:16"}


def test_report_is_deterministic(plan, real_reg):
    a = json.dumps(dd.capability_report(plan, real_reg), sort_keys=True)
    b = json.dumps(dd.capability_report(copy.deepcopy(plan), real_reg), sort_keys=True)
    assert a == b
    assert dd.report_markdown(dd.capability_report(plan, real_reg)) == dd.report_markdown(dd.capability_report(plan, real_reg))


# ---- coherence ----------------------------------------------------------------------------------------------------

def test_coherence_clean_on_dry_run(plan):
    assert dd.coherence_issues(plan) == []


def test_all_animated_scenes_are_flagged(plan):
    for sc in plan["scenes"]:
        sc["direction"]["motion"]["primary"] = "something moves"
    msgs = " ".join(dd.coherence_issues(plan))
    assert "every scene animates" in msgs


def test_hook_must_open_and_recap_or_cta_must_close(plan):
    plan["scenes"][0]["direction"]["purpose"] = "setup"
    plan["scenes"][-1]["direction"]["purpose"] = "mechanism"
    msgs = " ".join(dd.coherence_issues(plan))
    assert "must be the hook" in msgs and "recap or cta" in msgs


def test_arc_must_match_scene_purposes(plan):
    plan["brief"]["arc"] = ["hook", "cta"]
    assert any("brief.arc" in m for m in dd.coherence_issues(plan))


def test_duplicate_takeaways_and_missing_reframe_are_flagged(plan):
    plan["scenes"][2]["direction"]["takeaway"] = plan["scenes"][1]["direction"]["takeaway"]
    del plan["scenes"][3]["direction"]["reframe"]
    msgs = " ".join(dd.coherence_issues(plan))
    assert "same takeaway" in msgs and "missing direction.reframe" in msgs


def test_static_scene_with_cues_or_camera_is_flagged(plan):
    d = plan["scenes"][1]["direction"]
    d["cues"] = [{"at": "the trick", "do": "x"}]
    d["camera"] = "push-in"
    msgs = " ".join(dd.coherence_issues(plan))
    assert "cues are listed" in msgs and "cannot have a camera move" in msgs


def test_partially_directed_plan_is_flagged(plan):
    del plan["scenes"][2]["direction"]
    assert any("direct every scene or none" in m for m in dd.coherence_issues(plan))


def test_reference_only_capability_is_rejected(plan, real_reg, script):
    plan["scenes"][0]["direction"]["technique"] = ["ref:motion-ai-kit"]
    r = dd.check(plan, real_reg, script)
    assert not r["ok"] and r["validator"]


# ---- anchors, duration --------------------------------------------------------------------------------------------

def test_anchors_resolve_in_order(plan, script):
    scenes, total = dd.estimate_timeline(plan, script)
    starts = [s["i0"] for s in scenes]
    assert starts == sorted(starts) and starts[0] == 0
    assert abs(total - 56.0) < 0.5


def test_missing_scene_anchor_is_reported(plan, script):
    plan["scenes"][2]["starts_at"] = "words that are not in the script"
    assert any(m.startswith("scene anchors") for m in dd.anchor_issues(plan, script))


def test_cue_outside_its_scene_is_reported(plan, script):
    plan["scenes"][2]["direction"]["cues"][0]["at"] = "gets an answer"   # spoken in the next scene
    assert any("not in this scene's narration" in m for m in dd.anchor_issues(plan, script))


def test_duration_bounds(script):
    assert dd.duration_issue(script) is None
    assert "outside 45-60" in dd.duration_issue("word " * 20)
    assert "outside 45-60" in dd.duration_issue("word " * 400)


# ---- validator extensions (reframe, verify, substituted_from, secondary needs why) --------------------------------

def _dir(**over):
    d = {"purpose": "hook", "takeaway": "A short takeaway.", "treatment": "diagram", "technique": ["hf.rule:svg-path-draw"]}
    d.update(over)
    return d


def _plan(d):
    return {"schema": "sceneplan/1", "scenes": [{"id": "a", "title": "A", "starts_at": 0, "direction": d}]}


def _fields(issues):
    return [(i.scene, i.field) for i in issues]


def test_reframe_must_have_exactly_both_aspects(tmp_path):
    reg = small_registry(tmp_path)
    ok = {"16:9": "left to right", "9:16": "top to bottom"}
    assert dr.validate_plan(_plan(_dir(reframe=ok)), reg) == []
    assert ("a", "direction.reframe") in _fields(dr.validate_plan(_plan(_dir(reframe={"16:9": "x"})), reg))
    assert ("a", "direction.reframe") in _fields(dr.validate_plan(_plan(_dir(reframe={"16:9": "x", "9:16": ""})), reg))


def test_verify_must_be_unique_non_empty_strings(tmp_path):
    reg = small_registry(tmp_path)
    assert dr.validate_plan(_plan(_dir(verify=["a claim"])), reg) == []
    for bad in ([""], ["x", "x"], "x", [1]):
        assert ("a", "direction.verify") in _fields(dr.validate_plan(_plan(_dir(verify=bad)), reg)), bad


def test_substituted_from_rules(tmp_path):
    reg = small_registry(tmp_path)
    ok = dr.validate_plan(_plan(_dir(substituted_from="cand:p5", why="Preferred a drawn look; candidate not allowed.")), reg)
    assert ok == []
    no_why = dr.validate_plan(_plan(_dir(substituted_from="cand:p5")), reg)
    assert ("a", "direction.why") in _fields(no_why)
    installed = dr.validate_plan(_plan(_dir(substituted_from="hf.rule:svg-path-draw", why="x")), reg)
    assert ("a", "direction.substituted_from") in _fields(installed)
    unknown = dr.validate_plan(_plan(_dir(substituted_from="no:such", why="x")), reg)
    assert ("a", "direction.substituted_from") in _fields(unknown)


def test_secondary_motion_needs_a_reason(tmp_path):
    reg = small_registry(tmp_path)
    assert ("a", "direction.why") in _fields(dr.validate_plan(_plan(_dir(motion={"primary": "line draws", "secondary": "node glows"})), reg))
    assert dr.validate_plan(_plan(_dir(motion={"primary": "line draws", "secondary": "node glows"}, why="The glow shows where the line lands.")), reg) == []


def test_ambient_motion_is_rejected_by_default(tmp_path):
    reg = small_registry(tmp_path)
    assert ("a", "direction.motion.ambient") in _fields(dr.validate_plan(_plan(_dir(motion={"primary": "x", "ambient": "slow drift"})), reg))


# ---- backward compatibility and non-mutation ----------------------------------------------------------------------

def test_pilot_plan_without_direction_is_still_valid(real_reg):
    pilot = json.loads(PILOT_FIX.read_text(encoding="utf-8"))
    assert dr.validate_plan(pilot, real_reg) == []
    assert dd.coherence_issues(pilot) == []


def test_planning_does_not_mutate_plan_or_registry(plan, real_reg, script):
    before_plan = json.dumps(plan, sort_keys=True)
    before_reg = json.dumps(real_reg.entries, sort_keys=True)
    dd.check(plan, real_reg, script)
    dd.capability_report(plan, real_reg)
    dd.estimate_timeline(plan, script)
    dd.estimated_storyboard_md(plan, script)
    dd.select_capability(real_reg, ["treatment:handdrawn-p5brush"])
    assert json.dumps(plan, sort_keys=True) == before_plan
    assert json.dumps(real_reg.entries, sort_keys=True) == before_reg


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_checking_does_not_touch_files_on_disk(real_reg, script):
    watched = [PLAN_FIX, SCRIPT_FIX, PILOT_FIX, REGISTRY]
    pilot_src = REPO / "workspace/projects/pilot-001-agent-tool-use/src/scene-plan.json"
    if pilot_src.exists():
        watched.append(pilot_src)
    before = {str(p): _sha(p) for p in watched}
    dd.check(json.loads(PLAN_FIX.read_text(encoding="utf-8")), real_reg, script)
    assert {str(p): _sha(p) for p in watched} == before


def test_workspace_copy_matches_fixture_when_present():
    if not (WORK / "scene-plan.json").exists():
        pytest.skip("experiment directory not present")
    assert _sha(WORK / "scene-plan.json") == _sha(PLAN_FIX)
    assert _sha(WORK / "script.txt") == _sha(SCRIPT_FIX)
