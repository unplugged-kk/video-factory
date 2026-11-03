"""python -m contentos.skills <command>   (no rendering, no installs, no network)

  build                         regenerate config/creative-skills.json from the vendored bundle + a live probe
  verify                        bundle hashes, registry schema/ids/references, registry not stale  (exit 1 on any problem)
  probe                         what is installed right now
  list [--status S] [--category C] [--core]
  show SKILL                    id, name, or core name
  route "request" [--have song,footage,...] [--blocked]     ranked candidates; never auto-selects
  compat SKILL SKILL...         can these be combined (rule check, not a render test)
  deps SKILL                    requirements, missing capabilities, fallbacks, blockers
  plan --skill SKILL --script SPEC.yaml [--out FILE] [--content-id ID]        Track A skills only: writes a spec with visual_style + creative_skill
  ledger                        markdown ledger of every skill and status
  analyze-reference VIDEO --out DIR
  evidence --skill S --job J --note N [--fidelity full|approximate]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import registry as R

EVIDENCE = R.EVIDENCE_FILE


def _reg():
    return R.load()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="contentos.skills", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build"); sub.add_parser("verify"); sub.add_parser("probe"); sub.add_parser("ledger")
    p = sub.add_parser("list"); p.add_argument("--status"); p.add_argument("--category"); p.add_argument("--core", action="store_true")
    p = sub.add_parser("show"); p.add_argument("skill")
    p = sub.add_parser("deps"); p.add_argument("skill")
    p = sub.add_parser("route"); p.add_argument("request"); p.add_argument("--have", default=""); p.add_argument("--blocked", action="store_true")
    p = sub.add_parser("compat"); p.add_argument("skills", nargs="+")
    p = sub.add_parser("plan"); p.add_argument("--skill", required=True); p.add_argument("--script", required=True); p.add_argument("--out"); p.add_argument("--content-id")
    p = sub.add_parser("analyze-reference"); p.add_argument("video"); p.add_argument("--out", required=True); p.add_argument("--threshold", type=float, default=0.1)
    p = sub.add_parser("evidence"); p.add_argument("--skill", required=True); p.add_argument("--job", required=True); p.add_argument("--note", required=True)
    p.add_argument("--fidelity", default="approximate", choices=["full", "approximate"])
    a = ap.parse_args(argv)

    if a.cmd == "build":
        reg = R.build()
        errs = R.validate(reg)
        if errs:
            print("\n".join(errs)); return 1
        R.REGISTRY.write_text(json.dumps(reg, indent=1, sort_keys=False) + "\n")
        from collections import Counter
        print(f"wrote {R.REGISTRY.relative_to(R.ROOT)}: {len(reg['skills'])} skills", dict(Counter(s["status"] for s in reg["skills"])))
        return 0
    if a.cmd == "verify":
        problems = [f"bundle: {p}" for p in R.verify_library()]
        reg = _reg()
        problems += R.validate(reg)
        if R.stale(reg): problems.append("config/creative-skills.json is stale: run `python -m contentos.skills build`")
        print("\n".join(problems) or f"ok: bundle verified, {len(reg['skills'])} skills, registry current")
        return 1 if problems else 0
    if a.cmd == "probe":
        from .probe import probe
        for k, v in probe().items(): print(("OK " if v["ok"] else "NO ") + f"{k:30} {v['evidence']}")
        return 0
    if a.cmd == "analyze-reference":
        from .analyze import analyze
        r = analyze(Path(a.video), Path(a.out), a.threshold)
        print(json.dumps({k: r[k] for k in ("probe", "pacing", "audio", "contact_sheet")}, indent=1)); return 0
    if a.cmd == "evidence":
        reg = _reg(); s = R.find(reg, a.skill)
        if not s: print("unknown skill"); return 2
        ev = json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {}
        ev[s["name"] if s["kind"] == "creative" else f"core:{s['name']}"] = {"job": a.job, "note": a.note, "fidelity": a.fidelity}
        EVIDENCE.write_text(json.dumps(ev, indent=1, sort_keys=True) + "\n"); print("recorded; run build"); return 0

    reg = _reg()
    if a.cmd == "ledger":
        print(R.ledger_markdown(reg)); return 0
    if a.cmd == "list":
        for s in reg["skills"]:
            if (a.core) != (s["kind"] == "core-workflow") and a.core: continue
            if a.status and s["status"] != a.status: continue
            if a.category and s["category"] != a.category: continue
            print(f"{str(s['id']):28} {s['status']:34} {s['category']:34} {s['name']}")
        return 0
    if a.cmd in ("show", "deps"):
        s = R.find(reg, a.skill)
        if not s: print(f"unknown skill {a.skill!r}"); return 2
        print(json.dumps(s if a.cmd == "show" else {k: s[k] for k in ("id", "name", "status", "inputs_required", "requires", "missing", "fallbacks", "blockers", "limitations")}, indent=1)); return 0
    if a.cmd == "route":
        res = R.route(reg, a.request, [x for x in a.have.split(",") if x], a.blocked)
        print(json.dumps(res, indent=1)); return 0 if res else 1
    if a.cmd == "compat":
        r = R.compat(reg, a.skills); print(json.dumps(r, indent=1)); return 0 if r["compatible"] else 1
    if a.cmd == "plan":
        s = R.find(reg, a.skill)
        if not s: print(f"unknown skill {a.skill!r}"); return 2
        if s["execution"] != "track-a-scenekit":
            print(f"{s['name']} runs as {s['execution']}, not as a generated spec. Missing inputs: {', '.join(s['inputs_required']) or 'none'}. "
                  f"Recipe: {s['path']}. Status: {s['status']}.\n" + "\n".join(s["blockers"] + s["limitations"])); return 3
        spec = yaml.safe_load(Path(a.script).read_text())
        spec["visual_style"] = {**(spec.get("visual_style") if isinstance(spec.get("visual_style"), dict) else {}), "id": s["scenekit_style"]}
        if a.content_id: spec["content_id"] = a.content_id
        spec["creative_skill"] = {"id": s["id"], "name": s["name"], "status": s["status"], "registry_bundle": reg["bundle"],
                                  "approximation": [f["fallback"] for f in s["fallbacks"]]}
        out = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
        if a.out: Path(a.out).write_text(out); print(f"wrote {a.out}")
        else: print(out)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
