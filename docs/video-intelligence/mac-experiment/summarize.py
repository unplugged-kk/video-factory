"""Reads one result folder written by run.sh and prints/writes the per-arm verdicts. Standard library only.
Exit 0: every arm rendered and was gated. Exit 1: some arm failed to render or be gated (never reported as success).
It also states whether the hard-cut CONTROL behaved as a control; if it did not, the gate result for the other arms is suspect."""
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
ARMS = ("cut", "css", "shader", "shader-zi", "shader-in", "cut-dark", "css-dark", "shader-in-dark")
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
    ct = j(f"{arm}.gate-caption-text-window.json")
    r["caption_text_visible_in_window"] = (ct or {}).get("visible_ratio") if ct else None
    r["caption_hidden_at"] = (ct or {}).get("hidden_at") if ct else None
    r["layers_ok"] = (ly or {}).get("ok") if ly else None
    gated = all(x is not None for x in (tr, lg, cp, ly, cw, ct)) and bool((ct or {}).get("ok"))
    r["rendered_and_gated"] = r["render_rc"] == 0 and r["output_exists"] and gated
    harness_ok &= r["rendered_and_gated"]
    rows.append(r)

by = {r["arm"]: r for r in rows}
control = by["cut"]["transition"] == "hard_cut" and by["css"]["transition"] == "blend" and by["cut-dark"]["transition"] == "hard_cut" and by["css-dark"]["transition"] == "blend"
notes = []
if not control:
    notes.append("CONTROL INVALID: every cut arm must read hard_cut and every css arm blend; if not, do not trust the shader verdict.")
for arm in ("shader", "shader-zi", "shader-in", "shader-in-dark"):
    sh = by[arm]
    if not sh["rendered_and_gated"]:
        notes.append(f"{arm}: did not render/gate, no verdict")
        continue
    fell_back = bool(set(sh["log_codes"] or []) & {"shader_fallback_opacity_flip", "page_side_compositing_unavailable"})
    verdict = sh["transition"]
    hidden = sh["caption_hidden_at"] or []
    cap = "captions visible in every sample" if not hidden else f"CAPTIONS HIDDEN at t={hidden[0]}..{hidden[-1]} ({len(hidden)} samples)"
    if verdict == "blend" and not fell_back:
        notes.append(f"{arm}: blend, no fallback codes; {cap}")
    else:
        notes.append(f"{arm}: transition verdict {verdict}" + (" (log reports a fallback)" if fell_back else "") + f"; {cap}")
for arm in ("cut", "css", "cut-dark", "css-dark"):
    hidden = by[arm]["caption_hidden_at"] or []
    if hidden:
        notes.append(f"{arm} (control): CAPTIONS HIDDEN at {hidden}; the caption check or the script is wrong, so do not trust the shader rows")
        control = False
passing = [a for a in ("shader", "shader-zi", "shader-in", "shader-in-dark") if by[a]["rendered_and_gated"] and by[a]["transition"] == "blend" and not by[a]["caption_hidden_at"]]
notes.append("shader arms passing blend + caption visibility: " + (", ".join(passing) if passing else "none"))
res = {"folder": str(out), "harness_ok": harness_ok, "control_valid": control, "arms": rows, "notes": notes}
(out / "SUMMARY.json").write_text(json.dumps(res, indent=1))
lines = [f"{'arm':10}{'check':>6}{'render':>7}{'secs':>6}  {'transition':12}{'black':>6}  {'captions':>9}  {'in-win(ink)':>11}  {'text-vis':>8}  {'layers':7} log codes"]
for r in rows:
    lines.append(f"{r['arm']:10}{str(r['check_rc']):>6}{str(r['render_rc']):>7}{str(r['render_seconds']):>6}  {str(r['transition']):12}"
                 f"{str(r['black_fraction']):>6}  {str(r['captions_visible_ratio']):>9}  {str(r['captions_in_transition_window']):>11}  {str(r['caption_text_visible_in_window']):>8}  {str(r['layers_ok']):7} {','.join(r['log_codes'] or [])}")
lines += [""] + notes + ["", f"harness_ok={harness_ok} control_valid={control}"]
(out / "SUMMARY.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(0 if harness_ok else 1)
