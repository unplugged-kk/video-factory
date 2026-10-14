import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.intelligence import creative, styles  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
BRIEF = {"job": "ep4-example", "topic": "how DNS works", "content_type": "architecture-lesson",
         "length_kind": "short", "factual_density": "high", "register": "curious"}


def seeds():
    cards, problems = styles.load_all()
    assert problems == []
    return cards


def card(cid, **axes):
    c = copy.deepcopy(seeds()[0])
    c["id"] = cid
    c["axes"].update(axes)
    return c


def brief(**over):
    b = dict(BRIEF)
    b.update(over)
    return b


def rec(job, axes, created="2026-10-01", chosen="x"):
    return {"schema": creative.SCHEMA, "job": job, "created": created, "chosen": chosen, "axes": dict(axes)}


def test_brief_validation_rejects_bad_fields():
    assert creative.validate_brief(BRIEF) == []
    assert creative.validate_brief([]) == ["brief must be an object"]
    for k, bad in (("job", "-bad"), ("topic", "  "), ("content_type", "cooking"), ("length_kind", "medium"),
                   ("factual_density", "extreme"), ("register", "angry")):
        probs = creative.validate_brief(brief(**{k: bad}))
        assert len(probs) == 1 and k in probs[0], (k, probs)
    with pytest.raises(ValueError):
        creative.propose(brief(job=""), seeds())


def test_propose_is_deterministic():
    hist = [rec("a", seeds()[1]["axes"])]
    assert creative.propose(BRIEF, seeds(), hist) == creative.propose(BRIEF, seeds(), hist)


def test_fit_rewards_matching_content_type_and_penalises_avoid():
    c = seeds()[0]  # blueprint-diagram: architecture-lesson, how-to; avoid historical-explainer
    assert creative.score_card(c, BRIEF, [])["fit"] == 2
    assert creative.score_card(c, brief(content_type="historical-explainer"), [])["fit"] == -5
    s = creative.score_card(c, brief(content_type="news-opinion"), [])
    assert s["fit"] == 0 and s["score"] == 0


def test_novelty_counts_axes_against_most_recent_record_only():
    base = card("base-card")
    older = rec("old", card("o", layout_system="split", motion_grammar="parallax")["axes"], "2026-09-01")
    newest = rec("new", card("n", layout_system="split")["axes"], "2026-10-01")
    assert creative.score_card(base, BRIEF, [])["novelty"] == 0
    assert creative.score_card(base, BRIEF, [older, newest])["novelty"] == 1
    assert creative.score_card(base, BRIEF, [newest, older])["novelty"] == 2


def test_repeat_penalty_applies_for_same_combo_within_window_and_not_outside():
    base = card("base-card")
    same = rec("same", base["axes"])
    other = [rec(f"o{i}", card("o", layout_system="split", depth_model=d)["axes"])
             for i, d in enumerate(("flat", "pseudo-3d", "flat", "pseudo-3d", "flat"))]
    assert creative.score_card(base, BRIEF, [same], window=5)["repeat_penalty"] == -3
    assert creative.score_card(base, BRIEF, [same] + other[:4], window=5)["repeat_penalty"] == -3
    assert creative.score_card(base, BRIEF, [same] + other, window=5)["repeat_penalty"] == 0


def test_palette_is_not_an_input():
    hist = [rec("a", seeds()[1]["axes"])]
    plain = creative.propose(BRIEF, seeds(), hist)
    painted = []
    for i, c in enumerate(seeds()):
        c = copy.deepcopy(c)
        c["palette"] = {"bg": f"#00000{i}", "accent": "#ff0000"}
        painted.append(c)
    assert creative.propose(BRIEF, painted, hist) == plain


def test_three_seed_cards_give_three_candidates_and_no_warning():
    p = creative.propose(BRIEF, seeds())
    assert [c["style"] for c in p["candidates"]][0] == "blueprint-diagram"
    assert p["candidates"][0]["score"] == 4
    assert len(p["candidates"]) == 3 and p["warnings"] == []
    assert styles.check_distinct([{"id": c["style"], "axes": c["axes"]} for c in p["candidates"]]) == []


def test_fewer_cards_gives_warning():
    p = creative.propose(BRIEF, seeds()[:2])
    assert len(p["candidates"]) == 2 and len(p["warnings"]) == 1


def test_candidates_not_distinct_raise():
    with pytest.raises(ValueError, match="differ"):
        creative.propose(BRIEF, [card("aaa"), card("bbb"), seeds()[1]])


def test_unvalidated_cards_require_explicit_approval():
    cards = seeds()
    p = creative.propose(BRIEF, cards)
    assert all(c["experimental"] for c in p["candidates"])
    others = [c["style"] for c in p["candidates"][1:]]
    r = creative.make_record(BRIEF, p["candidates"], "blueprint-diagram", {o: "does not fit this brief" for o in others},
                             "2026-10-13", cards)
    assert r["requires_explicit_approval"] is True


def test_record_requires_reason_for_every_rejected_candidate():
    cards = seeds()
    cands = creative.propose(BRIEF, cards)["candidates"]
    others = [c["style"] for c in cands[1:]]
    with pytest.raises(ValueError, match="reason"):
        creative.make_record(BRIEF, cands, "blueprint-diagram", {others[0]: "8 chars!"}, "2026-10-13", cards)
    with pytest.raises(ValueError, match="reason"):
        creative.make_record(BRIEF, cands, "blueprint-diagram", {o: "7 chars" for o in others}, "2026-10-13", cards)
    r = creative.make_record(BRIEF, cands, "blueprint-diagram", {o: "8 chars!" for o in others}, "2026-10-13", cards)
    assert {x["style"] for x in r["rejected"]} == set(others)


def test_record_chosen_must_be_a_candidate():
    cards = seeds()
    cands = creative.propose(BRIEF, cards)["candidates"][:2]
    with pytest.raises(ValueError, match="candidates"):
        creative.make_record(BRIEF, cands, "slow-parallax-story", {}, "2026-10-13", cards)


def test_validate_record_round_trip():
    cards = seeds()
    cands = creative.propose(BRIEF, cards)["candidates"]
    r = creative.make_record(BRIEF, cands, "punch-split",
                             {c["style"]: "weaker fit for the brief" for c in cands if c["style"] != "punch-split"},
                             "2026-10-13", cards, note="n")
    assert creative.validate_record(r) == []
    assert r["axes"] == next(c for c in cards if c["id"] == "punch-split")["axes"]
    assert r["sound_strategy"] == next(c for c in cards if c["id"] == "punch-split")["sound"]
    bad = dict(r, rejected=r["rejected"][:1])
    assert creative.validate_record(bad)
    assert creative.validate_record(dict(r, schema="x"))


def test_variety_report_flags_one_axis_change_and_combo_repeat():
    a = card("a")["axes"]
    b = card("b", layout_system="split")["axes"]
    rep = creative.variety_report([rec("v1", a), rec("v2", b), rec("v3", a)], window=5)
    assert rep["meets_novelty_budget"] is False
    assert rep["per_video"][0]["axes_differing_from_previous"] is None
    assert rep["per_video"][1]["axes_differing_from_previous"] == 1
    assert rep["per_video"][2]["combo_repeated_within_window"] is True
    assert any("v2" in f and "1 axis" in f for f in rep["failures"])
    assert any("v3" in f and "repeats" in f for f in rep["failures"])


def test_variety_report_passes_for_distinct_sequence():
    recs = [rec(f"v{i}", c["axes"], chosen=c["id"]) for i, c in enumerate(seeds() + seeds()[:1])]
    rep = creative.variety_report(recs, window=2)
    assert rep["meets_novelty_budget"] is True and rep["failures"] == []
    assert rep["videos"] == 4 and sum(rep["transition_families_used"].values()) == 4
    assert sum(rep["motion_grammars_used"].values()) == 4


def _write_brief(tmp_path):
    f = tmp_path / "brief.json"
    f.write_text(json.dumps(BRIEF), encoding="utf-8")
    return f


def test_cli_record_writes_and_refuses_overwrite(tmp_path, capsys):
    bf, out = _write_brief(tmp_path), tmp_path / "rec.json"
    args = ["record", "--brief", str(bf), "--choose", "blueprint-diagram", "--out", str(out), "--created", "2026-10-13",
            "--reject", "punch-split=too punchy for a calm lesson", "--reject", "slow-parallax-story=story pacing, not a diagram"]
    assert creative.main(args) == 0
    r = json.loads(out.read_text(encoding="utf-8"))
    assert r["chosen"] == "blueprint-diagram" and r["created"] == "2026-10-13" and creative.validate_record(r) == []
    before = out.read_bytes()
    assert creative.main(args) == 1
    assert out.read_bytes() == before
    assert creative.main(args[:-4] + ["--out", str(tmp_path / "r2.json")]) == 2  # missing reasons
    assert not (tmp_path / "r2.json").exists()


def test_cli_report_exit_code_reflects_budget(tmp_path, capsys):
    good, bad = tmp_path / "good", tmp_path / "bad"
    good.mkdir()
    bad.mkdir()
    for i, c in enumerate(seeds()):
        (good / f"{i}.json").write_text(json.dumps(rec(f"g{i}", c["axes"], f"2026-10-0{i + 1}", c["id"])), encoding="utf-8")
    a = seeds()[0]["axes"]
    for i in range(2):
        (bad / f"{i}.json").write_text(json.dumps(rec(f"b{i}", a, f"2026-10-0{i + 1}")), encoding="utf-8")
    assert creative.main(["report", "--history", str(good)]) == 0
    assert creative.main(["report", "--history", str(bad)]) == 1
    assert creative.main(["report", "--history", str(tmp_path / "missing")]) == 2


def test_load_history_orders_by_created_then_job(tmp_path):
    a = seeds()[0]["axes"]
    for name, job, created in (("1", "zeta", "2026-10-01"), ("2", "alpha", "2026-10-02"), ("3", "beta", "2026-10-01")):
        (tmp_path / f"{name}.json").write_text(json.dumps(rec(job, a, created)), encoding="utf-8")
    (tmp_path / "other.json").write_text(json.dumps({"schema": "something-else"}), encoding="utf-8")
    assert [r["job"] for r in creative.load_history(tmp_path)] == ["beta", "zeta", "alpha"]
    assert creative.load_history(None) == []


def test_creative_does_not_touch_repo_files(tmp_path, capsys):
    def digest():
        return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((REPO / "config").rglob("*.json"))}
    before = digest()
    assert creative.main(["propose", "--brief", str(_write_brief(tmp_path))]) == 0
    assert digest() == before
