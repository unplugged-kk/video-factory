"""Reference-video analysis for a LOCAL file (implements the bundle's reference-video-analyzer where it is verifiable here).

Measures structure only: size, fps, duration, shot changes and pacing, loudness, dominant palette per shot, plus a contact
sheet through the existing preview tool. It does not read text, identify typography, transcribe, or download anything,
and it records those limits in the output. Analysis is of technique, not a licence to reuse the reference's expression.

  python -m contentos.skills analyze-reference VIDEO --out DIR [--threshold 0.3]
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
from pathlib import Path

import numpy as np

from .probe import _which


def _bin(name):
    p = _which(name)
    if not p:
        raise FileNotFoundError(f"{name} not found on PATH")
    return p


def _ff(args, timeout=300):
    return subprocess.run([_bin("ffmpeg"), "-hide_banner", *args], capture_output=True, text=True, timeout=timeout)


def probe(video: Path) -> dict:
    r = subprocess.run([_bin("ffprobe"), "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate,codec_name",
                        "-of", "json", str(video)], capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise ValueError(f"cannot read {video}: {r.stderr.strip()[:200]}")
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if not v:
        raise ValueError("no video stream")
    n, d = map(int, v["r_frame_rate"].split("/"))
    return {"width": v["width"], "height": v["height"], "fps": round(n / d, 3), "duration": float(j["format"]["duration"]),
            "has_audio": any(s["codec_type"] == "audio" for s in j["streams"])}


def shot_changes(video: Path, threshold: float, merge_s: float = 0.6) -> list[float]:
    """Frame-difference shot changes. Hits closer than `merge_s` are one event: a wipe, push or dissolve fires on many frames."""
    r = _ff(["-i", str(video), "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"])
    hits = [float(t) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]
    out: list[float] = []
    for t in hits:
        if not out or t - out[-1] > merge_s:
            out.append(round(t, 3))
    return out


def loudness(video: Path) -> dict | None:
    r = _ff(["-i", str(video), "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"])
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", r.stderr[r.stderr.rfind("Summary"):]) if "Summary" in r.stderr else None
    p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr[r.stderr.rfind("Summary"):]) if "Summary" in r.stderr else None
    return {"integrated_lufs": float(m.group(1)), "true_peak_dbfs": float(p.group(1))} if m else None


def _frame(video: Path, t: float, w=54, h=96) -> np.ndarray:
    r = subprocess.run([_bin("ffmpeg"), "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={w}:{h}:flags=area",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, timeout=60)
    return np.frombuffer(r.stdout, np.uint8).reshape(h, w, 3).astype(np.float32) / 255


def palette(video: Path, t: float) -> dict:
    f = _frame(video, t).reshape(-1, 3)
    q = (f * 4).astype(int).clip(0, 3)                     # 4 levels per channel = 64 bins
    keys, counts = np.unique(q[:, 0] * 16 + q[:, 1] * 4 + q[:, 2], return_counts=True)
    top = keys[np.argsort(-counts)[:3]]
    hexes = ["#%02x%02x%02x" % tuple(int(255 * (c + 0.5) / 4) for c in (k // 16, (k // 4) % 4, k % 4)) for k in top]
    lum = float((f @ np.array([0.2126, 0.7152, 0.0722], np.float32)).mean())
    return {"t": round(t, 2), "dominant": hexes, "luminance": round(lum, 3)}


def analyze(video: Path, out: Path, threshold: float = 0.1) -> dict:
    video, out = Path(video), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    p = probe(video)
    cuts = shot_changes(video, threshold)
    bounds = [0.0, *cuts, p["duration"]]
    shots = [{"index": i + 1, "start": a, "end": b, "length": round(b - a, 3)} for i, (a, b) in enumerate(zip(bounds, bounds[1:])) if b - a > 0.05]
    for s in shots:
        s["palette"] = palette(video, s["start"] + 0.5 * s["length"])
    lens = [s["length"] for s in shots]
    res = {"schema": "reference-analysis/1", "file": video.name, "probe": p, "scene_threshold": threshold, "cuts": cuts, "shots": shots,
           "pacing": {"shot_count": len(shots), "cuts_per_minute": round(len(cuts) / p["duration"] * 60, 2),
                      "median_shot_s": round(statistics.median(lens), 2), "min_shot_s": min(lens), "max_shot_s": max(lens)},
           "audio": loudness(video) if p["has_audio"] else None,
           "limits": ["structure only: no OCR, no typography or font identification, no transcript, no speaker/face analysis",
                      "cut detection is a frame-difference threshold (default 0.1, hits within 0.6 s merged). Measured on 3 scenekit renders with 5 known cuts each: recall 5/5 with 1 extra detection per video; at the old 0.3 default it found 0-3 of 5. Very similar adjacent scenes can still be missed. Check the contact sheet",
                      "output describes technique; do not reproduce the reference's exact frames, script, characters or shot order",
                      "source URL analysis is not available here (yt-dlp binary is broken); this analyzed a local file only"]}
    from ..production import preview
    times = [round(s["start"] + 0.5 * s["length"], 2) for s in shots][:12]
    try:
        frames = preview.video_frames(video, times, out)
        res["contact_sheet"] = str(preview.contact_sheet(frames, out / "contact-sheet.png", cols=6))
    except Exception as e:                                   # the sheet is a convenience; measurements stand without it
        res["contact_sheet_error"] = f"{type(e).__name__}: {e}"
    (out / "reference-analysis.json").write_text(json.dumps(res, indent=2))
    return res
