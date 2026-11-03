"""scenekit planner: style choice, per-scene intent, scene type, motion, and a variety report.

Rules this module enforces (all deterministic; no model call):
  * Data-backed scene types (diagram, code, compare, stat, steps) are used ONLY when the spec line carries the data
    (`visual:` mapping). The planner never invents nodes, code, numbers or relationships.
  * Text-only scenes (statement, pullquote, split) are chosen by intent fit + style affinity - repetition penalty.
  * Ties break on a seeded hash, so the same spec and seed always give the same plan.
  * A stat/chart must name a `source` or be marked `illustrative: true`; otherwise validation BLOCKs.

Thresholds in `variety_report` are PROVISIONAL: the measured baseline is "every scene shares one grammar"; the numbers
below only flag the obvious degenerate cases and have not been calibrated on a population of shipped videos.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter

from . import styles as S

PLAN_SCHEMA = "scenekit-plan/1"
MAX_NODES, MAX_LABEL, MAX_CODE_LINES, MAX_CODE_COLS, MAX_STEPS, MAX_POINTS, MAX_BARS = 8, 22, 12, 42, 6, 4, 5

INTENTS = ("hook", "problem", "definition", "mechanism", "architecture", "code", "example", "comparison",
           "evidence", "summary", "cta")
# Which text-only type reads best for an intent (score 0-3); stage types are authored, so not scored here.
TEXT_FIT = {
    "hook": {"pullquote": 3, "statement": 2, "split": 0}, "problem": {"statement": 3, "pullquote": 2, "split": 1},
    "definition": {"split": 3, "statement": 2, "pullquote": 1}, "mechanism": {"statement": 3, "split": 2, "pullquote": 0},
    "architecture": {"statement": 3, "split": 1, "pullquote": 0}, "code": {"statement": 3, "split": 1, "pullquote": 0},
    "example": {"split": 3, "statement": 2, "pullquote": 1}, "comparison": {"statement": 2, "split": 2, "pullquote": 1},
    "evidence": {"split": 3, "pullquote": 2, "statement": 1}, "summary": {"pullquote": 3, "statement": 2, "split": 1},
    "cta": {"pullquote": 3, "statement": 2, "split": 0},
}
TYPE_INTENT = {"diagram": "architecture", "code": "code", "compare": "comparison", "stat": "evidence", "steps": "mechanism"}

_KW = {
    "architecture": r"\b(architecture|service|services|queue|broker|topic|partition|producer|consumer|cluster|node|pod|gateway|pipeline|flow)\b",
    "code": r"\b(code|function|command|terminal|script|api|cli|json|yaml|python|bash|sql)\b",
    "comparison": r"\b(vs|versus|instead|compared|rather than|difference|unlike)\b",
    "evidence": r"\d|percent|%|\b(measured|benchmark|study|data)\b",
    "definition": r"\b(is a|is an|means|stands for|called|defined)\b",
    "problem": r"\b(problem|fails?|breaks?|wrong|slow|outage|stuck|pain|risk)\b",
    "summary": r"\b(recap|in short|remember|takeaway|so |that is why)\b",
}
_STYLE_KW = {
    "blueprint-architecture": r"kubernetes|kafka|microservice|architecture|distributed|pipeline|event|queue|network|cluster|devops|service",
    "code-first": r"\bcode\b|python|\bapi\b|\bcli\b|command|terminal|function|debug|sdk|script|json",
    "cinematic-documentary": r"history|story|why|future|infrastructure|ai |model|era|decade|rise of",
    "editorial-magazine": r"research|industry|report|study|analysis|market|paper|policy|trend",
    "kinetic-type": r"stop|never|myth|truth|secret|mistake|hot take|wrong",
    "clean-explainer": r"how |what is|explain|basics|concept|guide|works",
}


def _h(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def style_request(spec: dict) -> dict:
    """Normalise spec['visual_style'] (str or mapping) to {id, version, selection_mode, seed}."""
    vs = spec.get("visual_style")
    if isinstance(vs, str):
        vs = {"id": vs}
    vs = dict(vs or {})
    sid = vs.get("id") or "auto"
    return {"id": sid, "version": vs.get("version"), "selection_mode": "auto" if sid == "auto" else "explicit",
            "seed": int(vs.get("seed", _h(spec.get("content_id", "x")) % 100000))}


def recommend(spec: dict) -> list[dict]:
    text = " ".join([spec.get("title", ""), spec.get("topic", ""), " ".join(spec.get("tags") or [])]
                    + [f"{ln.get('say', '')} {ln.get('headline', '')}" for ln in spec.get("script", [])]).lower()
    data_types = Counter((ln.get("visual") or {}).get("type") for ln in spec.get("script", []))
    out = []
    for sid, pat in _STYLE_KW.items():
        hits = len(re.findall(pat, text))
        score = min(hits, 6) + (4 if sid == "blueprint-architecture" and data_types["diagram"] else 0) \
            + (4 if sid == "code-first" and data_types["code"] else 0) \
            + (2 if sid == "kinetic-type" and spec.get("kind", "short") == "short" and len(spec.get("script", [])) <= 6 else 0) \
            + (1 if sid == "clean-explainer" else 0)
        out.append({"id": sid, "score": score, "hits": hits})
    return sorted(out, key=lambda r: (-r["score"], r["id"]))


def resolve_style(spec: dict) -> dict:
    req = style_request(spec)
    if req["id"] == "auto":
        rec = recommend(spec)
        req["id"], req["recommendation"] = rec[0]["id"], rec[:3]
    s = S.get(req["id"])
    req["version"] = req["version"] or s["version"]
    if req["version"] != s["version"]:
        raise ValueError(f"style {req['id']} is at version {s['version']}, spec asks for {req['version']}")
    return req


# ---- authored-data validation (fail closed) ---------------------------------------------------------------------

def _lab(errs, path, v, limit=MAX_LABEL):
    if not isinstance(v, str) or not v.strip():
        errs.append(f"{path}: label must be a non-empty string")
    elif len(v) > limit:
        errs.append(f"{path}: label {v!r} is {len(v)} chars, max {limit} (it would not be readable on a phone)")


def validate_visual(v: dict, path: str = "visual") -> list[str]:
    errs: list[str] = []
    t = v.get("type")
    if t not in S.STAGE_TYPES + S.TEXT_TYPES:
        return [f"{path}.type: {t!r} unknown; use one of {S.STAGE_TYPES + S.TEXT_TYPES}"]
    if t == "diagram":
        nodes, edges = v.get("nodes") or [], v.get("edges") or []
        if not 2 <= len(nodes) <= MAX_NODES: errs.append(f"{path}.nodes: need 2-{MAX_NODES}, got {len(nodes)}")
        ids = [n.get("id") for n in nodes if isinstance(n, dict)]
        if len(set(ids)) != len(ids): errs.append(f"{path}.nodes: duplicate ids")
        for i, n in enumerate(nodes): _lab(errs, f"{path}.nodes[{i}]", n.get("label") if isinstance(n, dict) else None)
        if not edges: errs.append(f"{path}.edges: a diagram needs at least one edge")
        for i, e in enumerate(edges):
            if not (isinstance(e, (list, tuple)) and len(e) >= 2 and e[0] in ids and e[1] in ids and e[0] != e[1]):
                errs.append(f"{path}.edges[{i}]: must be [from_id, to_id(, label)] using declared, different node ids")
            elif len(e) > 2: _lab(errs, f"{path}.edges[{i}] label", e[2], 16)
    elif t == "code":
        lines = str(v.get("code", "")).rstrip("\n").split("\n")
        if not v.get("code"): errs.append(f"{path}.code: required (the planner never writes code for you)")
        if len(lines) > MAX_CODE_LINES: errs.append(f"{path}.code: {len(lines)} lines, max {MAX_CODE_LINES}")
        for i, ln in enumerate(lines):
            if len(ln) > MAX_CODE_COLS: errs.append(f"{path}.code line {i + 1}: {len(ln)} cols, max {MAX_CODE_COLS}")
        for f in v.get("focus") or []:
            if not (isinstance(f, int) and 1 <= f <= len(lines)): errs.append(f"{path}.focus: line {f!r} out of range")
    elif t == "compare":
        for side in ("left", "right"):
            d = v.get(side) or {}
            _lab(errs, f"{path}.{side}.title", d.get("title"), 18)
            pts = d.get("points") or []
            if not 1 <= len(pts) <= MAX_POINTS: errs.append(f"{path}.{side}.points: need 1-{MAX_POINTS}")
            for i, p in enumerate(pts): _lab(errs, f"{path}.{side}.points[{i}]", p, 30)
    elif t == "stat":
        bars = v.get("bars") or []
        if not (v.get("value") or bars): errs.append(f"{path}: needs `value` or `bars`")
        if len(bars) > MAX_BARS: errs.append(f"{path}.bars: max {MAX_BARS}")
        for i, b in enumerate(bars):
            _lab(errs, f"{path}.bars[{i}]", b.get("label") if isinstance(b, dict) else None, 16)
            if not isinstance(b.get("value"), (int, float)) or b["value"] < 0: errs.append(f"{path}.bars[{i}].value must be a number >= 0")
        if not v.get("source") and v.get("illustrative") is not True:
            errs.append(f"{path}: BLOCK - a stat or chart must name a `source` or set `illustrative: true` (no unsourced metrics)")
    elif t == "steps":
        st = v.get("steps") or []
        if not 2 <= len(st) <= MAX_STEPS: errs.append(f"{path}.steps: need 2-{MAX_STEPS}")
        for i, s in enumerate(st): _lab(errs, f"{path}.steps[{i}]", s, 34)
    return errs


def validate_spec_visuals(spec: dict) -> list[str]:
    errs = []
    for i, ln in enumerate(spec.get("script", []), 1):
        if ln.get("visual") is not None:
            errs += validate_visual(ln["visual"], f"script[{i}].visual")
    return errs


# ---- intent and planning ----------------------------------------------------------------------------------------

def classify_intent(ln: dict, i: int, n: int) -> str:
    if (ln.get("visual") or {}).get("type") in TYPE_INTENT:
        return TYPE_INTENT[ln["visual"]["type"]]
    tag = (ln.get("tag") or "").lower()
    if i == 1 or "hook" in tag: return "hook"
    if i == n or "cta" in tag: return "cta"
    text = f"{ln.get('say', '')} {ln.get('headline', '')}".lower()
    for intent in ("comparison", "evidence", "definition", "problem", "architecture", "code", "summary"):
        if re.search(_KW[intent], text): return intent
    return "mechanism" if "step" in tag else "example"


def plan(spec: dict, style: dict | None = None) -> dict:
    errs = validate_spec_visuals(spec)
    if errs:
        raise ValueError("visual validation failed:\n  " + "\n  ".join(errs))
    style = style or resolve_style(spec)
    st = S.get(style["id"])
    script = spec["script"]
    n, seed, scenes = len(script), style["seed"], []
    motions = [st["motion"]] + list(st["alt_motions"])
    for i, ln in enumerate(script, 1):
        intent = classify_intent(ln, i, n)
        v = ln.get("visual")
        if v:
            stype, why = v["type"], f"authored visual.type={v['type']}"
        else:
            best = None
            for cand in S.TEXT_TYPES:
                score = TEXT_FIT[intent][cand] + st["affinity"][cand]
                run = 0
                for prev in reversed(scenes):
                    if prev["type"] != cand: break
                    run += 1
                score -= 3 * (1 if run >= 1 else 0) + run          # immediate repeat costs 3, longer runs more
                score -= 1 if any(p["type"] == cand for p in scenes[-3:-1]) else 0
                key = (score, _h(seed, i, cand))
                if best is None or key > best[0]: best = (key, cand, score)
            stype, why = best[1], f"intent={intent} fit+affinity-repeat={best[2]}"
        mot = motions[0]
        if len(motions) > 1:                                         # rotate alternates, never the same twice in a row
            pick = motions[_h(seed, i, "m") % len(motions)]
            mot = pick if not scenes or pick != scenes[-1]["motion"] else next(m for m in motions if m != pick)
        if i == 1 and st["motion"] != "cut": mot = st["motion"]      # the hook always uses the style's signature motion
        scenes.append({"id": f"scene-{i:03d}", "index": i, "type": stype, "intent": intent, "motion": mot,
                       "layout": st["layout"], "transition_in": mot, "ground": S.ground_for(style["id"], i, seed), "why": why,
                       "data_backed": stype in S.STAGE_TYPES,
                       "reason_visual": "authored" if v else "text-only (no data supplied, nothing invented)"})
    return {"schema": PLAN_SCHEMA, "style": {k: style[k] for k in ("id", "version", "selection_mode", "seed")}
            | ({"recommendation": style["recommendation"]} if "recommendation" in style else {}),
            "scenes": scenes}


def variety_report(p: dict, durations: list[float] | None = None) -> dict:
    sc = p["scenes"]
    n = len(sc)
    sig = [(s["type"], s["motion"]) for s in sc]
    run = best_run = 1
    for a, b in zip(sig, sig[1:]):
        run = run + 1 if a == b else 1
        best_run = max(best_run, run)
    types = Counter(s["type"] for s in sc)
    checks = []

    def add(cid, status, evidence, fix, human=False, scene=None):
        checks.append({"id": cid, "status": status, "scene": scene, "evidence": evidence, "remediation": fix,
                       "human_review": human})
    distinct = len(set(sig))
    need = min(3, n)
    add("V1.signature_diversity", "PASS" if distinct >= need else ("BLOCK" if n >= 4 and distinct == 1 else "WARN"),
        f"{distinct} distinct (type, motion) signatures in {n} scenes (provisional minimum {need})",
        "supply `visual:` data for more scenes, or pick a style with more alternates")
    add("V2.adjacent_repeat", "PASS" if best_run <= 2 else "WARN",
        f"longest run of identical (type, motion) = {best_run} (provisional max 2)", "reorder or add authored visuals")
    top, topn = types.most_common(1)[0]
    add("V3.type_dominance", "PASS" if n < 4 or topn / n <= 0.6 else "WARN",
        f"most common type {top!r} = {topn}/{n} ({topn / n:.0%}; provisional max 60%)", "give more lines a data-backed visual")
    backed = sum(s["data_backed"] for s in sc)
    add("V4.data_backed_share", "PASS" if backed else "WARN",
        f"{backed}/{n} scenes carry authored data visuals",
        "a video with only text scenes explains by caption alone; author diagrams/code/compare where the script describes structure",
        human=True)
    if durations and len(durations) == n and n >= 3:
        r = max(durations) / max(min(durations), 0.01)
        add("V5.pacing_spread", "PASS" if r >= 1.15 else "WARN", f"longest/shortest scene = {r:.2f} (provisional min 1.15)",
            "scene length follows narration; very uniform pacing reads as a template", human=True)
    grounds = len({s["ground"] for s in sc})
    add("V6.ground_variants", "PASS" if grounds >= min(3, n) else "WARN",
        f"{grounds} distinct grounds assigned; repo Rule A needs ceil(n/2)={-(-n // 2)} measured distinct backdrops",
        "run `python -m contentos.intelligence.visual scenes` on the render; the grounds are tints of one family", human=False)
    status = "BLOCK" if any(c["status"] == "BLOCK" for c in checks) else ("WARN" if any(c["status"] == "WARN" for c in checks) else "PASS")
    return {"schema": "scenekit-variety/1", "style": p["style"]["id"], "style_version": p["style"]["version"],
            "seed": p["style"]["seed"], "status": status, "scene_count": n, "types": dict(types),
            "motions": dict(Counter(s["motion"] for s in sc)), "distinct_signatures": distinct,
            "longest_identical_run": best_run, "checks": checks,
            "note": "Thresholds are provisional and uncalibrated; see docs/video-intelligence/08-multi-style-system.md"}
