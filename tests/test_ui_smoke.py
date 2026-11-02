"""Opt-in local Track A journey. It is skipped unless CONTENTOS_UI_SMOKE=1.

The run uses the production core and stops at the first human gate. It does not grant approvals, export, or publish.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("CONTENTOS_UI_SMOKE") != "1",
    reason="set CONTENTOS_UI_SMOKE=1 to run one local HyperFrames job until the first gate",
)


def test_track_a_smoke_stops_at_the_first_human_gate(tmp_path, monkeypatch):
    from contentos import specs, storage
    from contentos.production import core

    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "publishing"))
    storage.preflight()
    path = specs.save_spec({
        "content_id": "ui-smoke", "title": "Creator Studio smoke", "format": "9:16", "kind": "short",
        "voice": "af_heart", "render": "hyperframes",
        "script": [{"headline": "Local", "say": "This smoke video stays on this machine."}],
    })
    result = core.run_until_blocked_or_done(path)
    assert result.ok is False
    assert result.failure_class == "blocked"
    assert result.stage in {"brief", "script", "voice"}
    assert not any(storage.publish_root().rglob("*.mp4"))
