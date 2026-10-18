"""F0 golden-output and hook-registry tests.

Golden test: with all features off, s_compose for the M1 baseline spec produces
a project/index.html whose SHA-256 matches the M1 baseline artifact exactly.
If the file is not deterministic (e.g. timestamps leak in), the test normalises
those fields and says so in a comment; this file documents exactly what was normalised.

Important: these tests do NOT render video. They only test the compose stage
(HTML generation) and the registry API.

NOTE: this module MUST NOT call contentos.pipeline.run() or touch the real ledger.
It calls s_compose directly with a synthetic ctx.
"""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from contentos.features import registry as _feat
from contentos.pipeline import s_compose, words_for, dur


FIXTURES = Path(__file__).parent / "fixtures" / "baseline"

BASELINE_YAML = FIXTURES / "m1-baseline-001.yaml"

GOLDEN_SHA256 = "b0ac447378bb5cef7a77d97fde7a59c83b5fc96e6cb0cdb983670434dc9e3cd2"

# The actual golden file for comparison (read-only M1 artifact)
GOLDEN_FILE = FIXTURES / "golden-index.html"


def _make_ctx(spec, tmp_dir: Path, audio_src: Path):
    """Build a minimal ctx for s_compose using pre-existing M1 audio."""
    job_dir = tmp_dir / "job"
    proj_dir = job_dir / "project"
    audio_dst = job_dir / "audio"
    audio_dst.mkdir(parents=True)
    proj_dir.mkdir(parents=True)
    # Copy M1 audio so we don't need TTS
    for wav in sorted(audio_src.glob("*.wav")):
        shutil.copy(wav, audio_dst / wav.name)
    # Also copy word-timing dirs if they exist
    for txdir in audio_src.glob("tx*"):
        if txdir.is_dir():
            shutil.copytree(txdir, audio_dst / txdir.name, dirs_exist_ok=True)
    W, H = 1080, 1920
    return {
        "id": "m1-baseline-001",
        "dir": job_dir,
        "spec": spec,
        "allow_paid": False,
        "res": (W, H),
        "force": False,
    }


M1_AUDIO = FIXTURES / "audio"


@pytest.mark.skipif(
    not BASELINE_YAML.exists() or not M1_AUDIO.exists() or not GOLDEN_FILE.exists(),
    reason="vendored M1 baseline fixtures missing under tests/fixtures/baseline",
)
def test_compose_golden_features_off():
    """With all features off, s_compose must produce an index.html byte-identical to the M1 artifact.

    Normalisation applied: NONE. If this test fails with a sha256 mismatch, check whether
    a timestamp or run-id leaked into the HTML and add a targeted normalisation here,
    documenting exactly what field was removed.
    """
    spec = yaml.safe_load(BASELINE_YAML.read_text())
    # Ensure features key is absent (baseline spec does not have it)
    assert "features" not in spec, "baseline spec must not have a features key"

    with tempfile.TemporaryDirectory() as td:
        ctx = _make_ctx(spec, Path(td), M1_AUDIO)
        s_compose(ctx)
        produced = (ctx["dir"] / "project" / "index.html").read_bytes()
        produced_sha = hashlib.sha256(produced).hexdigest()

        golden = GOLDEN_FILE.read_bytes()
        golden_sha = hashlib.sha256(golden).hexdigest()

        assert golden_sha == GOLDEN_SHA256, (
            f"Golden file sha256 mismatch: expected {GOLDEN_SHA256}, got {golden_sha}. "
            "The M1 artifact may have been modified."
        )
        assert produced_sha == GOLDEN_SHA256, (
            f"Produced index.html sha256 {produced_sha} != golden {GOLDEN_SHA256}. "
            "Either a hook changed compose output, or a timestamp/id leaked in. "
            "Investigate and add a targeted normalisation if the leak is benign."
        )


def test_registry_passthrough_when_features_absent():
    """All six hooks return pass-throughs when features key is absent."""
    spec = {"title": "t", "script": []}
    assert _feat.get("style_card", spec)(None, spec) is None
    assert _feat.get("scene_plan", spec)(None, spec) == []
    assert _feat.get("visual_layer", spec)(None, 1, "<div/>", [], spec) == ("<div/>", [])
    assert _feat.get("audio_bed", spec)(None, Path("/tmp/x.mp4"), spec) == Path("/tmp/x.mp4")
    assert _feat.get("captions_hook", spec)(None, spec) == {}
    assert _feat.get("qa_extra", spec)(None, Path("/tmp/x.mp4"), spec) == []


def test_registry_passthrough_when_features_empty():
    """All six hooks return pass-throughs when features dict is present but empty."""
    spec = {"title": "t", "script": [], "features": {}}
    assert _feat.get("style_card", spec)(None, spec) is None
    assert _feat.get("scene_plan", spec)(None, spec) == []


def test_registry_passthrough_when_feature_falsy():
    """A feature set to False/None is treated as off."""
    spec = {"title": "t", "script": [], "features": {"style_card": False}}
    assert _feat.get("style_card", spec)(None, spec) is None


def test_registry_keyerror_when_enabled_but_not_registered():
    """An enabled but unregistered feature raises KeyError (fail loud)."""
    spec = {"title": "t", "script": [], "features": {"style_card": True}}
    # Ensure style_card is not registered (it shouldn't be in F0)
    _feat._REGISTRY.pop("style_card", None)
    with pytest.raises(KeyError, match="style_card"):
        _feat.get("style_card", spec)


def test_register_and_get():
    """register() wires a handler; get() returns it when feature is on."""
    sentinel = object()
    def _my_handler(ctx, spec): return sentinel
    _feat.register("_test_only", _my_handler)
    spec = {"features": {"_test_only": True}}
    # Add a pass-through for the test feature name
    _feat._PASS_THROUGH["_test_only"] = lambda ctx, sp: None
    result = _feat.get("_test_only", spec)(None, spec)
    assert result is sentinel
    # Clean up
    _feat._REGISTRY.pop("_test_only", None)
    _feat._PASS_THROUGH.pop("_test_only", None)
