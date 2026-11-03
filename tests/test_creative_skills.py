"""Creative-skill registry: bundle integrity, schema, stable ids, status honesty, routing, compat, plan, analyzer, publish gate."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from contentos import providers
from contentos.scenekit import planner
from contentos.skills import __main__ as cli
from contentos.skills import analyze, classify, probe as probe_mod
from contentos.skills import registry as R

ROOT = Path(__file__).resolve().parent.parent
REG = R.load()
CATALOG = json.loads((R.LIB / "config/skill-catalog.json").read_text())["skills"]
creative = [s for s in REG["skills"] if s["kind"] == "creative"]
core = [s for s in REG["skills"] if s["kind"] == "core-workflow"]


# ---- bundle integrity ----------------------------------------------------------------------------------------------

def test_vendored_bundle_matches_its_manifest_byte_for_byte():
    assert R.verify_library() == []


def test_a_modified_skill_file_is_detected(tmp_path, monkeypatch):
    lib = tmp_path / "lib"
    shutil.copytree(R.LIB, lib)
    (lib / "skills/anime-reel/SKILL.md").write_text("tampered")
    monkeypatch.setattr(R, "LIB", lib)
    assert any("modified skills/anime-reel/SKILL.md" in p for p in R.verify_library())


# ---- registry shape and stable ids ---------------------------------------------------------------------------------

def test_registry_validates_and_is_current():
    assert R.validate(REG) == []
    assert not R.stale(REG), "run: python -m contentos.skills build"


def test_every_bundle_skill_has_a_registry_entry_with_its_catalog_id():
    assert [(s["id"], s["name"]) for s in creative] == [(e["id"], e["name"]) for e in CATALOG]
    dirs = {p.parent.name for p in (R.LIB / "skills").glob("*/SKILL.md")}
    assert dirs == {s["name"] for s in creative} and len(creative) == 79
    assert {s["name"] for s in core} == {p.parent.name for p in (R.LIB / "core-skills").glob("*/SKILL.md")} and len(core) == 7


def test_every_skill_has_exactly_one_allowed_status_and_a_reason_when_not_green():
    for s in REG["skills"]:
        assert s["status"] in R.STATUSES, s["name"]
        if s["status"].startswith("blocked") or s["status"] == "not-integrated":
            assert s["blockers"] or s["limitations"], s["name"]
        if s["status"] == "adapted-with-fallback" and s["kind"] == "creative":
            assert s["fallbacks"], s["name"]
        if s["status"] == "integrated-and-tested" and s["kind"] == "creative":
            assert s["evidence"], s["name"]


def test_no_creative_skill_claims_full_test_status_without_a_full_fidelity_render():
    assert not [s["name"] for s in creative if s["status"] == "integrated-and-tested"]


def test_unexecuted_recipes_say_so():
    for s in creative:
        if not s["evidence"]:
            assert any("never rendered" in l for l in s["limitations"]), s["name"]


def test_core_skills_point_at_existing_implementations_and_bundle_video_director_is_not_installed():
    for s in core:
        for imp in s.get("implementation", []):
            assert (ROOT / imp).exists(), (s["name"], imp)
    installed = {p.name for p in (ROOT / ".claude/skills").iterdir()}
    assert "video-director" in installed
    assert not (set(s["name"] for s in creative) & installed), "creative skills must not be dropped into .claude/skills (context bloat, collisions)"


def test_style_registry_is_mapped_onto_existing_styles_not_added_as_a_fourth_registry():
    from contentos.scenekit import styles
    assert {s["id"] for s in REG["styles"]} == {s["id"] for s in yaml.safe_load((R.LIB / "config/style-registry.yaml").read_text())["styles"]}
    for s in REG["styles"]:
        assert s["factory"].get("scenekit") in (None, *styles.STYLES)


# ---- classification rules -----------------------------------------------------------------------------------------

def _entry(name, sid=60, desc="x"):
    return {"id": sid, "name": name, "category": "c", "description": desc}


def test_inputs_and_requirements_come_from_the_skill_text():
    t = "Original invocation brief: Save it as .claude/skills/k/SKILL.md so I can run /k with a song MP3 and its lyrics attached.\n"
    t += "## Creative brief preserved from source\n- Time every word with forced alignment (torchaudio MMS_FA). every beat\n## Quality checklist"
    c = classify.classify(_entry("k"), t)
    assert {"song", "lyrics"} <= set(c["inputs_required"])
    assert {"align.forced_mms", "audio.beat_detect", "render.hyperframes"} <= set(c["requires"])


def test_decide_blocks_without_a_verified_fallback_and_adapts_with_one():
    c = {"requires": ["3d.blender", "render.hyperframes"], "ip_sensitive": None, "external_media_rights": False, "inputs_required": []}
    p = {"render.hyperframes": {"ok": True}, "3d.blender": {"ok": False}}
    assert classify.decide(c, p)["status"] == "blocked-by-dependency"
    c2 = {**c, "requires": ["align.forced_mms", "render.hyperframes"]}
    p2 = {"render.hyperframes": {"ok": True}, "align.forced_mms": {"ok": False}, "asr.word_timing_en": {"ok": True}}
    assert classify.decide(c2, p2)["status"] == "adapted-with-fallback"
    p3 = {**p2, "asr.word_timing_en": {"ok": False}}
    assert classify.decide(c2, p3)["status"] == "blocked-by-dependency"      # fallback itself unavailable


def test_ip_sensitive_skills_carry_an_original_assets_limitation():
    s = next(x for x in creative if x["name"] == "mirzapur-video")
    assert s["ip_sensitive"] and any("original characters" in l for l in s["limitations"])


# ---- probe ---------------------------------------------------------------------------------------------------------

def test_probe_reports_evidence_for_every_capability_a_skill_can_require():
    p = probe_mod.probe()
    assert all(set(v) == {"ok", "evidence"} and v["evidence"] for v in p.values())
    needed = {r for s in REG["skills"] for r in s["requires"]}
    assert needed <= set(p)
    assert p["render.remotion"]["ok"] is False                                   # never a lane


# ---- routing -------------------------------------------------------------------------------------------------------

def test_numbered_request_resolves_through_the_catalog_never_by_guess():
    r = R.route(REG, "20")
    assert r[0]["name"] == "blueprint-explainer" and r[0]["id"] == 20
    assert R.route(REG, "/numbered-video 4")[0]["name"] == "lyric-video"
    assert R.route(REG, "999") == []


def test_route_reports_missing_inputs_and_hides_blocked_skills_by_default():
    res = R.route(REG, "make a lyric video", have=["lyrics"])
    assert res and all(not r["status"].startswith("blocked") for r in res)
    assert all("song" in r["missing_inputs"] for r in res if r["name"] in ("lyric-video", "hindi-lyric-video"))
    assert not any(r["name"] == "youtube-clips" for r in R.route(REG, "find the best moments in a long youtube video"))
    assert R.route(REG, "find the best moments in a long youtube video", include_blocked=True)[0]["name"] == "youtube-clips"


def test_route_surfaces_a_runnable_explainer_with_no_missing_inputs():
    top = R.route(REG, "narrated explainer about kafka architecture", have=["script"])[0]
    assert top["execution"] == "track-a-scenekit" and top["readiness"] == "ready-to-run" and top["missing_inputs"] == []


# ---- combinations ---------------------------------------------------------------------------------------------------

def test_two_formats_cannot_be_combined():
    assert not R.compat(REG, ["lyric-video", "kids-story"])["compatible"]


def test_effects_that_fight_over_the_same_layer_conflict():
    r = R.compat(REG, ["depth-ui-reel", "magazine-cover"])
    assert not r["compatible"] and any("same layer" in x for x in r["reasons"])


def test_a_footage_format_accepts_a_grade_effect_and_blocked_skills_never_combine():
    assert R.compat(REG, ["talking-head-edit", "cinema-scope"])["compatible"]
    assert not R.compat(REG, ["talking-head-edit", "3d-explainer"])["compatible"]
    assert not R.compat(REG, ["nope"])["compatible"]


# ---- plan: registry -> scenekit spec ---------------------------------------------------------------------------------

def test_plan_produces_a_spec_the_scenekit_planner_accepts(tmp_path):
    base = yaml.safe_load((ROOT / "examples/styles/kafka-events.yaml").read_text())
    base.pop("visual_style")
    sp, out = tmp_path / "s.yaml", tmp_path / "o.yaml"
    sp.write_text(yaml.safe_dump(base))
    assert cli.main(["plan", "--skill", "blueprint-explainer", "--script", str(sp), "--content-id", "sample-x", "--out", str(out)]) == 0
    spec = yaml.safe_load(out.read_text())
    assert spec["content_id"] == "sample-x" and spec["visual_style"]["id"] == "blueprint-architecture"
    assert spec["creative_skill"]["name"] == "blueprint-explainer" and spec["creative_skill"]["id"] == 20
    assert planner.plan(spec)["style"]["id"] == "blueprint-architecture"


def test_plan_refuses_to_pretend_for_agent_authored_skills(tmp_path, capsys):
    sp = tmp_path / "s.yaml"
    sp.write_text("content_id: x\n")
    assert cli.main(["plan", "--skill", "kinetic-lyrics", "--script", str(sp)]) == 3
    assert "track-b-agent-authored" in capsys.readouterr().out


def test_scenekit_style_mappings_point_at_real_styles_and_every_mapped_skill_has_evidence_or_says_not():
    for s in creative:
        if s["execution"] == "track-a-scenekit":
            assert s["scenekit_style"] and s["status"] == "adapted-with-fallback"
            assert any("NOT built" in l for l in s["limitations"]), s["name"]


# ---- reference analyzer (synthetic video with a known cut) ----------------------------------------------------------

@pytest.mark.skipif(not probe_mod._which("ffmpeg"), reason="needs ffmpeg")
def test_analyzer_finds_a_known_hard_cut_and_records_its_limits(tmp_path):
    v = tmp_path / "t.mp4"
    subprocess.run([probe_mod._which("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x202020:s=108x192:r=30:d=2",
                    "-f", "lavfi", "-i", "color=c=0xe0e0a0:s=108x192:r=30:d=2", "-filter_complex", "[0][1]concat=n=2:v=1[v]", "-map", "[v]",
                    "-pix_fmt", "yuv420p", str(v)], check=True)
    res = analyze.analyze(v, tmp_path / "out")
    assert len(res["cuts"]) == 1 and abs(res["cuts"][0] - 2.0) < 0.2
    assert res["pacing"]["shot_count"] == 2 and res["probe"]["width"] == 108 and res["audio"] is None
    assert any("no OCR" in l for l in res["limits"]) and (tmp_path / "out/reference-analysis.json").exists()


def test_analyzer_rejects_a_missing_file(tmp_path):
    with pytest.raises((ValueError, FileNotFoundError)):
        analyze.analyze(tmp_path / "nope.mp4", tmp_path / "o")


# ---- publishing stays gated -----------------------------------------------------------------------------------------

def test_publishing_is_still_disabled_and_no_registry_command_can_publish():
    assert providers.load("youtube.yaml")["publish"]["enabled"] is False
    src = "".join(p.read_text() for p in (ROOT / "contentos/skills").glob("*.py"))
    assert not re.search(r"upload|youtube\.googleapis|publish\(|--approve", src.replace("publish gate", ""))


def test_ledger_lists_every_skill_once():
    md = R.ledger_markdown(REG)
    for s in REG["skills"]:
        assert len(re.findall(rf"^\| {re.escape(str(s['id']))} \| {re.escape(s['name'])} \|", md, re.M)) == 1
