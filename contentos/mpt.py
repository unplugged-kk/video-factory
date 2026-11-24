"""MoneyPrinterTurbo cuts reviewed local footage to our voice track and burns subtitles."""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import uuid
from pathlib import Path

from . import storage

ROOT = Path(__file__).resolve().parent.parent
MPT_DIR = ROOT / "vendor/MoneyPrinterTurbo"
CONTAINER_PROJECTS = "/workspace/projects"   # the workspace jobs/ folder, mounted read-only here in the container


def projects_root():
    return storage.jobs_root()
CONTAINER = "moneyprinterturbo-api"
# The only sources contentos will pass. MPT has more (wavespeed, seedance, ofox, ...) that bill per call.
LICENSE = {
    "pexels": ("Pexels License", "https://www.pexels.com/license/"),
    "pixabay": ("Pixabay Content License", "https://pixabay.com/service/license-summary/"),
    "coverr": ("Coverr License", "https://coverr.co/license"),
    "local": ("user-supplied, rights not verified by contentos", ""),
}
STAGED = "mpt-assets"
NARRATION = f"{STAGED}/narration.wav"
SHA = re.compile(r"[a-f0-9]{64}")
CLIP_SUFFIX = re.compile(r"\.[a-z0-9]{1,8}")
# Bold face, thick outline, 70% from the top: the Shorts UI covers the bottom ~20%.
STYLE = ["--font-name=BeVietnamPro-Bold.ttf", "--font-size=78", "--stroke-width=4",
         "--subtitle-position=custom", "--custom-position=70"]


class Unavailable(Exception):
    """The lane cannot run (stack down, key missing, bad spec). The pipeline reports it as BLOCKED."""


def _relative(path):
    rel = Path(path)
    if not rel.parts or rel.is_absolute() or ".." in rel.parts or rel.as_posix() != path:
        raise ValueError("expected a canonical relative path")
    return rel


def _open_input(root, relative):
    """Open a regular file beneath the jobs root without following any input symlink."""
    dirs = os.O_DIRECTORY | os.O_NOFOLLOW | os.O_RDONLY
    parent = os.open(root, dirs)
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, dirs, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        stream = os.fdopen(fd, "rb")
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            stream.close()
            raise ValueError("not a regular file")
        return stream
    finally:
        os.close(parent)


def request(spec, *, check_files=True):
    """Normalize the MPT spec; only compose needs access to the original files."""
    m = spec.get("mpt") or {}
    source = m.get("source", "pexels")
    if source not in LICENSE:
        raise Unavailable(f"mpt.source '{source}' not allowed, use one of {sorted(LICENSE)} (the rest bill per call)")
    lines = spec["script"]
    # MPT splits subtitles at commas; a lone opening word ("First, the script") becomes a 0.2 s flash.
    text = re.sub(r"(^|[.!?]\s+)(\w+),\s", r"\1\2 ", " ".join(ln["say"] for ln in lines))
    terms = m.get("terms") or [t for ln in lines if (t := ln.get("broll") or ln.get("headline"))] or spec.get("tags", [])
    materials = []
    if source == "local":
        configured = projects_root().absolute()
        base = configured.resolve()
        for p in m.get("materials") or []:
            try:
                # Resolve the workspace alias, but never follow a link within jobs/.
                supplied = ROOT / p
                relative = supplied.relative_to(configured if supplied.is_relative_to(configured) else base)
                relative = _relative(relative.as_posix())
                if check_files:
                    with _open_input(base, relative):
                        pass
            except (OSError, TypeError, ValueError) as exc:
                raise Unavailable(f"local material must be a regular file under workspace jobs/ without links: {p}") from exc
            materials.append(f"{CONTAINER_PROJECTS}/{relative.as_posix()}")
        if not materials:
            raise Unavailable("mpt.source=local needs mpt.materials")
    elif not terms:
        raise Unavailable("no b-roll search terms: add `broll:` to script lines or set mpt.terms")
    return {"script": text, "terms": [t.replace(",", " ") for t in terms], "source": source, "materials": materials,
            "aspect": spec.get("format", "9:16"), "clip_seconds": m.get("clip_seconds", 3)}


def cmd(req, task_id):
    """Pure: request -> argv. `--opt=value` form so text starting with '-' is never read as a flag."""
    c = ["docker", "exec", CONTAINER, "python", "cli.py", f"--task-id={task_id}", f"--video-script={req['script']}",
         f"--video-source={req['source']}", f"--custom-audio-file={req['audio']}", f"--video-aspect={req['aspect']}",
         "--bgm-type=none",  # MPT's bundled tracks have no verified licence
         "--subtitle-enabled", "--match-materials-to-script", f"--video-clip-duration={req['clip_seconds']}", *STYLE]
    if req["terms"]:
        c.append(f"--video-terms={','.join(req['terms'])}")
    if req["materials"]:
        c.append(f"--video-materials={','.join(req['materials'])}")
    return c


def _run(argv, timeout=1500):
    r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        err = (r.stderr.strip() or r.stdout.strip())[-400:]
        if "No such container" in err or "is not running" in err:
            raise Unavailable(f"MPT container '{CONTAINER}' is not running: docker compose up -d (video-factory root)")
        raise RuntimeError(f"{' '.join(argv)[:100]} -> {err}")
    return r.stdout


def compose(ctx):
    """Stage the exact local inputs before writing the reviewable request."""
    d, spec = ctx["dir"], ctx["spec"]
    req = request(spec)
    if req["source"] != "local":
        raise Unavailable("MPT stock must be obtained before approval: use mpt.source: local with staged source clips")
    root = projects_root().resolve()
    out = d / "project/mpt-request.json"
    stage = out.parent / STAGED
    for directory in (out.parent, stage):
        if directory.is_symlink():
            raise Unavailable("MPT staging directory cannot be a symlink")
        directory.mkdir(exist_ok=True)
    wavs = [d / "audio" / f"{i:02d}.wav" for i in range(1, len(spec["script"]) + 1)]
    if not all(w.is_file() for w in wavs):
        raise Unavailable("voice stage has not produced every line yet")
    lst = d / "audio/list.txt"
    lst.write_text("".join(f"file '{w.name}'\n" for w in wavs))
    entries = []
    with tempfile.TemporaryDirectory(prefix=".mpt-", dir=out.parent) as temp:
        work = Path(temp)
        for source in req.pop("materials"):
            origin = source.removeprefix(f"{CONTAINER_PROJECTS}/")
            relative = _relative(origin)
            suffix = relative.suffix.lower()
            if not CLIP_SUFFIX.fullmatch(suffix):
                raise Unavailable(f"MPT material needs a supported filename extension: {origin}")
            candidate = work / "clip"
            try:
                with _open_input(root, relative) as src, candidate.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                with candidate.open("rb") as src:
                    sha = hashlib.file_digest(src, "sha256").hexdigest()
            except (OSError, ValueError) as exc:
                raise Unavailable(f"could not stage MPT material: {origin}") from exc
            path = f"{STAGED}/{sha}{suffix}"
            candidate.replace(out.parent / path)
            entries.append({"path": path, "sha256": sha, "origin": origin, "license": LICENSE["local"][0]})
        full = work / "narration.wav"
        _run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(full)])
        with full.open("rb") as src:
            audio_sha = hashlib.file_digest(src, "sha256").hexdigest()
        full.replace(out.parent / NARRATION)
        manifest = work / out.name
        manifest.write_text(json.dumps({**req, "dependencies": entries, "audio_sha256": audio_sha}, sort_keys=True, indent=2))
        manifest.replace(out)  # sentinel is published last
    return [out.parent / NARRATION, out]


def reviewed_request(d, spec):
    """Resolve only reviewed project-relative inputs, both for approval and for Docker argv."""
    root = projects_root().resolve()
    try:
        d = Path(d).absolute()
        base = projects_root().absolute()
        job = d.relative_to(base if d.is_relative_to(base) else root)
        project = _relative((job / "project").as_posix())
        with _open_input(root, project / "mpt-request.json") as src:
            req = json.load(src)
        entries = req.pop("dependencies")
        audio_sha = req.pop("audio_sha256")
        expected = request(spec, check_files=False)
        origins = expected.pop("materials")
        if (req != expected or expected["source"] != "local" or not SHA.fullmatch(audio_sha)
                or not isinstance(entries, list) or len(entries) != len(origins)):
            raise ValueError("staged request does not match the current local specification")
        mounted = {}

        def check(path, expected_sha):
            relative = project / _relative(path)
            with _open_input(root, relative) as src:
                sha = hashlib.file_digest(src, "sha256").hexdigest()
            if sha != expected_sha:
                raise ValueError("staged material hash mismatch")
            container_path = f"{CONTAINER_PROJECTS}/{relative.as_posix()}"
            if "," in container_path:
                raise ValueError("MPT cannot encode commas in material paths")
            mounted[container_path] = sha
            return container_path

        audio = check(NARRATION, audio_sha)
        materials = []
        for entry, source in zip(entries, origins, strict=True):
            path, sha = entry["path"], entry["sha256"]
            origin = _relative(entry["origin"])
            suffix = origin.suffix.lower()
            if (source != f"{CONTAINER_PROJECTS}/{origin.as_posix()}"
                    or not SHA.fullmatch(sha) or not CLIP_SUFFIX.fullmatch(suffix)
                    or path != f"{STAGED}/{sha}{suffix}" or entry["license"] != LICENSE["local"][0]):
                raise ValueError("invalid dependency record")
            materials.append(check(path, sha))
        return {**req, "dependencies": entries, "materials": materials, "audio": audio}, mounted
    except (AttributeError, OSError, KeyError, TypeError, ValueError) as exc:
        raise Unavailable("MPT inputs are missing or do not match the staged request; re-run compose and review") from exc


def render(ctx):
    d = ctx["dir"]
    req, mounted = reviewed_request(d, ctx["spec"])
    # The container can see a different workspace at the same path. Check bytes, not existence.
    verify = ("import hashlib, sys\n"
              "for path, expected in zip(sys.argv[1::2], sys.argv[2::2]):\n"
              " with open(path, 'rb') as f:\n"
              "  h = hashlib.sha256()\n"
              "  for block in iter(lambda: f.read(1048576), b''): h.update(block)\n"
              "  if h.hexdigest() != expected: sys.exit('mounted dependency differs')\n")
    try:
        _run(["docker", "exec", CONTAINER, "python", "-c", verify, *(x for pair in mounted.items() for x in pair)])
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        raise Unavailable("MPT container mount does not match the reviewed inputs") from exc
    tid = str(uuid.uuid4())
    res = json.loads(_run(cmd(req, tid)).strip().splitlines()[-1])["result"]
    if not res.get("videos"):
        raise RuntimeError(f"MPT returned no video (warnings: {res.get('warnings')})")
    src = MPT_DIR / Path(res["videos"][0]).relative_to("/MoneyPrinterTurbo")
    if not src.is_file():
        raise RuntimeError(f"MPT reported {res['videos'][0]} but {src} is missing")
    video, rights = d / "video.mp4", d / "assets-rights.json"
    shutil.copy(src, video)
    name, url = LICENSE[req["source"]]
    rights.write_text(json.dumps({"lane": "mpt", "task_id": tid, "source": req["source"], "license": name, "terms": url,
                                  "dependencies": req["dependencies"]}, indent=2))
    return [video, rights]
