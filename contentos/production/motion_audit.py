"""Objective, reproducible motion metrics for comparing two builds of the SAME video (same script, narration, assets).

Nothing here judges taste. It reports what can be counted so a change to an animation rule or a skill can be
compared before and after: which easings a composition uses, how much of a render is visually still, and where a
single frame jumps (a camera or element pop). Subjective quality (does it look better?) stays a human call and is
reported separately by the caller.

Pure functions plus one ffmpeg wrapper (`video_ydif`); the wrapper needs ffmpeg, the rest does not."""
from __future__ import annotations

import re
import statistics
import subprocess
from pathlib import Path

_EASE = re.compile(r"""\bease\s*:\s*["']([^"']+)["']""")
_OVERSHOOT = re.compile(r"^(back|elastic|bounce)\b")
_YDIF = re.compile(r"lavfi\.signalstats\.YDIF=([0-9.eE+-]+)")


def ease_inventory(html: str) -> dict:
    """Count GSAP easings in a generated composition. `overshoot` = back/elastic/bounce (the 'bouncy' family)."""
    eases = _EASE.findall(html)
    by: dict[str, int] = {}
    for e in eases:
        by[e] = by.get(e, 0) + 1
    return {
        "total": len(eases),
        "by_ease": dict(sorted(by.items())),
        "overshoot": sum(n for e, n in by.items() if _OVERSHOOT.match(e)),
        "repeat_infinite": len(re.findall(r"\brepeat\s*:\s*-1\b", html)),
        "yoyo": len(re.findall(r"\byoyo\s*:\s*true\b", html)),
    }


def parse_ydif(text: str) -> list[float]:
    """Per-frame mean absolute luma difference from ffmpeg `signalstats` metadata output."""
    return [float(m) for m in _YDIF.findall(text)]


def motion_stats(ydif: list[float], fps: float, still_eps: float = 0.05, pop_factor: float = 4.0, pop_floor: float = 1.0) -> dict:
    """Summarise a per-frame difference series.

    still_fraction     share of frames whose change is below `still_eps` (nothing visibly moves)
    longest_still_s    longest run of such frames, in seconds
    pops               isolated one-frame jumps: value >= pop_floor and >= pop_factor x the larger neighbour.
                       A smooth move is a plateau and is not a pop; a snap or hard cut is. Hard cuts are counted
                       too, so compare two builds of the same edit rather than reading the absolute number.
    """
    n = len(ydif)
    if n == 0:
        return {"frames": 0}
    still = [v < still_eps for v in ydif]
    longest = run = 0
    for s in still:
        run = run + 1 if s else 0
        longest = max(longest, run)
    pops = []
    for i, v in enumerate(ydif):
        nb = max(ydif[i - 1] if i > 0 else 0.0, ydif[i + 1] if i + 1 < n else 0.0)
        if v >= pop_floor and v >= pop_factor * max(nb, 1e-6):
            pops.append(round(i / fps, 3))
    ordered = sorted(ydif)
    return {
        "frames": n,
        "mean": round(statistics.fmean(ydif), 4),
        "p95": round(ordered[min(n - 1, int(0.95 * n))], 4),
        "max": round(ordered[-1], 4),
        "still_fraction": round(sum(still) / n, 4),
        "longest_still_s": round(longest / fps, 3),
        "pops": pops,
        "pop_count": len(pops),
    }


def video_ydif(mp4: str | Path, width: int = 320) -> tuple[list[float], float]:
    """Run ffmpeg signalstats on a downscaled copy; returns (per-frame YDIF, fps)."""
    mp4 = str(mp4)
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                            "-of", "csv=p=0", mp4], capture_output=True, text=True, check=True).stdout.strip()
    a, _, b = probe.partition("/")
    fps = float(a) / float(b or 1)
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vf",
                          f"scale={width}:-2,signalstats,metadata=mode=print:key=lavfi.signalstats.YDIF:file=-",
                          "-an", "-f", "null", "-"], capture_output=True, text=True, check=True)
    return parse_ydif(out.stdout), fps


def compare(a: dict, b: dict, keys: list[str]) -> list[dict]:
    """Row-per-metric comparison of two flat metric dicts (control a, variant b)."""
    rows = []
    for k in keys:
        va, vb = a.get(k), b.get(k)
        delta = round(vb - va, 4) if isinstance(va, (int, float)) and isinstance(vb, (int, float)) else None
        rows.append({"metric": k, "control": va, "variant": vb, "delta": delta})
    return rows
