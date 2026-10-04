"""MoneyPrinterTurbo render lane. contentos keeps the script, the voice, the gates and QA; MPT only
sources free stock footage, cuts it to OUR voice track and burns subtitles. Driven through MPT's CLI
inside its container, because the HTTP API cannot take a voice track from outside its own task dir."""
import json
import re
import shutil
import subprocess
import tomllib
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MPT_DIR = ROOT / "vendor/MoneyPrinterTurbo"
PROJECTS = ROOT / "workspace/projects"   # mounted read-only at /workspace/projects in the container
CONTAINER = "moneyprinterturbo-api"
# The only sources contentos will pass. MPT has more (wavespeed, seedance, ofox, ...) that bill per call.
LICENSE = {
    "pexels": ("Pexels License", "https://www.pexels.com/license/"),
    "pixabay": ("Pixabay Content License", "https://pixabay.com/service/license-summary/"),
    "coverr": ("Coverr License", "https://coverr.co/license"),
    "local": ("user-supplied, rights not verified by contentos", ""),
}
KEY = {"pexels": "pexels_api_keys", "pixabay": "pixabay_api_keys", "coverr": "coverr_api_keys"}
# Bold face, thick outline, 70% from the top: the Shorts UI covers the bottom ~20%.
STYLE = ["--font-name=BeVietnamPro-Bold.ttf", "--font-size=78", "--stroke-width=4",
         "--subtitle-position=custom", "--custom-position=70"]


class Unavailable(Exception):
    """The lane cannot run (stack down, key missing, bad spec). The pipeline reports it as BLOCKED."""


def request(spec):
    """Pure: spec -> everything MPT needs. Raises Unavailable for anything contentos refuses to run."""
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
        base = PROJECTS.resolve()
        for p in m.get("materials") or []:
            f = (ROOT / p).resolve()
            if not f.is_relative_to(base):
                raise Unavailable(f"local material {p} must live under workspace/projects/ (all the container can see)")
            if not f.is_file():
                raise Unavailable(f"local material not found: {p}")
            materials.append(f"/workspace/projects/{f.relative_to(base).as_posix()}")
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
    """One voice track + a reviewable request. Nothing leaves the Mac yet (that happens at the render gate)."""
    d, spec = ctx["dir"], ctx["spec"]
    req = request(spec)
    key = KEY.get(req["source"])
    if key:
        try:
            have = tomllib.loads((MPT_DIR / "config.toml").read_text()).get("app", {}).get(key)
        except FileNotFoundError:
            raise Unavailable("vendor/MoneyPrinterTurbo/config.toml missing: copy config.example.toml")
        if not have:
            raise Unavailable(f"{key} is empty in vendor/MoneyPrinterTurbo/config.toml (free key), or set mpt.source: local")
    wavs = [d / "audio" / f"{i:02d}.wav" for i in range(1, len(spec["script"]) + 1)]
    if not all(w.exists() for w in wavs):
        raise Unavailable("voice stage has not produced every line yet")
    lst, full = d / "audio/list.txt", d / "audio/full.wav"
    lst.write_text("".join(f"file '{w.name}'\n" for w in wavs))  # relative to list.txt: no path escaping
    _run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(full)])
    out = d / "project/mpt-request.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({**req, "audio": f"/workspace/projects/{ctx['id']}/audio/full.wav"}, indent=2))
    return [full, out]  # the sentinel is written last


def render(ctx):
    d = ctx["dir"]
    req = json.loads((d / "project/mpt-request.json").read_text())
    try:  # a container started from another checkout still answers HTTP (doctor passes) but sees the wrong workspace
        _run(["docker", "exec", CONTAINER, "test", "-f", req["audio"]])
    except RuntimeError:
        raise Unavailable(f"MPT container cannot see {req['audio']}: it was started from another folder. "
                          f"docker compose up -d from {ROOT}")
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
                                  "materials": res.get("materials")}, indent=2))
    return [video, rights]
