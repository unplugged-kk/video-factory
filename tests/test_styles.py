import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.intelligence import styles  # noqa: E402
from contentos.production import direction  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SEED_IDS = ("blueprint-diagram", "punch-split", "slow-parallax-story")


def seed(cid):
    return json.loads((REPO / "config" / "styles" / f"{cid}.json").read_text(encoding="utf-8"))


def registry():
    return direction.load_registry()


def valid_card(**over):
    card = seed("blueprint-diagram")
    card.update(over)
    return card


def test_seed_cards_exist_and_validate():
    cards, problems = styles.load_all()
    assert sorted(c["id"] for c in cards) == sorted(SEED_IDS)
    assert problems == []


def test_seed_cards_are_unvalidated_and_have_no_evidence():
    for cid in SEED_IDS:
        card = seed(cid)
        assert card["status"] == "unvalidated"
        assert card["evidence"] == []


def test_seed_cards_are_pairwise_distinct_on_all_six_axes():
    cards = [seed(cid) for cid in SEED_IDS]
    for a, b in [(0, 1), (0, 2), (1, 2)]:
        assert len(styles.differing_axes(cards[a], cards[b])) == 6


def test_distinct_check_flags_a_palette_variant():
    a = seed("blueprint-diagram")
    b = copy.deepcopy(a)
    b["id"], b["name"] = "blueprint-recolour", "Blueprint recolour"
    problems = styles.check_distinct([a, b])
    assert problems and "blueprint-diagram" in problems[0] and "blueprint-recolour" in problems[0]


def test_missing_axis_is_rejected():
    card = valid_card()
    del card["axes"]["depth_model"]
    assert any("depth_model" in p for p in styles.validate_card(card, registry()))


def test_bad_enum_value_is_rejected():
    card = valid_card()
    card["axes"]["motion_grammar"] = "bounce"
    assert any("motion_grammar" in p for p in styles.validate_card(card, registry()))


def test_dial_out_of_range_is_rejected():
    card = valid_card()
    card["dials"]["energy"] = 6
    assert any("dials.energy" in p for p in styles.validate_card(card, registry()))


def test_validated_without_evidence_is_rejected():
    card = valid_card(status="validated", evidence=[])
    assert any("validated" in p for p in styles.validate_card(card, registry()))


def test_music_led_sound_is_rejected():
    card = valid_card()
    card["sound"]["mode"] = "music-led"
    assert any("sound.mode" in p for p in styles.validate_card(card, registry()))


def test_silent_with_cues_is_rejected():
    card = valid_card()
    card["sound"] = {"mode": "silent", "max_cues_per_minute": 3}
    assert any("silent" in p for p in styles.validate_card(card, registry()))


def test_r1_r6_flag_false_is_rejected():
    card = valid_card()
    card["motion"]["respects_r1_r6"] = False
    assert any("respects_r1_r6" in p for p in styles.validate_card(card, registry()))


def test_short_frame_checklist_is_rejected():
    card = valid_card(frame_checklist=["one", "two", "three"])
    assert any("frame_checklist" in p for p in styles.validate_card(card, registry()))


def test_unknown_capability_is_rejected():
    card = valid_card(requires=["skill:does-not-exist"])
    assert any("does-not-exist" in p for p in styles.validate_card(card, registry()))


def test_non_installed_capability_is_rejected():
    reg = registry()
    not_installed = next((cid for cid, e in reg.entries.items() if e["status"] != "installed"), None)
    if not_installed is None:
        pytest.skip("registry has no non-installed capability")
    problems = styles.validate_card(valid_card(requires=[not_installed]), reg)
    assert any(not_installed in p for p in problems)


def test_id_must_match_filename(tmp_path):
    (tmp_path / "other-name.json").write_text(json.dumps(seed("blueprint-diagram")), encoding="utf-8")
    cards, problems = styles.load_all(tmp_path, registry())
    assert cards == [] and any("other-name" in p for p in problems)


def test_validate_does_not_mutate_input():
    card = valid_card()
    before = copy.deepcopy(card)
    styles.validate_card(card, registry(), filename_stem="blueprint-diagram")
    assert card == before


def test_cli_validate_exit_codes(tmp_path):
    assert styles.main(["validate"]) == 0
    (tmp_path / "blueprint-diagram.json").write_text("{}", encoding="utf-8")
    assert styles.main(["validate", "--dir", str(tmp_path)]) == 1
    assert styles.main(["validate", "--dir", str(tmp_path / "missing")]) == 2


def test_no_existing_config_changed_by_loading():
    path = REPO / "config" / "capabilities.json"
    before = path.read_bytes()
    styles.load_all()
    assert path.read_bytes() == before


def test_seed_cards_have_reviewer_and_date():
    for cid in SEED_IDS:
        assert seed(cid)["reviewed_by"] == {"name": "Kishore", "date": "2026-10-13"}


def test_missing_reviewer_is_rejected():
    card = valid_card()
    del card["reviewed_by"]
    assert any("reviewed_by" in p for p in styles.validate_card(card, registry()))


def test_blank_reviewer_name_is_rejected():
    card = valid_card(reviewed_by={"name": "   ", "date": "2026-10-13"})
    assert any("reviewed_by.name" in p for p in styles.validate_card(card, registry()))


@pytest.mark.parametrize("bad", ["2026-13-40", "13/10/2026", "2026-10-13T00:00", None])
def test_bad_review_date_is_rejected(bad):
    card = valid_card(reviewed_by={"name": "kishore", "date": bad})
    assert any("reviewed_by.date" in p for p in styles.validate_card(card, registry()))


def test_ease_without_source_is_rejected():
    card = valid_card()
    card["motion"]["ease_sources"] = [{"ease": "power3.out", "file": ".claude/skills/explainer-motion-craft/SKILL.md"}]
    problems = styles.validate_card(card, registry())
    assert any("power2.inOut" in p and "no motion.ease_sources entry" in p for p in problems)


def test_ease_source_file_without_ease_name_is_rejected():
    card = valid_card()
    card["motion"]["ease_sources"][0]["file"] = "contentos/intelligence/styles.py"
    assert any("does not contain that ease name" in p for p in styles.validate_card(card, registry()))


@pytest.mark.parametrize("bad_file", ["no/such/file.md", "../outside.md", "/etc/hosts"])
def test_ease_source_outside_repo_is_rejected(bad_file):
    card = valid_card()
    card["motion"]["ease_sources"][0]["file"] = bad_file
    assert any("not a file inside the repo" in p for p in styles.validate_card(card, registry()))


def test_ease_source_for_unlisted_ease_is_rejected():
    card = valid_card()
    card["motion"]["ease_sources"].append({"ease": "power2.out", "file": ".claude/skills/explainer-motion-craft/SKILL.md"})
    assert any("power2.out" in p and "not in motion.ease_family" in p for p in styles.validate_card(card, registry()))


def test_ease_sources_must_have_exact_keys():
    card = valid_card()
    card["motion"]["ease_sources"][0] = {"ease": "power3.out"}
    assert any("exactly 'ease' and 'file'" in p for p in styles.validate_card(card, registry()))
