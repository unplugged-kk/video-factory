"""Tests for the multi-renderer architecture and rendering provider registry."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from contentos.renderers import RenderProvider, get_renderer, list_renderers, register
from contentos.renderers.base import RenderProvider as BaseRenderProvider
from contentos.renderers.hyperframes import HyperFramesRenderer
from contentos.renderers.mpt import MPTRenderer
from contentos.renderers.remotion import RemotionRenderer


def test_registry_contains_all_three_renderers():
    renderers = list_renderers()
    ids = {r["id"] for r in renderers}
    assert "hyperframes" in ids
    assert "remotion" in ids
    assert "mpt" in ids


def test_default_renderer_is_hyperframes():
    r1 = get_renderer()
    assert isinstance(r1, HyperFramesRenderer)
    assert r1.id == "hyperframes"

    r2 = get_renderer({})
    assert isinstance(r2, HyperFramesRenderer)

    r3 = get_renderer({"render": "hyperframes"})
    assert isinstance(r3, HyperFramesRenderer)


def test_get_renderer_by_spec_render_key():
    r_remotion = get_renderer({"render": "remotion"})
    assert isinstance(r_remotion, RemotionRenderer)
    assert r_remotion.id == "remotion"

    r_mpt = get_renderer({"render": "mpt"})
    assert isinstance(r_mpt, MPTRenderer)
    assert r_mpt.id == "mpt"


def test_get_renderer_unknown_raises_keyerror():
    with pytest.raises(KeyError, match="not registered"):
        get_renderer("non_existent_engine")


def test_remotion_capabilities():
    r = get_renderer("remotion")
    caps = r.capabilities()
    assert caps["engine"] == "remotion"
    assert "9:16" in caps["formats"]
    assert "spring_physics" in caps["features"]
    assert "word_level_captions" in caps["features"]
    assert caps["default"] is False


def test_hyperframes_capabilities():
    r = get_renderer("hyperframes")
    caps = r.capabilities()
    assert caps["engine"] == "hyperframes"
    assert caps["default"] is True


def test_remotion_validation():
    r = get_renderer("remotion")
    errors = r.validate({})
    assert len(errors) == 1
    assert "missing required 'script'" in errors[0].lower()

    valid = r.validate({"script": [{"say": "hello", "headline": "hi"}]})
    assert len(valid) == 0


def test_remotion_compose_generates_valid_project():
    r = get_renderer("remotion")
    spec = {
        "title": "Remotion Test Video",
        "script": [
            {"say": "Welcome to multi-renderer video synthesis", "headline": "Multi-Renderer", "tag": "01/TEST"},
            {"say": "Powered by Remotion and React", "headline": "React Motion", "tag": "02/TEST"},
        ],
    }

    with tempfile.TemporaryDirectory() as td:
        job_dir = Path(td) / "job"
        audio_dir = job_dir / "audio"
        audio_dir.mkdir(parents=True)

        # Create dummy voice wavs
        import wave
        for i in (1, 2):
            wav_path = audio_dir / f"{i:02d}.wav"
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(b"\x00" * 48000)  # 1 sec silence

        ctx = {
            "id": "remotion-test-001",
            "dir": job_dir,
            "spec": spec,
            "res": (1080, 1920),
        }

        provider_id, artifacts = r.compose(ctx)
        assert provider_id == "remotion"
        assert len(artifacts) >= 2

        proj = job_dir / "project_remotion"
        assert (proj / "src" / "Root.tsx").exists()
        assert (proj / "src" / "Video.tsx").exists()
        assert (proj / "src" / "scenes.json").exists()

        scenes = json.loads((proj / "src" / "scenes.json").read_text())
        assert len(scenes) == 2
        assert scenes[0]["headline"] == "Multi-Renderer"
        assert scenes[1]["headline"] == "React Motion"
        assert scenes[0]["duration_frames"] > 0

        video_tsx = (proj / "src" / "Video.tsx").read_text()
        assert "paddingBottom: 460" in video_tsx  # Safezone bottom padding
        assert "paddingRight: 190" in video_tsx   # Safezone side padding
