"""Unit tests for Lane M2-D: audio_bed."""
import subprocess
import tempfile
from pathlib import Path
import pytest
from contentos.features import registry as _feat
from contentos.features import audio_bed


def test_audio_bed_registers():
    assert "audio_bed" in _feat._REGISTRY


def test_audio_bed_passthrough_when_off():
    fake_path = Path("/tmp/fake_video.mp4")
    assert _feat.get("audio_bed", {})(None, fake_path, {}) == fake_path


def test_ambient_pad_synthesis():
    with tempfile.TemporaryDirectory() as td:
        out_wav = Path(td) / "test_pad.wav"
        audio_bed._generate_ambient_pad(2.0, out_wav)
        assert out_wav.exists()
        assert out_wav.stat().st_size > 1000


def test_audio_bed_remux_e2e():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        # Create a 2s synthetic test mp4 with silence audio
        test_mp4 = d / "video.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=640x360:r=30:d=2",
            "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", "2",
            "-c:v", "libx264", "-c:a", "aac",
            str(test_mp4)
        ]
        p = subprocess.run(cmd, capture_output=True)
        assert p.returncode == 0
        assert test_mp4.exists()

        spec = {"features": {"audio_bed": True}}
        ctx = {"dir": d, "spec": spec}

        out = _feat.get("audio_bed", spec)(ctx, test_mp4, spec)
        assert out == test_mp4
        assert test_mp4.exists()
        # Intermediates should exist
        assert (d / "audio" / "ambient_bed.wav").exists()
