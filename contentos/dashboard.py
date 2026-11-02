"""Local-only Creator Studio and legacy dashboard API."""
import json
import hashlib
import mimetypes
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from . import jev, ledger, providers, storage
from .pipeline import STAGES, artifact
from .ui_api import MAX_BODY, dispatch, valid_host
from .ui_state import job_state

ROOT = Path(__file__).resolve().parent.parent


def _job_dirs():
    """Job folders in the external workspace, plus not-yet-migrated projects from the old in-repo location (read-only)."""
    seen = {}
    jobs = storage.jobs_root()
    for p in storage.iter_job_dirs(jobs):
        if p.is_dir():
            seen[p.name] = p
    legacy = storage.REPO / "workspace" / "projects"
    for p in sorted(legacy.glob("*")) if legacy.is_dir() else []:
        if p.is_dir() and p.name not in seen:
            seen[p.name] = p
    return [seen[k] for k in sorted(seen)]


def _job_dir(cid):
    return storage.find_job_dir(cid) or storage.legacy_job_dir(cid) if storage.valid_job_id(cid) else None
SERVE = {"video.mp4": "video/mp4", "qa.json": "application/json", "script.md": "text/markdown",
         "metadata.yaml": "text/plain", "publish-result.json": "application/json",
         "script-lint.json": "application/json", "export-result.json": "application/json"}
_cache = {"t": 0, "providers": None, "jev": None}
UI_ROOT = Path(__file__).parent / "ui"


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
    for d in _job_dirs():
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
        if self.command != "HEAD":
            self.wfile.write(body)

    def _host_ok(self):
        if valid_host(self.headers.get("Host", "")):
            return True
        self._send(421, b"invalid host", "text/plain; charset=utf-8")
        return False

    def _api(self, body=b""):
        response = dispatch(
            self.command,
            self.path,
            dict(self.headers.items()),
            body,
            self.server.ui_token,
        )
        data = json.dumps(response.body).encode("utf-8")
        self._send(response.status, data, "application/json; charset=utf-8", response.headers)

    def _events(self, path):
        match = re.fullmatch(r"/api/v1/jobs/([^/]+)/events", path)
        if not match:
            return False
        content_id = unquote(match.group(1))
        if not storage.valid_job_id(content_id) or job_state(content_id) is None:
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return True
        once = parse_qs(urlsplit(self.path).query).get("once") == ["1"]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close" if once else "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        if once:
            self.close_connection = True
        self.end_headers()
        if self.command == "HEAD":
            return True
        prior = None
        try:
            while True:
                detail = job_state(content_id)
                if detail is None:
                    return True
                signal = {
                    "contentId": content_id,
                    "state": detail["state"],
                    "updated": detail["updated"],
                    "activeRun": detail.get("activeRun", False),
                    "nextAction": (detail.get("nextAction") or {}).get("kind"),
                }
                encoded = json.dumps(signal, sort_keys=True, separators=(",", ":"))
                revision = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
                if revision != prior:
                    signal["revision"] = revision
                    data = json.dumps(signal, separators=(",", ":")).encode("utf-8")
                    self.wfile.write(b"id: " + revision.encode("ascii") + b"\n")
                    self.wfile.write(b"event: progress\n")
                    self.wfile.write(b"data: " + data + b"\n\n")
                    self.wfile.flush()
                    prior = revision
                else:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                if once:
                    return True
                time.sleep(1)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return True

    def _static(self, path):
        relative = "index.html" if path in ("", "/", "/index.html") else unquote(path.lstrip("/"))
        if relative.startswith("ui/"):
            relative = relative[3:]
        candidate = (UI_ROOT / relative).resolve()
        try:
            candidate.relative_to(UI_ROOT.resolve())
        except ValueError:
            return False
        if not candidate.is_file() or candidate.suffix not in (".html", ".css", ".js", ".mjs", ".svg"):
            return False
        data = candidate.read_bytes()
        if candidate.name == "index.html":
            data = data.replace(b"__CONTENTOS_TOKEN__", self.server.ui_token.encode("ascii"))
        ctype = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if candidate.suffix in (".js", ".mjs"):
            ctype = "text/javascript"
        self._send(200, data, f"{ctype}; charset=utf-8",
                   {"Content-Security-Policy": "default-src 'self'; img-src 'self' data:; "
                                               "media-src 'self'; style-src 'self'; script-src 'self'; "
                                               "connect-src 'self'; object-src 'none'; base-uri 'none'; "
                                               "frame-ancestors 'none'",
                    "X-Content-Type-Options": "nosniff"})
        return True

    def _media(self, path):
        match = re.fullmatch(r"/media/([^/]+)/([^/]+)", path)
        if not match:
            return False
        content_id, name = map(unquote, match.groups())
        if not storage.valid_job_id(content_id) or not re.fullmatch(r"[\w.-]+", name):
            return False
        directory = _job_dir(content_id)
        if directory is None:
            return False
        if name in SERVE:
            candidate, ctype = directory / name, SERVE[name]
        elif name.endswith(".png"):
            candidate, ctype = directory / "previews" / name, "image/png"
        else:
            return False
        candidate = candidate.resolve()
        try:
            candidate.relative_to(directory.resolve())
        except ValueError:
            return False
        if not candidate.is_file():
            return False
        size = candidate.stat().st_size
        start, end, status = 0, max(0, size - 1), 200
        range_header = self.headers.get("Range", "")
        if range_header:
            range_match = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header)
            if not range_match:
                self._send(416, b"", ctype, {"Content-Range": f"bytes */{size}"})
                return True
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else size - 1
            if start >= size or end < start:
                self._send(416, b"", ctype, {"Content-Range": f"bytes */{size}"})
                return True
            end, status = min(end, size - 1), 206
        length = 0 if size == 0 else end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if self.command != "HEAD" and length:
            with candidate.open("rb") as stream:
                stream.seek(start)
                remaining = length
                while remaining:
                    chunk = stream.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        return True

    def do_GET(self):
        if not self._host_ok():
            return
        path = urlsplit(self.path).path
        if path == "/api/state":
            return self._send(200, json.dumps(state()).encode(), "application/json")
        if self._events(path):
            return
        if path.startswith("/api/v1/"):
            return self._api()
        if self._media(path) or self._static(path):
            return
        self._send(404, b"not found", "text/plain")

    do_HEAD = do_GET

    def do_POST(self):
        if not self._host_ok():
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._send(400, b"invalid content length", "text/plain")
        if length > MAX_BODY:
            return self._send(413, b"request body too large", "text/plain")
        self._api(self.rfile.read(length))


def make_server(port=4310):
    server = ThreadingHTTPServer(("127.0.0.1", port), H)
    server.ui_token = secrets.token_urlsafe(32)
    return server


def serve(port=4310):
    threading.Thread(target=_health, daemon=True).start()   # warm provider cache
    srv = make_server(port)
    print(f"dashboard: http://127.0.0.1:{port}  (local-only, Ctrl-C to stop)")
    srv.serve_forever()
