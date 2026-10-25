"""assets/1: an index of local media, so a job can find cutaway material by what it shows.

  python -m contentos.production.assets index DIR --out INDEX.json [--frames DIR] [--samples N] [--notes NOTES.json]
  python -m contentos.production.assets search INDEX.json QUERY [--limit N]
  python -m contentos.production.assets verify INDEX.json

`index` ffprobes every video, image and audio file under DIR, samples N frames per clip, and writes the index. A
description is never invented here: without `--notes` it also writes `<index>.notes.json` for a human or an agent
to fill in from the sampled frames, and a clip that has not been filled in stays `described: false`. Re-running
`index` with `--notes` merges what was written. `search` ranks clips by term overlap over that text and the path —
no embeddings, no network — and reports no hit rather than a guess (exit 1). `verify` re-checks the index against
the disk: exit 0 clean, 1 problems, 2 unreadable. Both the index and the frames must be written outside this repo,
like every other generated artifact."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ..qa import probe_video

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "assets/1"
VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".heic", ".tif", ".tiff", ".bmp")
AUDIO_EXT = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg")
NOTE_FIELDS = ("description", "tags", "license", "source")


def kind_for(path: Path) -> str | None:
    """video, image or audio from the extension; None when the file is neither (it is then not indexed)."""
    ext = Path(path).suffix.lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in IMAGE_EXT:
        return "image"
    if ext in AUDIO_EXT:
        return "audio"
    return None


def _fps(stream: dict | None) -> float | None:
    try:
        num, _, den = (stream or {})["r_frame_rate"].partition("/")
        return round(int(num) / int(den or 1), 3)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def facts(path: Path) -> dict:
    """What ffprobe says about the file. `readable: false` when it cannot be read; nothing is guessed."""
    info = probe_video(path)
    if not info:
        return {"readable": False}
    streams = info.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    try:
        duration = float((info.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        duration = None
    return {"readable": True, "duration_s": duration, "width": (video or {}).get("width"),
            "height": (video or {}).get("height"), "fps": _fps(video),
            "has_audio": any(s.get("codec_type") == "audio" for s in streams)}


def sample_frames(path: Path, kind: str, duration_s: float | None, out_dir: Path, n: int) -> list[dict]:
    """N frames spread through a video, so the notes are written from what is actually on screen."""
    if kind != "video" or n <= 0 or not duration_s:
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for i in range(n):
        t = duration_s * (i + 1) / (n + 1)
        dest = out_dir / f"{path.stem}_{i:02d}_{t:07.2f}.png"
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                            str(dest)], capture_output=True, text=True)
        if r.returncode == 0 and dest.exists():
            frames.append({"t": round(t, 2), "file": str(dest)})
    return frames


def index_dir(root: Path, frames_dir: Path, samples: int = 3) -> dict:
    """Walk root and index every media file. Descriptions stay empty until notes say otherwise."""
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    clips = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        kind = kind_for(p)
        if not kind:
            continue
        clip = {"path": str(p), "kind": kind, "size_bytes": p.stat().st_size, "description": "", "tags": [],
                "license": "unknown", "source": None, "described": False}
        clip.update(facts(p))
        clip["samples"] = sample_frames(p, kind, clip.get("duration_s"), Path(frames_dir), samples)
        clips.append(clip)
    return {"schema": SCHEMA, "root": str(root), "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "clips": clips}


def notes_skeleton(idx: dict) -> dict:
    """The fill-in form: one entry per clip, every note field empty."""
    return {c["path"]: {k: ([] if k == "tags" else "") for k in NOTE_FIELDS} for c in idx.get("clips", [])}


def merge_notes(idx: dict, notes: dict) -> dict:
    """Apply written notes. A clip is `described` only when its description is non-empty; unknown paths are reported."""
    for c in idx.get("clips", []):
        n = notes.get(c["path"]) or {}
        for k in NOTE_FIELDS:
            if k in n and n[k] not in (None, ""):
                c[k] = n[k]
        c["described"] = bool((c.get("description") or "").strip())
    missing = sorted(set(notes) - {c["path"] for c in idx.get("clips", [])})
    idx["notes_missing_from_index"] = missing
    return idx


def search(idx: dict, query: str, limit: int = 5) -> list[dict]:
    """Rank clips by whole-word overlap: tags weigh most, then the description, then the file path. A term matches a
    word, never a fragment, so a short word cannot score by sitting inside an unrelated path. Nothing is inferred."""
    terms = [t for t in re.split(r"[^0-9a-z]+", query.lower()) if t]
    if not terms:
        raise ValueError("empty query")
    hits = []
    for c in idx.get("clips", []):
        tags = " ".join(str(t).lower() for t in c.get("tags") or [])
        haystacks = (("tag", tags, 3), ("text", (c.get("description") or "").lower(), 2), ("path", c["path"].lower(), 1))
        score, why = 0, set()
        for term in terms:
            for label, text, weight in haystacks:
                if re.search(rf"\b{re.escape(term)}\b", text):
                    score += weight
                    why.add(f"{label}:{term}")
        if score:
            hits.append({"path": c["path"], "kind": c.get("kind"), "score": score, "why": sorted(why),
                         "described": c.get("described", False), "duration_s": c.get("duration_s"),
                         "samples": c.get("samples", [])})
    hits.sort(key=lambda h: (-h["score"], h["path"]))
    return hits[:limit]


def verify(idx: dict) -> list[str]:
    """Problems that make the index untrustworthy: wrong schema, a clip or frame gone from disk, a false `described`."""
    errs = []
    if not isinstance(idx, dict) or idx.get("schema") != SCHEMA:
        return [f"schema must be {SCHEMA!r}"]
    for i, c in enumerate(idx.get("clips") or []):
        if not isinstance(c, dict) or not c.get("path"):
            errs.append(f"clips[{i}] needs a path")
            continue
        if not Path(c["path"]).exists():
            errs.append(f"missing on disk: {c['path']}")
        if c.get("described") and not (c.get("description") or "").strip():
            errs.append(f"described without a description: {c['path']}")
        for s in c.get("samples") or []:
            if not Path(s.get("file", "")).exists():
                errs.append(f"missing sample frame: {s.get('file')}")
    return errs


def write_index(idx: dict, path: Path) -> Path:
    """Atomic write outside the repo. Re-indexing overwrites on purpose; an index is a cache, not a job artifact."""
    path = Path(path).expanduser().resolve()
    _check_outside_repo(path, "the index")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(idx, f, indent=2)
    os.replace(tmp, path)
    return path


def _check_outside_repo(path: Path, what: str) -> None:
    """Checked before anything is written, so a refused run leaves no frames behind either."""
    path = Path(path).expanduser().resolve()
    if path == ROOT or ROOT in path.parents:
        raise ValueError(f"{what} must be written outside the repository (use $VIDEO_FACTORY_WORKSPACE)")


def _load_index(path) -> dict:
    return json.loads(Path(path).read_text())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m contentos.production.assets", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ix = sub.add_parser("index", help="index a media folder (never writes a description of its own)")
    ix.add_argument("dir")
    ix.add_argument("--out", required=True, help="index path, outside the repo")
    ix.add_argument("--frames", help="where to write sampled frames (default: next to the index)")
    ix.add_argument("--samples", type=int, default=3, help="frames per video")
    ix.add_argument("--notes", help="notes file to merge; without it a fill-in skeleton is written next to the index")
    se = sub.add_parser("search", help="rank clips against a plain-English query (exit 1 when nothing matches)")
    se.add_argument("index")
    se.add_argument("query")
    se.add_argument("--limit", type=int, default=5)
    vf = sub.add_parser("verify", help="re-check an index against the disk")
    vf.add_argument("index")
    a = ap.parse_args(argv)

    if a.cmd == "search":
        try:
            idx = _load_index(a.index)
        except (OSError, ValueError) as e:
            print(f"cannot read index: {e}", file=sys.stderr)
            return 2
        hits = search(idx, a.query, a.limit)
        print(json.dumps({"query": a.query, "hits": hits}, indent=2))
        return 0 if hits else 1

    if a.cmd == "verify":
        try:
            idx = _load_index(a.index)
        except (OSError, ValueError) as e:
            print(f"cannot read index: {e}", file=sys.stderr)
            return 2
        errs = verify(idx)
        print(json.dumps({"ok": not errs, "problems": errs}, indent=2))
        return 1 if errs else 0

    out = Path(a.out)
    try:
        frames = Path(a.frames) if a.frames else out.parent / f"frames-{Path(a.dir).name}"
        _check_outside_repo(out, "the index")
        _check_outside_repo(frames, "the sampled frames")
        idx = index_dir(a.dir, frames, a.samples)
        notes_path = None
        if a.notes:
            idx = merge_notes(idx, _load_index(a.notes))
        write_index(idx, out)
        if not a.notes:
            notes_path = write_index(notes_skeleton(idx), out.with_suffix(".notes.json"))
    except (OSError, ValueError) as e:
        print(e, file=sys.stderr)
        return 2
    undescribed = sum(1 for c in idx["clips"] if not c.get("described"))
    print(json.dumps({"index": str(out.resolve()), "notes": str(notes_path) if notes_path else a.notes,
                      "clips": len(idx["clips"]), "undescribed": undescribed,
                      "unreadable": [c["path"] for c in idx["clips"] if not c.get("readable")]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
