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
