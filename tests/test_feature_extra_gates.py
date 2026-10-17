"""Unit tests for Lane M2-F: extra_gates."""
import subprocess
import tempfile
from pathlib import Path
import pytest
from contentos.features import registry as _feat
from contentos.features import extra_gates


def test_extra_gates_registers():
    assert "extra_gates" in _feat._REGISTRY


def test_extra_gates_passthrough_when_off():
    fake_path = Path("/tmp/fake_video.mp4")
    assert _feat.get("qa_extra", {})(None, fake_path, {}) == []


def test_extra_gates_synthetic_clip():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        # Create a 2s synthetic test mp4 with audio
        test_mp4 = d / "video.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:r=30:d=2",
            "-f", "lavfi", "-i", "sine=f=440:r=24000:d=2",
            "-t", "2",
            "-c:v", "libx264", "-c:a", "aac",
            str(test_mp4)
        ]
        p = subprocess.run(cmd, capture_output=True)
        assert p.returncode == 0

        spec = {"features": {"qa_extra": True}}
        ctx = {"dir": d, "spec": spec}

        results = _feat.get("qa_extra", spec)(ctx, test_mp4, spec)
        assert len(results) == 3
        checks = [r[0] for r in results]
        assert "extra_silence_gaps" in checks
        assert "extra_end_hold" in checks
        assert "extra_blank_field" in checks

        # Continuous sine tone should have no silence gaps
        silence_check = next(r for r in results if r[0] == "extra_silence_gaps")
        assert silence_check[1] == "PASS"
