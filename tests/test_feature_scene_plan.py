"""Unit tests for Lane M2-B: scene_plan."""
import pytest
from contentos.features import registry as _feat
from contentos.features import scene_plan


def test_scene_plan_registers():
    assert "scene_plan" in _feat._REGISTRY


def test_scene_plan_passthrough_when_off():
    spec = {"script": [{"say": "Hello world", "headline": "Hi"}]}
    assert _feat.get("scene_plan", spec)({}, spec) == []


def test_scene_plan_synthesizes_plan_when_enabled():
    spec = {
        "features": {"scene_plan": True},
        "script": [
            {"say": "First line of the script.", "headline": "Intro", "tag": "HOOK"},
            {"say": "Second line explains the tool loop.", "headline": "Tool Loop", "tag": "STEP 1"},
        ]
    }
    ctx = {}
    scenes = _feat.get("scene_plan", spec)(ctx, spec)
    assert len(scenes) == 2
    assert scenes[0]["id"] == "s1"
    assert scenes[0]["title"] == "Intro"
    assert scenes[0]["tag"] == "HOOK"
    assert scenes[0]["layout"] == "centered"
    assert "scene_plan" in ctx
    assert ctx["scene_plan"]["schema"] == "sceneplan/1"


def test_scene_plan_consumes_explicit_plan():
    explicit = {
        "schema": "sceneplan/1",
        "scenes": [
            {"id": "c1", "title": "Custom 1", "starts_at": 0, "layout": "grid"}
        ]
    }
    spec = {
        "features": {"scene_plan": {"plan": explicit}},
        "script": [{"say": "Hello"}]
    }
    ctx = {}
    scenes = _feat.get("scene_plan", spec)(ctx, spec)
    assert len(scenes) == 1
    assert scenes[0]["id"] == "c1"
    assert scenes[0]["layout"] == "grid"
