"""videojob/1: the shared manifest of one video job, plus the workflow selector that decides which capabilities run.

Content, style, workflow and renderer stay in separate blocks so each can change alone. Nothing here renders, calls a
network or reads media; the selector looks only at the declared inputs.

  python -m contentos.videojob select [--intent I] --input kind[:value] ... [--duration S]
  python -m contentos.videojob validate MANIFEST.json     exit 0 ok, 1 problems, 2 unreadable

The selector picks the smallest adequate capability set. It never invents lyrics, words or timings: when exact text or
word timing is not available it says so in `warnings`, and a missing critical input is a `blocker`."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "videojob/1"

CAPABILITIES = (
    "research", "voice", "video-understanding", "storyboard-director", "visual-style-engine",
    "motion-graphics-engine", "talking-head-editor", "lyric-video-engine", "asset-library",
    "video-renderer", "video-quality-checker",
)
# Where each capability is implemented today, so a selection never claims more than the repo has. `state` is `exists`
# when the artifact below is in this repo now and `planned` when nothing implements it yet (`by` is then None). `note`
# carries a limit that matters when the result is read out. tests/test_videojob.py checks every path here against disk.
IMPLEMENTED_BY = {
    "research": {"state": "exists", "by": "contentos/research.py"},
    "voice": {"state": "exists", "by": "contentos/pipeline.py", "note": "the `voice` stage (Kokoro)"},
    "video-understanding": {"state": "exists", "by": "contentos/production/align.py",
                            "note": "word timing only; no beat detection, vocal separation or diarization yet"},
    "storyboard-director": {"state": "exists", "by": ".claude/skills/video-director"},
    "visual-style-engine": {"state": "exists", "by": "contentos/intelligence/looks.py",
                            "note": "looks and effects are data in config/presets/; the builder does not read them yet"},
    "motion-graphics-engine": {"state": "exists", "by": ".claude/skills/explainer-motion-craft"},
    "talking-head-editor": {"state": "planned", "by": None},
    "lyric-video-engine": {"state": "planned", "by": None},
    "asset-library": {"state": "exists", "by": "contentos/production/assets.py",
                      "note": "an ffprobe index, sampled frames, agent-written notes and search over them"},
    "video-renderer": {"state": "exists", "by": "contentos/renderers/registry.py"},
    "video-quality-checker": {"state": "exists", "by": "contentos/qa.py"},
}
INPUT_KINDS = ("topic", "script", "audio", "video", "lyrics", "images", "data", "links", "screen", "brand", "broll")
INTENTS = ("create", "edit", "lyric", "repurpose", "assets", "news")
STATUSES = ("planned", "approved", "running", "rendered", "failed")
GRANULARITY = ("word", "phrase", "sentence", "none")
LONG_VIDEO_S = 600

TOP_KEYS = {"schema", "job_id", "objective", "intent", "inputs", "output", "workflow", "style", "timing", "plan_ref",
            "assets", "audio", "captions", "render", "validation", "outputs", "status"}
REQUIRED = {"schema", "job_id", "objective", "intent", "inputs", "output", "workflow", "status"}


def infer_intent(kinds: set[str], duration_s: float | None = None) -> str:
    if "audio" in kinds and "lyrics" in kinds:
        return "lyric"
    if "video" in kinds and (duration_s or 0) >= LONG_VIDEO_S:
        return "repurpose"
    if "video" in kinds:
        return "edit"
    if kinds and kinds <= {"broll", "images"}:
        return "assets"
    return "create"


def select(inputs: list[dict], intent: str | None = None, duration_s: float | None = None) -> dict:
    """inputs: [{"kind": one of INPUT_KINDS, ...}]. Returns {"intent", "capabilities":[{"id","why"}], "warnings", "blockers"}."""
    kinds = {i["kind"] for i in inputs}
    bad = kinds - set(INPUT_KINDS)
    if bad:
        raise ValueError(f"unknown input kind(s): {sorted(bad)}")
    if intent is not None and intent not in INTENTS:
        raise ValueError(f"unknown intent: {intent}")
    intent = intent or infer_intent(kinds, duration_s)
    caps: list[tuple[str, str]] = []
    warnings: list[str] = []
    blockers: list[str] = []

    def add(cap: str, why: str) -> None:
        if cap not in dict(caps):
            caps.append((cap, why))

    if intent == "assets":
        if not kinds & {"broll", "images", "video"}:
            blockers.append("no media to index: supply a folder of clips or images")
        add("asset-library", "index and search supplied media")
        return _result(intent, caps, warnings, blockers)

    if intent == "lyric":
        if "audio" not in kinds:
            blockers.append("a lyric video needs the song audio")
        if "lyrics" not in kinds:
            warnings.append("no lyrics supplied: text will come from transcription and may be wrong; word timing is "
                            "approximate unless forced alignment is installed")
        add("video-understanding", "align lyrics to the sung audio and detect beats")
        add("storyboard-director", "map each line to a visual motif")
        add("visual-style-engine", "resolve the requested look")
        add("lyric-video-engine", "animate lyrics from word timings and beats")
    elif intent in ("edit", "repurpose"):
        if "video" not in kinds:
            blockers.append(f"{intent} needs the source video")
        add("video-understanding", "transcribe, word-time and find shots in the source")
        add("talking-head-editor", "cut, reframe and place cutaways" if intent == "edit"
            else "pick strong moments and reframe each to the target aspect")
        if kinds & {"broll", "images", "screen"}:
            add("asset-library", "match supplied cutaway media to what is said")
        add("visual-style-engine", "resolve the requested look")
    else:  # create, news
        if not kinds & {"topic", "script", "audio", "video", "links", "data", "images", "screen"}:
            blockers.append("nothing to build from: give a topic, script, audio, data or media")
        if intent == "news" and not kinds & {"links", "topic"}:
            blockers.append("a news video needs source links or a topic to research")
        if intent == "news" or (kinds & {"links"} and not kinds & {"script", "audio"}) or kinds == {"topic"}:
            add("research", "gather and verify sources before scripting; keep credits")
        if "audio" in kinds or "video" in kinds:
            add("video-understanding", "transcribe and time the supplied speech")
        elif "script" in kinds or kinds & {"topic", "links"}:
            add("voice", "narrate the script; timings come from the generated audio")
            add("video-understanding", "word-time the narration")
        add("storyboard-director", "turn the content into scenes and shots")
        add("visual-style-engine", "resolve the requested look")
        if kinds & {"images", "screen", "broll"}:
            add("asset-library", "reuse supplied media with provenance")
        if "data" in kinds:
            add("motion-graphics-engine", "animate the supplied data")
    add("motion-graphics-engine", "captions, titles and motion tied to word timings")
    add("video-renderer", "build the composition and encode the outputs")
    add("video-quality-checker", "verify the rendered file before reporting")
    return _result(intent, caps, warnings, blockers)


def _result(intent, caps, warnings, blockers):
    """Each capability carries what implements it, so an agent reports the real state instead of an implied one."""
    rows = []
    for cid, why in caps:
        info = IMPLEMENTED_BY[cid]
        row = {"id": cid, "state": info["state"], "by": info["by"], "why": why}
        if info.get("note"):
            row["note"] = info["note"]
        rows.append(row)
    return {"intent": intent, "capabilities": rows, "warnings": warnings, "blockers": blockers}


def validate(m: dict) -> list[str]:
    errs: list[str] = []
    if not isinstance(m, dict):
        return ["manifest is not an object"]
    if m.get("schema") != SCHEMA:
        errs.append(f"schema must be {SCHEMA!r}")
    errs += [f"unknown key: {k}" for k in sorted(set(m) - TOP_KEYS)]
    errs += [f"missing key: {k}" for k in sorted(REQUIRED - set(m))]
    if m.get("intent") not in INTENTS:
        errs.append(f"intent must be one of {INTENTS}")
    if m.get("status") not in STATUSES:
        errs.append(f"status must be one of {STATUSES}")
    for i, inp in enumerate(m.get("inputs") or []):
        if not isinstance(inp, dict) or inp.get("kind") not in INPUT_KINDS:
            errs.append(f"inputs[{i}].kind must be one of {INPUT_KINDS}")
    wf = m.get("workflow")
    if isinstance(wf, dict):
        for c in wf.get("capabilities", []):
            if c.get("id") not in CAPABILITIES:
                errs.append(f"workflow capability not known: {c.get('id')!r}")
    elif "workflow" in m:
        errs.append("workflow must be an object")
    t = m.get("timing")
    if t is not None:
        if t.get("granularity") not in GRANULARITY:
            errs.append(f"timing.granularity must be one of {GRANULARITY}")
        elif t["granularity"] != "none" and not (t.get("tool") and t.get("confidence") is not None):
            errs.append("timing with granularity needs `tool` and `confidence`: never claim timing precision unreported")
    out = m.get("output") or {}
    for k in ("aspect",):
        if k in out and not isinstance(out[k], list):
            errs.append(f"output.{k} must be a list")
    return errs


def new_job(job_id: str, objective: str, inputs: list[dict], intent: str | None = None,
            output: dict | None = None, style: dict | None = None) -> dict:
    sel = select(inputs, intent, (output or {}).get("duration_s"))
    m = {"schema": SCHEMA, "job_id": job_id, "objective": objective, "intent": sel["intent"], "inputs": inputs,
         "output": output or {}, "workflow": sel, "status": "planned"}
    if style:
        m["style"] = style
    return m


def write(m: dict, job_dir: Path) -> Path:
    """Atomic write to <job_dir>/videojob.json. Refuses an in-repo directory and never overwrites."""
    job_dir = Path(job_dir).resolve()
    if job_dir == ROOT or ROOT in job_dir.parents:
        raise ValueError("job directory must be outside the repository (use $VIDEO_FACTORY_WORKSPACE)")
    errs = validate(m)
    if errs:
        raise ValueError("invalid manifest: " + "; ".join(errs))
    job_dir.mkdir(parents=True, exist_ok=True)
    dest = job_dir / "videojob.json"
    if dest.exists():
        raise FileExistsError(f"{dest} exists; not overwriting")
    fd, tmp = tempfile.mkstemp(dir=job_dir, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(m, f, indent=2)
    os.replace(tmp, dest)
    return dest


def _parse_input(s: str) -> dict:
    kind, _, value = s.partition(":")
    d: dict = {"kind": kind}
    if value:
        d["ref"] = value
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m contentos.videojob", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("--intent", choices=INTENTS)
    s.add_argument("--input", action="append", default=[], metavar="KIND[:REF]")
    s.add_argument("--duration", type=float, help="source duration in seconds (long sources imply repurpose)")
    v = sub.add_parser("validate")
    v.add_argument("manifest")
    a = ap.parse_args(argv)
    if a.cmd == "select":
        try:
            res = select([_parse_input(x) for x in a.input], a.intent, a.duration)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2
        print(json.dumps(res, indent=2))
        return 1 if res["blockers"] else 0
    try:
        m = json.loads(Path(a.manifest).read_text())
    except (OSError, ValueError) as e:
        print(f"cannot read manifest: {e}", file=sys.stderr)
        return 2
    errs = validate(m)
    print(json.dumps({"ok": not errs, "problems": errs}, indent=2))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
