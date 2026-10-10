import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import jev, ledger, learn  # noqa: E402


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path))   # the ledger lives in the (external) workspace


class FakeJev(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        out = {"candidates": [{**c, "decision": "pursue", "score": 0.7, "signals": {}} for c in body["candidates"]]}
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps(out).encode())

    def log_message(self, *a):
        pass


def test_triage_uses_jev_when_reachable(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    srv = HTTPServer(("127.0.0.1", 0), FakeJev)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(jev, "BASE", f"http://127.0.0.1:{srv.server_port}")
    r = jev.triage([{"title": "x"}])[0]
    assert (r["decision"], r["source"]) == ("pursue", "jev")


def test_triage_fails_open_to_watch_never_pursue(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setattr(jev, "BASE", "http://127.0.0.1:1")
    r = jev.triage([{"title": "x"}])[0]
    assert (r["decision"], r["source"]) == ("watch", "local_fallback")


def test_calibration_flags_overconfidence(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    for i in range(6):
        d = jev.record_decision("opportunity_score", f"t{i}", "pursue", 0.9, "jev", predicted={"score": 0.9})
        jev.record_outcome(d, {"score": 0.4})
    assert learn.calibration()[0]["verdict"] == "overconfident"


def test_thin_data_never_gives_verdict(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    ledger.record("r", "c", "render", "hyperframes", "FAIL", 0)
    assert learn.provider_stats()[0]["verdict"] == "insufficient_data"
    assert learn.platform_report()[0]["verdict"] == "insufficient_data"


def test_rank_requires_all_inputs_and_orders():
    good = dict(topic="a", demand=.9, novelty=.8, channel_fit=.9, competition=.2, cost=.2, risk=.1)
    bad = dict(topic="b", demand=.2, novelty=.2, channel_fit=.2, competition=.9, cost=.9, risk=.9)
    r = learn.rank_opportunities([bad, good, {"topic": "c", "demand": .5}])
    assert [x["topic"] for x in r][:2] == ["a", "b"] and r[2]["score"] is None
