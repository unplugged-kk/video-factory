"""Preview frames: look before you render, and look again at the finished MP4.
snapshot()      frames from a HyperFrames project at exact timestamps (headless Chrome; no render needed).
video_frames()  the same timestamps pulled from a finished MP4 with ffmpeg, so the delivered file is what gets inspected.
contact_sheet() one PNG tiling many frames, for reviewing a whole video at a glance.
Local only. --describe false keeps hyperframes from calling Gemini even if GEMINI_API_KEY is set (no external service)."""
import subprocess
from pathlib import Path

from .. import hf


def _run(cmd, cwd=None, timeout=300):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed: {(r.stderr or r.stdout)[-400:]}")
    return r.stdout


def snapshot(project, times, out, cwd=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    _run(hf.command("snapshot", project, "--at", ",".join(f"{t:.2f}" for t in times),
                 "--no-end", "--describe", "false", "-o", out), cwd=cwd)
    return sorted(out.glob("*.png"))


def video_frames(mp4, times, out, prefix="f"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for t in times:
        p = out / f"{prefix}_{t:07.2f}.png"
        _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1", str(p)])
        paths.append(p)
    return paths


def contact_sheet(images, out, cols=6, tile_h=360):
    """Tile images (same aspect) into one PNG. ffmpeg concat + tile filter only, no extra dependency."""
    import tempfile
    rows = -(-len(images) // cols)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for i in images:
            f.write(f"file '{Path(i).resolve()}'\nduration 1\n")
        lst = f.name
    try:
        _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-vf",
              f"scale=-2:{tile_h},tile={cols}x{rows}:padding=6:color=0x222222", "-frames:v", "1", str(out)])
    finally:
        Path(lst).unlink(missing_ok=True)
    return Path(out)
