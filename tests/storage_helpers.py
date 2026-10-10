"""Shared helpers for the storage tests: tiny real videos made with ffmpeg (never committed; built in tmp dirs)."""
import subprocess
from pathlib import Path


def make_video(path, *, w=1080, h=1920, seconds=2, audio=True, black=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    src = "color=c=black:size={w}x{h}" if black else "testsrc2=size={w}x{h}"
    src = src.format(w=w, h=h)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"{src}:rate=30:duration={seconds}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-af", "volume=0.4", "-c:a", "aac"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(path)]
    subprocess.run(cmd, check=True)
    return path
