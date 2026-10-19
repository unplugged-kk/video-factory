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

Optional extension keys: audio_cues, transition_windows, beats, markers describe sound and transitions on the same clock.
Validation is additive and strict; existing timelines without these keys validate unchanged.
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
    iss.extend(_validate_extensions(tl, words, scenes))
    return iss


def _validate_extensions(tl, words, scenes):
    iss = []

    def add(level, code, msg):
        iss.append({"level": level, "code": code, "msg": msg})

    duration_s = tl.get("duration_s", 0.0)
    sids = [s["id"] for s in scenes]
    smap = {s["id"]: s for s in scenes}

    def check_unique_ids(items, label):
        seen = set()
        for item in items:
            iid = item.get("id")
            if iid in seen:
                add("error", "id_duplicate", f"duplicate id {iid!r} in {label}")
            seen.add(iid)

    audio_cues = tl.get("audio_cues")
    if audio_cues is not None:
        check_unique_ids(audio_cues, "audio_cues")
        for c in audio_cues:
            cid = c.get("id", "")
            kind = c.get("kind")
            if kind not in ("sfx", "duck", "music"):
                add("error", "audio_cue_kind", f"cue {cid}: kind {kind!r} not in ('sfx', 'duck', 'music')")
            scene_id = c.get("scene")
            if scene_id not in smap:
                add("error", "audio_cue_scene", f"cue {cid}: unknown scene {scene_id!r}")
            at = c.get("at", {})
            wi = at.get("word")
            offset_s = at.get("offset_s", 0.0)
            if not isinstance(wi, int) or not (0 <= wi < len(words)):
                add("error", "audio_cue_word", f"cue {cid}: word index {wi} not in words")
            else:
                w = words[wi]
                if scene_id in smap:
                    sc = smap[scene_id]
                    if not (sc["w0"] <= wi <= sc["w1"]):
                        add("error", "audio_cue_not_in_scene", f"cue {cid}: word {wi} outside scene {scene_id}")
                expected_t = round(w["t0"] + offset_s, 3)
                if abs(c.get("t", 0.0) - (w["t0"] + offset_s)) > EPS:
                    add("error", "audio_cue_time", f"cue {cid}: t {c.get('t')} differs from word start + offset {expected_t}")
                if w.get("source") == "interpolated":
                    add("warning", "audio_cue_on_interpolated_word", f"cue {cid}: sits on interpolated word {wi}")
            dur_s = c.get("dur_s")
            t = c.get("t", 0.0)
            if not isinstance(dur_s, (int, float)) or dur_s <= 0 or (t + dur_s > duration_s + EPS):
                add("error", "audio_cue_dur", f"cue {cid}: invalid dur_s {dur_s} (must be > 0 and t + dur_s <= duration_s)")
            level_db = c.get("level_db")
            if isinstance(level_db, bool) or not isinstance(level_db, (int, float)) or level_db > 0:
                add("error", "audio_cue_level", f"cue {cid}: invalid level_db {level_db} (must be number <= 0)")

    trans_windows = tl.get("transition_windows")
    if trans_windows is not None:
        check_unique_ids(trans_windows, "transition_windows")
        from contentos.intelligence import styles
        allowed_trans = styles.AXES["transition_family"]
        for tw in trans_windows:
            tw_id = tw.get("id", "")
            from_s = tw.get("from_scene")
            to_s = tw.get("to_scene")
            kind = tw.get("kind")
            if kind not in allowed_trans:
                add("error", "transition_kind", f"transition {tw_id}: kind {kind!r} not in {allowed_trans}")
            if from_s not in smap or to_s not in smap:
                add("error", "transition_scene", f"transition {tw_id}: unknown from/to scene ({from_s}, {to_s})")
            else:
                from_idx = sids.index(from_s)
                to_idx = sids.index(to_s)
                if to_idx != from_idx + 1:
                    add("error", "transition_scene", f"transition {tw_id}: scenes {from_s} and {to_s} are not adjacent")
                else:
                    boundary = smap[from_s]["t1"]
                    t0 = tw.get("t0", 0.0)
                    t1 = tw.get("t1", 0.0)
                    if t1 <= t0 or not (t0 <= boundary + EPS and t1 >= boundary - EPS):
                        add("error", "transition_window", f"transition {tw_id}: window [{t0}, {t1}] must have t1 > t0 and contain boundary {boundary}")

    beats = tl.get("beats")
    if beats is not None:
        prev_t = None
        for b in beats:
            t = b.get("t", 0.0)
            if not isinstance(t, (int, float)) or t < 0.0 - EPS or t > duration_s + EPS:
                add("error", "beat_order", f"beat t {t} outside [0, {duration_s}]")
            elif prev_t is not None and t < prev_t - 1e-9:
                add("error", "beat_order", f"beat t {t} is decreasing after {prev_t}")
            prev_t = t

    markers = tl.get("markers")
    if markers is not None:
        check_unique_ids(markers, "markers")
        for m in markers:
            mid = m.get("id", "")
            t = m.get("t", 0.0)
            if not isinstance(t, (int, float)) or t < 0.0 - EPS or t > duration_s + EPS:
                add("error", "marker_range", f"marker {mid}: t {t} outside [0, {duration_s}]")

    return iss


def add_extensions(tl, audio_cues=None, transition_windows=None, beats=None, markers=None):
    import copy
    out = copy.deepcopy(tl)
    words = out.get("words", [])
    if audio_cues is not None:
        processed_cues = []
        for c in audio_cues:
            item = copy.deepcopy(c)
            wi = item.get("word") if "word" in item else item.get("at", {}).get("word")
            offset_s = item.get("offset_s", item.get("at", {}).get("offset_s", 0.0))
            if "at" not in item:
                item["at"] = {"word": wi, "offset_s": offset_s}
            if "t" not in item and wi is not None and 0 <= wi < len(words):
                item["t"] = round(words[wi]["t0"] + offset_s, 3)
            item.pop("word", None)
            item.pop("offset_s", None)
            processed_cues.append(item)
        out["audio_cues"] = processed_cues
    if transition_windows is not None:
        out["transition_windows"] = copy.deepcopy(transition_windows)
    if beats is not None:
        out["beats"] = copy.deepcopy(beats)
    if markers is not None:
        out["markers"] = copy.deepcopy(markers)
    return out


def cue_budget(tl, max_per_minute):
    import math
    iss = []
    duration_s = tl.get("duration_s", 0.0)
    audio_cues = tl.get("audio_cues", [])
    sfx_times = sorted([c["t"] for c in audio_cues if c.get("kind") == "sfx"])

    if duration_s < 60.0:
        allowed = math.ceil(max_per_minute * duration_s / 60.0)
        if len(sfx_times) > allowed:
            iss.append({
                "level": "warning",
                "code": "cue_budget",
                "msg": f"{len(sfx_times)} sfx cues exceeds allowed budget of {allowed} for {duration_s:.1f}s video",
            })
    else:
        window_s = 60.0
        for i, t in enumerate(sfx_times):
            count = sum(1 for t2 in sfx_times[i:] if t2 <= t + window_s)
            if count > max_per_minute:
                iss.append({
                    "level": "warning",
                    "code": "cue_budget",
                    "msg": f"{count} sfx cues in 60s window starting at {t:.2f}s exceeds max {max_per_minute} per minute",
                })
                break
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
