"""Read-only local dashboard. `./contentos.sh dashboard` -> http://127.0.0.1:4310
Serves one HTML page + JSON from the ledger and workspace. Binds to localhost only; serves only
whitelisted artifact names inside workspace/projects/<id>/ (no path traversal)."""
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import jev, ledger, providers
from .pipeline import STAGES, artifact

ROOT = Path(__file__).resolve().parent.parent
PROJ = ROOT / "workspace/projects"
SERVE = {"video.mp4": "video/mp4", "qa.json": "application/json", "script.md": "text/markdown",
         "metadata.yaml": "text/plain", "publish-result.json": "application/json", "script-lint.json": "application/json"}
_cache = {"t": 0, "providers": None, "jev": None}


def _health():
    """Provider probes shell out (npx etc.), so cache for 60 s."""
    if time.time() - _cache["t"] > 60:
        caps = {}
        for cap in providers.load("providers.yaml")["capabilities"]:
            prim, _ = providers.select(cap)
            caps[cap] = {"selected": prim["id"] if prim else None,
                         "candidates": [{"id": c["id"], "tier": c["tier"], "healthy": c["healthy"]} for c in providers.candidates(cap)]}
        _cache.update(t=time.time(), providers=caps, jev=jev.status())
    return _cache["providers"], _cache["jev"]


def state():
    c = ledger.db()
    runs = c.execute("SELECT rowid, run_id, content_id, stage, provider, status, start, end, error FROM runs ORDER BY rowid").fetchall()
    contents = {}
    for rid, run_id, cid, stage, prov, status, t0, t1, err in runs:
        s = contents.setdefault(cid, {}).setdefault(stage, {})
        s.update(provider=prov if prov != "-" else s.get("provider", "-"), status=status, secs=round(t1 - t0, 1), error=err, ts=t1, run_id=run_id)
        if status == "RUNNING" and time.time() - t0 > 600:
            s["status"] = "STALE"
    appr = {}
    for cid, gate, by, at in c.execute("SELECT content_id, gate, by, at FROM approvals"):
        appr.setdefault(cid, {})[gate] = {"by": by, "at": at}
    decs = c.execute("SELECT type, subject, decision, source, reasons, ts FROM decisions ORDER BY ts DESC LIMIT 25").fetchall()
    out = []
    for d in sorted(p for p in PROJ.glob("*") if p.is_dir()) if PROJ.exists() else []:
        cid, sts = d.name, contents.get(d.name, {})
        meta = json.loads((d / "content.json").read_text()) if (d / "content.json").exists() else {}
        stages = []
        for st in STAGES:
            row = sts.get(st)
            art = d / artifact(st, meta).replace("%02d", "01")
            status = row["status"] if row else ("DONE" if art.exists() else "PENDING")
            stages.append({"stage": st, "status": status, "provider": (row or {}).get("provider", ""), "secs": (row or {}).get("secs"),
                           "error": (row or {}).get("error", "")})
        qa = json.loads((d / "qa.json").read_text()) if (d / "qa.json").exists() else []
        rec = next((x for x in decs if x[0] == "publish_recommendation" and x[1] == cid), None)
        out.append({"id": cid, "title": meta.get("title", cid), "stages": stages, "qa": qa, "approvals": appr.get(cid, {}),
                    "has_video": (d / "video.mp4").exists(), "recommendation": {"decision": rec[2], "reasons": json.loads(rec[4])} if rec else None,
                    "updated": max([v["ts"] for v in sts.values()], default=0)})
    out.sort(key=lambda x: -x["updated"])
    jobs = [{"id": i, "content_id": cid, "status": st, "secs": secs, "error": err} for i, cid, st, _, secs, err in __import__("contentos.queue", fromlist=["x"]).listing()]
    pub = providers.load("youtube.yaml")["publish"]
    provs, jv = _health()
    return {"now": time.time(), "contents": out, "providers": provs, "jev": jv, "publish_enabled": pub["enabled"], "jobs": jobs,
            "decisions": [{"type": t, "subject": s, "decision": d, "source": src, "reasons": json.loads(r), "ts": ts} for t, s, d, src, r, ts in decs]}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, (Path(__file__).parent / "dashboard.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/state":
            return self._send(200, json.dumps(state()).encode(), "application/json")
        m = re.fullmatch(r"/media/([\w.-]+)/([\w.-]+)", self.path)
        if m and m.group(2) in SERVE and "/" not in m.group(1) and m.group(1) not in (".", ".."):
            f = PROJ / m.group(1) / m.group(2)
            if f.is_file():
                data, ctype = f.read_bytes(), SERVE[m.group(2)]
                rng = re.match(r"bytes=(\d+)-(\d*)", self.headers.get("Range", ""))
                if rng:
                    a = int(rng.group(1)); b = int(rng.group(2)) if rng.group(2) else len(data) - 1
                    return self._send(206, data[a:b + 1], ctype, {"Content-Range": f"bytes {a}-{b}/{len(data)}", "Accept-Ranges": "bytes"})
                return self._send(200, data, ctype, {"Accept-Ranges": "bytes"})
        self._send(404, b"not found", "text/plain")


def serve(port=4310):
    threading.Thread(target=_health, daemon=True).start()   # warm provider cache
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"dashboard: http://127.0.0.1:{port}  (read-only, Ctrl-C to stop)")
    srv.serve_forever()
