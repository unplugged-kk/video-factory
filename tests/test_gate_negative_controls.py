import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contentos.intelligence import styles
from contentos.intelligence import visual
from contentos.production import critic
from contentos.production import motion_audit
from contentos.production import timeline


# 1. motion_audit.motion_stats
def test_motion_stats_still_fraction_and_longest_still():
    # Bad: totally still sequence
    ydif_still = [0.0] * 100
    res_still = motion_audit.motion_stats(ydif_still, fps=25.0)
    assert res_still["still_fraction"] == 1.0
    assert res_still["longest_still_s"] == 4.0  # 100 frames / 25 fps = 4.0s

    # Good: smoothly moving sequence
    ydif_moving = [0.5] * 100
    res_moving = motion_audit.motion_stats(ydif_moving, fps=25.0)
    assert res_moving["still_fraction"] == 0.0
    assert res_moving["longest_still_s"] == 0.0


def test_motion_stats_pop_detection():
    # Bad: one isolated jump
    ydif_jump = [0.2] * 50 + [5.0] + [0.2] * 50
    res_jump = motion_audit.motion_stats(ydif_jump, fps=25.0)
    assert res_jump["pop_count"] == 1
    assert res_jump["pops"][0] == 2.0  # frame 50 / 25 fps = 2.0s

    # Good: smooth plateau
    ydif_plateau = [0.2] * 50 + [3.0] * 10 + [0.2] * 50
    res_plateau = motion_audit.motion_stats(ydif_plateau, fps=25.0)
    assert res_plateau["pop_count"] == 0


# 2. motion_audit.ease_inventory
def test_motion_audit_ease_inventory_variety():
    # Bad: HTML with no eases
    html_none = "<div class='card'>Static content</div>"
    res_none = motion_audit.ease_inventory(html_none)
    assert res_none["total"] == 0
    assert res_none["by_ease"] == {}

    # Good: HTML with 4 distinct eases
    html_four = """
    gsap.to('.a', {ease: 'power3.out'});
    gsap.to('.b', {ease: 'power2.inOut'});
    gsap.to('.c', {ease: 'power2.out'});
    gsap.to('.d', {ease: 'power3.inOut'});
    """
    res_four = motion_audit.ease_inventory(html_four)
    assert res_four["total"] == 4
    assert len(res_four["by_ease"]) == 4


# 3. critic.verdict & thresholds
def _dummy_critic_report(**overrides):
    base_scores = {d: 8 for d in critic.DIMENSIONS}
    rep = {
        "critic": "independent",
        "scores": base_scores,
        "hard_failures": [],
        "verdict": "pass",
        "notes": [{"issue": "all good"}],
    }
    rep.update(overrides)
    return rep


def test_critic_thresholds_pinned():
    assert critic.MIN_EACH == 7
    assert critic.MIN_AVG == 8.0
    assert len(critic.DIMENSIONS) == 8


def test_critic_verdict_rejects_on_hard_failure():
    rep = _dummy_critic_report(hard_failures=["dead_or_black_frames"])
    assert critic.verdict(rep) == "reject"


def test_critic_verdict_revises_on_low_score():
    scores = {d: 9 for d in critic.DIMENSIONS}
    scores["hook_clarity"] = 6  # 6 < MIN_EACH
    rep = _dummy_critic_report(scores=scores)
    assert critic.verdict(rep) == "revise"


def test_critic_verdict_passes_when_all_meet_thresholds():
    rep = _dummy_critic_report()
    assert critic.verdict(rep) == "pass"


# 4. critic.check
def test_critic_check_catches_claimed_verdict_mismatch():
    scores = {d: 9 for d in critic.DIMENSIONS}
    scores["hook_clarity"] = 6
    # claimed pass despite score 6
    rep_mismatch = _dummy_critic_report(scores=scores, verdict="pass")
    chk = critic.check(rep_mismatch)
    assert chk["ok"] is False
    assert any("claimed verdict 'pass' but scores imply 'revise'" in p for p in chk["problems"])

    rep_match = _dummy_critic_report(scores=scores, verdict="revise")
    assert critic.check(rep_match)["ok"] is True


# 5. critic.validate
def test_critic_validate_requires_independent_critic():
    rep_bad = _dummy_critic_report(critic="author")
    problems = critic.validate(rep_bad)
    assert any("critic must be 'independent'" in p for p in problems)

    rep_good = _dummy_critic_report(critic="independent")
    assert critic.validate(rep_good) == []


# 6. timeline.validate
def _dummy_timeline():
    lines = [
        {"id": "s1", "title": "S1", "t0": 0.0, "t1": 3.0, "words": [("one", 0.1, 0.5), ("two", 0.6, 1.0)], "sources": ["matched", "matched"]},
        {"id": "s2", "title": "S2", "t0": 3.0, "t1": 6.0, "words": [("three", 3.1, 3.5)], "sources": ["matched"]},
    ]
    cues = [{"scene": "s1", "word": 0, "do": "pop"}]
    return timeline.build_timeline("test-job", 30, 6.0, lines, cues)


def test_timeline_validate_catches_scene_gap():
    tl = _dummy_timeline()
    tl["scenes"][1]["t0"] = 3.5  # gap between 3.0 and 3.5
    issues = timeline.validate(tl)
    codes = [i["code"] for i in issues]
    assert "scene_gap" in codes


def test_timeline_validate_catches_word_outside_scene():
    tl = _dummy_timeline()
    tl["words"][0]["t0"] = 4.0  # word 0 is in s1 (0.0-3.0), but starts at 4.0
    tl["words"][0]["t1"] = 4.5
    issues = timeline.validate(tl)
    codes = [i["code"] for i in issues]
    assert "word_outside_scene" in codes


def test_timeline_validate_catches_cue_not_in_scene():
    tl = _dummy_timeline()
    # word 2 is in s2 (w0=2, w1=2), but cue anchors to scene s1
    tl["cues"][0]["scene"] = "s1"
    tl["cues"][0]["at"]["word"] = 2
    issues = timeline.validate(tl)
    codes = [i["code"] for i in issues]
    assert "cue_not_in_scene" in codes


def test_timeline_validate_catches_unverified_trust_claim():
    tl = _dummy_timeline()
    tl["alignment"]["timing_trust"] = "human-verified"
    tl["alignment"]["verified_anchors"] = []
    issues = timeline.validate(tl)
    codes = [i["code"] for i in issues]
    assert "trust" in codes


# 7. intelligence.visual Rule A / Rule B
def test_rule_a_catches_uniform_backdrop_without_motif():
    # Bad: all 4 scenes have the same backdrop
    plan_uniform = {
        "scenes": [
            {"id": "s1", "backdrop": "blue-grid"},
            {"id": "s2", "backdrop": "blue-grid"},
            {"id": "s3", "backdrop": "blue-grid"},
            {"id": "s4", "backdrop": "blue-grid"},
        ],
        "motif": None,
    }
    res_bad = visual.rule_a_from_plan(plan_uniform)
    assert res_bad["status"] == "fail"
    assert res_bad["ok"] is False

    # Good: 3 distinct backdrops across 4 scenes
    plan_varied = {
        "scenes": [
            {"id": "s1", "backdrop": "blue-grid"},
            {"id": "s2", "backdrop": "dark-dots"},
            {"id": "s3", "backdrop": "warm-paper"},
            {"id": "s4", "backdrop": "blue-grid"},
        ],
        "motif": None,
    }
    res_good = visual.rule_a_from_plan(plan_varied)
    assert res_good["status"] == "pass"
    assert res_good["ok"] is True


def test_rule_b_catches_duplicate_signature():
    sig = {
        "structure": "grid",
        "temperature": "cool",
        "texture": "grid",
        "base": {"hue": 6, "tier": "dark"},
        "accents": [6, 7],
    }
    history = [{"content_id": "prev-job", "signature": copy.deepcopy(sig)}]

    # Bad: identical look to recent video
    res_dup = visual.rule_b(sig, history, content_id="new-job")
    assert res_dup["ok"] is False
    assert "prev-job" in res_dup["duplicates"]

    # Good: differing on structure and temperature (>= 2 fields)
    sig_distinct = copy.deepcopy(sig)
    sig_distinct["structure"] = "paper"
    sig_distinct["temperature"] = "warm"
    res_distinct = visual.rule_b(sig_distinct, history, content_id="new-job")
    assert res_distinct["ok"] is True
    assert res_distinct["duplicates"] == []


# 8. styles.validate_card & check_distinct
def test_styles_validate_card_catches_invalid_fields():
    cards, _ = styles.load_all()
    bad_card = copy.deepcopy(cards[0])
    bad_card["status"] = "super-validated"  # invalid status
    problems = styles.validate_card(bad_card)
    assert any("status" in p for p in problems)


def test_styles_check_distinct_catches_insufficient_axis_difference():
    cards, _ = styles.load_all()
    c1 = copy.deepcopy(cards[0])
    c2 = copy.deepcopy(cards[0])
    c2["id"] = "card-variant-too-close"
    # mutate only 1 axis instead of >= 3
    c2["axes"]["layout_system"] = "split" if c1["axes"]["layout_system"] != "split" else "grid"

    problems = styles.check_distinct([c1, c2], min_axes=3)
    assert len(problems) >= 1
    assert any("differ on only 1 axes" in p for p in problems)
