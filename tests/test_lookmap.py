import copy
import json

import pytest

from contentos.intelligence import looks as L
from contentos.scenekit import lookmap as M
from contentos.scenekit import styles as S

LOOKS = L.load_dir()


def _look(i="flat-dark-news"):
    return copy.deepcopy(LOOKS[i])


def test_every_look_compiles_or_names_a_blocker():
    res = M.compile_all()
    assert len(res) == 30
    for i, r in res.items():
        if isinstance(r, M.LookBlocked):
            assert r.reasons, i
        else:
            assert S.check_style(i, r) == [], i
    assert not isinstance(res["flat-dark-news"], M.LookBlocked)
    assert not isinstance(res["watercolor-wash"], M.LookBlocked)
    assert any("rain" in x for x in res["aged-paper-rain"].reasons)


def test_compile_is_deterministic():
    a, b = M.to_style(_look()), M.to_style(_look())
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["look"]["look_digest"] == M._digest(LOOKS["flat-dark-news"])


def test_two_looks_differ_on_three_axes_and_in_tokens():
    a, b = M.to_style(_look("flat-dark-news")), M.to_style(_look("watercolor-wash"))
    assert M.axes_differing(a, b) >= 3
    assert a["tokens"]["bg"] != b["tokens"]["bg"] and a["tokens"]["accent"] != b["tokens"]["accent"]


def test_palette_fonts_motion_come_from_the_look():
    st = M.to_style(_look())
    assert st["tokens"]["bg"] == "#242021" and st["tokens"]["accent"] == "#e63946"
    assert st["motion"] == "cut"          # intensity 4
    assert M.contrast(st["tokens"]["ink"], st["tokens"]["bg"]) >= M.MIN_INK
    assert M.contrast(st["tokens"]["muted"], st["tokens"]["bg"]) >= M.MIN_INK


def test_unmapped_font_fails_closed():
    d = _look(); d["typography"]["display"] = "Comic Sans Nonexistent"
    with pytest.raises(M.LookBlocked, match="no system mapping"):
        M.to_style(d)


def test_low_contrast_fails_closed():
    d = _look(); d["palette"]["fg"] = "#2a2627"
    with pytest.raises(M.LookBlocked, match="contrast"):
        M.to_style(d)


def test_unpaintable_texture_and_unknown_base_fail_closed():
    d = _look(); d["texture"] = ["rain"]
    with pytest.raises(M.LookBlocked, match="rain"):
        M.to_style(d)
    d = _look(); d["base_style"] = "no-such-style"
    with pytest.raises(M.LookBlocked, match="base_style"):
        M.to_style(d)


def test_effect_preset_is_not_a_style():
    e = next(v for v in LOOKS.values() if v["kind"] == "effect")
    with pytest.raises(M.LookBlocked, match="effect"):
        M.to_style(e)


def test_css_is_safe_for_a_double_quoted_style_attribute():
    for r in M.compile_all().values():
        if isinstance(r, M.LookBlocked):
            continue
        for g in r["grounds"]:
            assert '"' not in g
        for layer in r["tokens"]["texture"]:
            assert '"' not in layer["image"] and "'" not in layer["image"]


def test_unread_look_fields_are_reported_not_faked():
    assert "effects" in M.to_style(_look())["look"]["unread"]


def test_builtin_styles_untouched():
    assert S.validate() == []
