import copy
import json
from pathlib import Path

from contentos.production import critic as c

GOOD = {"critic": "independent", "verdict": "pass", "scores": {d: 9 for d in c.DIMENSIONS}, "hard_failures": [], "notes": []}


def test_good_report_passes():
    assert c.validate(GOOD) == []
    assert c.verdict(GOOD) == "pass"
    assert c.check(GOOD)["ok"]


def test_hard_failure_forces_reject_even_with_perfect_scores():
    r = copy.deepcopy(GOOD)
    r["hard_failures"] = ["fabricated_data_unlabeled"]
    assert c.verdict(r) == "reject"
    r["verdict"] = "reject"
    assert c.check(r)["ok"]


def test_one_low_score_means_revise():
    r = copy.deepcopy(GOOD)
    r["scores"]["readability"] = 5
    assert c.verdict(r) == "revise"


def test_low_average_means_revise_even_if_each_meets_floor():
    r = copy.deepcopy(GOOD)
    r["scores"] = {d: 7 for d in c.DIMENSIONS}                     # each >= 7 but average 7.0 < 8.0
    assert c.verdict(r) == "revise"


def test_builder_cannot_overstate_verdict():
    r = copy.deepcopy(GOOD)
    r["scores"]["continuity"] = 3
    out = c.check(r)                                              # claims 'pass'
    assert not out["ok"] and out["computed_verdict"] == "revise" and "scores imply" in out["problems"][0]


def test_validation_catches_shape_errors():
    bad = {"critic": "builder", "verdict": "great", "scores": {"readability": 11, "av_sync": True, "bogus": 5},
           "hard_failures": ["nope"], "notes": [{"time": 1}]}
    msgs = " | ".join(c.validate(bad))
    for frag in ("independent", "readability", "av_sync", "unknown score dimension 'bogus'", "unknown hard failure", "verdict must", "notes must"):
        assert frag in msgs
    assert c.check(bad)["ok"] is False


def test_example_template_is_valid():
    p = Path(__file__).resolve().parents[1] / ".claude/skills/explainer-visual-qa/templates/critic-output.example.json"
    if p.exists():
        assert c.validate(json.loads(p.read_text())) == []
