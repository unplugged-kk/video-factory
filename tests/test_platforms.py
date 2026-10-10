import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.production import platforms as pf  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
REAL = REPO / "config" / "platforms.json"


@pytest.fixture(scope="module")
def reg():
    return pf.load(REAL)


def write(tmp_path, mutate):
    data = json.loads(REAL.read_text(encoding="utf-8"))
    mutate(data)
    p = tmp_path / "platforms.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ---- registry ----------------------------------------------------------------------------------------------------

def test_real_registry_loads_and_has_expected_platforms(reg):
    assert set(reg) == {"youtube", "instagram", "x", "threads", "linkedin", "tiktok"}


def test_tiktok_is_disabled_because_it_is_blocked_in_india(reg):
    assert reg["tiktok"]["available_in_india"] is False and reg["tiktok"]["default_enabled"] is False
    assert "tiktok" not in pf.default_platforms(reg)


def test_every_format_has_sources_and_confidence(reg):
    for p in reg.values():
        for f in p["formats"].values():
            assert f["sources"] and f["confidence"] in pf.CONFIDENCE


@pytest.mark.parametrize("mutate,msg", [
    (lambda d: d.update(schema="platforms/2"), "schema"),
    (lambda d: d["platforms"].append(copy.deepcopy(d["platforms"][0])), "duplicated"),
    (lambda d: d["platforms"][0]["formats"]["short"].update(max_seconds=0), "max_seconds"),
    (lambda d: d["platforms"][0]["formats"]["short"].update(confidence="rumour"), "confidence"),
    (lambda d: d["platforms"][0]["formats"]["short"].update(sources=[]), "source"),
    (lambda d: d["platforms"][0]["formats"]["short"].update(aspect_range=[2, 1]), "aspect_range"),
    (lambda d: d["platforms"][0]["formats"].update(medium=d["platforms"][0]["formats"]["short"]), "kind"),
])
def test_bad_registry_is_rejected(tmp_path, mutate, msg):
    with pytest.raises(pf.PlatformError, match=msg):
        pf.load(write(tmp_path, mutate))


def test_missing_file_is_a_clear_error(tmp_path):
    with pytest.raises(pf.PlatformError, match="cannot read"):
        pf.load(tmp_path / "nope.json")


# ---- aspect ------------------------------------------------------------------------------------------------------

def test_parse_aspect():
    assert pf.parse_aspect("9:16") == pytest.approx(0.5625)
    assert pf.parse_aspect("16:9") == pytest.approx(1.7778, abs=1e-3)
    for bad in ("916", "0:5", "a:b"):
        with pytest.raises(pf.PlatformError):
            pf.parse_aspect(bad)


# ---- check -------------------------------------------------------------------------------------------------------

def test_45_second_vertical_fits_every_default_platform(reg):
    res = pf.plan(reg, "short", 45, "9:16")
    assert {r["platform"] for r in res} == set(pf.default_platforms(reg))
    assert all(r["status"] in ("ok", "ok-unverified") for r in res)


def test_x_standard_limit_is_140_seconds(reg):
    assert pf.check(reg, "x", "short", 140, "9:16")["status"] == "ok"
    assert pf.check(reg, "x", "short", 141, "9:16")["status"] == "too-long"


def test_shorts_limit_and_horizontal_video(reg):
    assert pf.check(reg, "youtube", "short", 180, "9:16")["status"] == "ok"
    assert pf.check(reg, "youtube", "short", 181, "9:16")["status"] == "too-long"
    assert pf.check(reg, "youtube", "short", 60, "16:9")["status"] == "aspect-mismatch"


def test_instagram_aspect_window(reg):
    assert pf.check(reg, "instagram", "short", 60, "9:16")["status"] == "ok"
    assert pf.check(reg, "instagram", "short", 60, "1:1")["status"] == "ok"
    assert pf.check(reg, "instagram", "short", 60, "9:21")["status"] == "aspect-mismatch"


def test_third_party_limits_are_flagged_unverified(reg):
    r = pf.check(reg, "linkedin", "short", 60, "9:16")
    assert r["status"] == "ok-unverified" and "verify" in r["reasons"][0]


def test_disabled_platform_needs_explicit_override(reg):
    assert pf.check(reg, "tiktok", "short", 45, "9:16")["status"] == "disabled"
    r = pf.check(reg, "tiktok", "short", 45, "9:16", allow_disabled=True)
    assert r["status"] == "ok-unverified"          # conflicting sources


def test_paid_format_needs_opt_in(reg):
    assert pf.check(reg, "x", "long", 600, "16:9")["status"] == "needs-opt-in"
    assert pf.check(reg, "x", "long", 600, "16:9", opt_in=["x"])["status"] == "ok"


def test_unsupported_kind(reg):
    r = pf.check(reg, "threads", "long", 600, "16:9")
    assert r["status"] == "unsupported"


def test_tier_extends_youtube_long(reg):
    assert pf.check(reg, "youtube", "long", 1200, "16:9")["status"] == "too-long"
    assert pf.check(reg, "youtube", "long", 1200, "16:9", tier="verified")["status"] == "ok"
    with pytest.raises(pf.PlatformError, match="no tier"):
        pf.check(reg, "youtube", "long", 60, "16:9", tier="gold")


def test_unknown_platform_and_kind_raise(reg):
    with pytest.raises(pf.PlatformError):
        pf.check(reg, "myspace", "short", 10)
    with pytest.raises(pf.PlatformError):
        pf.check(reg, "x", "medium", 10)


# ---- budget ------------------------------------------------------------------------------------------------------

def test_short_budget_is_limited_by_x_standard(reg):
    b = pf.budget(reg, "short")
    assert b["max_seconds"] == 140 and b["limiting"] == "x"
    assert "tiktok" not in b["per_platform"]


def test_short_budget_without_x_is_the_next_smallest(reg):
    b = pf.budget(reg, "short", platforms=["youtube", "instagram", "threads"])
    assert b["max_seconds"] == 180 and b["limiting"] in ("youtube", "instagram")


def test_long_budget_lists_skipped_platforms(reg):
    b = pf.budget(reg, "long")
    assert b["max_seconds"] == 600 and b["limiting"] == "linkedin"
    assert b["skipped"]["x"] == "needs-opt-in" and b["skipped"]["threads"] == "unsupported" and b["skipped"]["instagram"] == "unsupported"


def test_long_budget_youtube_only_uses_tier(reg):
    assert pf.budget(reg, "long", platforms=["youtube"])["max_seconds"] == 900
    assert pf.budget(reg, "long", platforms=["youtube"], tiers={"youtube": "verified"})["max_seconds"] == 43200


def test_budget_with_nothing_usable(reg):
    b = pf.budget(reg, "long", platforms=["threads"])
    assert b["max_seconds"] is None and b["skipped"] == {"threads": "unsupported"}


def test_check_does_not_mutate_registry(reg):
    before = json.dumps(reg, sort_keys=True)
    pf.plan(reg, "short", 45, "9:16")
    pf.budget(reg, "long", tiers={"youtube": "verified"})
    assert json.dumps(reg, sort_keys=True) == before


# ---- CLI ---------------------------------------------------------------------------------------------------------

def test_cli_budget_and_check_exit_codes(capsys):
    assert pf._main(["budget", "--kind", "short"]) == 0
    assert "limited by x" in capsys.readouterr().out
    assert pf._main(["check", "--kind", "short", "--seconds", "56", "--aspect", "9:16"]) == 0
    assert pf._main(["check", "--kind", "short", "--seconds", "200", "--aspect", "9:16"]) == 1
    assert pf._main(["check", "--kind", "short", "--seconds", "10", "--platforms", "nope"]) == 2
    assert pf._main(["--registry", "/nonexistent.json", "list"]) == 2


# ---- owner ceiling -----------------------------------------------------------------------------------------------

def test_owner_limits_in_real_registry():
    o = pf.owner_limits(REAL)
    assert o["short"] == 300 and o["short_default"] == 180 and o["long"] is None


def test_owner_ceiling_is_a_hard_cap(reg):
    r = pf.check(reg, "threads", "short", 301, "9:16", owner_max=300)
    assert r["status"] == "over-owner-ceiling"       # Threads itself allows 300 s; the owner cap decides first
    assert pf.check(reg, "threads", "short", 300, "9:16", owner_max=300)["status"] == "ok"
    assert pf.check(reg, "threads", "short", 30, "9:16", owner_max=300)["status"] == "ok"   # shorter is always fine


def test_budget_owner_ceiling_binds_only_when_tighter(reg):
    assert pf.budget(reg, "short", owner_max=300)["limiting"] == "x"            # X 140 s is tighter than 300 s
    b = pf.budget(reg, "short", owner_max=120)
    assert b["limiting"] == "owner" and b["max_seconds"] == 120 and b["platform_max_seconds"] == 140
    assert pf.budget(reg, "short", platforms=["threads", "linkedin"], owner_max=180)["limiting"] == "owner"


def test_three_minute_master_fits_all_but_x(reg):
    res = {r["platform"]: r["status"] for r in pf.plan(reg, "short", 180, "9:16", owner_max=300)}
    assert res["x"] == "too-long"
    assert all(res[p] in ("ok", "ok-unverified") for p in ("youtube", "instagram", "threads", "linkedin"))


def test_five_minute_master_fits_only_threads_and_linkedin(reg):
    res = {r["platform"]: r["status"] for r in pf.plan(reg, "short", 300, "9:16", owner_max=300)}
    assert res["threads"] == "ok" and res["linkedin"] == "ok-unverified"
    assert {res[p] for p in ("youtube", "instagram", "x")} == {"too-long"}


def test_bad_owner_values_rejected(tmp_path):
    p = write(tmp_path, lambda d: d["owner"].update(short_max_seconds=-5))
    with pytest.raises(pf.PlatformError, match="owner.short"):
        pf.owner_limits(p)
    p = write(tmp_path, lambda d: d["owner"].update(short_default_max_seconds=900))
    with pytest.raises(pf.PlatformError, match="default"):
        pf.owner_limits(p)
