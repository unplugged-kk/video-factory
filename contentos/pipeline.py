"""Artifact-first pipeline. Every stage writes a durable file under <workspace>/jobs/YYYY/MM/<content_id>/
(the workspace is outside the repository; see contentos/storage.py) and one ledger row. Re-running skips stages whose artifact already exists (resume)."""
import html
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import yaml

from . import export as exporter
from . import hf, ledger, mpt, providers, storage
from .production import align
from .qa import probe_video, run_qa

ROOT = Path(__file__).resolve().parent.parent
SKILLS = [ROOT / "vendor/youtube-agent-skill/skills", Path("~/.claude/skills").expanduser()]
ENV = {**os.environ, "HYPERFRAMES_PYTHON": str(providers.VENV_PY)}
STAGES = ["brief", "script", "voice", "compose", "render", "qa", "package", "export", "publish"]


class Blocked(Exception):
    """A gate or missing prerequisite stopped the run. Not a crash."""


def skill_tool(skill, script):
    for base in SKILLS:
        p = base / skill / script
        if p.exists():
            return p
    raise Blocked(f"skill tool {skill}/{script} not installed")


SH_TIMEOUT = float(os.environ.get("CONTENTOS_SH_TIMEOUT", 600))        # a hung tool must not hold the lane forever
RENDER_TIMEOUT = float(os.environ.get("CONTENTOS_RENDER_TIMEOUT", 1800))


def _kill_tree(pid):
    """SIGKILL a process and everything under it (npx -> node -> Chrome); killing only the direct child leaves the rest running."""
    out = subprocess.run(["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True).stdout
    kids = {}
    for line in out.splitlines():
        child, parent = map(int, line.split())
        kids.setdefault(parent, []).append(child)
    order, stack = [], [pid]
    while stack:
        p = stack.pop()
        order.append(p)
        stack.extend(kids.get(p, []))
    for p in reversed(order):
        try:
            os.kill(p, signal.SIGKILL)
        except ProcessLookupError:
            pass


def sh(cmd, cwd=None, timeout=None):
    limit = timeout or SH_TIMEOUT
    p = subprocess.Popen(cmd, cwd=cwd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        _kill_tree(p.pid)
        p.communicate()
        raise RuntimeError(f"{' '.join(map(str, cmd))[:120]} -> timed out after {limit:.0f}s")
    if p.returncode:
        raise RuntimeError(f"{' '.join(map(str, cmd))[:120]} -> {err.strip()[-400:] or out.strip()[-400:]}")
    return out


def dur(path):
    return float(probe_video(path)["format"]["duration"])


# ---- stages: each returns (provider, [artifacts]) ------------------------------------------

def s_brief(ctx):
    p = ctx["dir"] / "content.json"
    p.write_text(json.dumps({**ctx["spec"], "content_id": ctx["id"], "status": "briefed"}, indent=2))
    return "local", [p]


def s_script(ctx):
    lines = ctx["spec"]["script"]
    md = ctx["dir"] / "script.md"
    md.write_text(f"# {ctx['spec']['title']}\n\n" + "\n\n".join(f"## Line {i+1}\n{ln['say']}" for i, ln in enumerate(lines)))
    lint = ctx["dir"] / "script-lint.json"
    out = sh(["python3", str(skill_tool("yt-script", "hookscore.py")), "--hook", lines[0]["say"], "--json"])
    lint.write_text(out)
    return "yt-script/hookscore", [md, lint]


def s_voice(ctx):
    prim, _ = providers.select("tts", ctx["allow_paid"])
    if not prim:
        raise Blocked("no healthy TTS provider (run: contentos doctor)")
    if prim["id"] != "kokoro_local":
        raise Blocked(f"TTS provider {prim['id']} selected but has no adapter yet")
    vd = ctx["dir"] / "audio"
    vd.mkdir(exist_ok=True)
    voice = ctx["spec"].get("voice", "af_heart")
    outs = []
    for i, ln in enumerate(ctx["spec"]["script"], 1):
        wav = vd / f"{i:02d}.wav"
        if not wav.exists():
            raw = vd / f"{i:02d}.raw.wav"
            sh(hf.command("tts", ln.get("tts", ln["say"]), "-v", voice, "-o", raw))
            sh(["ffmpeg", "-y", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "24000", str(wav)])
            raw.unlink()
        outs.append(wav)
    return prim["id"], outs


def words_for(wav, workdir):
    """Word timings from whisper.cpp (via hyperframes). Falls back to even spacing if ASR is unavailable."""
    workdir.mkdir(exist_ok=True)
    try:
        sh(hf.command("transcribe", wav, "--json", "-d", workdir))
        return [(w["text"], w["start"], w["end"]) for w in json.loads((workdir / "transcript.json").read_text())]
    except Exception:
        return None


def caption_words(toks, asr, d):
    """Caption timings for one script line: the SCRIPT words (their spelling is what the caption shows), timed by
    aligning them to the ASR words. asr is [(text,start,end)] from words_for, or None; without it the words are
    spaced evenly over the take. Sequence alignment keeps an ASR insertion/deletion from shifting every later word."""
    if asr:
        wl, _ = align.align_words(toks, [{"text": w, "start": s, "end": e} for w, s, e in asr])
        return wl
    step = (d - 0.35) / len(toks)
    return [(w, k * step, (k + 1) * step) for k, w in enumerate(toks)]


def _mpt(fn, ctx):
    try:
        return "mpt", fn(ctx)
    except mpt.Unavailable as e:
        raise Blocked(str(e))


def s_compose(ctx):
    if ctx["spec"].get("render") == "mpt":
        return _mpt(mpt.compose, ctx)
    spec, W, H = ctx["spec"], *map(int, ctx["res"])
    U = min(W, H)                                    # type scales with the short side, so 16:9 is not set in 1920-wide type
    proj = ctx["dir"] / "project"
    (proj / "assets/voice").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "contentos/templates/gsap.min.js", proj / "gsap.min.js")
    t, scenes, audios, anim = 0.0, [], [], []
    for i, ln in enumerate(spec["script"], 1):
        wav = ctx["dir"] / "audio" / f"{i:02d}.wav"
        shutil.copy(wav, proj / f"assets/voice/{i:02d}.wav")
        d = round(dur(wav) + 0.35, 2)
        asr = words_for(wav, ctx["dir"] / "audio" / f"tx{i:02d}")
        toks = ln["say"].split()                      # captions show the SCRIPT words; ASR supplies timing only
        wl = caption_words(toks, asr, d)
        cap = "".join(f'<span id="w{i}_{k}">{html.escape(w)}</span> ' for k, (w, _, _) in enumerate(wl))
        for k, (_, ws, we) in enumerate(wl):
            anim.append(f'tl.set("#w{i}_{k}",{{color:"#fbbf24"}},{t+ws:.2f});tl.set("#w{i}_{k}",{{color:"#fff"}},{t+we:.2f});')
        scenes.append(f'<div class="scene clip" id="s{i}" data-start="{t:.2f}" data-duration="{d}">'
                      f'<div class="head"><div class="tag">{html.escape(ln.get("tag", f"{i}/{len(spec['script'])}"))}</div>'
                      f'<h1 id="h{i}">{html.escape(ln["headline"])}</h1></div><p class="cap">{cap}</p></div>')
        audios.append(f'<audio id="a{i}" src="./assets/voice/{i:02d}.wav" data-start="{t:.2f}" data-duration="{d}" class="clip"></audio>')
        anim.append(f'tl.fromTo("#s{i}",{{opacity:0}},{{opacity:1,duration:.3}},{t:.2f});'
                    f'tl.fromTo("#h{i}",{{y:60,opacity:0}},{{y:0,opacity:1,duration:.5,ease:"power3.out"}},{t+.1:.2f});'
                    f'tl.to("#s{i}",{{opacity:0,duration:.25}},{t+d-.25:.2f});')
        t += d
    total = round(t, 2)
    (proj / "hyperframes.json").write_text(json.dumps({"width": W, "height": H, "fps": 30, "duration": total}))
    (proj / "index.html").write_text(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{html.escape(spec['title'])}</title>
<script src="./gsap.min.js"></script>
<style>*{{margin:0;box-sizing:border-box}}body{{width:{W}px;height:{H}px;overflow:hidden;background:#090a0f;font-family:-apple-system,"Helvetica Neue",sans-serif;color:#fff}}
#root{{position:relative;width:{W}px;height:{H}px;background:radial-gradient(circle at 50% 20%,#1a1e36,#08090e)}}
.scene{{position:absolute;inset:0;display:grid;grid-template-rows:minmax(0,1fr) auto;row-gap:40px;padding:120px 70px {int(H*0.16)}px;text-align:center;opacity:0}}
.head{{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:0}}
.tag{{font:700 34px ui-monospace,Menlo,monospace;letter-spacing:3px;color:#a5b4fc;margin-bottom:36px}}
h1{{font-size:{int(U*0.085)}px;font-weight:900;line-height:1.1;letter-spacing:-1px}}
.cap{{font-size:{int(U*0.058)}px;font-weight:800;line-height:1.25;color:#fff;text-shadow:0 4px 18px rgba(0,0,0,.7)}}.cap span{{display:inline-block;color:#fff}}</style></head>
<body><div id="root" data-composition-id="root" data-width="{W}" data-height="{H}" data-duration="{total}">
{''.join(scenes)}{''.join(audios)}</div>
<script>const tl=gsap.timeline({{paused:true}});{''.join(anim)}
window.__timelines=window.__timelines||{{}};window.__timelines["root"]=tl;</script></body></html>""")
    sh(hf.command("lint"), cwd=proj)
    return "hyperframes", [proj / "index.html", proj / "hyperframes.json"]


def s_render(ctx):
    if ctx["spec"].get("render") == "mpt":
        return _mpt(mpt.render, ctx)
    mp4 = ctx["dir"] / "video.mp4"
    cmd = hf.command("render", "-o", mp4)
    hf_q = ctx["spec"].get("_v1_hyperframes_quality")
    if isinstance(hf_q, str) and hf_q.strip():
        cmd.extend(["-q", hf_q.strip()])
    sh(cmd, cwd=ctx["dir"] / "project", timeout=RENDER_TIMEOUT)
    return "hyperframes", [mp4]


def s_qa(ctx):
    res = run_qa(ctx["dir"] / "video.mp4", ctx["spec"].get("format", "9:16"))
    p = ctx["dir"] / "qa.json"
    p.write_text(json.dumps([{"check": c, "status": s, "detail": d} for c, s, d in res], indent=2))
    fails = [c for c, s, _ in res if s == "FAIL"]
    if fails:
        raise RuntimeError(f"QA failed: {fails}")
    return "ffmpeg", [p]


def s_package(ctx):
    spec = ctx["spec"]
    lint = sh(["python3", str(skill_tool("yt-package", "title.py")), "--title", spec["title"], "--thumb", spec.get("thumb_text", ""), "--json"])
    meta = ctx["dir"] / "metadata.yaml"
    meta.write_text(yaml.safe_dump({"title": spec["title"], "description": spec.get("description", ""), "tags": spec.get("tags", []),
                                    "privacy": "private", "title_lint": json.loads(lint)}, sort_keys=False))
    return "yt-package/title", [meta]


def s_export(ctx):
    """Validate the final video and hand it to the publishing library (ready/ + sidecar). Idempotent; a video that fails
    validation stays in the workspace and never reaches ready/."""
    res = exporter.export_job(ctx["id"])
    p = ctx["dir"] / "export-result.json"
    p.write_text(json.dumps(res, indent=2))
    return "export", [p]


def s_publish(ctx):
    cfg = providers.load("youtube.yaml")["publish"]
    res = ctx["dir"] / "publish-result.json"
    if not cfg["enabled"]:
        res.write_text(json.dumps({"status": "DRY_RUN", "reason": "youtube.yaml publish.enabled=false", "would_upload": str(ctx["dir"] / "video.mp4"), "privacy": "private"}, indent=2))
        return "dry-run", [res]
    if not ledger.approved(ctx["id"], "PUBLISH_APPROVED"):
        raise Blocked("PUBLISH_APPROVED gate not granted: contentos approve <id> PUBLISH_APPROVED")
    prim, _ = providers.select("publish_youtube")
    if not prim:
        raise Blocked("no YouTube OAuth credentials at ~/.contentos/secrets/youtube-oauth.json")
    raise Blocked("YouTube upload adapter not implemented yet (see docs/youtube.md)")


FN = {"brief": s_brief, "script": s_script, "voice": s_voice, "compose": s_compose, "render": s_render,
      "qa": s_qa, "package": s_package, "export": s_export, "publish": s_publish}
ARTIFACT = {"brief": "content.json", "script": "script-lint.json", "voice": "audio/%02d.wav", "compose": "project/index.html",
            "render": "video.mp4", "qa": "qa.json", "package": "metadata.yaml", "export": "export-result.json", "publish": "publish-result.json"}
RENDER_LANES = ("hyperframes", "mpt")


def artifact(st, spec):
    """Resume sentinel for a stage. The mpt lane has no index.html; its reviewable compose output is the request."""
    return "project/mpt-request.json" if st == "compose" and spec.get("render") == "mpt" else ARTIFACT[st]


def _note_stage(d, st, arts):
    """Record a finished stage in the job manifest (relative paths only). The manifest is a record, never a gate."""
    try:
        upd = {"artifacts": {st: [storage.rel(a, d) for a in arts]}}
        if st == "render":
            upd["final_output"] = "video.mp4"
        storage.update_manifest(d, **upd)
    except (OSError, storage.StorageError):
        pass


def _note_failure(d, st, exc):
    try:
        m = storage.read_manifest(d)
        if m and m["status"] != "failed" and not (st == "export" and m["status"] == "ready"):
            storage.update_manifest(d, status="failed", failure={"stage": st, "reason": storage.scrub(exc), "at": storage.now_iso()})
    except (OSError, storage.StorageError):
        pass


def run(spec_path, allow_paid=False, force=False, only=None, approve_private=False):
    spec = yaml.safe_load(Path(spec_path).read_text())
    if spec.get("render", "hyperframes") not in RENDER_LANES:
        raise ValueError(f"render: {spec['render']!r} is not one of {RENDER_LANES}")
    cid = spec["content_id"]
    storage.preflight(publish=True)                 # clear error if a configured folder is missing or read-only; never falls back to the repo
    d, _manifest = storage.open_job(cid, spec)      # jobs/YYYY/MM/<content_id>/ plus manifest.json on first use
    if _manifest["status"] != "exported":           # a resumed, already exported job stays exported
        storage.update_manifest(d, status="running", failure=None)
    W, H = {"9:16": (1080, 1920), "16:9": (1920, 1080)}[spec.get("format", "9:16")]
    ctx = {"id": cid, "dir": d, "spec": spec, "allow_paid": allow_paid, "res": (W, H)}
    if approve_private:  # explicit test shortcut; private/dry-run only
        for g in ("RESEARCH_APPROVED", "SCRIPT_APPROVED", "PRODUCTION_APPROVED"):
            ledger.approve(cid, g, by="cli --approve-private")
    rid = ledger.new_run_id()
    report = []
    for st in STAGES:
        if only and st != only:
            continue
        art = d / artifact(st, spec).replace("%02d", "01")
        if art.exists() and not force and st != "publish":
            report.append((st, "SKIP(resume)", 0.0))
            continue
        gate = {"voice": "SCRIPT_APPROVED", "render": "PRODUCTION_APPROVED"}.get(st)
        t0 = time.time()
        ledger.record(rid, cid, st, "-", "RUNNING", t0)   # in-flight marker for the dashboard
        try:
            if gate and not ledger.approved(cid, gate):
                raise Blocked(f"gate {gate} not granted: contentos approve {cid} {gate}")
            prov, arts = FN[st](ctx)
            ledger.record(rid, cid, st, prov, "OK", t0, arts)
            _note_stage(d, st, arts)
            report.append((st, "OK", time.time() - t0))
        except Blocked as e:
            art.unlink(missing_ok=True)
            ledger.record(rid, cid, st, "-", "BLOCKED", t0, error=str(e))
            report.append((st, f"BLOCKED: {e}", time.time() - t0))
            break
        except Exception as e:
            art.unlink(missing_ok=True)  # never leave a half-built artifact that resume would trust
            ledger.record(rid, cid, st, "-", "FAIL", t0, error=str(e))
            _note_failure(d, st, e)
            report.append((st, f"FAIL: {e}", time.time() - t0))
            break
    return rid, report
