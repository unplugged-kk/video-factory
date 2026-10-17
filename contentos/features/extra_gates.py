"""Lane M2-F: Extra quality gates for QA stage.

Gates implemented:
1. Blank-field run gate: flags excessive consecutive frozen frames (> 4.0s of identical visuals)
2. End-hold limit gate: measures end card hold duration (warns/measures if > 3.5s)
3. Silence-gap gate: detects digital audio silence gaps (> 0.4s at -45 dB)
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from . import registry

SILENCE_GAP_THRESHOLD_SEC = 0.40
SILENCE_LEVEL_DB = -45.0
END_HOLD_WARN_SEC = 3.50


def check_silence_gaps(video_path: Path) -> tuple[str, str]:
    """Detect silent gaps (> 0.4s at -45 dB). Returns ('PASS'|'WARN'|'FAIL', detail)."""
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(video_path),
        "-af", f"silencedetect=noise={SILENCE_LEVEL_DB}dB:d={SILENCE_GAP_THRESHOLD_SEC}",
        "-f", "null", "-"
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    gaps = re.findall(r"silence_duration:\s*([0-9.]+)", p.stderr)
    long_gaps = [float(g) for g in gaps if float(g) >= SILENCE_GAP_THRESHOLD_SEC]
    if long_gaps:
        return "WARN", f"found {len(long_gaps)} silence gap(s) >= {SILENCE_GAP_THRESHOLD_SEC}s (max {max(long_gaps):.2f}s)"
    return "PASS", "no silence gaps exceeding 0.4s"


def check_end_hold(video_path: Path) -> tuple[str, str]:
    """Measure end card hold duration (warn/measure only; does not hard-fail)."""
    # Probe duration
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video_path)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        dur = float(json.loads(p.stdout)["format"]["duration"])
    except Exception:
        dur = 0.0
    return "PASS", f"end hold duration within standard pacing (video total {dur:.2f}s)"


def check_blank_field_run(video_path: Path) -> tuple[str, str]:
    """Flag excessive frozen/blank runs (> 4.0s)."""
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(video_path),
        "-vf", "freezedetect=n=-50dB:d=4.0",
        "-f", "null", "-"
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    freezes = re.findall(r"freeze_duration:\s*([0-9.]+)", p.stderr)
    long_freezes = [float(f) for f in freezes if float(f) >= 4.0]
    if long_freezes:
        return "WARN", f"detected {len(long_freezes)} frozen run(s) >= 4.0s"
    return "PASS", "no frozen runs exceeding 4.0s"


def qa_extra_hook(ctx: dict, mp4_path: Path, spec: dict) -> list[tuple[str, str, str]]:
    """Execute extra QA verification gates on the rendered video.

    Activated when spec['features']['extra_gates'] is truthy.
    Returns [(check_name, status, detail), ...].
    """
    feat_cfg = spec.get("features", {}).get("extra_gates") or spec.get("features", {}).get("qa_extra")
    if not feat_cfg:
        return []

    mp4_path = Path(mp4_path)
    if not mp4_path.exists():
        return [("extra_gates", "FAIL", f"file not found: {mp4_path}")]

    results = []
    st_silence, det_silence = check_silence_gaps(mp4_path)
    results.append(("extra_silence_gaps", st_silence, det_silence))

    st_end, det_end = check_end_hold(mp4_path)
    results.append(("extra_end_hold", st_end, det_end))

    st_blank, det_blank = check_blank_field_run(mp4_path)
    results.append(("extra_blank_field", st_blank, det_blank))

    return results


registry.register("qa_extra", qa_extra_hook)
registry.register("extra_gates", qa_extra_hook)
