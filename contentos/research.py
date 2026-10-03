"""Research stage: wraps the last30days skill (MIT, mvanhorn). Output is a dossier with source+timestamp+engagement
per item. Evidence only: no claim is asserted here. Writes workspace/research/<slug>/dossier.json."""
import json
import os
import re
import subprocess
import time
from pathlib import Path

from . import providers

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = Path("~/.agents/skills/last30days/scripts/last30days.py").expanduser()


def run(topic, days=30, deep=False):
    if not SCRIPT.exists():
        raise RuntimeError("last30days skill not installed at ~/.agents/skills/last30days")
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:60]
    out = ROOT / "workspace/research" / slug
    out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PATH": "/opt/homebrew/bin:" + os.environ["PATH"]}
    cmd = [str(providers.VENV_PY), str(SCRIPT), topic, "--emit", "json", "--no-browser-cookies", "--days", str(days),
           "--save-dir", str(out), "--deep" if deep else "--quick"]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[-300:])
    raw = json.loads(r.stdout)
    items = [{"source": x.get("source"), "title": x.get("title"), "url": x.get("url"), "engagement": x.get("engagement"),
              "relevance_checked": False} for x in raw.get("results", [])]
    dossier = {"topic": topic, "window_days": days, "fetched_at": time.time(), "source_status": raw.get("source_status"),
               "items": items, "caveat": "keyword retrieval; items may be off-topic. Human or Jev triage before use."}
    (out / "dossier.json").write_text(json.dumps(dossier, indent=2))
    return out / "dossier.json", dossier
