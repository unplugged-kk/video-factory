import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.intelligence import looks  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CARDS = looks.load_dir()
MAP = json.loads((REPO / "docs/generic-video/migration-map.json").read_text())["specs"]


def test_all_shipped_presets_validate():
    assert looks.validate_all() == []


def test_library_has_both_kinds_and_unique_ids():
    kinds = [c["kind"] for c in CARDS.values()]
    assert kinds.count("look") >= 25 and kinds.count("effect") >= 20
    assert len(CARDS) == len(kinds)


def test_every_look_effect_and_base_style_exists():
    for c in CARDS.values():
        if c["kind"] != "look":
            continue
        for e in c.get("effects", []):
            assert CARDS[e]["kind"] == "effect", (c["id"], e)
        if "base_style" in c:
            assert (REPO / "config/styles" / f"{c['base_style']}.json").exists()


def test_migration_map_covers_all_51_specs_and_targets_exist():
    assert len(MAP) == 51
    for name, m in MAP.items():
        assert m["presets"] or m["capabilities"], name
        for p in m["presets"]:
            assert p in CARDS, (name, p)
        for cap in m["capabilities"]:
            assert cap in __import__("contentos.videojob", fromlist=["x"]).CAPABILITIES, (name, cap)


def test_every_look_and_effect_is_used_by_the_map_or_a_look():
    used = {p for m in MAP.values() for p in m["presets"]}
    used |= {e for c in CARDS.values() if c["kind"] == "look" for e in c.get("effects", [])}
    assert set(CARDS) - used == set()


def test_check_rejects_bad_cards():
    good = copy.deepcopy(CARDS["anime-cel"])
    bad = copy.deepcopy(good)
    bad["palette"]["accent"] = "red"
    bad["bogus"] = 1
    bad["needs"] = ["telepathy"]
    bad["summary"] = "in the style of Attack on Titan"
    msg = " ".join(looks.check(bad, CARDS))
    for needle in ("palette.accent", "unknown key: bogus", "needs must", "third-party name"):
        assert needle in msg


def test_blocklist_does_not_flag_ordinary_words():
    c = copy.deepcopy(CARDS["punch-in-zoom"])
    c["summary"] = "no more than one punch-in per sentence"
    assert looks.check(c, CARDS) == []


def test_combine_keeps_base_and_drops_effects_that_do_not_fit():
    merged = looks.combine(CARDS["crayon-chalkboard"], CARDS["neon-sign"], CARDS)
    assert merged["palette"]["accent"] == CARDS["neon-sign"]["palette"]["accent"]
    assert merged["typography"] == CARDS["crayon-chalkboard"]["typography"]
    assert "neon-outline-trace" not in merged["effects"] and "segmentation" not in merged["needs"]
    assert merged["combined_from"] == ["crayon-chalkboard", "neon-sign"]
    assert looks.check(merged, CARDS) == []


def test_combine_keeps_fitting_effects_within_a_family():
    merged = looks.combine(CARDS["neon-sign"], CARDS["rgb-glitch-news"], CARDS)
    assert "rgb-split-glitch" in merged["effects"] and "neon-outline-trace" in merged["effects"]
    assert looks.check(merged, CARDS) == []


def test_combine_rejects_effects():
    with pytest.raises(ValueError):
        looks.combine(CARDS["punch-in-zoom"], CARDS["anime-cel"], CARDS)


def test_cli(capsys):
    assert looks.main(["validate"]) == 0
    assert looks.main(["show", "anime-cel"]) == 0
    assert looks.main(["show", "nope"]) == 2
    assert looks.main(["combine", "anime-cel", "comic-halftone"]) == 0
