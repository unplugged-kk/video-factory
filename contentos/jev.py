"""Adapter to Jev (ContentForge server/decision). Jev decides, contentos executes after its own gates.
Auth: ContentForge is session-gated, so the caller supplies a session cookie in CONTENTFORGE_COOKIE.
Every call is recorded in the local decisions table (source=jev or local_fallback) for calibration."""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request

from . import ledger

BASE = os.environ.get("CONTENTFORGE_URL", "http://localhost:3000").rstrip("/")


def _req(method, path, body=None, timeout=30):
    h = {"Content-Type": "application/json"}
    if os.environ.get("CONTENTFORGE_COOKIE"):
        h["Cookie"] = os.environ["CONTENTFORGE_COOKIE"]
    r = urllib.request.Request(BASE + path, method=method, headers=h, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, {"message": e.read().decode()[:300]}
    except Exception as e:
        return 0, {"message": f"{type(e).__name__}: {e}"}


def status():
    """-> dict(reachable, authed, jev_configured, detail)"""
    code, j = _req("GET", "/api/decision/status", timeout=5)
    if code == 0:
        return {"reachable": False, "authed": False, "jev_configured": False, "detail": j["message"]}
    if code == 401:
        return {"reachable": True, "authed": False, "jev_configured": False, "detail": "401: set CONTENTFORGE_COOKIE from a logged-in session"}
    return {"reachable": True, "authed": code == 200, "jev_configured": bool(j.get("jev", {}).get("configured")),
            "engine_enabled": j.get("engine", {}).get("enabled"), "detail": f"HTTP {code}"}


def record_decision(dtype, subject, decision, confidence, source, reasons=(), predicted=None):
    did = hashlib.sha256(f"{dtype}|{subject}|{time.time()}".encode()).hexdigest()[:12]
    with ledger.db() as c:
        c.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (did, dtype, subject, decision, confidence, source, json.dumps(list(reasons)),
                   json.dumps(predicted) if predicted is not None else None, None, time.time()))
    return did


def record_outcome(decision_id, actual):
    with ledger.db() as c:
        c.execute("UPDATE decisions SET actual=? WHERE id=?", (json.dumps(actual), decision_id))


def triage(candidates, context=None):
    """candidates: [{title, summary?, url?}]. Returns [{title, decision, score, source, decision_id}].
    Fail-open to 'watch' (never silently 'pursue') when Jev is unreachable/unauthed/unconfigured."""
    body = {"candidates": [{"id": str(i), **c} for i, c in enumerate(candidates)], "context": context or {}}
    code, j = _req("POST", "/api/decision/triage", body, timeout=120)
    out = []
    if code == 200:
        for t in j["candidates"]:
            did = record_decision("research_triage", t["title"], t["decision"], t.get("score"), "jev", [], {"score": t.get("score")})
            out.append({"title": t["title"], "decision": t["decision"], "score": t.get("score"), "source": "jev", "decision_id": did})
        return out
    for c in candidates:
        did = record_decision("research_triage", c["title"], "watch", None, "local_fallback", [f"jev unavailable: HTTP {code} {j.get('message','')[:80]}"])
        out.append({"title": c["title"], "decision": "watch", "score": None, "source": "local_fallback", "decision_id": did})
    return out
