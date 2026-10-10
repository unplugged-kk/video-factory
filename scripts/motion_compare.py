#!/usr/bin/env python
"""Reproducible A/B harness for motion-design changes on a COPY of a finished explainer project.

Why: a skill or rule is only worth adopting if the same video gets measurably better. This copies a project (script,
narration, audio, assets and plan stay byte-identical), applies a named variant to the builder copy only, rebuilds,
renders both with the same renderer, and reports counted metrics (motion_audit) plus frames for human review.
The source project is never written to.

  python scripts/motion_compare.py prepare  <src_project> <exp_dir>
  python scripts/motion_compare.py build    <exp_dir>
  python scripts/motion_compare.py render   <exp_dir>
  python scripts/motion_compare.py measure  <exp_dir>
  python scripts/motion_compare.py frames   <exp_dir> [--at 1.5 5 9 ...]
  python scripts/motion_compare.py report   <exp_dir>

Run with ~/.contentos/venv/bin/python from anywhere. `prepare` refuses to overwrite an existing experiment."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from contentos import hf  # noqa: E402
from contentos.production import motion_audit as ma, preview  # noqa: E402

VARIANTS = ("control", "variant-b")
FORMATS = {"landscape": (1920, 1080), "portrait": (1080, 1920)}
COPY_IGNORE = ("renders", "delivery", "preview", "qa", "logs", "landscape", "portrait", ".DS_Store", "__pycache__")
REPO_LINE = "REPO = Path(__file__).resolve().parents[4]"

# Variant B = rules ported from the audit into the existing HyperFrames builder (no new framework, no new dependency).
OLD_CAMERA = '''    for k, sid in enumerate(("hook", "goal-tools", "request", "run", "result", "loop", "cta")):
        s0, s1, xm, ym = G["cam"][k]
        t0, t1 = b[sid]["t0"], b[sid]["t1"]
        add(f'tl.fromTo("#stage",{{scale:{s0},x:{xm * 0},y:0}},{{scale:{s1},x:{xm},y:{ym},duration:{t1 - t0:.2f},ease:"sine.inOut"}},{t0:.2f});')
'''
NEW_CAMERA = '''    for k, sid in enumerate(("hook", "goal-tools", "request", "run", "result", "loop", "cta")):
        s0, s1, xm, ym = G["cam"][k]
        t0, t1 = b[sid]["t0"], b[sid]["t1"]
        # move once (<=0.9 s) from wherever the last scene ended, then HOLD: no snap at the cut, no drift in the back half
        add(f'tl.to("#stage",{{scale:{s1},x:{xm},y:{ym},duration:{min(0.9, t1 - t0):.2f},ease:"power2.inOut"}},{t0:.2f});')
'''


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(cmd, cwd, log: Path, check=True):
    log.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    with log.open("w") as f:
        r = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    if check and r.returncode:
        raise SystemExit(f"FAILED ({r.returncode}): {' '.join(map(str, cmd))}  see {log}")
    return r.returncode, round(time.time() - t, 2)


def apply_variant_b(builder: Path) -> list[str]:
    t = builder.read_text()
    notes = []
    t2, n = re.subn(r'back\.out\([^)]*\)', 'power3.out', t)
    if n == 0:
        raise SystemExit("variant-b: expected back.out easings in the builder; source changed, update the patch")
    notes.append(f"smooth settle: {n} back.out -> power3.out")
    if OLD_CAMERA not in t2:
        raise SystemExit("variant-b: camera block not found; source changed, update the patch")
    t2 = t2.replace(OLD_CAMERA, NEW_CAMERA)
    notes.append("camera: continuous, single <=0.9 s move per scene then hold")
    builder.write_text(t2)
    return notes


def cmd_prepare(a):
    src, out = Path(a.src).resolve(), Path(a.exp).resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} exists and is not empty; choose a new experiment directory")
    out.mkdir(parents=True, exist_ok=True)
    before = {p.relative_to(src).as_posix(): sha(p) for p in sorted(src.rglob("*")) if p.is_file() and p.name != ".DS_Store"}
    (out / "SOURCE-TREE-SHA256.before.json").write_text(json.dumps(before, indent=0))
    meta = {"source": str(src), "variants": {}}
    for v in VARIANTS:
        shutil.copytree(src, out / v, ignore=shutil.ignore_patterns(*COPY_IGNORE))
        b = out / v / "src/build_pilot.py"
        txt = b.read_text()
        if REPO_LINE not in txt:
            raise SystemExit("builder REPO line not found")
        b.write_text(txt.replace(REPO_LINE, f"REPO = Path({str(REPO)!r})"))
        meta["variants"][v] = apply_variant_b(b) if v == "variant-b" else ["unchanged existing workflow"]
    (out / "experiment.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


def cmd_build(a):
    for v in VARIANTS:
        d = Path(a.exp) / v
        rc, s = run([sys.executable, str(d / "src/build_pilot.py"), str(d)], REPO, d / "logs/build.log")
        print(f"built {v} in {s}s")


def cmd_render(a):
    out = {}
    for v in VARIANTS:
        d = Path(a.exp).resolve() / v
        for fmt in FORMATS:
            mp4 = d / "renders" / f"{v}-{fmt}.mp4"
            mp4.parent.mkdir(exist_ok=True)
            rc, s = run(hf.command("render", "-o", mp4), d / fmt, d / f"logs/render-{fmt}.log")
            out[f"{v}/{fmt}"] = {"render_seconds": s, "bytes": mp4.stat().st_size}
            print(v, fmt, out[f"{v}/{fmt}"], flush=True)
    (Path(a.exp) / "render-times.json").write_text(json.dumps(out, indent=1))


def ffprobe(mp4: Path) -> dict:
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(mp4)],
                                  capture_output=True, text=True, check=True).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    return {"duration_s": round(float(j["format"]["duration"]), 3), "width": v["width"], "height": v["height"], "codec": v["codec_name"],
            "fps": v["r_frame_rate"], "bytes": int(j["format"]["size"])}


def cmd_measure(a):
    exp = Path(a.exp).resolve()
    times = json.loads((exp / "render-times.json").read_text())
    res = {"identical_inputs": {}, "runs": {}}
    for rel in ("audio/mix.wav", "captions/word-timings.json", "script/narration.txt", "src/scene-plan.json"):
        res["identical_inputs"][rel] = len({sha(exp / v / rel) for v in VARIANTS}) == 1
    for v in VARIANTS:
        for fmt in FORMATS:
            d = exp / v
            mp4 = d / "renders" / f"{v}-{fmt}.mp4"
            r = ffprobe(mp4)
            r["render_seconds"] = times[f"{v}/{fmt}"]["render_seconds"]
            r["ease"] = ma.ease_inventory((d / fmt / "index.html").read_text())
            ydif, fps = ma.video_ydif(mp4)
            r["motion"] = ma.motion_stats(ydif, fps)
            for name in ("lint", "check"):
                rc, _ = run(hf.command(name), d / fmt, d / f"logs/{name}-{fmt}.log", check=False)
                r[name] = {"exit": rc, "tail": (d / f"logs/{name}-{fmt}.log").read_text().strip().splitlines()[-3:]}
            res["runs"][f"{v}/{fmt}"] = r
            print("measured", v, fmt, flush=True)
    (exp / "results.json").write_text(json.dumps(res, indent=1))


def cmd_frames(a):
    exp = Path(a.exp).resolve()
    at = a.at or [1.5, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45]
    for fmt in FORMATS:
        for v in VARIANTS:
            imgs = preview.video_frames(str(exp / v / "renders" / f"{v}-{fmt}.mp4"), at, str(exp / "frames" / f"{v}-{fmt}"), f"{v}-{fmt}")
            preview.contact_sheet(imgs, str(exp / "frames" / f"sheet-{v}-{fmt}.png"), cols=4 if fmt == "landscape" else 6, tile_h=270 if fmt == "landscape" else 400)
    print("frames ->", exp / "frames")


def cmd_report(a):
    exp = Path(a.exp).resolve()
    res = json.loads((exp / "results.json").read_text())
    lines = ["| format | metric | control | variant-b |", "|---|---|---|---|"]
    for fmt in FORMATS:
        c, b = res["runs"][f"control/{fmt}"], res["runs"][f"variant-b/{fmt}"]
        rows = [("render s", c["render_seconds"], b["render_seconds"]), ("size MB", round(c["bytes"] / 1e6, 2), round(b["bytes"] / 1e6, 2)),
                ("duration s", c["duration_s"], b["duration_s"]), ("easings", c["ease"]["total"], b["ease"]["total"]),
                ("overshoot easings", c["ease"]["overshoot"], b["ease"]["overshoot"]),
                ("still fraction", c["motion"]["still_fraction"], b["motion"]["still_fraction"]),
                ("longest still s", c["motion"]["longest_still_s"], b["motion"]["longest_still_s"]),
                ("mean frame change", c["motion"]["mean"], b["motion"]["mean"]), ("pops", c["motion"]["pop_count"], b["motion"]["pop_count"]),
                ("lint exit", c["lint"]["exit"], b["lint"]["exit"]), ("check exit", c["check"]["exit"], b["check"]["exit"])]
        lines += [f"| {fmt} | {m} | {x} | {y} |" for m, x, y in rows]
    text = "\n".join(lines) + "\n\nidentical inputs: " + json.dumps(res["identical_inputs"]) + "\n"
    (exp / "report.md").write_text(text)
    print(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prepare"); p.add_argument("src"); p.add_argument("exp"); p.set_defaults(f=cmd_prepare)
    for n, f in (("build", cmd_build), ("render", cmd_render), ("measure", cmd_measure), ("report", cmd_report)):
        p = sp.add_parser(n); p.add_argument("exp"); p.set_defaults(f=f)
    p = sp.add_parser("frames"); p.add_argument("exp"); p.add_argument("--at", nargs="*", type=float); p.set_defaults(f=cmd_frames)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
