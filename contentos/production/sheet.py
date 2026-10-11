"""Timeline-labelled contact sheet ("sheet/1"): frames of a finished video at the moments that matter, each tile labelled with the
time, scene, spoken word and cue that the timeline says is there, so a reviewer who did not build the video can map what is on
screen to what is being said.

Reads a timeline/1 file (see timeline.py; shadow mode) and an MP4. Local only: ffmpeg/ffprobe, no extra Python dependency, no
network, no renderer. Labels are drawn with ffmpeg's drawtext, which needs a font file; if none is found (or drawtext is missing)
the default is to FAIL rather than silently hand a reviewer an unlabelled sheet. `allow_unlabelled=True` opts into the plain sheet;
the JSON manifest written beside the PNG always carries every label, so the mapping exists as data either way.

Timing caveat carried into the manifest: word times are ASR-derived and unverified (timeline `alignment.timing_trust`), so a tile's
word label means "the word the timeline says is being spoken", not "proved to be audible at this frame"."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from . import preview

SCHEMA = "sheet/1"
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf",
]


class SheetError(RuntimeError):
    pass


def find_font(explicit=None):
    for p in [explicit, os.environ.get("CONTENTOS_SHEET_FONT"), *FONT_CANDIDATES]:
        if p and Path(p).is_file():
            return str(p)
    return None


def pick_times(tl, settle_s=0.15, min_gap_s=0.15):
    """Moments worth looking at: just after each scene starts, just before it ends, and `settle_s` after each cue (so the
    effect the cue triggers has begun). Points closer than `min_gap_s` merge and keep every reason. Returns [(t, [reasons])]."""
    fps = tl.get("fps") or 30
    last = max(tl["duration_s"] - 1.0 / fps, 0.0)
    pts = []
    for sc in tl["scenes"]:
        pts.append((sc["t0"] + 1.0 / fps, "scene-start"))
        pts.append((sc["t1"] - 2.0 / fps, "scene-end"))
    for c in tl["cues"]:
        pts.append((c["t"] + settle_s, "cue " + c["id"]))
    pts = sorted((min(max(round(t, 3), 0.0), last), r) for t, r in pts)
    out = []
    for t, r in pts:
        if out and t - out[-1][0] < min_gap_s:
            out[-1][1].append(r)
        else:
            out.append((t, [r]))
    return out


def describe(tl, t, reasons, settle_s=0.15, max_chars=48):
    """What the timeline says is at time t: scene, the word being spoken (if any), cues that fired within `settle_s` before t."""
    scene = next((s for s in tl["scenes"] if s["t0"] <= t < s["t1"]), tl["scenes"][-1])
    word = next((w for w in tl["words"] if w["t0"] <= t < w["t1"]), None)
    cues = [c for c in tl["cues"] if c["scene"] == scene["id"] and c["t"] <= t <= c["t"] + settle_s + 1e-6]
    l1 = f"{t:6.2f}s  {scene['id']}"
    l2 = f"w{word['i']} {word['text']}" + ("" if word["source"] == "matched" else f" ({word['source']})") if word else "(no word spoken)"
    l3 = (cues[0]["id"] + " " + cues[0].get("do", "")) if cues else ", ".join(reasons)
    full = "\n".join([l1, l2, l3])
    l1, l2, l3 = (x if len(x) <= max_chars else x[:max_chars - 1] + "…" for x in (l1, l2, l3))
    return {"t": round(t, 3), "scene": scene["id"], "why": reasons,
            "word": {"i": word["i"], "text": word["text"], "source": word["source"]} if word else None,
            "cues": [c["id"] for c in cues], "label": "\n".join([l1, l2, l3]), "label_full": full}


def _ffprobe_size(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    try:
        w, h = (int(x) for x in r.stdout.strip().split(",")[:2])
        return w, h
    except ValueError:
        raise SheetError(f"cannot read the video size of {video}: {r.stderr[-200:]}")


def _drawtext_available():
    r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    return " drawtext " in r.stdout


def _label_frame(src, dst, label, font, size):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(label)
        tf = f.name
    try:
        vf = (f"drawtext=fontfile={_esc(font)}:textfile={_esc(tf)}:fontsize={size}:fontcolor=white:"
              f"box=1:boxcolor=black@0.72:boxborderw={max(6, size // 3)}:x={size // 2}:y=h-text_h-{size // 2}:line_spacing={size // 4}")
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, str(dst)], capture_output=True, text=True)
        if r.returncode:
            raise SheetError(f"drawtext failed: {r.stderr[-300:]}")
    finally:
        Path(tf).unlink(missing_ok=True)


def _esc(path):
    """ffmpeg filter-option escaping for a file path (backslash, colon, quote)."""
    return str(path).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def build_sheet(video, tl, out_dir, cols=6, tile_h=360, settle_s=0.15, allow_unlabelled=False, font=None):
    """Writes <out_dir>/sheet.png, sheet.json and the frames. Returns the manifest dict."""
    out_dir = Path(out_dir)
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    width, height = _ffprobe_size(video)
    size = max(16, height // 34)
    max_chars = max(12, int((width - size) / (size * 0.58)))      # a label must fit inside its own frame; the full text stays in the manifest
    tiles = [describe(tl, t, r, settle_s, max_chars) for t, r in pick_times(tl, settle_s)]
    font_path = find_font(font)
    labelled = bool(font_path) and _drawtext_available()
    if not labelled and not allow_unlabelled:
        raise SheetError("cannot draw labels (no font file found or ffmpeg has no drawtext); set CONTENTOS_SHEET_FONT to a .ttf, "
                         "or pass allow_unlabelled=True for a plain sheet (the manifest still carries the labels)")
    raw = preview.video_frames(video, [t["t"] for t in tiles], frames_dir, prefix="raw")
    finals = []
    for k, (src, tile) in enumerate(zip(raw, tiles)):
        tile["frame"] = str(Path("frames") / f"tile_{k:02d}.png")
        dst = out_dir / tile["frame"]
        if labelled:
            _label_frame(src, dst, tile["label"], font_path, size)
        else:
            dst.write_bytes(Path(src).read_bytes())
        finals.append(dst)
    preview.contact_sheet(finals, out_dir / "sheet.png", cols=cols, tile_h=tile_h)
    manifest = {"schema": SCHEMA, "video": str(video), "timeline_job": tl.get("job"), "labelled": labelled, "font": font_path if labelled else None,
                "timing_trust": tl.get("alignment", {}).get("timing_trust"), "settle_s": settle_s, "cols": cols, "tiles": tiles,
                "note": "word labels are what the timeline says is spoken at that time; word times are ASR-derived unless timing_trust says otherwise"}
    (out_dir / "sheet.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Timeline-labelled contact sheet from an MP4 and a timeline/1 file")
    ap.add_argument("video")
    ap.add_argument("timeline")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--tile-h", type=int, default=360)
    ap.add_argument("--settle", type=float, default=0.15)
    ap.add_argument("--allow-unlabelled", action="store_true")
    ap.add_argument("--font")
    a = ap.parse_args(argv)
    tl = json.loads(Path(a.timeline).read_text(encoding="utf-8"))
    try:
        m = build_sheet(a.video, tl, a.out, a.cols, a.tile_h, a.settle, a.allow_unlabelled, a.font)
    except SheetError as e:
        print(f"sheet: {e}")
        return 2
    print(json.dumps({"sheet": str(Path(a.out) / "sheet.png"), "tiles": len(m["tiles"]), "labelled": m["labelled"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
