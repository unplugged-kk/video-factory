"""style-checkpoint/1: advisory style-frame / storyboard checkpoint record.

Records human review of 3-8 frames (or 1 frame for lite mode) before full video
generation. Pure record and verification: does not generate frames, does not
block video rendering or stages, and does not touch approval gates.

  python -m contentos.production.checkpoint request --job J --style S --frame F1 ... --shot S1 ... --out FILE [--lite]
  python -m contentos.production.checkpoint verify FILE
  python -m contentos.production.checkpoint decide FILE --decision approved --by NAME --human [--note TEXT]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

from contentos.intelligence import styles

SCHEMA = "style-checkpoint/1"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_DECISIONS = {"approved", "redirect", "rejected"}
_JOB = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def request(job: str, style: str, frames: list[str], shot_list: list[str], out: str | Path, mode: str = "full") -> dict:
    if not isinstance(job, str) or not _JOB.match(job):
        raise ValueError(f"job {job!r} must match [A-Za-z0-9][A-Za-z0-9._-]{{0,127}}")
    if mode not in ("full", "lite"):
        raise ValueError(f"mode {mode!r} must be 'full' or 'lite'")
    if not isinstance(frames, (list, tuple)) or not frames:
        raise ValueError("frames must be a non-empty list of paths")
    if mode == "full" and not (3 <= len(frames) <= 8):
        raise ValueError(f"full mode requires 3-8 frames, got {len(frames)}")
    if mode == "lite" and len(frames) != 1:
        raise ValueError(f"lite mode requires exactly 1 frame, got {len(frames)}")
    for f in frames:
        p = Path(f)
        if not p.is_file():
            raise ValueError(f"frame file not found or not regular file: {f}")
        if p.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"frame {f} has extension {p.suffix!r}; allowed: {sorted(ALLOWED_EXTENSIONS)}")
    if not isinstance(shot_list, (list, tuple)) or not shot_list:
        raise ValueError("shot_list must be a non-empty list of strings")
    if not all(isinstance(s, str) and s.strip() for s in shot_list):
        raise ValueError("each shot in shot_list must be a non-empty string")
    if mode == "full" and len(shot_list) < 3:
        raise ValueError(f"full mode requires at least 3 shot descriptions, got {len(shot_list)}")

    cards, _ = styles.load_all()
    valid_styles = {c["id"] for c in cards}
    cat_dir = styles.STYLES_DIR / "catalog"
    if cat_dir.is_dir():
        try:
            cat_cards, _ = styles.load_all(cat_dir)
            valid_styles.update(c["id"] for c in cat_cards)
        except Exception:
            pass
    if style not in valid_styles:
        raise ValueError(f"unknown style {style!r}; valid: {sorted(valid_styles)}")

    out_path = Path(out)
    if out_path.exists():
        raise ValueError(f"refusing to overwrite existing file: {out_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    frame_entries = [{"path": str(f), "sha256": _sha256_file(f)} for f in frames]
    rec = {
        "schema": SCHEMA,
        "job": job,
        "style": style,
        "mode": mode,
        "frames": frame_entries,
        "shot_list": [s.strip() for s in shot_list],
        "status": "pending",
        "decision": None,
        "advisory": True,
    }
    out_path.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec


def verify(path: Path | str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise OSError(f"checkpoint file not found: {p}")
    rec = json.loads(p.read_text(encoding="utf-8"))
    if rec.get("schema") != SCHEMA:
        raise ValueError(f"schema is {rec.get('schema')!r}, expected {SCHEMA!r}")

    changed, missing = [], []
    for entry in rec.get("frames", []):
        fpath = Path(entry["path"])
        if not fpath.is_file():
            missing.append(entry["path"])
        elif _sha256_file(fpath) != entry.get("sha256"):
            changed.append(entry["path"])
    return {"stale": bool(changed or missing), "changed": changed, "missing": missing}


def decide(path: Path | str, decision: str, by: str, human: bool, note: str = "", at: str | None = None) -> dict:
    if not human:
        raise ValueError("human review confirmation required (--human flag)")
    if not isinstance(by, str) or not by.strip():
        raise ValueError("by must be a non-empty string naming the human reviewer")
    decision = decision.strip().lower()
    if decision not in ALLOWED_DECISIONS:
        raise ValueError(f"decision {decision!r} not in {sorted(ALLOWED_DECISIONS)}")
    p = Path(path)
    if not p.is_file():
        raise OSError(f"checkpoint file not found: {p}")
    rec = json.loads(p.read_text(encoding="utf-8"))
    if rec.get("schema") != SCHEMA:
        raise ValueError(f"schema is {rec.get('schema')!r}, expected {SCHEMA!r}")
    if rec.get("status") != "pending":
        raise ValueError(f"cannot decide checkpoint with status {rec.get('status')!r}; must be 'pending'")
    if decision in ("redirect", "rejected") and len(note.strip()) < 8:
        raise ValueError(f"note of >= 8 characters required for decision {decision!r}")

    v = verify(path)
    if v["stale"]:
        raise ValueError(f"checkpoint is stale (frames missing or modified); re-request checkpoint before deciding: {v}")

    rec["status"] = decision
    rec["decision"] = {
        "by": by.strip(),
        "at": at or datetime.date.today().isoformat(),
        "note": note.strip(),
    }
    p.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp_req = sub.add_parser("request", help="Request style-frame checkpoint")
    sp_req.add_argument("--job", required=True, help="Job identifier")
    sp_req.add_argument("--style", required=True, help="Style card ID")
    sp_req.add_argument("--frame", dest="frames", action="append", required=True, help="Frame path (repeat 3-8 or 1 for lite)")
    sp_req.add_argument("--shot", dest="shot_list", action="append", required=True, help="Shot description (repeat >= 3 or >= 1 for lite)")
    sp_req.add_argument("--out", required=True, help="Destination JSON file")
    sp_req.add_argument("--lite", action="store_true", help="Lite mode (1 frame)")

    sp_ver = sub.add_parser("verify", help="Verify checkpoint frame integrity")
    sp_ver.add_argument("path", help="Path to checkpoint JSON")

    sp_dec = sub.add_parser("decide", help="Record human review decision")
    sp_dec.add_argument("path", help="Path to checkpoint JSON")
    sp_dec.add_argument("--decision", required=True, choices=["approved", "redirect", "rejected"])
    sp_dec.add_argument("--by", required=True, help="Reviewer name")
    sp_dec.add_argument("--human", action="store_true", help="Speed-bump confirmation")
    sp_dec.add_argument("--note", default="", help="Review note")
    sp_dec.add_argument("--at", default=None, help="Decision date (YYYY-MM-DD)")

    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code != 0 else 0

    try:
        if a.cmd == "request":
            mode = "lite" if a.lite else "full"
            request(a.job, a.style, a.frames, a.shot_list, a.out, mode=mode)
            print(f"wrote {a.out}")
            return 0
        if a.cmd == "verify":
            res = verify(a.path)
            print(json.dumps(res, indent=1))
            return 1 if res["stale"] else 0
        if a.cmd == "decide":
            rec = decide(a.path, a.decision, a.by, a.human, note=a.note, at=a.at)
            print(f"checkpoint {a.path} decided: {rec['status']}")
            return 0
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
