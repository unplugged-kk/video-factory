"""Artifact-first pipeline. Every stage writes a durable file under <workspace>/jobs/YYYY/MM/DD/<content_id>/
(the workspace is outside the repository; see contentos/storage.py) and one ledger row. Re-running skips stages whose artifact already exists (resume)."""
import hashlib
import html
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import yaml

from . import export as exporter
from . import hf, ledger, mpt, providers, storage
from .production import align, recovery, supplied_audio
from .qa import probe_video, run_qa
from .features import registry as _feat

ROOT = Path(__file__).resolve().parent.parent
SKILLS = [ROOT / "vendor/youtube-agent-skill/skills", Path("~/.claude/skills").expanduser()]
ENV = {**os.environ, "HYPERFRAMES_PYTHON": str(providers.VENV_PY)}
STAGES = ["brief", "script", "voice", "compose", "render", "qa", "package", "export", "publish"]
LOOK_SCHEMA = "look/1"          # what the export stage records about the look of a video that actually shipped


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


def _append_log(path, text):
    if path is None:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def sh(cmd, cwd=None, timeout=None, log_path=None):
    limit = timeout or SH_TIMEOUT
    _append_log(log_path, f"$ {shlex.join(map(str, cmd))}\n")
    p = subprocess.Popen(cmd, cwd=cwd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        _kill_tree(p.pid)
        out, err = p.communicate()
        _append_log(log_path, f"[stdout]\n{out}[stderr]\n{err}[timeout after {limit:.0f}s]\n")
        raise RuntimeError(f"{' '.join(map(str, cmd))[:120]} -> timed out after {limit:.0f}s")
    _append_log(log_path, f"[stdout]\n{out}[stderr]\n{err}[exit {p.returncode}]\n")
    if p.returncode:
        raise RuntimeError(f"{' '.join(map(str, cmd))[:120]} -> {err.strip()[-400:] or out.strip()[-400:]}")
    return out


def _stage_sh(ctx, cmd, cwd=None, timeout=None):
    """Call the historical shell seam unchanged unless this run captures a stage log."""
    if ctx.get("log_path"):
        return sh(cmd, cwd=cwd, timeout=timeout, log_path=ctx["log_path"])
    return sh(cmd, cwd=cwd, timeout=timeout)


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
    out = _stage_sh(ctx, ["python3", str(skill_tool("yt-script", "hookscore.py")),
                          "--hook", lines[0]["say"], "--json"])
    lint.write_text(out)
    return "yt-script/hookscore", [md, lint]


def _voice_multilingual(ctx):
    """Non-English (or per-line language) jobs: route each line through contentos.lang. Plain English never gets here."""
    from .lang import capabilities as _lcap, router as _lr, script as _lscript, tts as _ltts
    from .lang.errors import LangError
    vd = ctx["dir"] / "audio"
    try:
        spec = ctx["spec"]
        problems = []
        for i, ln in enumerate(spec["script"], 1):         # per-line language wins; the script must really be in it
            lang = _lr.resolve(spec, ln).language
            problems += [f"{p} [{lang}]" for p in _lscript.validate(lang, [ln["say"]]) ]
        if problems:
            raise LangError("script does not match its language: " + "; ".join(problems), code="script_language_mismatch")
        status = {l: _lcap.status_of(l)["status"] for l in {_lr.resolve(spec, ln).language for ln in spec["script"]}}
        if "blocked" in status.values():
            bad = [l for l, st in status.items() if st == "blocked"]
            raise LangError("language " + ", ".join(f"{_lcap.status_of(l)['name']} ({l})" for l in bad) + " is blocked: "
                            + "; ".join(_lcap.status_of(l)["status_reason"] for l in bad), code="language_blocked")
        res = _ltts.synthesize_lines(spec, vd)
    except LangError as e:
        raise Blocked(f"language routing: {e}")
    meta = {"schema": "voice-languages/1", "capability_status": status,
            "notice": "; ".join(f"{l} is {st}: not production-ready" for l, st in status.items() if st != "production-ready") or None,
            "lines": [{"index": i, **r.to_dict()} for i, r in enumerate(res, 1)]}
    (vd / "voice-languages.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return res[0].backend, [Path(r.path) for r in res]


def s_voice(ctx):
    from .lang import router as _lr
    if not _lr.is_legacy(ctx["spec"]):
        if supplied_audio.has_record(ctx["dir"]):
            raise Blocked("this job holds supplied audio; use a different job id for a generated voice")
        return _voice_multilingual(ctx)
    if supplied_audio.has_record(ctx["dir"]):       # never silently replace a supplied take with a generated voice
        raise Blocked("this job holds supplied audio (supplied-audio/supplied-audio.json) but the pipeline cannot use it yet "
                      "(G3 records provenance and rights only); use a different job id for a generated voice")
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
            _stage_sh(ctx, hf.command("tts", ln.get("tts", ln["say"]), "-v", voice, "-o", raw))
            _stage_sh(ctx, ["ffmpeg", "-y", "-i", str(raw), "-af",
                            "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "24000", str(wav)])
            raw.unlink()
        outs.append(wav)
    return prim["id"], outs


def words_for(wav, workdir, log_path=None, language=None):
    """Word timings from whisper.cpp (via hyperframes). Falls back to even spacing if ASR is unavailable.
    `language` (en/None keeps the original path untouched): any other language is routed to its configured whisper model and an
    ASR failure is an error, never a silent switch to even spacing, because fake caption timing in Hindi cannot be told from real."""
    workdir.mkdir(exist_ok=True)
    if language not in (None, "en"):
        from .lang import asr as _lasr, config as _lc, router as _lr
        from .lang.errors import LangError as _LE
        cfg = _lc.load()
        route = _lr.resolve({"language": language}, None, cfg)
        try:
            r = _lasr.route_transcribe(wav, route, cfg)
        except _LE as e:
            if e.code == "asr_model_missing" and cfg["languages"][route.language].get("timing_fallback"):
                # the language config allows measured-duration even spacing; it is recorded, never presented as word timing
                (workdir / "asr-route.json").write_text(json.dumps({"timing": "even-spacing from measured audio duration, UNVERIFIED word timing",
                                                                    "reason": str(e), "route_language": route.language}, ensure_ascii=False))
                return None
            raise
        (workdir / "transcript.json").write_text(json.dumps(r["words"], ensure_ascii=False))
        (workdir / "asr-route.json").write_text(json.dumps({k: r[k] for k in ("model", "asr_model_id", "language", "seconds", "route_language")}))
        return [(w["text"], w["start"], w["end"]) for w in r["words"]]
    try:
        if log_path:
            sh(hf.command("transcribe", wav, "--json", "-d", workdir), log_path=log_path)
        else:
            sh(hf.command("transcribe", wav, "--json", "-d", workdir))
        return [(w["text"], w["start"], w["end"]) for w in json.loads((workdir / "transcript.json").read_text())]
    except Exception:
        return None


def caption_words(toks, asr, d, language=None):
    """Caption timings for one script line: the SCRIPT words (their spelling is what the caption shows), timed by
    aligning them to the ASR words. asr is [(text,start,end)] from words_for, or None; without it the words are
    spaced evenly over the take. Sequence alignment keeps an ASR insertion/deletion from shifting every later word."""
    if asr:
        fold = None
        if language not in (None, "en"):              # Whisper writes English terms in Latin where the script has Devanagari
            from .lang import lexicon
            fold = lexicon.fold
        wl, _ = align.align_words(toks, [{"text": w, "start": s, "end": e} for w, s, e in asr], fold=fold)
        return wl
    step = (d - 0.35) / len(toks)
    return [(w, k * step, (k + 1) * step) for k, w in enumerate(toks)]


def _mpt(fn, ctx):
    try:
        return "mpt", fn(ctx)
    except mpt.Unavailable as e:
        raise Blocked(str(e))


def s_compose(ctx):
    if ctx["spec"].get("render") == "remotion":
        from .renderers import get_renderer
        return get_renderer("remotion").compose(ctx)
    if ctx["spec"].get("render") == "mpt":
        return _mpt(mpt.compose, ctx)
    if ctx["spec"].get("visual_style"):              # opt-in multi-style scene kit; absent key = unchanged path below
        from .scenekit import compose as _scenekit
        return _scenekit.compose(ctx, dur=dur, words_for=words_for, caption_words=caption_words, stage=_stage_sh,
                                 lint_cmd=hf.command("lint"),
                                 cap_override=_feat.get("captions_hook", ctx["spec"])(ctx, ctx["spec"]))
    spec, W, H = ctx["spec"], *map(int, ctx["res"])
    U = min(W, H)                                    # type scales with the short side, so 16:9 is not set in 1920-wide type
    # Hook 1: style/decision-record resolution (Lane A). No-op when feature off.
    _feat.get("style_card", spec)(ctx, spec)
    proj = ctx["dir"] / "project"
    (proj / "assets/voice").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "contentos/templates/gsap.min.js", proj / "gsap.min.js")
    # Hook 2: scene-plan consumption (Lane B). Returns [] (pass-through) when feature off.
    _scene_plan = _feat.get("scene_plan", spec)(ctx, spec)
    ctx['_scene_plan'] = _scene_plan
    t, scenes, audios, anim = 0.0, [], [], []
    # Hook 5: caption/headline reveal override (Lane E). Returns {} when feature off.
    _cap_override = _feat.get("captions_hook", spec)(ctx, spec)
    for i, ln in enumerate(spec["script"], 1):
        wav = ctx["dir"] / "audio" / f"{i:02d}.wav"
        shutil.copy(wav, proj / f"assets/voice/{i:02d}.wav")
        d = round(dur(wav) + 0.35, 2)
        workdir = ctx["dir"] / "audio" / f"tx{i:02d}"
        _lang = ln.get("lang") or spec.get("language")
        _kw = {"language": _lang} if _lang not in (None, "en") else {}    # English call shape is unchanged
        asr = (words_for(wav, workdir, log_path=ctx["log_path"], **_kw)
               if ctx.get("log_path") else words_for(wav, workdir, **_kw))
        toks = ln["say"].split()                      # captions show the SCRIPT words; ASR supplies timing only
        wl = caption_words(toks, asr, d) if not _kw else caption_words(toks, asr, d, **_kw)
        cap = "".join(f'<span id="w{i}_{k}">{html.escape(w)}</span> ' for k, (w, _, _) in enumerate(wl))
        for k, (_, ws, we) in enumerate(wl):
            anim.append(f'tl.set("#w{i}_{k}",{{color:"#fbbf24"}},{t+ws:.2f});tl.set("#w{i}_{k}",{{color:"#fff"}},{t+we:.2f});')
        tag_text = ln.get("tag", f"{i}/{len(spec['script'])}")
        headline_text = ln["headline"]
        if _cap_override.get("clean_tags"):
            is_hook = (i == 1)
            is_cta = (i == len(spec["script"]))
            from .features.captions_hook import clean_tag_and_headline
            tag_text, headline_text = clean_tag_and_headline(tag_text, headline_text, is_hook, is_cta)
        tag_html = f'<div class="tag">{html.escape(tag_text)}</div>' if tag_text else ''
        scene_html = (f'<div class="scene clip" id="s{i}" data-start="{t:.2f}" data-duration="{d}">'
                      f'<div class="head">{tag_html}'
                      f'<h1 id="h{i}">{html.escape(headline_text)}</h1></div><p class="cap">{cap}</p></div>')
        # Hook 3: per-scene backdrop/transition injection (Lane C). Pass-through when off.
        scene_html, _ = _feat.get("visual_layer", spec)(ctx, i, scene_html, [], spec)
        scenes.append(scene_html)
        audios.append(f'<audio id="a{i}" src="./assets/voice/{i:02d}.wav" data-start="{t:.2f}" data-duration="{d}" class="clip"></audio>')
        anim.append(f'tl.fromTo("#s{i}",{{opacity:0}},{{opacity:1,duration:.3}},{t:.2f});'
                    f'tl.fromTo("#h{i}",{{y:60,opacity:0}},{{y:0,opacity:1,duration:.5,ease:"power3.out"}},{t+.1:.2f});'
                    f'tl.to("#s{i}",{{opacity:0,duration:.25}},{t+d-.25:.2f});')
        t += d
    total = round(t, 2)
    bottom_padding = int(H * _cap_override["safezone_bottom_padding"]) if _cap_override.get("safezone_bottom_padding") else int(H * 0.16)
    side_padding = _cap_override.get("safezone_side_padding", 70)
    (proj / "hyperframes.json").write_text(json.dumps({"width": W, "height": H, "fps": 30, "duration": total}))
    from .lang import typography as _typ            # Latin text: empty string, so English output is byte-identical
    _indic_css = _typ.block(_typ.script_kind(" ".join(f"{ln.get('say', '')} {ln.get('headline', '')} {ln.get('tag', '')}" for ln in spec["script"])),
                            ["h1", ".tag", ".cap"])
    (proj / "index.html").write_text(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{html.escape(spec['title'])}</title>
<script src="./gsap.min.js"></script>
<style>*{{margin:0;box-sizing:border-box}}body{{width:{W}px;height:{H}px;overflow:hidden;background:#090a0f;font-family:-apple-system,"Helvetica Neue",sans-serif;color:#fff}}
#root{{position:relative;width:{W}px;height:{H}px;background:radial-gradient(circle at 50% 20%,#1a1e36,#08090e)}}
.scene{{position:absolute;inset:0;display:grid;grid-template-rows:minmax(0,1fr) auto;row-gap:40px;padding:120px {side_padding}px {bottom_padding}px;text-align:center;opacity:0}}
.head{{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:0}}
.tag{{font:700 34px ui-monospace,Menlo,monospace;letter-spacing:3px;color:#a5b4fc;margin-bottom:36px}}
h1{{font-size:{int(U*0.085)}px;font-weight:900;line-height:1.1;letter-spacing:-1px}}
.cap{{font-size:{int(U*0.058)}px;font-weight:800;line-height:1.25;color:#fff;text-shadow:0 4px 18px rgba(0,0,0,.7)}}.cap span{{display:inline-block;color:#fff}}{_indic_css}</style></head>
<body><div id="root" data-composition-id="root" data-width="{W}" data-height="{H}" data-duration="{total}">
{''.join(scenes)}{''.join(audios)}</div>
<script>const tl=gsap.timeline({{paused:true}});{''.join(anim)}
window.__timelines=window.__timelines||{{}};window.__timelines["root"]=tl;</script></body></html>""")
    _stage_sh(ctx, hf.command("lint"), cwd=proj)
    return "hyperframes", [proj / "index.html", proj / "hyperframes.json"]


def s_render(ctx):
    if ctx["spec"].get("render") == "remotion":
        from .renderers import get_renderer
        return get_renderer("remotion").render(ctx)
    if ctx["spec"].get("render") == "mpt":
        return _mpt(mpt.render, ctx)
    mp4 = ctx["dir"] / "video.mp4"
    cmd = hf.command("render", "-o", mp4)
    hf_q = ctx["spec"].get("_v1_hyperframes_quality")
    if isinstance(hf_q, str) and hf_q.strip():
        cmd.extend(["-q", hf_q.strip()])
    _stage_sh(ctx, cmd, cwd=ctx["dir"] / "project", timeout=RENDER_TIMEOUT)
    # Hook 4: post-render audio stage (Lane D). Pass-through returns mp4 unchanged.
    mp4 = _feat.get("audio_bed", ctx["spec"])(ctx, mp4, ctx["spec"])
    return "hyperframes", [mp4]


def s_qa(ctx):
    res = run_qa(ctx["dir"] / "video.mp4", ctx["spec"].get("format", "9:16"))
    # Hook 6: extra gates (Lane F). Returns [] when feature off.
    res = list(res) + _feat.get("qa_extra", ctx["spec"])(ctx, ctx["dir"] / "video.mp4", ctx["spec"])
    p = ctx["dir"] / "qa.json"
    p.write_text(json.dumps([{"check": c, "status": s, "detail": d} for c, s, d in res], indent=2))
    fails = [c for c, s, _ in res if s == "FAIL"]
    if fails:
        raise RuntimeError(f"QA failed: {fails}")
    return "ffmpeg", [p]


def s_package(ctx):
    spec = ctx["spec"]
    lint = _stage_sh(ctx, ["python3", str(skill_tool("yt-package", "title.py")),
                           "--title", spec["title"], "--thumb", spec.get("thumb_text", ""), "--json"])
    meta = ctx["dir"] / "metadata.yaml"
    meta.write_text(yaml.safe_dump({"title": spec["title"], "description": spec.get("description", ""), "tags": spec.get("tags", []),
                                    "privacy": "private", "title_lint": json.loads(lint)}, sort_keys=False))
    return "yt-package/title", [meta]


def _record_look(ctx):
    """Record this video's look in the shipped-look ledger, so Rule B's window reflects what actually shipped.

    Best-effort by design: an export has already cost a render, so a missing composition, an unreadable manifest or an
    unwritable ledger reports itself rather than failing the export. The look is recorded even when it repeats a recent
    one (`require_ok=False`), because the ledger is the history of what shipped and a duplicate that shipped is exactly
    what the next check needs to see; the Rule B verdict is kept in the job's own look.json.
    """
    from .intelligence import visual
    out = {"schema": LOOK_SCHEMA, "content_id": ctx["id"], "series": None, "signature": None,
           "status": "skipped", "verdict": None, "reason": None}
    try:
        out["series"] = (storage.read_manifest(ctx["dir"]) or {}).get("project_id")
        out["signature"] = visual.signature_of(ctx["dir"])
        res = visual.claim(ctx["id"], out["signature"], series=out["series"], require_ok=False)
        out["status"] = "recorded" if res.get("recorded") else "not-recorded"
        out["verdict"] = {"ok": res.get("ok"), "duplicates": res.get("duplicates"), "refused": res.get("refused")}
    except Exception as exc:                          # deliberately broad: no look record may ever fail an export
        out["reason"] = storage.scrub(exc)
        print(f"{ctx['id']}: look not recorded: {out['reason']}", file=sys.stderr)
    try:
        p = ctx["dir"] / "look.json"
        p.write_text(json.dumps(out, indent=2), encoding="utf-8")
        return p
    except OSError:
        return None                                   # the export itself already succeeded; nothing more to do


def s_export(ctx):
    """Validate the final video and hand it to the publishing library (ready/ + sidecar). Idempotent; a video that fails
    validation stays in the workspace and never reaches ready/."""
    blockers = supplied_audio.publish_blockers(ctx["dir"])
    if blockers:                                     # a gate-style stop, not a crash: fix the rights record and re-run export
        raise Blocked("supplied audio blocks publication: " + "; ".join(blockers))
    res = exporter.export_job(ctx["id"], force=bool(ctx.get("force")))
    p = ctx["dir"] / "export-result.json"
    p.write_text(json.dumps(res, indent=2))
    look = _record_look(ctx)                         # only after a successful export, and never fatal
    return "export", ([p, look] if look else [p])


def s_publish(ctx):
    cfg = providers.load("youtube.yaml")["publish"]
    res = ctx["dir"] / "publish-result.json"
    if not cfg["enabled"]:
        res.write_text(json.dumps({"status": "DRY_RUN", "reason": "youtube.yaml publish.enabled=false", "would_upload": str(ctx["dir"] / "video.mp4"), "privacy": "private"}, indent=2))
        return "dry-run", [res]
    blockers = supplied_audio.publish_blockers(ctx["dir"])
    if blockers:
        raise Blocked("supplied audio blocks publication: " + "; ".join(blockers))
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
RENDER_LANES = ("hyperframes", "remotion", "mpt")


GATE_OF = {"voice": "SCRIPT_APPROVED", "render": "PRODUCTION_APPROVED"}
CONTRACT = "video-factory.contract.v1"


def _digest(parts):
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def script_digest(spec):
    """What SCRIPT_APPROVED covers: the title and every line's spoken text, exactly as the voice stage will read it."""
    body = {"title": spec.get("title"), "script": [{"say": ln["say"], "tts": ln.get("tts")} for ln in spec["script"]]}
    from .lang import router as _lr
    if not _lr.is_legacy(spec):                       # English digests are unchanged, so existing approvals stay valid
        body["language"] = {"language": spec.get("language"), "voice": spec.get("voice"), "lines": [ln.get("lang") for ln in spec["script"]]}
    return _digest([json.dumps(body, sort_keys=True, ensure_ascii=False)])


def production_digest(d, spec):
    """What PRODUCTION_APPROVED covers: the composed project plus every audio take. None until the composition exists."""
    d = Path(d)
    comp = d / artifact("compose", spec)
    if not comp.is_file():
        return None
    parts = [f"composition {artifact('compose', spec)} {exporter.sha256_file(comp)}"]
    parts += [f"audio {w.name} {exporter.sha256_file(w)}" for w in sorted((d / "audio").glob("*.wav"))]
    return _digest(parts)


def gate_digest(gate, d, spec):
    return script_digest(spec) if gate == "SCRIPT_APPROVED" else production_digest(d, spec) if gate == "PRODUCTION_APPROVED" else None


def _check_gate(cid, gate, d, spec):
    """Raise Blocked unless `gate` is granted for the content as it is now. Unbound (legacy) grants pass with a warning."""
    cur = gate_digest(gate, d, spec)
    state, bound = ledger.check_gate(cid, gate, cur)
    if state == "none":
        raise Blocked(f"gate {gate} not granted: contentos approve {cid} {gate}")
    if state == "mismatch":
        raise Blocked(f"gate {gate} was approved for different content: approved digest {', '.join(bound)}, current digest {cur or 'unavailable'}; "
                      f"review the change and re-approve: contentos approve {cid} {gate}")
    if state == "unbound":
        print(f"warning: {gate} for {cid} is an unbound approval (no content digest), so edits made since cannot be detected; "
              f"re-approve to bind it: contentos approve {cid} {gate}", file=sys.stderr)


def _authorized_by():
    """The identity that authorised a ContentForge job, set by factory_worker.mjs. One short printable line, or None."""
    raw = os.environ.get("CONTENTOS_FACTORY_AUTHORIZED_BY", "")
    ident = " ".join("".join(ch if ch.isprintable() else " " for ch in raw).split())[:120]
    return ident or None


def artifact(st, spec):
    """Resume sentinel for a stage. The mpt lane has no index.html; its reviewable compose output is the request."""
    if st == "compose":
        if spec.get("render") == "remotion":
            return "project_remotion/src/Video.tsx"
        if spec.get("render") == "mpt":
            return "project/mpt-request.json"
    return ARTIFACT[st]


def rerun_plan(stage):
    """Stages and approval gates affected by forcing one stage.

    Sentinels after the selected stage stop counting as current. Script and composition grants are revoked only when
    the forced stage can change the artifact those grants reviewed.
    """
    if stage not in STAGES:
        raise ValueError(f"unknown pipeline stage: {stage}")
    index = STAGES.index(stage)
    gates = []
    if index <= STAGES.index("script"):
        gates.append("SCRIPT_APPROVED")
    if index <= STAGES.index("compose"):
        gates.append("PRODUCTION_APPROVED")
    return STAGES[index + 1:], gates


def invalidate_downstream(directory, spec, stage):
    """Delete stale downstream sentinels and revoke the approval gates they depended on."""
    later, gates = rerun_plan(stage)
    root = Path(directory).resolve()
    removed = []

    def _unlink(path):
        candidate = Path(path)
        if candidate.is_symlink() or not candidate.is_file():
            return
        try:
            candidate.resolve().relative_to(root)
        except ValueError:
            return
        candidate.unlink()
        removed.append(str(candidate.relative_to(root)))

    for name in later:
        _unlink(root / artifact(name, spec).replace("%02d", "01"))
    if "voice" in later:
        audio = root / "audio"
        if audio.is_dir() and not audio.is_symlink():
            for wav in audio.glob("*.wav"):
                _unlink(wav)
    if "compose" in later:
        for name in ("project/index.html", "project/mpt-request.json", "project_remotion/src/Video.tsx"):
            _unlink(root / name)
    revoked = []
    for gate in gates:
        if ledger.revoke(spec["content_id"], gate, f"forced rerun of {stage}"):
            revoked.append(gate)
    return {"stage": stage, "removed": removed, "revokedApprovals": revoked}


def stage_log_path(job_dir, stage):
    """Stable location for diagnostics from one pipeline stage."""
    if stage not in STAGES:
        raise ValueError(f"unknown pipeline stage: {stage}")
    return Path(job_dir) / "logs" / f"{stage}.log"


# A stage whose sentinel is not enough on its own: presence means "this stage ran", which is only the same as "the result
# is still current" for export, whose output can be superseded by a later render. The guard returns None to allow the
# skip, or the reason it must not be reported as done.
RESUME_GUARD = {"export": exporter.resume_blocker}


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


def _note_spec(d, m, spec_path):
    """Remember which spec drives this job so `contentos approve` can bind an approval to the content it reviewed."""
    src = str(Path(spec_path).resolve())
    if m.get("source_spec") != src:
        try:
            storage.update_manifest(d, source_spec=src)
        except (OSError, storage.StorageError):
            pass


def run(spec_path, allow_paid=False, force=False, only=None, approve_private=False, recover=False, recovery_log=None):
    spec = yaml.safe_load(Path(spec_path).read_text())
    if spec.get("render", "hyperframes") not in RENDER_LANES:
        raise ValueError(f"render: {spec['render']!r} is not one of {RENDER_LANES}")
    cid = spec["content_id"]
    storage.preflight(publish=True)                 # clear error if a configured folder is missing or read-only; never falls back to the repo
    try:
        d, _manifest = storage.open_job(cid, spec)  # jobs/YYYY/MM/DD/<content_id>/ plus manifest.json on first use
    except storage.StorageError as exc:
        # A manifest we cannot read - a legacy contentos-project-manifest/1, say - needs an operator, not a traceback.
        # Scoped to this one call on purpose: preflight, QA and export StorageErrors must still surface as themselves.
        # Reported as a blocked row so every caller agrees: the CLI exits non-zero, the worker marks the job blocked
        # rather than failed, and core.classify() sees a blocked stage, which is not transient, so nothing retries.
        rid = ledger.new_run_id()
        ledger.record(rid, cid, "manifest", "-", "BLOCKED", time.time(), error=str(exc))
        return rid, [("manifest", f"BLOCKED: {exc}", 0.0)]
    with storage.file_lock(d / ".run.lock", blocking=False):     # one run per job; a second run is refused, not queued
        removed = recovery.scrub_interrupted(cid, spec, d) if recover else []
        if removed:
            message = f"{cid}: redoing artifacts a killed run left unfinished: {', '.join(removed)}"
            if recovery_log:
                recovery_log(message)
            else:
                print(message, file=sys.stderr, flush=True)
        _note_spec(d, _manifest, spec_path)
        if only and force:
            invalidate_downstream(d, spec, only)
        return _stages(cid, d, spec, _manifest, allow_paid, force, only, approve_private)


def _stages(cid, d, spec, _manifest, allow_paid, force, only, approve_private):
    """Run the stages in order. Split out of run() so the per-job lock can wrap the loop without re-indenting it."""
    if _manifest["status"] != "exported":           # a resumed, already exported job stays exported
        storage.update_manifest(d, status="running", failure=None)
    W, H = {"9:16": (1080, 1920), "16:9": (1920, 1080)}[spec.get("format", "9:16")]
    ctx = {"id": cid, "dir": d, "spec": spec, "allow_paid": allow_paid, "res": (W, H), "force": bool(force)}
    ident = _authorized_by()
    grant = {"by": "cli --approve-private" + (f" authorized-by={ident}" if ident else ""),
             "note": f"contract={CONTRACT} job={cid}" if ident else ""}
    if approve_private:  # explicit test shortcut; private/dry-run only
        for g in ("RESEARCH_APPROVED", "SCRIPT_APPROVED", "PRODUCTION_APPROVED"):
            ledger.approve(cid, g, **grant, subject_sha256=script_digest(spec) if g == "SCRIPT_APPROVED" else None)
    rid = ledger.new_run_id()
    report = []
    for st in STAGES:
        if only and st != only:
            continue
        art = d / artifact(st, spec).replace("%02d", "01")
        if art.exists() and not force and st != "publish":
            guard = RESUME_GUARD.get(st)
            blocker = guard(ctx["dir"]) if guard else None
            if blocker is None and GATE_OF.get(st) == "SCRIPT_APPROVED":
                # a resume must not hide a script edited after approval; only digest-bound approvals can object, so old jobs resume as before
                state, bound = ledger.check_gate(cid, "SCRIPT_APPROVED", script_digest(spec))
                if state == "mismatch":
                    blocker = f"gate SCRIPT_APPROVED was approved for different content: approved digest {', '.join(bound)}, current digest {script_digest(spec)}; review the change and re-approve: contentos approve {cid} SCRIPT_APPROVED"
            if blocker is None:
                report.append((st, "SKIP(resume)", 0.0))
                continue
            # The stage did succeed; it is the RESUME that is refused. The sentinel is kept on purpose - the Blocked
            # handler below unlinks a half-built artifact, and doing that here would let the next plain run export for
            # real, which is exactly the write being prevented here.
            ledger.record(rid, cid, st, "-", "BLOCKED", time.time(), error=blocker)
            report.append((st, f"BLOCKED: {blocker}", 0.0))
            break
        gate = GATE_OF.get(st)
        t0 = time.time()
        log_path = stage_log_path(d, st)
        ctx["log_path"] = log_path
        _append_log(log_path, f"\n--- stage {st} run {rid} ---\n")
        ledger.record(rid, cid, st, "-", "RUNNING", t0)   # in-flight marker for the dashboard
        if gate:
            if approve_private and gate == "PRODUCTION_APPROVED":   # the composition did not exist when the private grant was made; bind it now
                cur = production_digest(d, spec)
                if cur and ledger.check_gate(cid, gate, cur)[0] != "ok":
                    ledger.approve(cid, gate, **grant, subject_sha256=cur)
            try:
                _check_gate(cid, gate, d, spec)
            except Blocked as e:
                # A gate refusal is not a failed stage: the existing sentinel is the reviewed artifact and must survive
                # so a forced rerun cannot destroy work the gate just protected.
                _append_log(log_path, f"[stage BLOCKED] {e}\n")
                ledger.record(rid, cid, st, "-", "BLOCKED", t0, error=str(e))
                report.append((st, f"BLOCKED: {e}", time.time() - t0))
                break
        try:
            prov, arts = FN[st](ctx)
            ledger.record(rid, cid, st, prov, "OK", t0, arts)
            _append_log(log_path, f"[stage OK provider={prov}]\n")
            _note_stage(d, st, arts)
            report.append((st, "OK", time.time() - t0))
        except Blocked as e:
            _append_log(log_path, f"[stage BLOCKED] {e}\n")
            art.unlink(missing_ok=True)
            ledger.record(rid, cid, st, "-", "BLOCKED", t0, error=str(e))
            report.append((st, f"BLOCKED: {e}", time.time() - t0))
            break
        except Exception as e:
            _append_log(log_path, f"[stage FAIL] {e}\n")
            art.unlink(missing_ok=True)  # never leave a half-built artifact that resume would trust
            ledger.record(rid, cid, st, "-", "FAIL", t0, error=str(e))
            _note_failure(d, st, e)
            report.append((st, f"FAIL: {e}", time.time() - t0))
            break
    return rid, report
