"""How to invoke the pinned HyperFrames CLI.

Jobs live outside the repository (see storage.py), so `npx --no-install hyperframes` run with a job folder as its
working directory cannot see the repo's node_modules and tries to fetch a different version from the network. The
repo's own binary is called by absolute path instead, which also keeps every stage on the pinned version.
Override with HYPERFRAMES_BIN (a path to a hyperframes executable)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def binary():
    """The hyperframes executable to run, as a one-element list, or the npx fallback if the repo has none installed."""
    env = os.environ.get("HYPERFRAMES_BIN", "").strip()
    if env:
        return [env]
    local = ROOT / "node_modules" / ".bin" / "hyperframes"
    if local.exists():
        return [str(local)]
    return ["npx", "--no-install", "hyperframes"]


def command(*args):
    return [*binary(), *map(str, args)]
