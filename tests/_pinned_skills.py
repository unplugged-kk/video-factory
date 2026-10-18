"""Skip marker for tests that need the gitignored, hash-pinned upstream skills (never installs them)."""
import subprocess
import sys
from pathlib import Path

import pytest

_verify = subprocess.run(
    [sys.executable, str(Path(__file__).resolve().parent.parent / "scripts/upstream_skills.py"), "verify"],
    capture_output=True, text=True,
)

needs_pinned_skills = pytest.mark.skipif(
    _verify.returncode != 0,
    reason="pinned upstream skills not installed (`python scripts/upstream_skills.py verify` failed: "
    + " | ".join(_verify.stdout.splitlines()[:3]) + "); run `python scripts/upstream_skills.py sync` to enable",
)


def _hf_installed():
    from contentos import hf
    return hf.binary()[0] != "npx"


needs_hyperframes_bin = pytest.mark.skipif(
    not _hf_installed(),
    reason="repo-local hyperframes binary missing (node_modules/.bin/hyperframes); run `npm ci` to enable",
)


def _remotion_installed():
    from contentos.renderers import remotion
    return remotion.REMOTION_BIN.exists()


needs_remotion = pytest.mark.skipif(
    not _remotion_installed(),
    reason="Remotion toolchain missing (~/.contentos/remotion/node_modules/.bin/remotion); see docs for the Remotion lane setup",
)


def _local_tts_healthy():
    from contentos import providers
    return any(c["healthy"] and c["tier"] not in ("paid_api", "low_cost_api") for c in providers.candidates("tts"))


needs_local_tts = pytest.mark.skipif(
    not _local_tts_healthy(),
    reason="no healthy local TTS provider (e.g. `kokoro_onnx` python module); the test needs a local and a paid provider both healthy",
)
