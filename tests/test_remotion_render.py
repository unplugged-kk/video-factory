"""End-to-end integration test for Remotion rendering provider."""
from __future__ import annotations

import tempfile
import wave
from pathlib import Path

import pytest

from contentos.renderers import get_renderer


def test_remotion_render_e2e():
    r = get_renderer("remotion")
    spec = {
        "title": "Remotion Autonomous E2E",
        "script": [
            {"say": "Autonomous validation with Remotion", "headline": "Remotion Provider", "tag": "01/INTEGRATION"},
        ],
    }

    with tempfile.TemporaryDirectory() as td:
        job_dir = Path(td) / "job"
        audio_dir = job_dir / "audio"
        audio_dir.mkdir(parents=True)

        # 1-second sine wave voice
        wav_path = audio_dir / "01.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(b"\x00" * 48000)

        ctx = {
            "id": "remotion-e2e-001",
            "dir": job_dir,
            "spec": spec,
            "res": (1080, 1920),
        }

        # 1. Compose
        prov_id, artifacts = r.compose(ctx)
        assert prov_id == "remotion"
        assert len(artifacts) >= 2

        # 2. Render
        render_id, out_artifacts = r.render(ctx)
        assert render_id == "remotion"
        assert len(out_artifacts) == 1

        mp4 = out_artifacts[0]
        assert mp4.exists()
        assert mp4.stat().st_size > 1000

        # 3. Inspect
        meta = r.inspect(mp4)
        assert meta["streams"][0]["codec_name"] == "h264"
        assert meta["streams"][0]["width"] == 1080
        assert meta["streams"][0]["height"] == 1920
