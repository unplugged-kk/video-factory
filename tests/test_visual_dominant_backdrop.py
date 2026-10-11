"""Rule B for per-scene backdrops: the signature is the DURATION-DOMINANT backdrop (approved decision). Scene data shapes are
the real ones: ep3 audio/timing.json scenes[]{id,start,dur} with CSS #s-<id>; ep2 scenes.json scenes[]{id,start,end}."""
import json
import math

from contentos.intelligence import visual as v

# ep3 variant C, real durations (hook, bigidea, contrast, outputs, llm, cta) and its backdrops
EP3_DURS = [("hook", 10.249), ("bigidea", 10.163), ("contrast", 11.315), ("outputs", 9.673), ("llm", 8.009), ("cta", 4.164)]
EP3_CSS = """
:root{--bg:#06080c}
.scene{background-color:#0a0e18}
#s-hook{background:linear-gradient(rgba(255,255,255,.055) 1px,rgba(255,255,255,0) 1px),#0a0e18}
#s-bigidea{background:radial-gradient(circle at 50% 18%,#1a2670 0%,#0e1650 46%,#070b30 100%)}
#s-contrast{background:#10303a}
#s-outputs{background:linear-gradient(180deg,#16414a 0%,#0f2d3a 55%,#0a1d28 100%)}
#s-llm{background:radial-gradient(circle at 50% 30%,#2a2470 0%,#191858 48%,#0c0c30 100%)}
#s-cta{background:radial-gradient(circle at 50% 42%,#16587a 0%,#0c2f4e 50%,#071626 100%)}
"""


def timing(durs):
    t, out = 0.0, []
    for sid, d in durs:
        out.append({"id": sid, "start": round(t, 3), "dur": d})
        t += d
    return {"total_s": round(t, 3), "scenes": out}


def two(a_css, b_css, da, db, extra=""):
    css = f"#root{{background:#0a0e18}} #s-a{{background:{a_css}}} #s-b{{background:{b_css}}} {extra}"
    return css, timing([("a", da), ("b", db)])


# ---- durations: real shapes and bad data -------------------------------------------------------------------------

def test_durations_from_dur_and_from_end_minus_start():
    d, p = v.scene_durations({"scenes": [{"id": "x", "start": 0, "dur": 4.5}, {"id": "S1-hook", "start": 4.5, "end": 9.0}]})
    assert d == [("x", 4.5), ("S1-hook", 4.5)] and p == []


def test_invalid_durations_are_reported_and_excluded():
    doc = {"scenes": [{"id": "a", "dur": 5}, {"id": "b", "dur": -1}, {"id": "c", "dur": "7"}, {"id": "d", "dur": float("nan")},
                      {"id": "e", "dur": True}, {"dur": 3}, {"id": "f"}, "junk"]}
    d, p = v.scene_durations(doc)
    assert d == [("a", 5.0)]
    codes = [x["code"] for x in p]
    assert codes.count("invalid_duration") == 5 and codes.count("scene_without_id") == 2 and len(p) == 7
    assert {"b", "c", "d", "e", "f"} <= {x.get("scene") for x in p}


def test_no_scenes_is_reported():
    for doc in (None, {}, {"scenes": []}, {"scenes": "x"}, []):
        d, p = v.scene_durations(doc)
        assert d == [] and p[0]["code"] == "no_scenes"


def test_duplicate_scene_ids_are_flagged_but_both_count():
    d, p = v.scene_durations({"scenes": [{"id": "a", "dur": 2}, {"id": "a", "dur": 3}]})
    assert d == [("a", 2.0), ("a", 3.0)] and p == [{"code": "duplicate_scene_id", "scene": "a"}]


# ---- global backdrop: behaviour preserved ------------------------------------------------------------------------

def test_global_backdrop_signature_is_unchanged():
    css = "#root{background:radial-gradient(circle,#1a2670,#070b30)} .scene{position:absolute}"
    t = timing([("a", 5), ("b", 5)])
    sig, info = v.signature_for(css, t)
    assert sig == v.signature_from_css(css) and info["basis"] == "global-rule"
    assert v.backdrop_warnings(css, t) == []


def test_no_timing_falls_back_and_keeps_the_old_warning():
    css, _ = two("#f4efe6", "#e8f0ff", 5, 5)
    sig, info = v.signature_for(css, None)
    assert sig == v.signature_from_css(css) and info["basis"] == "global-rule"
    codes = [w["code"] for w in v.backdrop_warnings(css, None)]
    assert codes == ["per_scene_backdrops_not_in_signature", "scene_durations_unavailable"]


# ---- per-scene: dominant, distribution, unequal durations --------------------------------------------------------

def test_ep3_distribution_and_dominant():
    prof = v.backdrop_profile(EP3_CSS, timing(EP3_DURS))
    assert prof["usable"] and len(prof["backdrops"]) == 6          # every scene has its own rule
    assert math.isclose(prof["total_seconds"], 53.573, abs_tol=1e-6)
    assert math.isclose(sum(b["share"] for b in prof["backdrops"]), 1.0, abs_tol=2e-3)
    dom = prof["dominant"]
    # real ep3: contrast 21.1%, hook 19.1%, bigidea 19.0%, outputs 18.1%, llm 15.0%, cta 7.8%. The winner is contrast, but six
    # near-equal backdrops are exactly the case where "dominant" means little, so it is flagged, not silently chosen
    assert dom["scenes"] == ["contrast"] and dom["seconds"] == 11.315 and prof["ambiguous"]
    assert len(prof["tied"]) == 4
    assert v.signature_for(EP3_CSS, timing(EP3_DURS))[1]["basis"] == "duration-dominant"


def test_signature_follows_the_dominant_backdrop_not_the_root():
    css, t = two("#f4efe6", "#10303a", 3, 9)                         # b (dark teal) lasts longer; #root is dark navy
    sig, _ = v.signature_for(css, t)
    assert sig["base"]["tier"] in ("dark", "dim") and sig["temperature"] == "cool"
    css2, t2 = two("#f4efe6", "#10303a", 9, 3)                       # a (light) dominates now
    sig2, _ = v.signature_for(css2, t2)
    assert sig2["base"]["tier"] == "light" and sig2 != sig


def test_unequal_durations_the_longest_total_wins_across_scenes():
    css = "#root{background:#0a0e18} #s-a{background:#10303a} #s-b{background:#f4efe6} #s-c{background:#10303a}"
    prof = v.backdrop_profile(css, timing([("a", 3), ("b", 5), ("c", 3)]))   # teal 6s total beats light 5s
    assert prof["dominant"]["decl"] == "#10303a" and prof["dominant"]["scenes"] == ["a", "c"] and prof["dominant"]["seconds"] == 6.0
    assert not prof["ambiguous"]


def test_scene_without_its_own_rule_inherits_the_global_backdrop():
    css = "#root{background:#0a0e18} #s-b{background:#f4efe6}"
    prof = v.backdrop_profile(css, timing([("a", 7), ("b", 3)]))
    assert prof["dominant"]["inherits_global"] and prof["dominant"]["scenes"] == ["a"]
    sig, _ = v.signature_for(css, timing([("a", 7), ("b", 3)]))
    assert sig == v.signature_from_css(css)                         # dominant is the global one: same as before


def test_stale_root_no_longer_decides_when_every_scene_overrides_it():
    css = "#root{background:#0a0e18} #s-a{background:#f4efe6} #s-b{background:#e8f0ff}"
    sig, info = v.signature_for(css, timing([("a", 4), ("b", 6)]))
    assert info["basis"] == "duration-dominant" and sig["base"]["tier"] == "light"
    assert all("#0a0e18" != b["decl"] for b in info["profile"]["backdrops"])


# ---- warnings, ties --------------------------------------------------------------------------------------------

def test_multiple_backdrops_always_warn_and_report_the_share():
    w = v.backdrop_warnings(EP3_CSS, timing(EP3_DURS))
    assert w[0]["code"] == "multiple_backdrops" and w[0]["backdrops"] == 6 and w[0]["basis"] == "duration-dominant"
    assert math.isclose(w[0]["dominant_share"], 11.315 / 53.573, abs_tol=1e-3)
    assert "dominant_backdrop_ambiguous" in [x["code"] for x in w]            # real ep3 is a near-tie


def test_exact_tie_is_flagged_and_broken_by_earliest_scene():
    css, t = two("#10303a", "#f4efe6", 5, 5)
    prof = v.backdrop_profile(css, t)
    assert prof["ambiguous"] and prof["dominant"]["scenes"] == ["a"] and len(prof["tied"]) == 2
    assert "dominant_backdrop_ambiguous" in [w["code"] for w in v.backdrop_warnings(css, t)]


def test_near_tie_within_five_points_is_ambiguous_and_the_longer_still_wins():
    css, t = two("#10303a", "#f4efe6", 4.8, 5.2)                      # 48% vs 52%: 4 points apart
    prof = v.backdrop_profile(css, t)
    assert prof["ambiguous"] and prof["dominant"]["scenes"] == ["b"]


def test_clear_winner_is_not_ambiguous():
    css, t = two("#10303a", "#f4efe6", 3, 7)
    assert not v.backdrop_profile(css, t)["ambiguous"]


def test_tie_breaking_is_deterministic_and_independent_of_css_order():
    t = timing([("a", 5), ("b", 5)])
    c1 = "#root{background:#000} #s-a{background:#10303a} #s-b{background:#f4efe6}"
    c2 = "#root{background:#000} #s-b{background:#f4efe6} #s-a{background:#10303a}"
    assert v.backdrop_profile(c1, t)["dominant"]["scenes"] == v.backdrop_profile(c2, t)["dominant"]["scenes"] == ["a"]
    assert v.backdrop_profile(c1, t) == v.backdrop_profile(c1, t)


# ---- missing or invalid duration data --------------------------------------------------------------------------

def test_all_durations_invalid_falls_back_with_a_reason():
    css, _ = two("#f4efe6", "#e8f0ff", 1, 1)
    bad = {"scenes": [{"id": "a", "dur": 0}, {"id": "b", "dur": "x"}]}
    sig, info = v.signature_for(css, bad)
    assert info["basis"] == "global-rule" and sig == v.signature_from_css(css)
    w = v.backdrop_warnings(css, bad)
    assert [x["code"] for x in w] == ["per_scene_backdrops_not_in_signature", "scene_durations_unavailable"]
    assert "invalid_duration" in w[1]["message"]


def test_partly_invalid_durations_still_compute_and_say_what_was_dropped():
    css, _ = two("#10303a", "#f4efe6", 1, 1)
    doc = {"scenes": [{"id": "a", "dur": 2}, {"id": "b", "dur": 8}, {"id": "c", "dur": -3}]}
    w = v.backdrop_warnings(css, doc)
    assert [x["code"] for x in w] == ["multiple_backdrops", "timing_invalid_duration"] and w[1]["scene"] == "c"


# ---- timing discovery, claim, CLI ------------------------------------------------------------------------------

def test_load_timing_finds_job_layout_and_prefers_explicit(tmp_path):
    (tmp_path / "project").mkdir()
    (tmp_path / "audio").mkdir()
    comp = tmp_path / "project" / "index.html"
    comp.write_text("x")
    assert v.load_timing(comp) is None
    (tmp_path / "audio" / "timing.json").write_text(json.dumps(timing([("a", 1)])))
    assert v.load_timing(comp)["scenes"][0]["id"] == "a"
    other = tmp_path / "t2.json"
    other.write_text(json.dumps(timing([("z", 2)])))
    assert v.load_timing(comp, other)["scenes"][0]["id"] == "z"
    pilot = tmp_path / "t3.json"
    pilot.write_text(json.dumps({"narration_seconds": 1, "total": 2}))      # pilot-001 shape: no scenes
    assert v.scene_durations(v.load_timing(comp, pilot))[1][0]["code"] == "no_scenes"


def test_claim_guard_still_refuses_then_records_basis(tmp_path):
    css, t = two("#10303a", "#f4efe6", 3, 7)
    sig, info = v.signature_for(css, t)
    w = v.backdrop_warnings(css, t)
    ledger = tmp_path / "vl.json"
    r = v.claim("job-1", sig, seed=tmp_path / "none.json", path=ledger, warnings=w, basis=info["basis"])
    assert not r["ok"] and "refused" in r and not ledger.exists()
    r = v.claim("job-1", sig, seed=tmp_path / "none.json", path=ledger, warnings=w, acknowledge_warnings=True, basis=info["basis"])
    assert r["ok"] and json.loads(ledger.read_text())["entries"][0]["basis"] == "duration-dominant"


def test_cli_check_reports_distribution_ties_and_sensitivity(tmp_path, capsys, monkeypatch):
    job = tmp_path / "job"
    (job / "project").mkdir(parents=True)
    (job / "audio").mkdir()
    css, t = two("#10303a", "#f4efe6", 5, 5)
    (job / "project" / "index.html").write_text(f"<html><style>{css}</style></html>")
    (job / "audio" / "timing.json").write_text(json.dumps(t))
    monkeypatch.setattr(v, "ledger", lambda *a, **k: [])
    rc = v._main(["check", str(job)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["basis"] == "duration-dominant" and len(out["backdrop_distribution"]) == 2
    assert {x["code"] for x in out["warnings"]} == {"multiple_backdrops", "dominant_backdrop_ambiguous"}
    assert len(out["tie_sensitivity"]) == 2 and all(x["rule_b_ok"] for x in out["tie_sensitivity"])
