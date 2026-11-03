"""Measure visual diversity from decoded frames (1 fps, 54x96 thumbnails). Descriptive, not a quality score.

  python scripts/style_diversity.py LABEL=VIDEO [LABEL=VIDEO ...]

Per video:
  content    share of pixels on an edge (|dx|+|dy| of luminance > 0.06) in the 108x192 thumbnail: text, shapes, diagram strokes.
             Smooth gradient grounds do not count. Low = mostly empty frame. Coarse: a thumbnail blurs fine text.
  within     mean pairwise thumbnail distance between frames of the SAME video (how varied the video is from scene to scene)
  luma       mean luminance, 0-1
Across videos (same-script comparisons only make sense when durations match):
  matrix     mean thumbnail distance at aligned normalised times; higher = more different looks
"""
import itertools
import subprocess
import sys

import numpy as np

W, H = 108, 192


def frames(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps=1,scale={W}:{H}:flags=area", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).astype(np.float32) / 255


def stats(fr):
    y = fr @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    cov = [float(((np.abs(np.diff(f, axis=1))[:-1] + np.abs(np.diff(f, axis=0))[:, :-1]) > 0.06).mean()) for f in y]
    d = [float(np.linalg.norm(a - b, axis=2).mean()) for a, b in itertools.combinations(fr, 2)]
    luma = float(y.mean())
    return float(np.mean(cov)), float(np.mean(d)), luma


def aligned(a, b, n=24):
    ia, ib = np.linspace(0, len(a) - 1, n).astype(int), np.linspace(0, len(b) - 1, n).astype(int)
    return float(np.mean([np.linalg.norm(a[i] - b[j], axis=2).mean() for i, j in zip(ia, ib)]))


def main(args):
    vids = {k: frames(v) for k, v in (a.split("=", 1) for a in args)}
    print(f"{'video':28} {'frames':>6} {'content':>8} {'within':>7} {'luma':>6}")
    for k, fr in vids.items():
        c, w, l = stats(fr)
        print(f"{k:28} {len(fr):6d} {c:8.3f} {w:7.3f} {l:6.2f}")
    keys = list(vids)
    print("\ncross-video distance (aligned times)\n" + " " * 28 + "".join(f"{k[:9]:>10}" for k in keys))
    for a in keys:
        print(f"{a:28}" + "".join(f"{aligned(vids[a], vids[b]):10.3f}" for b in keys))


if __name__ == "__main__":
    main(sys.argv[1:])
