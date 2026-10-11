"""Dense caption-visibility check for a transition window, immune to bright transition effects.

The gate's `captions` check counts text-like ink in the caption region, so a bright iris blob can be mistaken for captions.
This one counts DARK pixels that have LIGHT pixels close on both sides of the same row: the signature of dark glyph strokes on
the light caption plate (#FAF9F5). A bright blob, a dark scene background or a plate edge has light on one side only.

  python caption_window.py <video.mp4> <start> <duration> [--pad 0.15] [--step 0.05] [--region x,y,w,h] [--polarity dark-on-light|light-on-dark] > out.json

Reference scores are measured on the same video at 2.0 s (caption 1) and 9.0 s (caption 2); a sample is "visible" when its score
is at least 40% of the smaller reference. Standard library + ffmpeg only. Exit 0 always for a readable video (the verdict is in the
JSON); exit 2 if frames cannot be read. Thresholds are provisional, calibrated on this experiment only."""
import argparse
import json
import subprocess
import sys

DARK, LIGHT, REACH, MIN_FRACTION = 90, 225, 60, 0.4
POLARITIES = ("dark-on-light", "light-on-dark")


def gray_crop(video, t, region):
    x, y, w, h = region
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
           "-vf", f"crop={w}:{h}:{x}:{y},format=gray", "-f", "rawvideo", "-"]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0 or len(p.stdout) != w * h:
        return None
    return p.stdout


def plate_text_score(buf, w, h, polarity="dark-on-light"):
    """dark-on-light: dark glyph pixels flanked by light plate pixels. light-on-dark: the mirror, for a dark plate."""
    light = LIGHT
    if polarity == "light-on-dark":
        buf = bytes(255 - v for v in buf)
        light = 190                       # a dark plate (#2b2a27, luma ~42) inverts to ~213; the glyphs invert to <= 30
    score = 0
    for r in range(h):
        row = buf[r * w:(r + 1) * w]
        pref = [0] * (w + 1)
        for i, v in enumerate(row):
            pref[i + 1] = pref[i] + (1 if v >= light else 0)
        for i, v in enumerate(row):
            if v <= DARK:
                lo, hi = max(0, i - REACH), min(w, i + REACH + 1)
                if pref[i] - pref[lo] > 0 and pref[hi] - pref[i + 1] > 0:
                    score += 1
    return score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("start", type=float)
    ap.add_argument("duration", type=float)
    ap.add_argument("--pad", type=float, default=0.15)
    ap.add_argument("--step", type=float, default=0.05)
    ap.add_argument("--region", default="70,1374,870,214")
    ap.add_argument("--polarity", default="dark-on-light", choices=POLARITIES)
    a = ap.parse_args()
    region = tuple(int(v) for v in a.region.split(","))
    w, h = region[2], region[3]
    refs = {}
    for name, t in (("caption1", 2.0), ("caption2", 9.0)):
        b = gray_crop(a.video, t, region)
        if b is None:
            print(json.dumps({"ok": False, "error": f"cannot read reference frame at {t}s"}))
            return 2
        refs[name] = plate_text_score(b, w, h, a.polarity)
    floor = MIN_FRACTION * min(refs.values())
    n = int(round((a.duration + 2 * a.pad) / a.step))
    samples = []
    for i in range(n + 1):
        t = round(a.start - a.pad + i * a.step, 3)
        b = gray_crop(a.video, t, region)
        if b is None:
            print(json.dumps({"ok": False, "error": f"cannot read frame at {t}s"}))
            return 2
        s = plate_text_score(b, w, h, a.polarity)
        samples.append({"t": t, "score": s, "visible": s >= floor})
    hidden = [s["t"] for s in samples if not s["visible"]]
    res = {"ok": True, "references": refs, "floor": round(floor, 1), "window": [a.start - a.pad, a.start + a.duration + a.pad],
           "samples": samples, "visible_ratio": round(1 - len(hidden) / len(samples), 3), "hidden_at": hidden,
           "all_visible": not hidden, "polarity": a.polarity, "region": list(region),
           "limits": "counts dark glyph-like pixels flanked by light plate pixels; a caption plate with no text, or text on a dark plate, would read hidden"}
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
