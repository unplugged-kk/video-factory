"""Final-video validation before anything is exported (reuses contentos.qa; adds the file-level checks).

validate_video() never raises for a bad video: it returns {"status": "passed"|"failed", "checks": [...]}. A video passes
only when no check FAILs. If ffprobe/ffmpeg are missing the result is "failed" (an unvalidated video is never exported).
WARN results (for example frozen frames on a text slide) do not fail a video; they are recorded in the sidecar."""
from __future__ import annotations

from pathlib import Path

from . import qa, storage


def _row(check, status, detail):
    return {"check": check, "status": status, "detail": str(detail)}


def validate_video(path, fmt="9:16", *, require_audio=True):
    path = Path(path)
    checks = []
    result = {"status": "failed", "checked_at": storage.now_iso(), "checks": checks,
              "duration_seconds": None, "width": None, "height": None}
    if not path.is_file():
        checks.append(_row("file_exists", "FAIL", "final video is missing"))
        return result
    size = path.stat().st_size
    checks.append(_row("file_exists", "PASS", f"{size} bytes"))
    if size <= 0:
        checks.append(_row("file_non_empty", "FAIL", "file is empty"))
        return result
    try:
        with open(path, "rb") as f:
            f.read(1024)
    except OSError as exc:
        checks.append(_row("file_readable", "FAIL", exc))
        return result
    checks.append(_row("file_readable", "PASS", ""))
    try:
        info = qa.probe_video(path)
        rows = qa.run_qa(path, fmt)
    except (OSError, KeyError, ValueError) as exc:           # no ffprobe/ffmpeg, or a format the QA config does not know
        checks.append(_row("tooling", "FAIL", f"cannot validate: {exc}"))
        return result
    for check, status, detail in rows:
        if check == "audio_track" and status == "FAIL" and not require_audio:
            status, detail = "WARN", f"{detail} (audio not required for this job)"
        checks.append(_row(check, status, detail))
    if info:
        v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        if v:
            result["width"], result["height"] = v.get("width"), v.get("height")
        try:
            result["duration_seconds"] = round(float(info["format"]["duration"]), 2)
        except (KeyError, TypeError, ValueError):
            pass
        if not result["duration_seconds"] or result["duration_seconds"] <= 0:
            checks.append(_row("duration_positive", "FAIL", "duration is not positive"))
    result["status"] = "failed" if any(c["status"] == "FAIL" for c in checks) else "passed"
    return result


def summary(result):
    """Small form for a sidecar: status and per-check results without details that could hold paths."""
    return {"status": result["status"], "checked_at": result["checked_at"],
            "checks": [{"check": c["check"], "status": c["status"]} for c in result["checks"]]}
