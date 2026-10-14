"""The two background rules, enforced by measurement.

Rule A (inside one video): the scene backdrops must not all be the same. At least ceil(scenes/2) distinct backdrops,
never all identical, unless the plan declares an intentional motif (recorded, reported as a warning, not hidden).
  Measured from the rendered video (`scenes`) or from declared backdrop ids before compose (`plan`).
  This rule covers the BACKDROP only (frame margins, not the centre where content sits; foreground near a margin can add
  false variety, so the check errs toward passing). Layout and motion rhythm are judged by the independent critic.
Rule B (across videos): a new video's visual signature must differ from each of the last N shipped videos on at least
2 of 5 fields (structure, temperature, texture, base, accents). A series may declare `--shared accents` (and/or texture)
as brand tokens; those are then not counted, so a channel can keep its accent colour but not its whole look.

Per-scene backdrops (a composition that paints #s-<id> / #scene-<id> / #<id> / .scene-<id> / [data-scene] rules): the
signature is that of the DURATION-DOMINANT backdrop, the one whose scenes last longest in total (durations from the
timing file: scenes[].dur, or end-start). The distribution is always reported; a warning is always raised when more
than one backdrop is used (so `claim` needs --acknowledge-warnings); near-ties (top two within 5 points of total
duration) are flagged as ambiguous and Rule B is also evaluated for each tied candidate. Without usable scene durations
the signature falls back to the single global rule (#root, .scene, body) and says so.

Signature = {structure: radial|linear|flat|mesh|paper, temperature: warm|cool|neutral, texture: grid|noise|paper|none,
base: {hue: 0-11|null, tier: dark|dim|mid|light}, accents: [the two most used accent hue buckets]}. Hue buckets are 30 degrees wide; colours in
adjacent buckets count as the same family (teal and cyan are one family). Comparing hue buckets, not hex values,
is what stops "a slightly different blue" from passing as a new look.

Ledger: config/visual-languages.seed.json (Git; shipped videos) + <workspace>/intelligence/visual-languages.json
(written by `claim`, under a lock). Nothing here edits a project.

  python -m contentos.intelligence.visual used <job-id|dir>
  python -m contentos.intelligence.visual check <job-id|dir> [--window 5] [--shared accents] [--timing timing.json]
  python -m contentos.intelligence.visual claim <content-id> <job-id|dir> [--series S] [--shared accents] [--dry-run]
  python -m contentos.intelligence.visual scenes <video.mp4> (--timing timing.json | --starts 0,9.2,..) [--motif WHY]
  python -m contentos.intelligence.visual plan <plan.json>        # {"scenes":[{"id":..,"backdrop":..}],"motif":null}
"""
from __future__ import annotations

import argparse
import colorsys
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from .. import storage

REPO = Path(__file__).resolve().parent.parent.parent
SEED = REPO / "config" / "visual-languages.seed.json"
FIELDS = ("structure", "temperature", "texture", "base", "accents")
SHAREABLE = ("accents", "texture")
MIN_DIFFERENT = 2
WINDOW = 5
BACKDROP_TOLERANCE = 0.04      # RGB distance (0-1 scale) below which two scene margins count as the same backdrop
HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


class VisualError(Exception):
    pass


# ---- colour helpers -----------------------------------------------------------------------------------------------

def _rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _lum(rgb):
    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = map(lin, rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def tier(rgb):
    y = _lum(rgb)
    return "dark" if y < 0.03 else "dim" if y < 0.12 else "mid" if y < 0.5 else "light"


def hue_bucket(rgb):
    h, l, s = colorsys.rgb_to_hls(*rgb)
    if s < 0.15 or l < 0.02 or l > 0.98:
        return None
    return int(h * 360 // 30) % 12


def temperature(bucket):
    if bucket is None:
        return "neutral"
    return "warm" if bucket in (0, 1, 2, 11) else "cool" if bucket in (6, 7, 8, 9) else "neutral"


def _near(a, b):
    if a is None or b is None:
        return a is b
    d = abs(a - b) % 12
    return min(d, 12 - d) <= 1


def _accents_match(a, b):
    return all(any(_near(x, y) for y in b) for x in a) and all(any(_near(y, x) for x in a) for y in b)


# ---- signature from the composition's own CSS ---------------------------------------------------------------------

def _css_text(html_path):
    p = Path(html_path)
    text = p.read_text(encoding="utf-8", errors="replace")
    parts = [text]
    for href in re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]*href=["\']([^"\'#?]+)', text) + \
            re.findall(r'<link[^>]+href=["\']([^"\'#?]+\.css)', text):
        if "://" in href:
            continue
        css = (p.parent / href)
        if css.is_file():
            parts.append(css.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def _decl(css, selector_pattern):
    m = re.search(selector_pattern + r"\s*\{([^}]*)\}", css)
    if not m:
        return None
    b = re.search(r"background(?:-image)?\s*:\s*([^;}]+)", m.group(1))
    return b.group(1) if b else None


def _vars(css):
    return {k: v.strip() for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;}]+)", css)}


def _resolve(value, variables):
    for _ in range(3):
        value = re.sub(r"var\((--[\w-]+)\)", lambda m: variables.get(m.group(1), ""), value)
    return value


def signature_from_css(css, decl_override=None):
    """Signature of a composition. `decl_override` (a resolved background declaration) replaces the #root/.scene/body
    lookup; it is how the duration-dominant per-scene backdrop is used. Without it behaviour is unchanged."""
    variables = _vars(css)
    decl = decl_override
    if decl is None:
        for sel in (r"#root", r"\.scene\b", r"html\s*,\s*body", r"body"):
            decl = _decl(css, sel)
            if decl:
                decl = _resolve(decl, variables)
                if HEX.search(decl) or "gradient" in decl:
                    break
        if not decl and "--bg" in variables:
            decl = _resolve(variables["--bg"], variables)
    colors = [_rgb(m.group(0)) for m in HEX.finditer(decl or "")]
    if not colors:
        colors = [(0.03, 0.03, 0.05)]
    mean = tuple(sum(c[i] for c in colors) / len(colors) for i in range(3))
    radial, linear = (decl or "").count("radial-gradient"), (decl or "").count("linear-gradient")
    base_tier, base_hue = tier(mean), hue_bucket(mean)
    if radial >= 3:
        structure = "mesh"
    elif radial:
        structure = "radial"
    elif linear:
        structure = "linear"
    else:
        structure = "flat"
    low = css.lower()
    if re.search(r"#grid\b|\.grid-bg|bg-grid", low) or re.search(r"linear-gradient\([^)]*1px,\s*transparent\s*1px\)", (decl or "").lower() if decl_override is not None else low):
        texture = "grid"
    elif "feturbulence" in low or re.search(r"\.noise|#noise|grain", low):
        texture = "noise"
    elif "paper" in low or (base_tier == "light" and temperature(base_hue) == "warm"):
        texture = "paper"
    else:
        texture = "none"
    if base_tier == "light" and texture == "paper":
        structure = "paper"
    # accents: the design tokens first (saturated colours declared as CSS variables, ordered by how often var(--x) is used),
    # then any saturated colour in the CSS by frequency. Hue families, so teal and cyan count once.
    def accent_bucket(value):
        m = HEX.search(value or "")
        if not m:
            return None
        r = _rgb(m.group(0))
        h, l, s = colorsys.rgb_to_hls(*r)
        return hue_bucket(r) if s >= 0.45 and 0.25 <= l <= 0.8 else None
    tokens = {}
    for name, value in variables.items():
        b = accent_bucket(value)
        if b is not None:
            tokens[b] = tokens.get(b, 0) + css.count(f"var({name})") + 1
    counts = dict(tokens)
    if len(counts) < 2:                                      # no (or one) token: fall back to every saturated colour
        for m in HEX.finditer(css):
            b = accent_bucket(m.group(0))
            if b is not None:
                counts[b] = counts.get(b, 0) + 1
    fam = []
    for b, _ in sorted(counts.items(), key=lambda kv: -kv[1]):
        if not any(_near(b, f) for f in fam):
            fam.append(b)
    return {"structure": structure, "temperature": temperature(base_hue), "texture": texture,
            "base": {"hue": base_hue, "tier": base_tier}, "accents": fam[:2]}   # the two most used accent families, most used first


SCENE_RULE = re.compile(r"(#s-[\w-]+|#scene-[\w-]+|\.scene-[\w-]+|\[data-scene[^\]]*\])\s*\{([^}]*)\}")


def scene_backdrop_warnings(css):
    """KF-006. The signature is read from ONE rule (#root, else .scene, else body). If the composition paints its backdrops
    per scene (#s-*, #scene-*, .scene-*, [data-scene]), that rule can be stale or absent and the signature then describes a
    backdrop no scene shows. This does not change the signature; it says when it may not describe the video.
    What the signature *should* be for a per-scene video is an open decision (docs/video-intelligence/04-...)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    variables = _vars(css)
    scene_fills = {}
    for sel, body in SCENE_RULE.findall(css):
        m = re.search(r"background(?:-image|-color)?\s*:\s*([^;}]+)", body)
        if not m:
            continue
        v = _resolve(m.group(1), variables)
        cols = [_rgb(h.group(0)) for h in HEX.finditer(v)]
        if cols or "gradient" in v:
            mean = tuple(sum(c[i] for c in cols) / len(cols) for i in range(3)) if cols else (0.03, 0.03, 0.05)
            scene_fills[sel] = (tier(mean), hue_bucket(mean))
    if not scene_fills:
        return []
    root = _decl(css, r"#root")
    root = _resolve(root, variables) if root else None
    cols = [_rgb(h.group(0)) for h in HEX.finditer(root or "")]
    if root and (cols or "gradient" in root):
        mean = tuple(sum(c[i] for c in cols) / len(cols) for i in range(3)) if cols else (0.03, 0.03, 0.05)
        root_fill = (tier(mean), hue_bucket(mean))
    else:
        root_fill = None
    differs = [s for s, f in scene_fills.items() if root_fill is None or f[0] != root_fill[0] or not _near(f[1], root_fill[1])]
    if not differs:
        return []
    return [{"code": "per_scene_backdrops_not_in_signature", "severity": "warning",
             "stale_root": root_fill is not None, "scenes_differing": sorted(differs),
             "message": (f"signature is read from #root/.scene/body, but {len(differs)} scene rule(s) paint a different backdrop"
                         f"{'' if root_fill is None else ' than #root'}; the signature may not describe this video")}]


TIE_SHARE = 0.05          # top two backdrops within 5 points of the total duration are an ambiguous dominant
SCENE_SELECTORS = ("#s-{id}", "#scene-{id}", "#{id}", ".scene-{id}", '[data-scene="{id}"]', "[data-scene='{id}']")


def scene_durations(doc):
    """[(scene id, seconds)] and a list of problems from a timing document. Real shapes: ep3 timing.json
    scenes[]{id,start,dur}; ep2 scenes.json scenes[]{id,start,end}. Duration = dur, else end - start. Anything else (no id,
    non-number, bool, NaN/inf, <= 0, duplicate id) is reported and the scene is left out (duplicates keep both, flagged)."""
    out, problems, seen = [], [], set()
    scenes = (doc or {}).get("scenes") if isinstance(doc, dict) else None
    if not isinstance(scenes, list) or not scenes:
        return [], [{"code": "no_scenes", "message": "the timing document has no scenes[]"}]
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) 
    for i, sc in enumerate(scenes):
        sid = sc.get("id") if isinstance(sc, dict) else None
        if not isinstance(sid, str) or not sid:
            problems.append({"code": "scene_without_id", "index": i})
            continue
        if sid in seen:
            problems.append({"code": "duplicate_scene_id", "scene": sid})
        seen.add(sid)
        d = sc.get("dur")
        if d is None and num(sc.get("start")) and num(sc.get("end")):
            d = sc["end"] - sc["start"]
        if not num(d) or d <= 0:
            problems.append({"code": "invalid_duration", "scene": sid, "value": repr(sc.get("dur", sc.get("end")))})
            continue
        out.append((sid, float(d)))
    return out, problems


def _norm_decl(decl):
    return re.sub(r"\s+", " ", re.sub(r"!important", "", decl, flags=re.IGNORECASE)).strip().lower()


def _scene_decl(css, sid, variables):
    for fmt in SCENE_SELECTORS:
        m = re.search(re.escape(fmt.format(id=sid)) + r"\s*\{([^}]*)\}", css)
        if not m:
            continue
        b = re.search(r"background(?:-image|-color)?\s*:\s*([^;}]+)", m.group(1))
        if b:
            v = _resolve(b.group(1), variables)
            if HEX.search(v) or "gradient" in v:
                return _norm_decl(v)
    return None


def backdrop_profile(css, timing_doc):
    """Total duration per backdrop. A scene's backdrop is its own rule's background; a scene with none inherits the global
    one (#root/.scene/body). Returns None when per-scene durations are unusable (caller falls back to the global rule)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    variables = _vars(css)
    durs, problems = scene_durations(timing_doc)
    if not durs:
        return {"usable": False, "problems": problems, "backdrops": []}
    glob = None
    for sel in (r"#root", r"\.scene\b", r"html\s*,\s*body", r"body"):
        d = _decl(css, sel)
        if d:
            d = _resolve(d, variables)
            if HEX.search(d) or "gradient" in d:
                glob = _norm_decl(d)
                break
    groups, order = {}, []
    for sid, secs in durs:
        own = _scene_decl(css, sid, variables)
        key = own if own is not None else (glob if glob is not None else "(global default)")
        if key not in groups:
            groups[key] = {"decl": key, "scenes": [], "seconds": 0.0, "inherits_global": own is None}
            order.append(key)
        groups[key]["scenes"].append(sid)
        groups[key]["seconds"] += secs
    total = sum(g["seconds"] for g in groups.values())
    rows = [dict(g, seconds=round(g["seconds"], 3), share=round(g["seconds"] / total, 4)) for g in (groups[k] for k in order)]
    ranked = sorted(range(len(rows)), key=lambda i: (-round(rows[i]["seconds"], 3), i))     # equal seconds: earliest first
    top = rows[ranked[0]]
    tied = [rows[i] for i in ranked if top["share"] - rows[i]["share"] < TIE_SHARE]
    return {"usable": True, "total_seconds": round(total, 3), "backdrops": rows, "dominant": top,
            "ambiguous": len(tied) > 1, "tied": [t["decl"] for t in tied] if len(tied) > 1 else [], "problems": problems}


def signature_for(css, timing_doc=None):
    """(signature, basis). basis explains where the signature came from; it is recorded with a claim."""
    prof = backdrop_profile(css, timing_doc) if timing_doc is not None else None
    if not prof or not prof["usable"] or len(prof["backdrops"]) < 2:
        return signature_from_css(css), {"basis": "global-rule", "profile": prof}
    dom = prof["dominant"]
    return signature_from_css(css, decl_override=dom["decl"]), {"basis": "duration-dominant", "profile": prof}


def backdrop_warnings(css, timing_doc=None):
    """Warnings for Rule B. Multiple backdrops always warn. See the module docstring for the semantics."""
    prof = backdrop_profile(css, timing_doc) if timing_doc is not None else None
    if prof and prof["usable"] and len(prof["backdrops"]) >= 2:
        d = prof["dominant"]
        w = [{"code": "multiple_backdrops", "severity": "warning", "basis": "duration-dominant",
              "dominant_share": d["share"], "dominant_seconds": d["seconds"], "backdrops": len(prof["backdrops"]),
              "message": (f"{len(prof['backdrops'])} backdrops in use; the signature is the duration-dominant one "
                          f"({d['share']:.0%} of {prof['total_seconds']}s, scenes {','.join(d['scenes'])}); Rule B does not see the others")}]
        if prof["ambiguous"]:
            w.append({"code": "dominant_backdrop_ambiguous", "severity": "warning", "tied": prof["tied"],
                      "message": f"top backdrops are within {TIE_SHARE:.0%} of total duration; picked the longest (earliest on equal), Rule B also evaluated per candidate"})
        for pr in prof["problems"]:
            w.append({"code": "timing_" + pr["code"], "severity": "warning", **{k: v for k, v in pr.items() if k != "code"}})
        return w
    base = scene_backdrop_warnings(css)
    if base and (prof is None or not prof["usable"]):
        reason = "no timing file found or it has no usable scene durations" if prof is None else "scene durations unusable: " + ", ".join(p["code"] for p in prof["problems"])
        base.append({"code": "scene_durations_unavailable", "severity": "warning", "message": reason + "; falling back to the global rule"})
    return base


def load_timing(composition, explicit=None):
    """Timing document for a composition: --timing, else <job>/audio/timing.json or <job>/scenes.json next to the
    composition's folder (project/, portrait/, hf/ ...) or in the same folder. First one that has scenes[] wins."""
    cands = [Path(explicit)] if explicit else []
    c = Path(composition).parent
    for base in (c, c.parent):
        cands += [base / "audio" / "timing.json", base / "scenes.json", base / "timing.json"]
    for p in cands:
        if p.is_file():
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                if explicit:
                    raise VisualError(f"unreadable timing file {p}") from None
                continue
            if isinstance(doc, dict) and isinstance(doc.get("scenes"), list) and doc["scenes"]:
                return doc
            if explicit:
                return doc
    if explicit:
        raise VisualError(f"timing file {explicit} not found")
    return None


COMPOSITIONS = ("project/index.html", "portrait/index.html", "hf/index.html", "index.html", "landscape/index.html")


def find_composition(target):
    t = Path(target)
    d = t if t.is_dir() else (storage.find_job_dir(str(target)) if storage.valid_job_id(str(target)) else None)
    if d is None:
        raise VisualError(f"{target}: not a directory and not a known job id")
    for rel in COMPOSITIONS:
        if (d / rel).is_file():
            return d / rel
    raise VisualError(f"no composition (index.html) found under {d}")


def signature_of(target):
    return signature_from_css(_css_text(find_composition(target)))


# ---- Rule B -------------------------------------------------------------------------------------------------------

def differing(a, b, shared=()):
    """Fields on which two signatures count as different (fields in `shared` are brand tokens and are skipped)."""
    out = []
    for f in FIELDS:
        if f in shared:
            continue
        if f == "base":
            same = a["base"]["tier"] == b["base"]["tier"] and _near(a["base"]["hue"], b["base"]["hue"])
        elif f == "accents":
            same = _accents_match(a["accents"], b["accents"])
        else:
            same = a[f] == b[f]
        if not same:
            out.append(f)
    return out


def ledger_path():
    return storage.workspace_root() / "intelligence" / "visual-languages.json"


def _read_entries(path):
    p = Path(path)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("entries", [])
    except (OSError, ValueError) as exc:
        raise VisualError(f"unreadable ledger {p}: {exc}") from exc


def ledger(seed=SEED, workspace_ledger=None):
    return _read_entries(seed) + _read_entries(workspace_ledger if workspace_ledger is not None else ledger_path())


def rule_b(signature, entries, *, content_id=None, window=WINDOW, shared=()):
    bad = [s for s in shared if s not in SHAREABLE]
    if bad:
        raise VisualError(f"only {SHAREABLE} may be shared brand tokens, not {bad}")
    recent = [e for e in entries if e["content_id"] != content_id][-window:]
    results = []
    for e in recent:
        diff = differing(signature, e["signature"], shared)
        results.append({"against": e["content_id"], "different_on": diff, "ok": len(diff) >= MIN_DIFFERENT})
    failing = [r for r in results if not r["ok"]]
    return {"rule": "B", "ok": not failing, "required": MIN_DIFFERENT, "shared": list(shared), "compared": results,
            "duplicates": [r["against"] for r in failing]}


def claim(content_id, signature, *, series=None, shared=(), window=WINDOW, dry_run=False, seed=SEED, path=None,
          warnings=(), acknowledge_warnings=False, basis=None, require_ok=True):
    """Record a look in the ledger.

    `require_ok` decides whether Rule B gates the write. The default (True) refuses to record a look that repeats a
    recent one, which is what the CLI wants: a recorded look is one that passed. Callers that must keep a faithful
    history instead - the pipeline does, after a successful export - pass require_ok=False, because a duplicate that
    actually shipped is exactly what the next check needs to see. The verdict is returned either way.
    """
    storage.check_job_id(content_id)
    path = Path(path) if path else ledger_path()
    with storage.file_lock(path.with_suffix(".lock")):
        entries = ledger(seed, path)
        res = rule_b(signature, entries, content_id=content_id, window=window, shared=shared)
        if warnings:
            res["warnings"] = list(warnings)
        if res["ok"] and warnings and not dry_run and not acknowledge_warnings:
            res["ok"] = False
            res["refused"] = "signature may not describe this video (see warnings); re-run with --acknowledge-warnings to record anyway"
            return res
        if (res["ok"] or not require_ok) and not dry_run:
            mine = [e for e in _read_entries(path) if e["content_id"] != content_id]
            mine.append({"content_id": content_id, "series": series, "signature": signature, "shared": list(shared),
                         "recorded_at": storage.now_iso(), "source": "claim", **({"basis": basis} if basis else {})})
            storage.write_json_atomic(path, {"schema": "visual-languages/1", "entries": mine})
            res["recorded"] = True
        return res


# ---- Rule A -------------------------------------------------------------------------------------------------------

def _frame_ring(video, t, size=32):
    """Mean RGB of the top and side margins of one frame (not the bottom: captions live there, not the centre: content)."""
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
           "-vf", f"scale={size}:{size}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=60)
    if r.returncode or len(r.stdout) < size * size * 3:
        raise VisualError(f"cannot read a frame at {t:.2f}s from {video}")
    px = r.stdout
    def at(x, y):
        i = (y * size + x) * 3
        return px[i] / 255, px[i + 1] / 255, px[i + 2] / 255
    m = max(2, size // 12)
    ring = [at(x, y) for y in range(size) for x in range(size) if y < m or (x < m or x >= size - m) and y < size * 0.8]
    return tuple(sum(p[i] for p in ring) / len(ring) for i in range(3))


def scene_backdrop(video, t):
    ring = _frame_ring(video, t)
    return {"hue": hue_bucket(ring), "tier": tier(ring), "rgb": [round(c, 3) for c in ring]}


def _same_backdrop(a, b):
    dist = math.dist(a["rgb"], b["rgb"])
    return a["tier"] == b["tier"] and _near(a["hue"], b["hue"]) and dist < BACKDROP_TOLERANCE


def _groups(items, same):
    parent = list(range(len(items)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if same(items[i], items[j]):
                parent[find(i)] = find(j)
    return len({find(i) for i in range(len(items))})


def rule_a_result(distinct, scenes, motif=None):
    need = math.ceil(scenes / 2) if scenes > 1 else 1
    ok = distinct >= need and not (scenes > 1 and distinct == 1)
    status = "pass" if ok else ("warn" if motif else "fail")
    return {"rule": "A", "ok": ok or bool(motif), "status": status, "scenes": scenes, "distinct_backdrops": distinct,
            "required": need, "motif": motif if not ok else None,
            "note": "backdrop only; layout and motion rhythm are judged by the critic"}


def rule_a_from_video(video, starts, total, motif=None):
    bounds = list(starts) + [total]
    backdrops = [scene_backdrop(video, (bounds[i] + bounds[i + 1]) / 2) for i in range(len(starts))]
    res = rule_a_result(_groups(backdrops, _same_backdrop), len(backdrops), motif)
    res["backdrops"] = backdrops
    return res


def rule_a_from_plan(plan):
    ids = [s.get("backdrop") for s in plan["scenes"]]
    if not all(ids):
        raise VisualError("every scene needs a 'backdrop' id (a name you choose for its background treatment)")
    return rule_a_result(len(set(ids)), len(ids), plan.get("motif"))


# ---- CLI ----------------------------------------------------------------------------------------------------------

def _duration(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True, timeout=60)
    try:
        return float(r.stdout.strip())
    except ValueError as exc:
        raise VisualError(f"cannot read the duration of {video}") from exc


def starts_from_timing(doc, video):
    """Scene start times from a timing file: scenes[].start (ep3 style) or a resolved scene plan's scenes[].t0."""
    scenes = doc.get("scenes") or []
    key = "start" if scenes and "start" in scenes[0] else "t0"
    if not scenes or key not in scenes[0]:
        raise VisualError("the timing file has no scenes with 'start' or 't0'")
    total = doc.get("total_s") or doc.get("total") or _duration(video)
    return [float(sc[key]) for sc in scenes], float(total)


def _report(res):
    print(json.dumps(res, indent=2))


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m contentos.intelligence.visual", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("used"); u.add_argument("target")
    u.add_argument("--timing")
    c = sub.add_parser("check"); c.add_argument("target"); c.add_argument("--timing"); c.add_argument("--as", dest="content_id", help="content id to exclude from the comparison (default: the folder name)"); c.add_argument("--window", type=int, default=WINDOW); c.add_argument("--shared", nargs="*", default=[])
    cl = sub.add_parser("claim"); cl.add_argument("content_id"); cl.add_argument("target"); cl.add_argument("--series"); cl.add_argument("--timing")
    cl.add_argument("--window", type=int, default=WINDOW); cl.add_argument("--shared", nargs="*", default=[]); cl.add_argument("--dry-run", action="store_true"); cl.add_argument("--acknowledge-warnings", action="store_true")
    s = sub.add_parser("scenes"); s.add_argument("video"); s.add_argument("--timing"); s.add_argument("--starts"); s.add_argument("--motif")
    p = sub.add_parser("plan"); p.add_argument("plan")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "used":
            comp = find_composition(a.target)
            css, timing = _css_text(comp), load_timing(comp, a.timing)
            sig, info = signature_for(css, timing)
            _report(sig)
            for w in backdrop_warnings(css, timing):
                print(f"warning: {w['message']}", file=sys.stderr)
            return 0
        if a.cmd == "check":
            comp = find_composition(a.target)
            css, timing = _css_text(comp), load_timing(comp, a.timing)
            sig, info = signature_for(css, timing)
            cid = a.content_id or (Path(a.target).name if Path(a.target).is_dir() else a.target)
            res = rule_b(sig, ledger(), content_id=cid, window=a.window, shared=a.shared)
            warns = backdrop_warnings(css, timing)
            extra = {"basis": info["basis"]}
            prof = info["profile"]
            if prof and prof.get("usable") and len(prof["backdrops"]) >= 2:
                extra["backdrop_distribution"] = [{"decl": b["decl"], "scenes": b["scenes"], "seconds": b["seconds"], "share": b["share"]} for b in prof["backdrops"]]
                if prof["ambiguous"]:
                    extra["tie_sensitivity"] = [{"candidate": d, "rule_b_ok": rule_b(signature_from_css(css, decl_override=d), ledger(), content_id=cid, window=a.window, shared=a.shared)["ok"]} for d in prof["tied"]]
            _report({"signature": sig, **res, **extra, **({"warnings": warns} if warns else {})})
            return 0 if res["ok"] else 1
        if a.cmd == "claim":
            comp = find_composition(a.target)
            css, timing = _css_text(comp), load_timing(comp, a.timing)
            sig, info = signature_for(css, timing)
            res = claim(a.content_id, sig, series=a.series, shared=a.shared, window=a.window, dry_run=a.dry_run,
                        warnings=backdrop_warnings(css, timing), acknowledge_warnings=a.acknowledge_warnings, basis=info["basis"])
            _report(res)
            return 0 if res["ok"] else 1
        if a.cmd == "scenes":
            if a.timing:
                starts, total = starts_from_timing(json.loads(Path(a.timing).read_text()), a.video)
            elif a.starts:
                starts, total = [float(x) for x in a.starts.split(",")], _duration(a.video)
            else:
                raise VisualError("give --timing or --starts")
            res = rule_a_from_video(a.video, starts, total, a.motif)
            _report(res)
            return 0 if res["ok"] else 1
        if a.cmd == "plan":
            res = rule_a_from_plan(json.loads(Path(a.plan).read_text()))
            _report(res)
            return 0 if res["ok"] else 1
    except (VisualError, storage.StorageError, OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(_main())
