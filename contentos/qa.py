"""Deterministic video QA with ffprobe/ffmpeg. Returns list of (check, PASS|FAIL|WARN, detail)."""
import json
import re
import subprocess

from .providers import load


SILENT_LUFS = -60.0   # at or below this the track is treated as silence (fixed constant, not a config threshold)


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_video(path):
    r = _run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    return json.loads(r.stdout) if r.returncode == 0 else None


def run_qa(path, fmt="9:16"):
    cfg = load("quality.yaml")["video"]
    want = cfg["formats"][fmt]
    out = []
    info = probe_video(path)
    if not info:
        return [("render_integrity", "FAIL", "ffprobe cannot read file")]
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if not v:                                  # audio-only / data-only file: clean FAIL, never a TypeError below
        return [("render_integrity", "FAIL", "no video stream")]
    try:
        dur = float(info["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        return [("render_integrity", "FAIL", "no readable duration")]
    out.append(("render_integrity", "PASS", f"{dur:.1f}s"))
    out.append(("resolution", "PASS" if (v["width"], v["height"]) == (want["width"], want["height"]) else "FAIL", f"{v['width']}x{v['height']}"))
    num, den = (int(x) for x in v["r_frame_rate"].split("/"))
    fps = num / den
    out.append(("frame_rate", "PASS" if fps >= cfg["min_fps"] else "FAIL", f"{fps:.1f}fps"))
    out.append(("duration", "PASS" if dur <= want["max_seconds"] else "FAIL", f"{dur:.1f}s <= {want['max_seconds']}s"))
    out.append(("audio_track", "PASS" if a else "FAIL", a["codec_name"] if a else "missing"))
    if a:
        r = _run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"])
        m = re.search(r"I:\s+(-?[\d.]+) LUFS", r.stderr[r.stderr.rfind("Summary"):])
        p = re.search(r"Peak:\s+(-?[\d.]+|-?inf) dBFS", r.stderr[r.stderr.rfind("Summary"):])   # pure silence prints 'Peak: -inf'
        peak = float(p.group(1)) if p else None
        # A silent track (ebur128 floors at about -70 LUFS; peak -inf) is as bad as a missing one: FAIL, not WARN.
        silent = (m is not None and float(m.group(1)) <= SILENT_LUFS) or (peak is not None and peak <= SILENT_LUFS)
        if m:
            lufs = float(m.group(1)); t = cfg["loudness_lufs"]
            if silent:
                out.append(("loudness", "FAIL", f"{lufs} LUFS: audio track is silent"))
            else:   # otherwise loudness stays WARN-only by design
                out.append(("loudness", "PASS" if abs(lufs - t["target"]) <= t["tolerance"] else "WARN", f"{lufs} LUFS (target {t['target']})"))
        if peak is not None:
            out.append(("clipping", "PASS" if peak <= cfg["max_true_peak_db"] else "FAIL", f"peak {peak} dBFS"))
    r = _run(["ffmpeg", "-nostats", "-i", str(path), "-vf", f"blackdetect=d={cfg['max_black_seconds']}:pix_th=0.10", "-an", "-f", "null", "-"])
    blk = re.findall(r"black_duration:([\d.]+)", r.stderr)
    out.append(("black_frames", "FAIL" if blk else "PASS", f"{len(blk)} segments >{cfg['max_black_seconds']}s"))
    r = _run(["ffmpeg", "-nostats", "-i", str(path), "-vf", f"freezedetect=n=-60dB:d={cfg['max_freeze_seconds']}", "-an", "-f", "null", "-"])
    # freezedetect prints freeze_duration only when a freeze ENDS; a freeze that runs to the end of the file only has
    # freeze_start, so count whichever is larger (a mid-file freeze has one of each).
    frz = max(re.findall(r"freeze_duration: ([\d.]+)", r.stderr), re.findall(r"freeze_start: ([\d.]+)", r.stderr), key=len)
    out.append(("frozen_frames", "WARN" if frz else "PASS", f"{len(frz)} segments >{cfg['max_freeze_seconds']}s"))
    return out
