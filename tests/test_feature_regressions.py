"""Regressions for defects the end-to-end pass confirmed (see docs/E2E-VERIFICATION.md).

Both are fast and toolchain-free, so they run in the default suite and in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contentos.features import registry, visual_layer  # noqa: E402

# Exactly the opening tag s_compose emits for scene 1, which is what the hook rewrites.
SCENE = '<div class="scene clip" id="s1" data-start="0.00" data-duration="2.00"><p class="cap">hi</p></div>'


def _decor(ctx, spec=None):
    html, _ = visual_layer.visual_layer_hook(
        ctx, 1, SCENE, [], spec if spec is not None else {"features": {"visual_layer": True}}
    )
    return html


def test_style_card_id_drives_the_container_style():
    """ctx['style_card'] is the chosen card dict, whose key is 'id'.

    The hook used to read 'chosen', which a card dict never has, so every style-family
    container style below it was unreachable and the default style was always used.
    """
    html = _decor({"style_card": {"id": "sketch-hand-drawn"}})
    assert "2px dashed" in html, "sketch card style not applied"


def test_a_different_card_family_gives_a_different_style():
    product = _decor({"style_card": {"id": "product-launch"}})
    kinetic = _decor({"style_card": {"id": "kinetic-typography"}})
    assert "perspective(1000px)" in product, "product card style not applied"
    assert "border-left:6px solid #fbbf24" in kinetic, "kinetic card style not applied"
    assert product != kinetic


def test_without_a_card_the_default_style_is_used():
    html = _decor({})
    assert "1px solid rgba(255,255,255,0.08)" in html
    assert "2px dashed" not in html


def test_spec_style_is_still_used_when_there_is_no_card():
    html = _decor({}, {"features": {"visual_layer": True}, "style": "product-launch"})
    assert "perspective(1000px)" in html


def test_extra_gates_alias_passes_through_when_off():
    """extra_gates registers this name too; it needs a pass-through or get() raises KeyError."""
    assert registry.get("extra_gates", {})({}, "/nope.mp4", {}) == []


def test_extra_gates_alias_reaches_the_handler_when_on():
    spec = {"features": {"extra_gates": True}}
    res = registry.get("extra_gates", spec)({}, "/nope.mp4", spec)
    assert res and res[0][0] == "extra_gates" and res[0][1] == "FAIL"
