"""Learning loops. Pure analysis over the local ledger: they RECOMMEND, they never execute or publish.
Every function returns plain dicts so a human (or Jev) can inspect the reasoning. Thin data => says so."""
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import jev, ledger, storage

MIN_N = 5          # below this, report 'insufficient_data' rather than a verdict
ROOT = Path(__file__).resolve().parent.parent


# LOOP 7 + 8: skill/provider reliability from real runs ---------------------------------
def provider_stats():
    rows = ledger.db().execute("SELECT stage, provider, status, end-start FROM runs WHERE status IN ('OK','FAIL')").fetchall()
    g = defaultdict(list)
    known = {st_: pv for st_, pv, status, _ in rows if status == "OK"}   # failures log provider '-': attribute to the stage's known provider
    for stage, prov, status, secs in rows:
        if True:
            g[(stage, known.get(stage, prov) if prov == "-" else prov)].append((status == "OK", secs))
    out = []
    for (stage, prov), v in sorted(g.items()):
        n, ok = len(v), sum(1 for o, _ in v if o)
        rate = ok / n
        verdict = "insufficient_data" if n < MIN_N else ("REPLACE_CANDIDATE" if rate < 0.8 else "healthy")
        out.append({"stage": stage, "provider": prov, "runs": n, "success": round(rate, 2),
                    "p50_s": round(st.median(s for _, s in v), 1), "verdict": verdict})
    return out


# LOOP 6: cost --------------------------------------------------------------------------
def cost_report():
    rows = ledger.db().execute("SELECT provider, count(*), sum(cash_cost) FROM runs GROUP BY provider").fetchall()
    paid = [p for p, _, c in rows if (c or 0) > 0]
    return {"by_provider": [{"provider": p, "runs": n, "cash_usd": round(c or 0, 4)} for p, n, c in rows],
            "total_cash_usd": round(sum((c or 0) for _, _, c in rows), 4),
            "note": "cash only; local compute (electricity) is not estimated",
            "paid_providers_used": paid}


# LOOP 9: decision calibration ----------------------------------------------------------
def calibration():
    rows = ledger.db().execute("SELECT type, source, confidence, predicted, actual FROM decisions WHERE actual IS NOT NULL").fetchall()
    g = defaultdict(list)
    for t, src, conf, pred, act in rows:
        p, a = json.loads(pred or "{}").get("score"), json.loads(act).get("score")
        if p is not None and a is not None:
            g[(t, src)].append(p - a)
    out = []
    for (t, src), errs in sorted(g.items()):
        n = len(errs)
        bias = st.mean(errs)
        verdict = "insufficient_data" if n < MIN_N else ("overconfident" if bias > 0.1 else "underconfident" if bias < -0.1 else "calibrated")
        out.append({"type": t, "source": src, "n": n, "mean_error": round(bias, 3), "verdict": verdict})
    return out or [{"verdict": "insufficient_data", "note": "no decisions have an outcome attached yet (jev.record_outcome)"}]


# LOOP 2: opportunity ranking (caller supplies measured inputs, 0..1; nothing is invented) -
W = {"demand": 0.25, "novelty": 0.15, "channel_fit": 0.20, "competition": -0.15, "cost": -0.10, "risk": -0.15}


def rank_opportunities(cands):
    out = []
    for c in cands:
        missing = [k for k in W if k not in c]
        if missing:
            out.append({"topic": c["topic"], "score": None, "error": f"missing inputs: {missing}"})
            continue
        score = 0.5 + sum(W[k] * (c[k] - 0.5) for k in W)
        out.append({"topic": c["topic"], "score": round(score, 3), "breakdown": {k: c[k] for k in W}, "weights": W})
    return sorted(out, key=lambda x: -(x["score"] or -1))


# LOOP 4 + 5: packaging / platform from ingested metrics --------------------------------
def _group(key):
    g = defaultdict(list)
    for r in ledger.db().execute(f"SELECT {key}, ctr, avg_view_pct, views FROM video_metrics").fetchall():
        g[r[0]].append(r[1:])
    out = []
    for k, v in sorted(g.items(), key=lambda kv: str(kv[0])):
        n = len(v)
        out.append({key: k, "n": n, "mean_ctr": round(st.mean(x[0] for x in v), 3), "mean_retention": round(st.mean(x[1] for x in v), 3),
                    "verdict": "insufficient_data" if n < MIN_N else "ok", "caveat": "correlation only, not causal"})
    return out or [{"verdict": "insufficient_data", "note": "no metrics ingested; needs YouTube Analytics (planned)"}]


def platform_report():
    return _group("platform")


def packaging_report():
    return _group("CASE WHEN hook_score>=55 THEN 'hook>=55' ELSE 'hook<55' END")


# LOOP 3 + 10: per-video recommendation, publish stays gated -------------------------------
def recommend(content_id, use_jev=False):
    d = storage.find_job_dir(content_id) or storage.legacy_job_dir(content_id) or (storage.jobs_root() / content_id)
    reasons, rec = [], "HOLD"
    qa = d / "qa.json"
    if not qa.exists():
        return {"content_id": content_id, "recommendation": "REVISE", "reasons": ["no qa.json: render and QA first"], "publish_requires": "PUBLISH_APPROVED"}
    fails = [x["check"] for x in json.loads(qa.read_text()) if x["status"] == "FAIL"]
    warns = [x["check"] for x in json.loads(qa.read_text()) if x["status"] == "WARN"]
    lint = d / "script-lint.json"
    if lint.exists():
        h = json.loads(lint.read_text())[0]
        floor = 55
        if h["verdict"] < floor:
            reasons.append(f"hook {h['verdict']}/100 ({h['band']}), floor {floor}; weakest property: {min(h['properties'], key=h['properties'].get)}")
            rec = "REVISE"
    if fails:
        rec, reasons = "REVISE", reasons + [f"QA FAIL: {fails}"]
    if warns:
        reasons.append(f"QA WARN: {warns}")
    if use_jev:
        topic = json.loads((d / "content.json").read_text()).get("title", content_id)
        j = jev.triage([{"title": topic}])[0]
        reasons.append(f"jev triage: {j['decision']} ({j['source']})")
        if j["decision"] == "drop":
            rec = "ABANDON"
    if rec == "HOLD" and not fails:
        rec = "PUBLISH"
        reasons.append("checks clear; recommendation only, public publish stays gated")
    did = jev.record_decision("publish_recommendation", content_id, rec, None, "local_rules", reasons)
    return {"content_id": content_id, "recommendation": rec, "reasons": reasons, "decision_id": did, "publish_requires": "PUBLISH_APPROVED"}
