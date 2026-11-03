"""Contact sheet at each scene's 75% point, read from the job's composed index.html (no guessing times).
  python scripts/scene_sheet.py JOB_DIR OUT_DIR [fraction]
"""
import re
import subprocess
import sys
from pathlib import Path

job, out = Path(sys.argv[1]), Path(sys.argv[2])
frac = float(sys.argv[3]) if len(sys.argv) > 3 else 0.75
html = (job / "project/index.html").read_text()
ts = [float(s) + frac * float(d) for s, d in re.findall(r'class="scene clip[^"]*" id="s\d+"[^>]*? data-start="([\d.]+)" data-duration="([\d.]+)"', html)]
subprocess.run([str(Path(__file__).resolve().parent.parent / "contentos.sh"), "preview", str(job / "video.mp4"), "--at",
                ",".join(f"{t:.2f}" for t in ts), "--out", str(out), "--sheet", "--cols", "6"], check=True)
