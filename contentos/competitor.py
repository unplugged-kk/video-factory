"""Competitor teardown for public videos: agent-reach (yt-dlp) metadata+transcript -> measured hook/title scores.
Measures only what is visible (words, counts). Never claims why a video worked. Saves workspace/research/competitors.json."""
import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

from . import providers

ROOT = Path(__file__).resolve().parent.parent
AR = os.path.expanduser("~/.local/bin/agent-reach")
ENV = {**os.environ, "PATH": f"/opt/homebrew/bin:{os.path.expanduser('~/.local/bin')}:{os.environ['PATH']}"}
OPEN_WORDS = 35   # ~15 s of speech at 150 wpm; transcripts here carry no timestamps


def _skill(skill, script):
    for base in (ROOT / "vendor/youtube-agent-skill/skills", Path("~/.claude/skills").expanduser()):
        if (base / skill / script).exists():
            return base / skill / script
    raise RuntimeError(f"{skill}/{script} not installed")


def _get(cmd, url, extra=()):
    r = subprocess.run([AR, "get", f"youtube.{cmd}", url, "--json", *extra], capture_output=True, text=True, env=ENV, timeout=180)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[-200:])
    return json.loads(r.stdout)["items"][0]


def analyze(url):
    info, tr = _get("info", url), _get("transcript", url, ["--max-tokens", "600"])
    words = tr["text"].replace("\n", " ").split()
    opening = " ".join(words[:OPEN_WORDS])
    hs = json.loads(subprocess.run(["python3", str(_skill("yt-script", "hookscore.py")), "--hook", opening, "--json"], capture_output=True, text=True).stdout)[0]
    spec = importlib.util.spec_from_file_location("swipe", _skill("yt-viral", "swipe.py"))
    sw = importlib.util.module_from_spec(spec); spec.loader.exec_module(sw)
    e = info.get("engagement", {})
    return {"url": url, "title": info["title"], "channel": info["author"], "published": info["published_at"],
            "views": e.get("views"), "likes": e.get("likes"), "duration_s": e.get("duration_s"),
            "like_rate": round(e["likes"] / e["views"], 4) if e.get("views") and e.get("likes") else None,
            "title_formula": sw.classify(info["title"]), "opening": opening, "opening_score": hs["verdict"], "opening_band": hs["band"],
            "opening_weakest": min(hs["properties"], key=hs["properties"].get)}


def run(urls):
    out = ROOT / "workspace/research"; out.mkdir(parents=True, exist_ok=True)
    rows = []
    for u in urls:
        try:
            rows.append(analyze(u))
        except Exception as ex:
            rows.append({"url": u, "error": str(ex)})
    (out / "competitors.json").write_text(json.dumps({"fetched_at": time.time(), "videos": rows,
        "caveat": "views are not normalised by channel size; use yt-viral swipe.py with >=4 videos/channel for outlier ranking"}, indent=2))
    return rows
