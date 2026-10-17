"""Unit tests for Lane M2-E: captions_hook."""
import pytest
from contentos.features import registry as _feat
from contentos.features import captions_hook


def test_captions_hook_registers():
    assert "captions_hook" in _feat._REGISTRY


def test_captions_hook_passthrough_when_off():
    spec = {}
    assert _feat.get("captions_hook", spec)({}, spec) == {}


def test_clean_scaffold_tags():
    tag, head = captions_hook.clean_tag_and_headline("HOOK", "The Model Asks", True, False)
    assert tag == "EXPLAINER"

    tag, head = captions_hook.clean_tag_and_headline("STEP 1", "Goal and Tools", False, False)
    assert tag == ""

    tag, head = captions_hook.clean_tag_and_headline("CTA", "Next: when it fails", False, True)
    assert tag == "UP NEXT"


def test_captions_hook_enabled_settings():
    spec = {"features": {"captions_hook": True}}
    res = _feat.get("captions_hook", spec)({}, spec)
    assert res.get("enabled") is True
    assert res.get("safezone_bottom_padding") >= 0.22
