import copy
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.production import direction as dr  # noqa: E402
from contentos.production import sceneplan  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "pilot-001-scene-plan.json"
REAL_PILOT_PLAN = REPO / "workspace/projects/pilot-001-agent-tool-use/src/scene-plan.json"
REAL_PILOT_RESOLVED = REPO / "workspace/projects/pilot-001-agent-tool-use/storyboard/scene-plan.resolved.json"


def entry(cid, kind="rule", status="installed", path="skills/x.md", **kw):
    e = {"id": cid, "name": cid, "kind": kind, "status": status, "purpose": "p", "path": path, "context": ["hyperframes"],
         "requires": [], "offline": True, "paid": False, "limitations": [], "fallback": None}
    if status != "installed":
        e["status_reason"] = f"{status} because of a test reason"
    e.update(kw)
    return e


def base_entries():
    return [
        entry("hf.native:html-svg-css", kind="native"),
        entry("hf.rule:svg-path-draw", requires=["hf.native:html-svg-css"]),
        entry("hf.blueprint:camera-journey", kind="blueprint"),
        entry("renderer:hyperframes", kind="renderer"),
        entry("lane:mpt", kind="lane", status="available", path=None, fallback="hf.native:html-svg-css"),
        entry("hf.rule:svg-draw-ext", status="available", path=None, fallback="hf.native:html-svg-css"),
        entry("treatment:handdrawn", kind="treatment", status="candidate", path=None, fallback="hf.native:html-svg-css"),
        entry("treatment:vibe", kind="treatment", status="unavailable", path=None),
    ]


def make_registry(tmp_path, entries=None, files=("skills/x.md",)):
    root = tmp_path / "repo"
    for f in files:
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        (root / f).write_text("x", encoding="utf-8")
    cfg = root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "capabilities.json").write_text(
        json.dumps({"schema": "capabilities/1", "capabilities": entries if entries is not None else base_entries()}), encoding="utf-8")
    return dr.load_registry(cfg / "capabilities.json", root), root


def plan(*scenes, brief=None):
    p = {"schema": "sceneplan/1", "scenes": list(scenes) or [{"id": "hook", "title": "Hook", "starts_at": 0}]}
    if brief is not None:
        p["brief"] = brief
    return p


def good_direction(**over):
    d = {"purpose": "hook", "takeaway": "The model only asks for a tool call.", "treatment": "diagram",
         "technique": ["hf.rule:svg-path-draw"]}
    d.update(over)
    return d


def fields(issues):
    return [(i.scene, i.field) for i in issues]


# ---- 1. existing plans without direction -------------------------------------------------------------------------

def test_plan_without_direction_or_brief_validates(tmp_path):
    reg, _ = make_registry(tmp_path)
    p = plan({"id": "a", "title": "A", "starts_at": 0, "visual": "free text", "transition": "cut"},
             {"id": "b", "title": "B", "starts_at": "the model picks one"})
    assert dr.validate_plan(p, reg) == []


def test_wrong_schema_and_bad_scene_basics_are_reported(tmp_path):
    reg, _ = make_registry(tmp_path)
    issues = dr.validate_plan({"schema": "sceneplan/2", "scenes": [{"id": "a", "starts_at": 3}, {"id": "a", "starts_at": 2}, {"starts_at": -1}]}, reg)
    msgs = " | ".join(str(i) for i in issues)
    assert ("(plan)", "schema") in fields(issues)
    assert ("a", "id") in fields(issues) and "duplicate" in msgs
    assert ("a", "starts_at") in fields(issues) and "must increase" in msgs
    assert ("#2", "id") in fields(issues) and ("#2", "starts_at") in fields(issues)


# ---- 2. valid direction block -------------------------------------------------------------------------------------

def test_valid_direction_and_brief_validate(tmp_path):
    reg, _ = make_registry(tmp_path)
    d = good_direction(why="A packet path shows who acts.", focal="tool_use block", camera="pan-to:external-system",
                       motion={"primary": "draw-on", "secondary": "node highlight", "ambient": "none"},
                       cues=[{"at": "in a typical setup", "do": "nodes enter"}, {"at": 12, "do": "chip lights"}],
                       assets=[{"ref": "logo.svg", "source": "own drawing", "license": "CC0"}],
                       fallback="hf.native:html-svg-css", checks=["phone-legible", "cue-sync<=2f"], exit="dissolve", text_zone="caption-band")
    brief = {"audience": "developers", "takeaway": "Models ask, apps run.", "arc": ["hook", "mechanism", "cta"], "tone": "clear",
             "personality": "calm-precise", "renderer": "hyperframes", "opt_in": []}
    assert dr.validate_plan(plan({"id": "s", "title": "S", "starts_at": 0, "direction": d}, brief=brief), reg) == []


# ---- 3. unknown ids -----------------------------------------------------------------------------------------------

def test_unknown_capability_is_rejected_with_a_suggestion(tmp_path):
    reg, _ = make_registry(tmp_path)
    issues = dr.validate_plan(plan({"id": "s", "starts_at": 0, "direction": good_direction(technique=["hf.rule:svg-path-drawn"])}), reg)
    assert fields(issues) == [("s", "direction.technique[0]")]
    assert "unknown capability" in issues[0].message and "hf.rule:svg-path-draw" in issues[0].message
    assert issues[0].value == "hf.rule:svg-path-drawn"


def test_unknown_fallback_and_opt_in_ids_are_rejected(tmp_path):
    reg, _ = make_registry(tmp_path)
    p = plan({"id": "s", "starts_at": 0, "direction": good_direction(fallback="nope:nothing")}, brief={"opt_in": ["nope:other"]})
    assert ("s", "direction.fallback") in fields(dr.validate_plan(p, reg))
    assert ("(brief)", "brief.opt_in[0]") in fields(dr.validate_plan(p, reg))


def test_only_technique_kinds_can_be_techniques(tmp_path):
    reg, _ = make_registry(tmp_path)
    issues = dr.validate_plan(plan({"id": "s", "starts_at": 0, "direction": good_direction(technique=["renderer:hyperframes"])}), reg)
    assert fields(issues) == [("s", "direction.technique[0]")] and "cannot be a scene technique" in issues[0].message


# ---- 4. unavailable -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["production", "experimental"])
def test_unavailable_capability_is_rejected_in_every_mode(tmp_path, mode):
    reg, _ = make_registry(tmp_path)
    d = good_direction(technique=["treatment:vibe"], experimental=(mode == "experimental"), why="trying it")
    issues = dr.validate_plan(plan({"id": "s", "starts_at": 0, "direction": d}), reg, mode=mode)
    assert ("s", "direction.technique[0]") in fields(issues)
    assert any("unavailable" in i.message and "test reason" in i.message for i in issues)


# ---- 5. candidate / available gating -------------------------------------------------------------------------------

def cand_plan(experimental, **kw):
    d = good_direction(technique=["treatment:handdrawn"], treatment="handdrawn", why="hand-drawn series", fallback="hf.native:html-svg-css", **kw)
    if experimental is not None:
        d["experimental"] = experimental
    return plan({"id": "s", "starts_at": 0, "direction": d})


def test_candidate_rejected_in_production_even_if_scene_is_marked(tmp_path):
    reg, _ = make_registry(tmp_path)
    got = fields(dr.validate_plan(cand_plan(True), reg, mode="production"))
    assert ("s", "direction.technique[0]") in got and ("s", "direction.experimental") in got


def test_candidate_needs_scene_flag_even_in_experimental_mode(tmp_path):
    reg, _ = make_registry(tmp_path)
    issues = dr.validate_plan(cand_plan(None), reg, mode="experimental")
    assert fields(issues) == [("s", "direction.technique[0]")] and "experimental = true" in issues[0].message


def test_candidate_allowed_with_flag_and_experimental_mode(tmp_path):
    reg, _ = make_registry(tmp_path)
    assert dr.validate_plan(cand_plan(True), reg, mode="experimental") == []


def test_candidate_and_available_require_a_fallback(tmp_path):
    reg, _ = make_registry(tmp_path)
    d = good_direction(technique=["treatment:handdrawn"], treatment="handdrawn", why="x", experimental=True)
    issues = dr.validate_plan(plan({"id": "s", "starts_at": 0, "direction": d}), reg, mode="experimental")
    assert fields(issues) == [("s", "direction.fallback")]


def test_available_capability_requires_opt_in(tmp_path):
    reg, _ = make_registry(tmp_path)
    d = good_direction(technique=["hf.rule:svg-draw-ext"], fallback="hf.native:html-svg-css")
    bad = dr.validate_plan(plan({"id": "s", "starts_at": 0, "direction": d}), reg)
    assert fields(bad) == [("s", "direction.technique[0]")] and "brief.opt_in" in bad[0].message
    assert dr.validate_plan(plan({"id": "s", "starts_at": 0, "direction": d}, brief={"opt_in": ["hf.rule:svg-draw-ext"]}), reg) == []


def test_opt_in_of_installed_capability_is_rejected(tmp_path):
    reg, _ = make_registry(tmp_path)
    issues = dr.validate_plan(plan(brief={"opt_in": ["hf.rule:svg-path-draw"]}), reg)
    assert fields(issues) == [("(brief)", "brief.opt_in[0]")]


# ---- 6. required fields, enums, actionable messages -----------------------------------------------------------------

def test_missing_required_fields_and_bad_values_are_actionable(tmp_path):
    reg, _ = make_registry(tmp_path)
    d = {"purpose": "intro", "treatment": "gif", "takeaway": " ".join(["word"] * 25), "camera": "zoom-wildly", "bogus": 1,
         "motion": {"primary": "a", "ambient": "float"}, "cues": [{"at": -1, "do": ""}, {"at": 1}], "assets": [{"ref": "a", "source": "b", "license": "unknown"}],
         "checks": ["a", "a"]}
    issues = dr.validate_plan(plan({"id": "scn", "starts_at": 0, "direction": d}), reg)
    got = dict(((i.scene, i.field), i) for i in issues)
    for f in ("direction.technique", "direction.purpose", "direction.treatment", "direction.takeaway", "direction.camera", "direction.bogus",
              "direction.motion.ambient", "direction.cues[0].at", "direction.cues[0].do", "direction.cues[1]", "direction.assets[0].license", "direction.checks"):
        assert ("scn", f) in got, f
    assert got[("scn", "direction.purpose")].value == "intro" and "hook" in got[("scn", "direction.purpose")].message
    assert str(got[("scn", "direction.treatment")]).startswith("scene scn: direction.treatment:")
    assert got[("scn", "direction.technique")].value is None   # missing field reports value None


def test_ambient_allowed_only_when_brief_permits(tmp_path):
    reg, _ = make_registry(tmp_path)
    d = good_direction(motion={"primary": "x", "ambient": "slow gradient drift"})
    sc = {"id": "s", "starts_at": 0, "direction": d}
    assert fields(dr.validate_plan(plan(sc), reg)) == [("s", "direction.motion.ambient")]
    assert dr.validate_plan(plan(sc, brief={"allow_ambient": True}), reg) == []


def test_why_required_for_handdrawn_and_footage(tmp_path):
    reg, _ = make_registry(tmp_path)
    issues = dr.validate_plan(plan({"id": "s", "starts_at": 0, "direction": good_direction(treatment="footage")}), reg)
    assert fields(issues) == [("s", "direction.why")]


def test_brief_checks(tmp_path):
    reg, _ = make_registry(tmp_path)
    issues = dr.validate_plan(plan(brief={"personality": "goofy", "renderer": "remotion", "arc": ["intro"], "extra": 1}), reg)
    assert {i.field for i in issues} == {"brief.personality", "brief.renderer", "brief.arc", "brief.extra"}


# ---- 7. no mutation -----------------------------------------------------------------------------------------------

def test_validator_does_not_mutate_plan_or_registry(tmp_path):
    reg, _ = make_registry(tmp_path)
    entries_before = copy.deepcopy(reg.entries)
    good = plan({"id": "s", "starts_at": 0, "direction": good_direction(why="because")}, brief={"opt_in": []})
    bad = cand_plan(None)
    bad["scenes"][0]["direction"]["bogus"] = [1, {"a": 2}]
    for p in (good, bad):
        snapshot = copy.deepcopy(p)
        dr.validate_plan(p, reg, mode="experimental")
        dr.validate_plan(p, reg)
        assert p == snapshot
    assert reg.entries == entries_before


def test_load_plan_and_cli_do_not_modify_the_file(tmp_path, capsys):
    reg, root = make_registry(tmp_path)
    f = tmp_path / "plan.json"
    f.write_text(json.dumps(plan({"id": "s", "starts_at": 0, "direction": good_direction()})), encoding="utf-8")
    before = (f.read_bytes(), f.stat().st_mtime_ns)
    assert dr._main(["validate", str(f), "--registry", str(root / "config/capabilities.json")]) == 0
    assert (f.read_bytes(), f.stat().st_mtime_ns) == before
    assert "OK: 0 issue(s)" in capsys.readouterr().out


def test_cli_exit_codes(tmp_path, capsys):
    _, root = make_registry(tmp_path)
    regp = str(root / "config/capabilities.json")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(plan({"id": "s", "starts_at": 0, "direction": good_direction(technique=["nope:x"])})), encoding="utf-8")
    assert dr._main(["validate", str(bad), "--registry", regp]) == 1
    assert "unknown capability" in capsys.readouterr().out
    assert dr._main(["validate", str(tmp_path / "missing.json"), "--registry", regp]) == 2
    assert dr._main(["validate", str(bad), "--registry", str(tmp_path / "missing-registry.json")]) == 2


# ---- 8. Pilot 001 --------------------------------------------------------------------------------------------------

def test_pilot_001_fixture_validates_against_a_registry(tmp_path):
    reg, _ = make_registry(tmp_path)
    p = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert p["schema"] == "sceneplan/1" and len(p["scenes"]) == 7 and not any("direction" in s for s in p["scenes"])
    assert dr.validate_plan(p, reg) == []


@pytest.mark.skipif(not REAL_PILOT_PLAN.exists(), reason="pilot workspace not present (gitignored)")
def test_pilot_fixture_matches_the_real_pilot_plan_and_both_validate(tmp_path):
    reg, _ = make_registry(tmp_path)
    real = json.loads(REAL_PILOT_PLAN.read_text(encoding="utf-8"))
    assert real == json.loads(FIXTURE.read_text(encoding="utf-8")), "fixture is stale: refresh tests/fixtures/pilot-001-scene-plan.json"
    assert dr.validate_plan(real, reg) == []


@pytest.mark.skipif(not REAL_PILOT_RESOLVED.exists(), reason="pilot workspace not present (gitignored)")
def test_resolved_plan_is_a_derived_artifact_with_its_own_schema(tmp_path):
    reg, _ = make_registry(tmp_path)
    resolved = json.loads(REAL_PILOT_RESOLVED.read_text(encoding="utf-8"))
    assert resolved["schema"] == "sceneplan/1.resolved"          # not an input contract; the validator says so rather than guessing
    assert ("(plan)", "schema") in fields(dr.validate_plan(resolved, reg))


def test_resolver_behaviour_is_unchanged_and_passes_direction_through():
    words = [(t, i * 1.0, i * 1.0 + 0.8) for i, t in enumerate("alpha beta gamma delta epsilon".split())]
    d = good_direction()
    p = {"scenes": [{"id": "a", "title": "A", "starts_at": 0}, {"id": "b", "title": "B", "starts_at": "gamma", "direction": d}]}
    before = copy.deepcopy(p)
    out = sceneplan.resolve(p, words, audio_end=5.0)
    assert p == before
    assert [s["t0"] for s in out] == [0.0, 2.0] and out[1]["direction"] == d and "direction" not in out[0]


# ---- 9. malformed registry ---------------------------------------------------------------------------------------

def write_reg(tmp_path, text):
    f = tmp_path / "cap.json"
    f.write_text(text, encoding="utf-8")
    return f


def test_registry_missing_or_not_json(tmp_path):
    with pytest.raises(dr.RegistryError, match="cannot read"):
        dr.load_registry(tmp_path / "nope.json", tmp_path)
    with pytest.raises(dr.RegistryError, match="not valid JSON"):
        dr.load_registry(write_reg(tmp_path, "{not json"), tmp_path)


def test_registry_reports_every_problem_at_once(tmp_path):
    bad = [
        entry("a:ok"),
        entry("a:ok"),                                                     # duplicate
        entry("b:badstatus", status="installed") | {"status": "ready"},    # invalid status
        entry("c:noreason", status="candidate") | {"status_reason": ""},   # candidate without reason
        entry("d:fallback-to-candidate", fallback="c:noreason"),           # fallback must be installed
        entry("e:dangling", requires=["zzz:missing"]),
        entry("f:self", fallback="f:self"),
        entry("g:kind", kind="magic"),
        {"id": "h:partial"},
        entry("Bad Id"),
        entry("i:abs", path="/etc/passwd"),
        entry("j:dots", path="../outside.md"),
        entry("k:slash", path="a\\b.md"),
        entry("l:extra") | {"surprise": 1},
    ]
    with pytest.raises(dr.RegistryError) as ei:
        dr.load_registry(write_reg(tmp_path, json.dumps({"schema": "capabilities/1", "capabilities": bad})), tmp_path)
    text = "\n".join(ei.value.problems)
    for needle in ("duplicate id", "status 'ready'", "requires a non-empty status_reason", "fallback 'c:noreason' must be installed",
                   "'zzz:missing' is not a registered capability", "refers to itself", "kind 'magic'", "missing required field",
                   "id must look like", "must be relative", "unknown field 'surprise'"):
        assert needle in text, needle
    assert len(ei.value.problems) >= 12


def test_registry_wrong_schema_and_shape(tmp_path):
    with pytest.raises(dr.RegistryError, match="schema must be"):
        dr.load_registry(write_reg(tmp_path, json.dumps({"schema": "x", "capabilities": [entry("a:b")]})), tmp_path)
    with pytest.raises(dr.RegistryError, match="non-empty list"):
        dr.load_registry(write_reg(tmp_path, json.dumps({"schema": "capabilities/1", "capabilities": []})), tmp_path)
    with pytest.raises(dr.RegistryError, match="JSON object"):
        dr.load_registry(write_reg(tmp_path, "[]"), tmp_path)


def test_installed_entry_cannot_require_a_non_installed_one(tmp_path):
    bad = [entry("a:cand", kind="treatment", status="candidate", path=None), entry("a:inst", requires=["a:cand"])]
    with pytest.raises(dr.RegistryError, match="installed capability requires"):
        dr.load_registry(write_reg(tmp_path, json.dumps({"schema": "capabilities/1", "capabilities": bad})), tmp_path)


# ---- 10. paths: safe and deterministic -----------------------------------------------------------------------------

def test_resolve_inside_rejects_unsafe_paths(tmp_path):
    (tmp_path / "ok.md").write_text("x")
    assert dr.resolve_inside(tmp_path, "ok.md") == (tmp_path / "ok.md").resolve()
    for bad in ("/etc/passwd", "../x", "a/../../x", "a\\b", "", "x\0y"):
        with pytest.raises(ValueError):
            dr.resolve_inside(tmp_path, bad)


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="no symlink support")
def test_symlink_escaping_the_repo_is_rejected(tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("secret")
    reg, root = make_registry(tmp_path)
    (root / "skills/link.md").symlink_to(outside)
    reg2, _ = make_registry(tmp_path / "second", [entry("hf.rule:linked", path="skills/link.md")], files=())
    # reuse the first repo's tree for the second registry
    reg2.root = root
    assert "outside the repository" in reg2.path_problem("hf.rule:linked")
    issues = dr.validate_plan(plan({"id": "s", "starts_at": 0, "direction": good_direction(technique=["hf.rule:linked"])}), reg2)
    assert fields(issues) == [("s", "direction.technique[0]")] and "registered as installed but" in issues[0].message


def test_missing_installed_file_is_reported_only_when_referenced(tmp_path):
    entries = [entry("hf.native:html-svg-css", kind="native"), entry("hf.rule:gone", path="skills/gone.md")]
    reg, _ = make_registry(tmp_path, entries)
    assert dr.validate_plan(plan(), reg) == []     # not referenced: plan still validates
    issues = dr.validate_plan(plan({"id": "s", "starts_at": 0, "direction": good_direction(technique=["hf.rule:gone"])}), reg)
    assert "does not exist" in issues[0].message and "upstream_skills.py sync" in issues[0].message
    assert any("hf.rule:gone" in p for p in dr.check_registry(reg))


def test_check_registry_is_deterministic_and_detects_drift(tmp_path):
    root = tmp_path / "repo"
    anim = root / ".claude/skills/hyperframes-animation"
    for n in ("b-rule", "a-rule", "extra-rule"):
        (anim / "rules").mkdir(parents=True, exist_ok=True)
        (anim / "rules" / f"{n}.md").write_text("x")
    (anim / "blueprints").mkdir(parents=True)
    (anim / "blueprints/bp.md").write_text("x")
    paths = {n: f".claude/skills/hyperframes-animation/rules/{n}.md" for n in ("a-rule", "b-rule")}
    entries = [entry(f"hf.rule:{n}", path=p) for n, p in paths.items()] + [entry("hf.rule:ghost", path=None),
               entry("hf.blueprint:bp", kind="blueprint", path=".claude/skills/hyperframes-animation/blueprints/bp.md")]
    reg, _ = make_registry(tmp_path / "x", entries, files=())
    reg.root = root
    first = dr.check_registry(reg)
    assert first == dr.check_registry(reg) == sorted(first)
    assert "hf.rule:extra-rule: file exists in rules/ but is not in the registry" in first
    assert "hf.rule:ghost: registered rule has no file in rules/" in first


# ---- the real registry -----------------------------------------------------------------------------------------------

REAL = REPO / "config/capabilities.json"
SKILLS_PRESENT = (REPO / ".claude/skills/hyperframes-animation/rules").is_dir() and (REPO / ".claude/skills/explainer-motion-craft/SKILL.md").is_file()


def test_real_registry_is_well_formed_and_conservative():
    reg = dr.load_registry()
    assert reg.counts() == {"installed": 88, "available": 2, "candidate": 1, "unavailable": 2}
    assert reg.get("renderer:hyperframes")["status"] == "installed"
    assert reg.get("treatment:handdrawn-p5brush")["status"] == "candidate"        # stays a candidate until an explicit decision
    assert reg.get("treatment:vibe-filter")["status"] == "unavailable"            # no verified implementation
    assert reg.get("ref:motion-ai-kit")["status"] == "unavailable"                # reference-only
    assert all(e["paid"] is False for e in reg.entries.values() if e["status"] in ("installed", "available", "candidate"))
    assert sum(e["kind"] == "rule" for e in reg.entries.values()) == 48 and sum(e["kind"] == "blueprint" for e in reg.entries.values()) == 22
    ids = [c["id"] for c in json.loads(REAL.read_text(encoding="utf-8"))["capabilities"]]
    assert len(ids) == len(set(ids)) == 93


@pytest.mark.skipif(not SKILLS_PRESENT, reason="vendored skills not synced (python scripts/upstream_skills.py sync)")
def test_real_registry_matches_the_files_on_disk():
    assert dr.check_registry(dr.load_registry()) == []


@pytest.mark.skipif(not SKILLS_PRESENT, reason="vendored skills not synced (python scripts/upstream_skills.py sync)")
def test_real_registry_accepts_a_real_direction_and_rejects_the_reference_only_kit():
    reg = dr.load_registry()
    good = plan({"id": "s", "starts_at": 0, "direction": good_direction(technique=["hf.rule:svg-path-draw", "hf.rule:asr-keyword-glow"],
                                                                         why="packet path plus keyword glow")})
    assert dr.validate_plan(good, reg) == []
    bad = plan({"id": "s", "starts_at": 0, "direction": good_direction(technique=["ref:motion-ai-kit"])})
    assert any("unavailable" in i.message for i in dr.validate_plan(bad, reg, mode="experimental"))
