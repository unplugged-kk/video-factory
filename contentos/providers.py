"""Provider selection: local-first policy + live health probes."""
import importlib.util
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VENV_PY = Path(os.environ.get("HYPERFRAMES_PYTHON", "~/.contentos/venv/bin/python")).expanduser()


def load(name):
    return yaml.safe_load((ROOT / "config" / name).read_text())


def probe(spec):
    """Return (ok, detail). Never raises."""
    try:
        if "env" in spec:
            return bool(os.environ.get(spec["env"])), f"env {spec['env']}"
        if "path" in spec:
            p = Path(spec["path"]).expanduser()
            return p.exists(), str(p)
        if "py_import" in spec:
            r = subprocess.run([str(VENV_PY), "-c", f"import {spec['py_import']}"], capture_output=True, timeout=30)
            return r.returncode == 0, f"{VENV_PY.name} import {spec['py_import']}"
        if "cmd" in spec:
            if not shutil.which(spec["cmd"][0]):
                return False, f"{spec['cmd'][0]} not on PATH"
            r = subprocess.run(spec["cmd"], capture_output=True, timeout=60)
            return r.returncode == 0, " ".join(spec["cmd"])
        if "http" in spec:
            urllib.request.urlopen(spec["http"], timeout=5).close()  # non-2xx raises
            return True, spec["http"]
        if "always" in spec:
            return True, "always"
        return False, f"unknown probe {sorted(spec)}"  # a typo'd key must not read as healthy
    except Exception as e:  # bad CPU type, timeout, ...
        return False, f"{type(e).__name__}: {e}"


def candidates(capability, allow_paid=False):
    """Healthy providers for a capability, ordered by tier rank then quality (desc)."""
    pol, prov = load("local-first-policy.yaml"), load("providers.yaml")
    allow_paid = allow_paid or pol.get("allow_paid", False)
    out = []
    for pid, spec in prov["capabilities"][capability].items():
        rank = pol["tier_rank"][spec["tier"]]
        ok, detail = probe(spec["probe"])
        paid_blocked = spec["tier"] in ("paid_api", "low_cost_api") and not allow_paid
        out.append({"id": pid, "tier": spec["tier"], "rank": rank, "quality": spec["quality"],
                    "healthy": ok and not paid_blocked, "detail": detail + (" (paid blocked by policy)" if ok and paid_blocked else "")})
    out.sort(key=lambda c: (not c["healthy"], c["rank"], -c["quality"]))
    return out


def select(capability, allow_paid=False):
    """-> (primary, fallbacks). primary is None when nothing healthy."""
    c = candidates(capability, allow_paid)
    healthy = [x for x in c if x["healthy"]]
    return (healthy[0] if healthy else None), healthy[1:]
