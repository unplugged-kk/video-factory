"""Pure planning helpers for the video-director (Motion Director M2).

The creative work (audience, hook, scenes, treatments) is done by the `video-director` skill. This module holds the parts
that can be checked mechanically, so a plan cannot quietly drift from the capability registry or from its own narration:

  * select_capability()   choose among preferred capabilities by status, recording any substitution;
  * capability_report()   what a plan selects, with status, fallbacks and substitutions;
  * coherence_issues()    structural story checks (hook first, arc matches scenes, not everything animated, ...);
  * anchor_issues() / estimate_timeline()  scene anchors and cue phrases must exist in the script, in order, with an
                          ESTIMATED timeline (words / 2.5 per second; the real timeline comes from aligned audio);
  * check()               validator + coherence + anchors + duration in one call.

Nothing here renders, calls a network, or modifies its inputs. Planning is read-only with respect to plans and registry.

CLI (exit 0 = ok, 1 = problems, 2 = unreadable input):
  python -m contentos.production.director check  PLAN.json --script SCRIPT.txt [--mode production|experimental] [--registry PATH]
  python -m contentos.production.director report PLAN.json --script SCRIPT.txt --out DIR      # writes capability report + estimated storyboard
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from . import direction as dr
from . import platforms as pf
from . import sceneplan

WORDS_PER_SECOND = 2.5          # explainer-motion-craft R6 budgets 2.3-2.5 words/s; an estimate, never a measurement
DEFAULT_FALLBACK = "hf.native:html-svg-css"
STATIC_PREFIX = "none"          # a scene is static when direction.motion.primary starts with "none"


@dataclass(frozen=True)
class Selection:
    chosen: str | None              # capability id to use, or None when nothing verified can do the job
    status: str | None              # registry status of `chosen`
    substituted_from: str | None    # the first preference, when it could not be used
    reason: str                     # why the first preference could not be used ("" when it was used)
    needs_review: bool              # True when no verified capability was usable


def usable(reg, cid, *, mode="production", opt_in=(), experimental=False, allow_paid=False):
    """(ok, reason) for using capability `cid` as a scene technique under the given permissions."""
    e = reg.get(cid)
    if e is None:
        return False, "unknown capability id"
    if e["kind"] not in dr.TECHNIQUE_KINDS:
        return False, f"kind {e['kind']!r} is not a scene technique"
    if e["paid"] and not allow_paid:
        return False, "needs a paid service and paid use has not been approved"
    st = e["status"]
    if st == "unavailable":
        return False, f"unavailable: {e['status_reason']}"
    if st == "candidate" and not (mode == "experimental" and experimental):
        return False, f"candidate (needs mode='experimental' and an experimental scene): {e['status_reason']}"
    if st == "available" and cid not in opt_in:
        return False, f"available only after a prerequisite, not opted in: {e['status_reason']}"
    if st == "installed":
        problem = reg.path_problem(cid)
        if problem:
            return False, f"registered as installed but {problem}"
    return True, ""


def select_capability(reg, preferred, *, mode="production", opt_in=(), experimental=False, allow_paid=False, fallback=None):
    """Pick the first usable capability from `preferred` (most wanted first). If the first preference is not usable the
    result records the substitution. When none is usable, fall back to `fallback`, then the first preference's registry
    fallback, then DEFAULT_FALLBACK; if even those are unusable, return chosen=None and needs_review=True."""
    preferred = list(preferred)
    if not preferred:
        raise ValueError("preferred must name at least one capability id")
    perms = dict(mode=mode, opt_in=tuple(opt_in), experimental=experimental, allow_paid=allow_paid)
    first_ok, first_reason = usable(reg, preferred[0], **perms)
    if first_ok:
        return Selection(preferred[0], reg.get(preferred[0])["status"], None, "", False)
    candidates = preferred[1:]
    e0 = reg.get(preferred[0])
    for c in (fallback, e0["fallback"] if e0 else None, DEFAULT_FALLBACK):
        if c and c not in candidates:
            candidates.append(c)
    for cid in candidates:
        ok, _ = usable(reg, cid, **perms)
        if ok:
            return Selection(cid, reg.get(cid)["status"], preferred[0], first_reason, False)
    return Selection(None, None, preferred[0], first_reason, True)


def is_static(direction):
    m = direction.get("motion") if isinstance(direction, dict) else None
    primary = m.get("primary", "") if isinstance(m, dict) else ""
    return isinstance(primary, str) and primary.strip().lower().startswith(STATIC_PREFIX)


def _scenes(plan):
    return [s for s in plan.get("scenes", []) if isinstance(s, dict)]


def capability_report(plan, reg):
    """Deterministic summary of the capabilities a plan selects. Pure; reads only."""
    rows, used = [], {}
    for sc in _scenes(plan):
        d = sc.get("direction")
        if not isinstance(d, dict):
            continue
        sel = []
        for cid in d.get("technique", []):
            e = reg.get(cid)
            sel.append({"id": cid, "status": e["status"] if e else "unknown", "kind": e["kind"] if e else None,
                        "offline": e["offline"] if e else None, "paid": e["paid"] if e else None})
            used[cid] = e
        rows.append({"scene": sc.get("id"), "treatment": d.get("treatment"), "static": is_static(d), "selected": sel,
                     "declared_fallback": d.get("fallback"), "substituted_from": d.get("substituted_from"),
                     "experimental": bool(d.get("experimental", False))})
    by_status = {}
    for cid, e in used.items():
        by_status.setdefault(e["status"] if e else "unknown", []).append(cid)
    return {
        "scenes": rows,
        "summary": {
            "distinct_capabilities": len(used),
            "by_status": {k: sorted(v) for k, v in sorted(by_status.items())},
            "non_installed_used": sorted(c for c, e in used.items() if e is None or e["status"] != "installed"),
            "paid_used": sorted(c for c, e in used.items() if e is not None and e["paid"]),
            "substitutions": [{"scene": r["scene"], "preferred": r["substituted_from"], "selected": [s["id"] for s in r["selected"]],
                               "fallback": r["declared_fallback"]} for r in rows if r["substituted_from"]],
            "static_scenes": [r["scene"] for r in rows if r["static"]],
        },
    }


def report_markdown(report):
    out = ["# Capability report", "", "| Scene | Treatment | Static | Selected (status) | Fallback | Substituted from |", "|---|---|---|---|---|---|"]
    for r in report["scenes"]:
        sel = ", ".join(f"`{s['id']}` ({s['status']})" for s in r["selected"])
        out.append(f"| {r['scene']} | {r['treatment']} | {'yes' if r['static'] else 'no'} | {sel} | {r['declared_fallback'] or '-'} | {r['substituted_from'] or '-'} |")
    s = report["summary"]
    out += ["", f"Distinct capabilities used: {s['distinct_capabilities']}", ""]
    for st, ids in s["by_status"].items():
        out.append(f"- {st}: " + ", ".join(f"`{i}`" for i in ids))
    out.append(f"- Non-installed capabilities used: {s['non_installed_used'] or 'none'}")
    out.append(f"- Paid capabilities used: {s['paid_used'] or 'none'}")
    out.append(f"- Static scenes: {s['static_scenes'] or 'none'}")
    for sub in s["substitutions"]:
        out.append(f"- Substitution in `{sub['scene']}`: preferred `{sub['preferred']}` replaced by {sub['selected']} (declared fallback {sub['fallback']})")
    return "\n".join(out) + "\n"


def _collapse(seq):
    out = []
    for x in seq:
        if not out or out[-1] != x:
            out.append(x)
    return out


def coherence_issues(plan):
    """Structural story checks that do not need the registry or the script. Returns a list of strings (empty = coherent)."""
    issues, scenes = [], _scenes(plan)
    directed = [s for s in scenes if isinstance(s.get("direction"), dict)]
    if not directed:
        return issues                                      # plans without direction have nothing to check
    if len(directed) != len(scenes):
        issues.append("some scenes have a direction block and some do not; direct every scene or none")
        return issues
    purposes = [s["direction"].get("purpose") for s in scenes]
    if purposes[0] != "hook":
        issues.append(f"first scene purpose is {purposes[0]!r}; the opening scene must be the hook")
    if purposes[-1] not in ("recap", "cta"):
        issues.append(f"last scene purpose is {purposes[-1]!r}; end on a recap or cta")
    arc = (plan.get("brief") or {}).get("arc")
    if arc is not None and arc != _collapse(purposes):
        issues.append(f"brief.arc {arc} does not match the scene purposes in order {_collapse(purposes)}")
    take = [s["direction"].get("takeaway") for s in scenes]
    if len(set(take)) != len(take):
        issues.append("two scenes share the same takeaway; merge them or give each its own")
    if len(scenes) >= 3 and all(not is_static(s["direction"]) for s in scenes):
        issues.append("every scene animates; at least one scene should stay static for clarity")
    for s in scenes:
        if "reframe" not in s["direction"]:
            issues.append(f"scene {s.get('id')!r}: missing direction.reframe (16:9 and 9:16 composition notes)")
        d = s["direction"]
        if is_static(d) and d.get("cues"):
            issues.append(f"scene {s.get('id')!r}: motion.primary says static but cues are listed; make the motion explicit or drop the cues")
        if d.get("camera", "hold") != "hold" and is_static(d):
            issues.append(f"scene {s.get('id')!r}: a static scene cannot have a camera move")
    return issues


def _words(script):
    return script.split()


def estimate_timeline(plan, script, wps=WORDS_PER_SECOND):
    """Resolve scene anchors against the script with ESTIMATED word times. Returns (scenes, total_seconds)."""
    ws = _words(script)
    timed = [(w, i / wps, (i + 1) / wps) for i, w in enumerate(ws)]
    total = len(ws) / wps
    return sceneplan.resolve(plan, timed, total), total


def anchor_issues(plan, script):
    """Every scene anchor and cue phrase must exist in the script, in order; cues must fall inside their scene."""
    issues = []
    try:
        scenes, _ = estimate_timeline(plan, script)
    except ValueError as exc:
        return [f"scene anchors: {exc}"]
    words = [sceneplan.norm(w) for w in _words(script)]
    for sc in scenes:
        d = sc.get("direction") or {}
        for n, cue in enumerate(d.get("cues", [])):
            at = cue.get("at")
            if isinstance(at, int):
                if not sc["i0"] <= at <= sc["i1"]:
                    issues.append(f"scene {sc['id']!r}: cue[{n}] word index {at} is outside the scene's words {sc['i0']}-{sc['i1']}")
                continue
            target = [sceneplan.norm(x) for x in at.split()]
            hit = any(words[i:i + len(target)] == target for i in range(sc["i0"], sc["i1"] - len(target) + 2))
            if not hit:
                issues.append(f"scene {sc['id']!r}: cue[{n}] phrase {at!r} is not in this scene's narration")
    return issues


def duration_issue(script, lo=45, hi=60, wps=WORDS_PER_SECOND):
    est = len(_words(script)) / wps
    return None if lo <= est <= hi else f"estimated duration {est:.1f}s is outside {lo}-{hi}s ({len(_words(script))} words at {wps}/s)"


def check(plan, reg, script, *, mode="production", lo=45, hi=60):
    """Run every M2 check. Returns a dict; `ok` is True only when nothing was found."""
    validator = [str(i) for i in dr.validate_plan(plan, reg, mode=mode)]
    coherence = coherence_issues(plan)
    paid = capability_report(plan, reg)["summary"]["paid_used"]
    capabilities = [f"paid capabilities selected without approval: {paid}"] if paid else []
    anchors = anchor_issues(plan, script)
    dur = duration_issue(script, lo, hi)
    words = len(_words(script))
    return {"validator": validator, "coherence": coherence, "capabilities": capabilities, "anchors": anchors, "duration": dur,
            "words": words, "estimated_seconds": round(words / WORDS_PER_SECOND, 1),
            "ok": not (validator or coherence or capabilities or anchors or dur)}


def estimated_storyboard_md(plan, script, title=None):
    scenes, total = estimate_timeline(plan, script)
    note = (f"ESTIMATED timeline: {len(_words(script))} words at {WORDS_PER_SECOND} words/s = {total:.1f} s. "
            "Real times come from the aligned voice track when the video is built.")
    return sceneplan.storyboard_md(plan, scenes, title or plan.get("title", "Untitled"), note)


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m contentos.production.director", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "report"):
        p = sub.add_parser(name)
        p.add_argument("plan")
        p.add_argument("--script", required=True)
        p.add_argument("--mode", choices=dr.MODES, default="production")
        p.add_argument("--registry", default=None)
        p.add_argument("--kind", choices=pf.KINDS, default=None,
                       help="short|long: take the maximum length from config/platforms.json (owner ceiling and platform limits); shorter is fine")
        p.add_argument("--platforms", default=None, help="comma-separated platform ids for --kind (default: enabled platforms)")
        p.add_argument("--min-seconds", type=float, default=None)
        p.add_argument("--max-seconds", type=float, default=None)
        if name == "report":
            p.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        reg = dr.load_registry(args.registry)
        plan = dr.load_plan(args.plan)
        script = Path(args.script).read_text(encoding="utf-8")
    except (dr.RegistryError, OSError, json.JSONDecodeError) as exc:
        print(f"cannot read input: {exc}", file=sys.stderr)
        return 2
    lo, hi = args.min_seconds, args.max_seconds
    if args.kind:
        try:
            b = pf.budget(pf.load(), args.kind, platforms=[x for x in (args.platforms or "").split(",") if x] or None,
                          owner_max=pf.owner_limits()[args.kind])
        except pf.PlatformError as exc:
            print(f"cannot read platform limits: {exc}", file=sys.stderr)
            return 2
        if b["max_seconds"] is None:
            print(f"no platform has a usable {args.kind}-form format", file=sys.stderr)
            return 2
        hi = hi if hi is not None else b["max_seconds"]
        lo = lo if lo is not None else 1                 # "if it is less, that is also fine"
        print(f"[platforms] {args.kind}-form maximum {hi:g} s (limited by {b['limiting']})")
    res = check(plan, reg, script, mode=args.mode, lo=45 if lo is None else lo, hi=60 if hi is None else hi)
    for key in ("validator", "coherence", "capabilities", "anchors"):
        for line in res[key]:
            print(f"[{key}] {line}")
    if res["duration"]:
        print(f"[duration] {res['duration']}")
    print(f"{'OK' if res['ok'] else 'FAILED'} [{args.mode} mode]: {res['words']} words, ~{res['estimated_seconds']} s estimated")
    if args.cmd == "report":
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        rep = capability_report(plan, reg)
        (out / "capability-report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (out / "capability-report.md").write_text(report_markdown(rep), encoding="utf-8")
        (out / "storyboard.estimated.md").write_text(estimated_storyboard_md(plan, script), encoding="utf-8")
        print(f"wrote capability-report.json, capability-report.md, storyboard.estimated.md to {out}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(_main())
