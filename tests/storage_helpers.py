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


def approve(job_id, render=None):
    """Make a job exportable the way the factory does: a ledger render attestation for the video.mp4 in place now,
    plus both gates granted and bound to the content that render was made from. Export refuses anything less.
    Writes a one-line spec under <workspace>/test-specs and, if absent, a stub composition for the `render` lane."""
    import yaml
    from contentos import export, ledger, pipeline, storage
    d = storage.find_job_dir(job_id)
    spec = {"content_id": job_id, "title": f"T {job_id}", "script": [{"say": "One thing."}], **({"render": render} if render else {})}
    sp = storage.workspace_root() / "test-specs" / f"{job_id}.yaml"
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(yaml.safe_dump(spec))
    comp = d / pipeline.artifact("compose", spec)
    if not comp.exists():
        comp.parent.mkdir(parents=True, exist_ok=True)
        comp.write_text("<html>test composition</html>")
    subjects = pipeline.render_subjects(d, spec, "pipeline")
    for gate, digest in subjects.items():
        ledger.approve(job_id, gate, by="test", subject_sha256=digest)
    if (d / "video.mp4").is_file():
        ledger.attest_render(job_id, export.sha256_file(d / "video.mp4"), "pipeline", str(sp),
                             subjects["SCRIPT_APPROVED"], subjects["PRODUCTION_APPROVED"])
    return job_id
