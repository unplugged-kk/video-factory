"""contentos CLI. Run with: ./contentos <cmd>"""
import argparse
import sys

import yaml

from . import ledger, providers
from .qa import run_qa

ICON = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL", "NOT_INSTALLED": "NOT_INSTALLED", "OPTIONAL": "OPTIONAL"}
FIX = {
    "kokoro_local": f"uv pip install --python {providers.VENV_PY} kokoro-onnx soundfile",
    "chatterbox_mlx": "optional: recreate ~/.voice-clone-venv with mlx-audio and put a reference clip at ~/Desktop/voice-sample.wav",
    "elevenlabs": "optional paid fallback: export ELEVENLABS_API_KEY=... and set allow_paid or --allow-paid",
    "hyperframes_transcribe": "brew install whisper-cpp", "whisper_cpp": "brew install whisper-cpp",
    "hyperframes": "npm ci   (version pinned in package.json; needs Chrome)", "ffmpeg": "brew install ffmpeg   (arm64 build; /usr/local/bin/ffmpeg is x86 and dead without Rosetta)",
    "ollama_local": "brew install ollama && ollama pull qwen3:8b", "contentforge_gateway": "export AI_BASE_URL/AI_API_KEY from ContentForge .env",
    "claude_api": "optional: export ANTHROPIC_API_KEY", "ytdlp": "brew install yt-dlp", "youtube_data_api": "create API key in Google Cloud, export YOUTUBE_API_KEY",
    "youtube_data_api_oauth": "OAuth client JSON -> ~/.contentos/secrets/youtube-oauth.json (publishing stays gated)",
    "jev_contentforge": "export CONTENTFORGE_URL=http://<contentforge-host>:<port>",
    "mpt": "docker compose up -d   (from the video-factory root; Dory must be running)",
}


def cmd_doctor(a):
    cfg = providers.load("providers.yaml")["capabilities"]
    worst = 0
    for cap in cfg:
        cands = providers.candidates(cap, allow_paid=True)
        prim, _ = providers.select(cap)
        print(f"\n[{cap}]  selected: {prim['id'] if prim else 'NONE'}")
        for c in cands:
            paid = c["tier"] == "paid_api"
            if c["healthy"] or (paid and "paid blocked" in c["detail"]):
                st = "PASS" if c["healthy"] else "OPTIONAL"
            else:
                st = "OPTIONAL" if paid else "NOT_INSTALLED"
            print(f"  {st:14} {c['id']:24} {c['tier']:14} {c['detail']}")
            if st == "NOT_INSTALLED":
                print(f"  {'':14} fix: {FIX.get(c['id'], '-')}")
        if not prim:
            worst = 1
    return worst


def cmd_route(a):
    cap = a.capability
    prim, fb = providers.select(cap, a.allow_paid)
    print(f"{cap}: primary={prim['id'] if prim else None} fallback={[f['id'] for f in fb]}")
    return 0 if prim else 1


def cmd_pipeline(a):
    from . import pipeline
    rid, rep = pipeline.run(a.spec, a.allow_paid, a.force, a.only, a.approve_private)
    print(f"run {rid}")
    for st, status, secs in rep:
        print(f"  {st:9} {status}  ({secs:.1f}s)")
    return 0 if all(s.startswith(("OK", "SKIP")) for _, s, _ in rep) else 1


def cmd_qa(a):
    res = run_qa(a.video, a.format)
    for c, s, d in res:
        print(f"  {s:5} {c:18} {d}")
    return 1 if any(s == "FAIL" for _, s, _ in res) else 0


def cmd_approve(a):
    ledger.approve(a.content_id, a.gate, note=a.note)
    print(f"approved {a.gate} for {a.content_id}")


def cmd_status(a):
    for r in ledger.recent():
        print("  ".join(str(x) for x in r))


def cmd_jev(a):
    import json
    from . import jev
    if a.action == "status":
        print(json.dumps(jev.status(), indent=2))
    else:
        for r in jev.triage([{"title": x} for x in a.topics]):
            print(f"  {r['decision']:7} {str(r['score']):6} {r['source']:14} {r['title']}")


def cmd_learn(a):
    import json
    from . import learn
    fn = {"providers": learn.provider_stats, "cost": learn.cost_report, "calibration": learn.calibration,
          "platforms": learn.platform_report, "packaging": learn.packaging_report}[a.loop]
    print(json.dumps(fn(), indent=2))


def cmd_recommend(a):
    import json
    from . import learn
    print(json.dumps(learn.recommend(a.content_id, a.jev), indent=2))


def cmd_dashboard(a):
    from . import dashboard
    dashboard.serve(a.port)


def cmd_research(a):
    from . import research
    path, d = research.run(a.topic, a.days, a.deep)
    print(f"{path}  sources={d['source_status']}")
    for i in d["items"]:
        print(f"  [{i['source']}] {i['title'][:80]}  {i['engagement']}")


def cmd_competitor(a):
    from . import competitor
    for r in competitor.run(a.urls):
        if "error" in r:
            print(f"  ERROR {r['url']}: {r['error']}"); continue
        print(f"  {r['title'][:60]}\n    {r['channel']} | {r['views']:,} views | like rate {r['like_rate']} | {r['duration_s']}s | title formula: {r['title_formula']}\n    opening {r['opening_score']}/100 {r['opening_band']} (weakest: {r['opening_weakest']}): {r['opening'][:110]}")


def cmd_queue(a):
    from . import queue
    if a.action == "add":
        ids = queue.add(a.args, a.approve_private, a.priority)
        print(f"queued jobs: {ids}")
    elif a.action == "list":
        for r in queue.listing():
            print("  ", *r)
    elif a.action == "requeue":
        queue.requeue(int(a.args[0]))


def cmd_worker(a):
    from . import queue
    queue.work(a.concurrency, a.once)


def cmd_factory_worker(a):
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    script = root / "contentos/adapters/v1/factory_worker.mjs"
    cmd = ["node", str(script)]
    if a.once:
        cmd.append("--once")
    if a.port != 4300:
        cmd.extend(["--port", str(a.port)])
    return subprocess.call(cmd, cwd=str(root))


def main():
    p = argparse.ArgumentParser(prog="contentos")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("doctor").set_defaults(f=cmd_doctor)
    sp.add_parser("status").set_defaults(f=cmd_status)
    r = sp.add_parser("route"); r.add_argument("capability"); r.add_argument("--allow-paid", action="store_true"); r.set_defaults(f=cmd_route)
    pl = sp.add_parser("pipeline"); pl.add_argument("action", choices=["run"]); pl.add_argument("spec")
    pl.add_argument("--allow-paid", action="store_true"); pl.add_argument("--force", action="store_true")
    pl.add_argument("--only"); pl.add_argument("--approve-private", action="store_true", help="grant research/script/production gates (never publish)")
    pl.set_defaults(f=cmd_pipeline)
    q = sp.add_parser("qa"); q.add_argument("video"); q.add_argument("--format", default="9:16"); q.set_defaults(f=cmd_qa)
    ap = sp.add_parser("approve"); ap.add_argument("content_id"); ap.add_argument("gate"); ap.add_argument("--note", default=""); ap.set_defaults(f=cmd_approve)
    j = sp.add_parser("jev"); j.add_argument("action", choices=["status", "triage"]); j.add_argument("topics", nargs="*"); j.set_defaults(f=cmd_jev)
    l = sp.add_parser("learn"); l.add_argument("loop", choices=["providers", "cost", "calibration", "platforms", "packaging"]); l.set_defaults(f=cmd_learn)
    rc = sp.add_parser("recommend"); rc.add_argument("content_id"); rc.add_argument("--jev", action="store_true"); rc.set_defaults(f=cmd_recommend)
    d = sp.add_parser("dashboard"); d.add_argument("--port", type=int, default=4310); d.set_defaults(f=cmd_dashboard)
    rs = sp.add_parser("research"); rs.add_argument("topic"); rs.add_argument("--days", type=int, default=30); rs.add_argument("--deep", action="store_true"); rs.set_defaults(f=cmd_research)
    cp = sp.add_parser("competitor"); cp.add_argument("urls", nargs="+"); cp.set_defaults(f=cmd_competitor)
    q = sp.add_parser("queue"); q.add_argument("action", choices=["add", "list", "requeue"]); q.add_argument("args", nargs="*")
    q.add_argument("--approve-private", action="store_true"); q.add_argument("--priority", type=int, default=0); q.set_defaults(f=cmd_queue)
    w = sp.add_parser("worker"); w.add_argument("--concurrency", type=int, default=2); w.add_argument("--once", action="store_true", help="drain the queue then exit"); w.set_defaults(f=cmd_worker)
    fw = sp.add_parser("factory-worker", help="ContentForge v1 queue worker (VIDEO_FACTORY_ROOT)")
    fw.add_argument("--once", action="store_true", help="process available jobs then exit")
    fw.add_argument("--port", type=int, default=4300, help="manifest.json HTTP port for processingReady")
    fw.set_defaults(f=cmd_factory_worker)
    a = p.parse_args()
    sys.exit(a.f(a) or 0)
