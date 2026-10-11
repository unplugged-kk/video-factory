"""Reads one result folder written by run.sh and prints/writes the per-arm verdicts. Standard library only.
Exit 0: every arm rendered and was gated. Exit 1: some arm failed to render or be gated (never reported as success).
It also states whether the hard-cut CONTROL behaved as a control; if it did not, the gate result for the other arms is suspect."""
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
ARMS = ("cut", "css", "shader")
EXPECT = {"cut": "hard_cut", "css": "blend"}          # shader: no expectation, that is the question


def j(name):
    p = out / name
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def rc(arm, key):
    p = out / f"{arm}.{key}.rc"
    try:
        return int(p.read_text().strip())
    except (OSError, ValueError):
        return None


rows, harness_ok = [], True
for arm in ARMS:
    r = {"arm": arm, "check_rc": rc(arm, "check"), "render_rc": rc(arm, "render"), "render_seconds": rc(arm, "seconds"),
         "output_exists": (out / f"{arm}.mp4").is_file()}
    tr, lg, cp, ly = j(f"{arm}.gate-transition.json"), j(f"{arm}.gate-log.json"), j(f"{arm}.gate-captions.json"), j(f"{arm}.gate-layers.json")
    r["transition"] = (tr or {}).get("transitions", [{}])[0].get("verdict") if tr else None
    r["black_fraction"] = (tr or {}).get("transitions", [{}])[0].get("black_fraction") if tr else None
    r["log_codes"] = sorted({f["code"] for f in (lg or {}).get("findings", [])}) if lg is not None else None
    r["captions_visible_ratio"] = (cp or {}).get("visible_ratio") if cp else None
    r["captions_ok"] = (cp or {}).get("ok") if cp else None
    cw = j(f"{arm}.gate-captions-window.json")
    r["captions_in_transition_window"] = (cw or {}).get("visible_ratio") if cw else None
    r["layers_ok"] = (ly or {}).get("ok") if ly else None
    gated = all(x is not None for x in (tr, lg, cp, ly, cw))
    r["rendered_and_gated"] = r["render_rc"] == 0 and r["output_exists"] and gated
    harness_ok &= r["rendered_and_gated"]
    rows.append(r)

by = {r["arm"]: r for r in rows}
control = by["cut"]["transition"] == "hard_cut" and by["css"]["transition"] == "blend"
notes = []
if not control:
    notes.append("CONTROL INVALID: the cut arm must read hard_cut and the css arm blend; if not, do not trust the shader verdict.")
sh = by["shader"]
if sh["rendered_and_gated"]:
    fell_back = bool(set(sh["log_codes"] or []) & {"shader_fallback_opacity_flip", "page_side_compositing_unavailable"})
    verdict = sh["transition"]
    if verdict == "blend":
        notes.append("shader arm reads blend but the log reports a fallback: inspect the frames" if fell_back
                     else "shader arm: blend, no black frames, no fallback codes in the log")
    else:
        notes.append({"hard_cut": "shader arm: HARD CUT (silent fallback)", "black": "shader arm: BLACK frames",
                      "inconclusive": "shader arm: inconclusive (endpoints too similar to judge)"}.get(verdict, "shader arm: unrecognised verdict")
                     + (" (log reports a fallback)" if fell_back else ""))
else:
    notes.append("shader arm did not render/gate: no shader verdict")
for r in rows:
    q = r["captions_in_transition_window"]
    if q is not None and q < 0.9:
        notes.append(f"{r['arm']} arm: CAPTIONS HIDDEN during the transition window (visible in {q:.0%} of samples; the captions are continuous by construction). "
                     "The caption ink check can be fooled by bright transition effects, so also look at the frames.")
res = {"folder": str(out), "harness_ok": harness_ok, "control_valid": control, "arms": rows, "notes": notes}
(out / "SUMMARY.json").write_text(json.dumps(res, indent=1))
lines = [f"{'arm':7}{'check':>6}{'render':>7}{'secs':>6}  {'transition':12}{'black':>6}  {'captions':>9}  {'in-window':>9}  {'layers':7} log codes"]
for r in rows:
    lines.append(f"{r['arm']:7}{str(r['check_rc']):>6}{str(r['render_rc']):>7}{str(r['render_seconds']):>6}  {str(r['transition']):12}"
                 f"{str(r['black_fraction']):>6}  {str(r['captions_visible_ratio']):>9}  {str(r['captions_in_transition_window']):>9}  {str(r['layers_ok']):7} {','.join(r['log_codes'] or [])}")
lines += [""] + notes + ["", f"harness_ok={harness_ok} control_valid={control}"]
(out / "SUMMARY.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(0 if harness_ok else 1)
