"""Unit tests for Lane M2-A: style_card and creative decision record."""
import json
import tempfile
from pathlib import Path
import pytest

from contentos.features import registry as _feat
from contentos.features import style_card


def test_style_card_registers():
    assert "style_card" in _feat._REGISTRY


def test_style_card_execution_default():
    with tempfile.TemporaryDirectory() as td:
        job_dir = Path(td)
        spec = {
            "content_id": "test-style-job",
            "title": "Agent Tool Use",
            "content_type": "ai-workflow",
            "features": {"style_card": True},
        }
        ctx = {"id": "test-style-job", "dir": job_dir, "spec": spec}
        
        handler = _feat.get("style_card", spec)
        handler(ctx, spec)
        
        assert "style_card" in ctx
        assert "creative_decision" in ctx
        assert ctx["style_card"]["id"] in ("blueprint-diagram", "punch-split", "slow-parallax-story")
        
        rec_path = job_dir / "creative-decision.json"
        assert rec_path.exists()
        rec_data = json.loads(rec_path.read_text(encoding="utf-8"))
        assert rec_data["job"] == "test-style-job"
        assert rec_data["chosen"] == ctx["style_card"]["id"]


def test_style_card_override():
    with tempfile.TemporaryDirectory() as td:
        job_dir = Path(td)
        spec = {
            "content_id": "test-style-override",
            "title": "Custom Architecture",
            "features": {"style_card": {"chosen": "punch-split"}},
        }
        ctx = {"id": "test-style-override", "dir": job_dir, "spec": spec}
        
        handler = _feat.get("style_card", spec)
        handler(ctx, spec)
        
        assert ctx["style_card"]["id"] == "punch-split"
        assert ctx["creative_decision"]["chosen"] == "punch-split"
