"""KF-006: Rule B reads its signature from one rule (#root, else .scene, else body). With per-scene backdrops that rule can be
stale or absent. These fixtures pin what is known (the warning, the selector bug) and deliberately do NOT pin what the signature
of a per-scene video should be; that decision is open (docs/video-intelligence/04-visual-reliability-gate.md)."""
import json

from contentos.intelligence import visual as v

GLOBAL = "#root{background:radial-gradient(circle at 30% 20%,#1b2a6b,#0a0e18)} .scene{position:absolute}"
STALE_ROOT = ("#root{background:#0a0e18} .scene{position:absolute}"
              " #s-a{background:#f4efe6} #s-b{background:#e8f0ff} #s-c{background:#ffe9d6}")
NO_ROOT = "body{margin:0} #s-a{background:#102a43} #s-b{background:#7a1f1f}"
SAME_AS_ROOT = "#root{background:#0a0e18} #s-a{background:#0a0e18} #s-b{background:#0b0f19}"
CLASS_SCENES = ".scene-a{background:#f4efe6} .scene-b{background:#7a1f1f} body{background:#0a0e18}"


def test_global_backdrop_has_no_warning():
    assert v.scene_backdrop_warnings(GLOBAL) == []


def test_per_scene_with_stale_root_warns():
    w = v.scene_backdrop_warnings(STALE_ROOT)
    assert len(w) == 1 and w[0]["stale_root"] and len(w[0]["scenes_differing"]) == 3


def test_per_scene_without_root_warns():
    w = v.scene_backdrop_warnings(NO_ROOT)
    assert len(w) == 1 and not w[0]["stale_root"]


def test_scenes_matching_root_do_not_warn():
    assert v.scene_backdrop_warnings(SAME_AS_ROOT) == []


def test_comments_are_ignored():
    assert v.scene_backdrop_warnings("/* #s-a{background:#f4efe6} */ #root{background:#0a0e18}") == []


def test_signature_is_unchanged_by_the_warning():
    # the warning is additive; the signature of the stale-root fixture is still whatever #root says
    assert v.signature_from_css(STALE_ROOT)["base"]["tier"] == "dark"


def test_scene_prefixed_class_is_not_read_as_the_global_scene_rule():
    # pin: _decl requires '{' right after the selector, so ".scene-a" was never read as ".scene" (checked; not a bug)
    sig = v.signature_from_css(CLASS_SCENES)
    assert sig["base"]["tier"] == "dark"          # from body, not from .scene-a (light)


def _sig():
    return v.signature_from_css(STALE_ROOT)


def test_claim_refuses_to_record_with_unacknowledged_warnings(tmp_path):
    w = v.scene_backdrop_warnings(STALE_ROOT)
    ledger = tmp_path / "vl.json"
    r = v.claim("job-1", _sig(), seed=tmp_path / "none.json", path=ledger, warnings=w)
    assert not r["ok"] and "refused" in r and not ledger.exists()


def test_claim_records_when_acknowledged(tmp_path):
    w = v.scene_backdrop_warnings(STALE_ROOT)
    ledger = tmp_path / "vl.json"
    r = v.claim("job-1", _sig(), seed=tmp_path / "none.json", path=ledger, warnings=w, acknowledge_warnings=True)
    assert r["ok"] and r["recorded"] and r["warnings"]
    assert json.loads(ledger.read_text())["entries"][0]["content_id"] == "job-1"


def test_claim_dry_run_never_refuses(tmp_path):
    w = v.scene_backdrop_warnings(STALE_ROOT)
    r = v.claim("job-1", _sig(), seed=tmp_path / "none.json", path=tmp_path / "vl.json", warnings=w, dry_run=True)
    assert r["ok"] and r["warnings"]


def test_claim_without_warnings_is_unchanged(tmp_path):
    ledger = tmp_path / "vl.json"
    r = v.claim("job-1", v.signature_from_css(GLOBAL), seed=tmp_path / "none.json", path=ledger)
    assert r["ok"] and r["recorded"] and "warnings" not in r
