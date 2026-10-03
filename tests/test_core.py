import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import providers  # noqa: E402

ROOT = providers.ROOT


def test_paid_never_default():
    prim, _ = providers.select("tts")
    assert prim is None or prim["tier"] != "paid_api"


def test_paid_blocked_unless_allowed(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    ids = [c["id"] for c in providers.candidates("tts") if c["healthy"]]
    assert "elevenlabs" not in ids
    assert "elevenlabs" in [c["id"] for c in providers.candidates("tts", allow_paid=True) if c["healthy"]]


def test_local_beats_paid_even_when_both_healthy(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    c = providers.candidates("tts", allow_paid=True)
    assert c[0]["tier"] != "paid_api"


def test_registry_providers_exist():
    reg = yaml.safe_load((ROOT / "registry/capabilities.yaml").read_text())["capabilities"]
    known = {p for cap in providers.load("providers.yaml")["capabilities"].values() for p in cap}
    for name, c in reg.items():
        for p in c.get("provider", []):
            assert p in known or p in {"llm", "youtube-niche-finder"}, f"{name}: unknown provider {p}"


def test_publish_disabled_by_default():
    cfg = providers.load("youtube.yaml")["publish"]
    assert cfg["enabled"] is False and cfg["default_privacy"] == "private" and cfg["allow_public"] is False
