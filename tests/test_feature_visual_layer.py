"""Unit tests for Lane M2-C: visual_layer."""
import pytest
from contentos.features import registry as _feat
from contentos.features import visual_layer


def test_visual_layer_registers():
    assert "visual_layer" in _feat._REGISTRY


def test_visual_layer_passthrough_when_off():
    spec = {}
    html = '<div class="scene clip" id="s1"><h1>Title</h1></div>'
    res_html, res_anim = _feat.get("visual_layer", spec)({}, 1, html, [], spec)
    assert res_html == html
    assert res_anim == []


def test_visual_layer_distinct_backdrops_and_decor():
    spec = {"features": {"visual_layer": True}}
    seen_bgs = set()
    for idx in range(1, 8):
        html = f'<div class="scene clip" id="s{idx}"><h1>Scene {idx}</h1></div>'
        res_html, _ = _feat.get("visual_layer", spec)({}, idx, html, [], spec)
        assert f'id="s{idx}"' in res_html
        assert "background:" in res_html
        assert f'id="decor{idx}"' in res_html
        # Extract background value
        for bg in visual_layer.BACKDROPS:
            if bg in res_html:
                seen_bgs.add(bg)
                break
    # Satisfies Rule A: at least 4 distinct backdrops across 7 scenes
    assert len(seen_bgs) >= 4
