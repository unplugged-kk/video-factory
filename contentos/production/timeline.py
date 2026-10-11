"""timeline/1: one JSON file per job holding words, scenes and cues on a single clock (SHADOW MODE).

Status: shadow. Nothing reads this file yet: compose, captions and QA keep using their existing inputs
(`audio/timing.json`, `captions/word-timings.json`, `project/timings.js`). This module only derives a `timeline.json` from those
existing artifacts, validates it, and checks it against the legacy data so that a later switch-over is a measured step.
It runs no ASR, no render and no network, and imports neither pipeline.py nor any renderer.

Time facts are not invented here. Word times come from `align.align_words` (the existing script-to-ASR sequence alignment),
scene times from `sceneplan.resolve`, cue times from the word each cue is anchored to. The only new things are the container,
the per-word `source` label and the checks. Word timing is ASR-derived and is labelled so: `timing_trust` stays
"asr-derived-unverified" until a human-marked anchor set (roadmap experiment E1) measures the error.

Word `source` values: "matched" (one-to-one with an ASR word), "span" (several script words, or one script word, timed from the
ASR span they replace, e.g. "spellchecker" heard as "spell"+"checker": an extension to the 06 spec's two values) and
"interpolated" (no ASR counterpart; timed between its neighbours).
"""
import difflib
import hashlib
import json
from pathlib import Path

from .align import norm

SCHEMA = "timeline/1"
TRUST_UNVERIFIED = "asr-derived-unverified"
EPS = 0.006          # legacy timings.js keeps two decimals; word-timings.json three


def word_sources(script_words, asr_words):
    """Label each script word matched / span / interpolated using the same normalisation and matcher as align_words
    (SequenceMatcher over norm()), so the label always agrees with how align_words timed the word."""
    a = [norm(w) for w in script_words]
    b = [norm(w) for w in asr_words]
    out = ["interpolated"] * len(a)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            out[i1:i2] = ["matched"] * (i2 - i1)
        elif tag == "replace" and i2 > i1 and j2 > j1:
            out[i1:i2] = ["span"] * (i2 - i1)
    return out


def build_timeline(job, fps, duration_s, lines, cues, audio=None, alignment=None, min_hold_s=2.0):
    """lines: one dict per scene, in order: {id, title, t0, t1, words: [(text, t0, t1)] absolute seconds, sources: [str]}.
    cues: [{scene, word (global index), do}] anchored to narration words. Returns the timeline/1 dict."""
    words, scenes = [], []
    for ln in lines:
        first = len(words)
        for k, (text, s, e) in enumerate(ln["words"]):
            words.append({"i": len(words), "text": text, "t0": round(s, 3), "t1": round(e, 3), "source": ln["sources"][k]})
        scenes.append({"id": ln["id"], "title": ln.get("title", ""), "t0": round(ln["t0"], 3), "t1": round(ln["t1"], 3),
                       "w0": first, "w1": len(words) - 1, "min_hold_s": min_hold_s})
    cue_out = []
    for n, c in enumerate(cues):
        w = words[c["word"]]
        cue_out.append({"id": f"c{n + 1:02d}-{c['scene']}", "kind": "visual", "scene": c["scene"],
                        "at": {"word": c["word"], "offset_s": 0.0}, "t": w["t0"], "do": c.get("do", "")})
    return {"schema": SCHEMA, "job": job, "fps": fps, "duration_s": round(duration_s, 3),
            "audio": audio or {"source": "generated", "sha256": None, "rights": {"status": "unassessed"}},
            "alignment": {"method": "sequence-match", "timing_trust": TRUST_UNVERIFIED, "verified_anchors": [], **(alignment or {})},
            "words": words, "scenes": scenes, "cues": cue_out}


def validate(tl):
    """Returns a list of {level: error|warning, code, msg}. No error means the file is internally consistent;
    it says nothing about whether the word times are CORRECT (that needs human anchors)."""
    iss = []

    def add(level, code, msg):
        iss.append({"level": level, "code": code, "msg": msg})

    if tl.get("schema") != SCHEMA:
        add("error", "schema", f"schema is {tl.get('schema')!r}, expected {SCHEMA!r}")
    al = tl.get("alignment", {})
    if al.get("timing_trust") != TRUST_UNVERIFIED and not al.get("verified_anchors"):
        add("error", "trust", "timing_trust claims more than 'asr-derived-unverified' without verified_anchors")
    words, scenes = tl.get("words", []), tl.get("scenes", [])
    prev = None
    for w in words:
        if w["t1"] < w["t0"]:
            add("error", "word_negative", f"word {w['i']} {w['text']!r} ends before it starts")
        if prev is not None and w["t0"] < prev["t0"] - 1e-9:
            add("error", "word_order", f"word {w['i']} {w['text']!r} starts before word {prev['i']}")
        prev = w
    if not scenes:
        add("error", "no_scenes", "timeline has no scenes")
    for k, sc in enumerate(scenes):
        if sc["t1"] <= sc["t0"]:
            add("error", "scene_empty", f"scene {sc['id']} has no duration")
        if k and abs(sc["t0"] - scenes[k - 1]["t1"]) > EPS:
            add("error", "scene_gap", f"scene {sc['id']} starts at {sc['t0']} but {scenes[k - 1]['id']} ends at {scenes[k - 1]['t1']}")
        for w in words[sc["w0"]:sc["w1"] + 1]:
            if w["t0"] < sc["t0"] - EPS or w["t1"] > sc["t1"] + EPS:
                add("error", "word_outside_scene", f"word {w['i']} {w['text']!r} ({w['t0']}-{w['t1']}) is outside scene {sc['id']} ({sc['t0']}-{sc['t1']})")
        if sc["t1"] - sc["t0"] < sc.get("min_hold_s", 0):
            add("warning", "min_hold", f"scene {sc['id']} lasts {sc['t1'] - sc['t0']:.2f}s, below its minimum hold {sc['min_hold_s']}s (reported, not changed)")
    if scenes:
        if abs(scenes[0]["t0"]) > EPS:
            add("error", "start", f"first scene starts at {scenes[0]['t0']}, not 0")
        if abs(scenes[-1]["t1"] - tl.get("duration_s", -1)) > EPS:
            add("error", "end", f"last scene ends at {scenes[-1]['t1']} but duration_s is {tl.get('duration_s')}")
    sids = {s["id"] for s in scenes}
    for c in tl.get("cues", []):
        if c["scene"] not in sids:
            add("error", "cue_scene", f"cue {c['id']} names unknown scene {c['scene']}")
            continue
        wi = c["at"]["word"]
        if not 0 <= wi < len(words):
            add("error", "cue_word", f"cue {c['id']} anchors to word {wi}, which does not exist")
            continue
        sc = next(s for s in scenes if s["id"] == c["scene"])
        if not sc["w0"] <= wi <= sc["w1"]:
            add("error", "cue_not_in_scene", f"cue {c['id']} anchors to word {wi} outside scene {c['scene']}")
        if words[wi]["source"] == "interpolated":
            add("warning", "cue_on_interpolated_word", f"cue {c['id']} sits on word {wi} {words[wi]['text']!r}, which has no ASR counterpart")
    return iss


def compare_legacy(tl, T):
    """Shadow check: the timeline must reproduce what the composition already loads (`window.__T`: duration, scenes,
    cues, captions). Returns {ok, checked, diffs}; a diff beyond EPS (the legacy file's rounding) is listed, never hidden."""
    diffs, checked = [], 0

    def close(a, b):
        return abs(a - b) <= EPS

    if not close(tl["duration_s"], T["duration"]):
        diffs.append(f"duration {tl['duration_s']} vs {T['duration']}")
    checked += 1
    by = {s["id"]: s for s in tl["scenes"]}
    for sc in T["scenes"]:
        t = by.get(sc["id"])
        checked += 2
        if not t:
            diffs.append(f"scene {sc['id']} missing from timeline")
            continue
        if not close(t["t0"], sc["start"]):
            diffs.append(f"scene {sc['id']} start {t['t0']} vs {sc['start']}")
        if not close(t["t1"] - t["t0"], sc["dur"]):
            diffs.append(f"scene {sc['id']} duration {round(t['t1'] - t['t0'], 3)} vs {sc['dur']}")
    for sid, caps in T["captions"].items():
        t = by.get(sid)
        if not t:
            continue
        mine = [w for w in tl["words"][t["w0"]:t["w1"] + 1]]
        checked += 1
        if len(mine) != len(caps):
            diffs.append(f"scene {sid}: {len(mine)} timeline words vs {len(caps)} legacy captions")
            continue
        for w, (text, s, e) in zip(mine, caps):
            checked += 3
            if w["text"] != text or not close(w["t0"], s) or not close(w["t1"], e):
                diffs.append(f"scene {sid} word {w['i']} {w['text']!r} {w['t0']}-{w['t1']} vs {text!r} {s}-{e}")
    mine_cues = {}
    for c in tl["cues"]:
        mine_cues.setdefault(c["scene"], []).append(c["t"])
    for sid, times in T["cues"].items():
        checked += 1
        got = mine_cues.get(sid, [])
        if len(got) != len(times) or any(not close(a, b) for a, b in zip(got, times)):
            diffs.append(f"scene {sid} cue times {got} vs {times}")
    return {"ok": not diffs, "checked": checked, "diffs": diffs}


def build_from_project(proj, job=None):
    """Derive timeline/1 from a project's EXISTING artifacts (read-only): storyboard/scene-plan.resolved.json,
    audio/timing.json, captions/word-timings.json and the per-line whisper transcripts audio/txNN/transcript.json."""
    proj = Path(proj)
    plan = json.loads((proj / "storyboard/scene-plan.resolved.json").read_text(encoding="utf-8"))
    timing = json.loads((proj / "audio/timing.json").read_text(encoding="utf-8"))
    caps = json.loads((proj / "captions/word-timings.json").read_text(encoding="utf-8"))
    lines, cues, matched, total, wer_num = [], [], 0, 0, 0.0
    for n, (sc, ts) in enumerate(zip(plan["scenes"], timing["scenes"]), 1):
        words = [tuple(w) for w in caps[sc["id"]]]
        tx = proj / "audio" / f"tx{n:02d}" / "transcript.json"
        asr = [w["text"] for w in json.loads(tx.read_text(encoding="utf-8"))] if tx.exists() else None
        sources = word_sources([w[0] for w in words], asr) if asr is not None else ["interpolated"] * len(words)
        lines.append({"id": sc["id"], "title": sc["title"], "t0": ts["start"], "t1": round(ts["start"] + ts["dur"], 3),
                      "words": words, "sources": sources})
        for c in sc.get("direction", {}).get("cues", []):
            cues.append({"scene": sc["id"], "word": c["at"], "do": c.get("do", "")})
    for st in timing.get("alignment", {}).values():
        matched += st["matched"]
        total += st["script_words"]
        wer_num += st["wer"] * st["script_words"]
    mix = proj / "project/assets/mix.wav"
    audio = {"source": "generated", "sha256": hashlib.sha256(mix.read_bytes()).hexdigest() if mix.exists() else None,
             "rights": {"status": "unassessed", "note": "no rights vocabulary approved yet (roadmap G3)"}}
    alignment = {"match_ratio": round(matched / total, 4) if total else 1.0, "wer": round(wer_num / total, 4) if total else 0.0}
    return build_timeline(job or proj.name, timing.get("fps", 30), timing["total_s"], lines, cues, audio, alignment)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Shadow-mode timeline/1: derive, validate and compare against the legacy timings.js")
    ap.add_argument("project")
    ap.add_argument("-o", "--out", help="write timeline.json here (default: do not write)")
    a = ap.parse_args(argv)
    proj = Path(a.project)
    tl = build_from_project(proj)
    issues = validate(tl)
    legacy = proj / "project/timings.js"
    cmp = None
    if legacy.exists():
        cmp = compare_legacy(tl, json.loads(legacy.read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";")))
    if a.out:
        Path(a.out).write_text(json.dumps(tl, indent=1), encoding="utf-8")
    print(json.dumps({"job": tl["job"], "words": len(tl["words"]), "scenes": len(tl["scenes"]), "cues": len(tl["cues"]),
                      "issues": issues, "legacy_comparison": cmp}, indent=1))
    return 1 if any(i["level"] == "error" for i in issues) or (cmp and not cmp["ok"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
