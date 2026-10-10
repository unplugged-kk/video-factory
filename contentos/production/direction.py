"""Read-only validator for the optional `direction` block of a `sceneplan/1` scene plan (Motion Director M1).

What it does:
  * loads and checks `config/capabilities.json` (schema "capabilities/1"): the only capabilities a director may name;
  * validates a scene plan: the existing sceneplan/1 contract, an optional top-level `brief`, and an optional per-scene
    `direction` block, including every capability reference;
  * returns actionable Issue objects (scene, field, offending value, what to do). It never rewrites a plan, never touches
    the resolver in sceneplan.py, never renders, and makes no network call.

Optional direction fields added in M2 (smallest extension; no schema bump): `reframe` (16:9 and 9:16 composition notes),
`verify` (details to fact-check) and `substituted_from` (the preferred but non-installed capability that a fallback replaced).

Capability statuses (see docs/factory-v2/11-motion-director-m1-report.md):
  installed    verified present and usable; allowed in production.
  available    known and usable after a documented prerequisite; a plan acknowledges it by listing the id in brief.opt_in.
  candidate    experimental; allowed only in mode="experimental" AND on a scene marked direction.experimental = true.
  unavailable  known but absent or blocked; always rejected.

CLI (exit 0 = ok, 1 = problems found, 2 = a file could not be read):
  python -m contentos.production.direction validate PLAN.json [--mode production|experimental] [--registry PATH]
  python -m contentos.production.direction registry [--registry PATH]
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = ROOT / "config" / "capabilities.json"

PLAN_SCHEMA = "sceneplan/1"
REGISTRY_SCHEMA = "capabilities/1"
STATUSES = ("installed", "available", "candidate", "unavailable")
KINDS = ("renderer", "skill", "house-rule", "rule", "blueprint", "native", "treatment", "lane", "tool", "ref")
CONTEXTS = ("hyperframes", "pre-render", "post-render", "alternate-renderer", "reference")
TECHNIQUE_KINDS = ("rule", "blueprint", "native", "treatment")   # what a scene's direction.technique may name
MODES = ("production", "experimental")
PURPOSES = ("hook", "setup", "mechanism", "example", "contrast", "recap", "cta")
TREATMENTS = ("text", "diagram", "stat", "ui-demo", "metaphor", "footage", "handdrawn", "static")
PERSONALITIES = ("calm-precise", "premium", "energetic", "playful")
MAX_TAKEAWAY_WORDS = 20
_ID = re.compile(r"^[a-z][a-z0-9.]*:[A-Za-z0-9][A-Za-z0-9._-]*$")
_CAMERA = re.compile(r"^(hold|push|pull-back|pan-to:\S+)$")

_ENTRY_REQUIRED = ("id", "name", "kind", "status", "purpose", "path", "context", "requires", "offline", "paid", "limitations", "fallback")
_ENTRY_OPTIONAL = ("status_reason", "roles")
_BRIEF_KEYS = ("audience", "takeaway", "arc", "tone", "personality", "renderer", "opt_in", "allow_ambient")
_DIRECTION_REQUIRED = ("purpose", "takeaway", "treatment", "technique")
_DIRECTION_OPTIONAL = ("focal", "why", "motion", "cues", "camera", "exit", "text_zone", "assets", "fallback", "checks", "experimental",
                     "reframe", "verify", "substituted_from")


class RegistryError(ValueError):
    """The capability registry is unreadable or malformed. `.problems` lists every problem found."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("capability registry invalid:\n  - " + "\n  - ".join(self.problems))


@dataclass(frozen=True)
class Issue:
    scene: str      # scene id, "#<index>" when it has none, or "(plan)" / "(brief)"
    field: str      # dotted field path, e.g. "direction.technique[1]"
    value: object   # the offending value
    message: str    # what is wrong and what to do

    def __str__(self):
        return f"scene {self.scene}: {self.field}: {self.message} (got {self.value!r})"


def _rel_problem(rel):
    """Syntactic check of a repository-relative path; returns a problem string or None. No filesystem access."""
    if not isinstance(rel, str) or not rel.strip():
        return "must be a non-empty string"
    if "\0" in rel or "\\" in rel:
        return "must use '/' separators and contain no NUL"
    p = PurePosixPath(rel)
    if p.is_absolute() or ".." in p.parts:
        return "must be relative and must not contain '..'"
    return None


def resolve_inside(root: Path, rel: str) -> Path:
    """Resolve `rel` under `root`; raise ValueError if it is unsafe or (after following symlinks) leaves `root`."""
    bad = _rel_problem(rel)
    if bad:
        raise ValueError(bad)
    base = Path(root).resolve()
    target = (base / rel).resolve()
    if target != base and base not in target.parents:
        raise ValueError("resolves outside the repository (symlink?)")
    return target


class Registry:
    """A validated, immutable view of capabilities.json. Built only by load_registry()."""

    def __init__(self, data, root, path):
        self.root = Path(root)
        self.path = Path(path)
        self.entries = {e["id"]: e for e in data["capabilities"]}
        self.verified = data.get("verified", {})

    def __contains__(self, cap_id):
        return cap_id in self.entries

    def get(self, cap_id):
        return self.entries.get(cap_id)

    def counts(self):
        out = {s: 0 for s in STATUSES}
        for e in self.entries.values():
            out[e["status"]] += 1
        return out

    def path_problem(self, cap_id):
        """None if the capability's path is absent from the registry or exists safely on disk; else a message."""
        rel = self.entries[cap_id]["path"]
        if rel is None:
            return None
        try:
            target = resolve_inside(self.root, rel)
        except ValueError as exc:
            return f"path {rel!r} {exc}"
        if not target.is_file():
            return f"path {rel!r} does not exist (vendored skills need `python scripts/upstream_skills.py sync`)"
        return None


def _validate_registry_data(data):
    problems = []
    if not isinstance(data, dict):
        return ["top level must be a JSON object"]
    if data.get("schema") != REGISTRY_SCHEMA:
        problems.append(f"schema must be {REGISTRY_SCHEMA!r}, got {data.get('schema')!r}")
    caps = data.get("capabilities")
    if not isinstance(caps, list) or not caps:
        problems.append("'capabilities' must be a non-empty list")
        return problems
    seen, by_id = set(), {}
    for i, e in enumerate(caps):
        tag = f"capabilities[{i}]"
        if not isinstance(e, dict):
            problems.append(f"{tag}: must be an object")
            continue
        cid = e.get("id")
        tag = f"{cid!r}" if isinstance(cid, str) else tag
        for k in _ENTRY_REQUIRED:
            if k not in e:
                problems.append(f"{tag}: missing required field {k!r}")
        for k in e:
            if k not in _ENTRY_REQUIRED + _ENTRY_OPTIONAL:
                problems.append(f"{tag}: unknown field {k!r}")
        if not isinstance(cid, str) or not _ID.match(cid):
            problems.append(f"{tag}: id must look like 'namespace:name', got {cid!r}")
            continue
        if cid in seen:
            problems.append(f"{tag}: duplicate id")
        seen.add(cid)
        by_id[cid] = e
        if e.get("kind") not in KINDS:
            problems.append(f"{tag}: kind {e.get('kind')!r} not one of {list(KINDS)}")
        if e.get("status") not in STATUSES:
            problems.append(f"{tag}: status {e.get('status')!r} not one of {list(STATUSES)}")
        for k in ("name", "purpose"):
            if k in e and not (isinstance(e[k], str) and e[k].strip()):
                problems.append(f"{tag}: {k} must be a non-empty string")
        if "path" in e and e["path"] is not None and _rel_problem(e["path"]):
            problems.append(f"{tag}: path {_rel_problem(e['path'])}, got {e['path']!r}")
        for k in ("offline", "paid"):
            if k in e and not isinstance(e[k], bool):
                problems.append(f"{tag}: {k} must be true or false")
        for k in ("context", "requires", "limitations", "roles"):
            if k in e and not (isinstance(e[k], list) and all(isinstance(x, str) and x for x in e[k])):
                problems.append(f"{tag}: {k} must be a list of non-empty strings")
        if isinstance(e.get("context"), list):
            for c in e["context"]:
                if c not in CONTEXTS:
                    problems.append(f"{tag}: context {c!r} not one of {list(CONTEXTS)}")
        if "fallback" in e and e["fallback"] is not None and not isinstance(e["fallback"], str):
            problems.append(f"{tag}: fallback must be a capability id or null")
        if e.get("status") in STATUSES and e.get("status") != "installed":
            if not (isinstance(e.get("status_reason"), str) and e["status_reason"].strip()):
                problems.append(f"{tag}: status {e['status']!r} requires a non-empty status_reason")
    for cid, e in by_id.items():
        for ref_field in ("requires", "fallback"):
            refs = e.get(ref_field)
            refs = [refs] if isinstance(refs, str) else (refs if isinstance(refs, list) else [])
            for r in refs:
                if not isinstance(r, str):
                    continue
                if r == cid:
                    problems.append(f"{cid!r}: {ref_field} refers to itself")
                elif r not in by_id:
                    problems.append(f"{cid!r}: {ref_field} {r!r} is not a registered capability")
                elif ref_field == "fallback" and by_id[r].get("status") != "installed":
                    problems.append(f"{cid!r}: fallback {r!r} must be installed (is {by_id[r].get('status')!r})")
                elif ref_field == "requires" and e.get("status") == "installed" and by_id[r].get("status") != "installed":
                    problems.append(f"{cid!r}: installed capability requires {r!r}, which is {by_id[r].get('status')!r}")
    return problems


def load_registry(path=None, root=None) -> Registry:
    """Load and structurally validate the registry. Raises RegistryError listing every problem. File existence of
    capability paths is NOT checked here (see check_registry), so plans that never touch a missing skill still validate."""
    path = Path(path) if path else REGISTRY_PATH
    root = Path(root) if root else path.resolve().parent.parent     # <root>/config/capabilities.json
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RegistryError([f"cannot read {path}: {exc}"]) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RegistryError([f"{path} is not valid JSON: {exc}"]) from exc
    problems = _validate_registry_data(data)
    if problems:
        raise RegistryError(problems)
    return Registry(data, root, path)


def check_registry(reg: Registry):
    """Compare the registry with the files on disk. Returns a sorted list of problem strings (empty = consistent)."""
    problems = []
    for cid in sorted(reg.entries):
        msg = reg.path_problem(cid)
        if msg:
            problems.append(f"{cid}: {msg}")
    anim = reg.root / ".claude/skills/hyperframes-animation"
    for kind, sub, prefix in (("rule", "rules", "hf.rule:"), ("blueprint", "blueprints", "hf.blueprint:")):
        d = anim / sub
        if not d.is_dir():
            continue
        on_disk = {f"{prefix}{p.stem}" for p in d.glob("*.md")}
        listed = {c for c, e in reg.entries.items() if e["kind"] == kind}
        for c in sorted(on_disk - listed):
            problems.append(f"{c}: file exists in {sub}/ but is not in the registry")
        for c in sorted(listed - on_disk):
            problems.append(f"{c}: registered {kind} has no file in {sub}/")
    craft = reg.root / ".claude/skills/explainer-motion-craft/SKILL.md"
    if craft.is_file():
        on_disk = {f"craft:{m}" for m in re.findall(r"^- \*\*(R\d+) ", craft.read_text(encoding="utf-8"), re.M)}
        listed = {c for c, e in reg.entries.items() if e["kind"] == "house-rule"}
        for c in sorted(on_disk ^ listed):
            problems.append(f"{c}: house rule differs between explainer-motion-craft and the registry")
    return problems


def load_plan(path):
    """Read a scene plan from disk without modifying it."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _is_anchor(a):
    return (isinstance(a, int) and not isinstance(a, bool) and a >= 0) or (isinstance(a, str) and bool(a.strip()))


def _nonempty_str(v):
    return isinstance(v, str) and bool(v.strip())


def validate_plan(plan, registry: Registry, mode="production"):
    """Validate `plan` against the sceneplan/1 contract and the registry. Pure: `plan` and `registry` are never modified.
    Returns a list of Issue (empty = valid). Plans without brief/direction validate exactly as before."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {list(MODES)}, got {mode!r}")
    issues = []

    def err(scene, field, value, message):
        issues.append(Issue(scene, field, value, message))

    if not isinstance(plan, dict):
        err("(plan)", "plan", type(plan).__name__, "scene plan must be a JSON object")
        return issues
    if plan.get("schema") != PLAN_SCHEMA:
        err("(plan)", "schema", plan.get("schema"), f"must be {PLAN_SCHEMA!r}; this validator supports only that contract")
    opt_in = []
    brief = plan.get("brief")
    allow_ambient = False
    if brief is not None:
        opt_in, allow_ambient = _validate_brief(brief, registry, err)
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        err("(plan)", "scenes", scenes, "must be a non-empty list")
        return issues
    seen_ids, last_int = set(), None
    for idx, sc in enumerate(scenes):
        label = sc.get("id") if isinstance(sc, dict) and _nonempty_str(sc.get("id")) else f"#{idx}"
        if not isinstance(sc, dict):
            err(label, "scene", sc, "must be an object")
            continue
        if not _nonempty_str(sc.get("id")):
            err(label, "id", sc.get("id"), "required non-empty string")
        elif sc["id"] in seen_ids:
            err(label, "id", sc["id"], "duplicate scene id")
        else:
            seen_ids.add(sc["id"])
        if "starts_at" not in sc or not _is_anchor(sc["starts_at"]):
            err(label, "starts_at", sc.get("starts_at"), "required: a word index >= 0 or a non-empty narration phrase")
        a = sc.get("starts_at")
        if isinstance(a, int) and not isinstance(a, bool):
            if last_int is not None and a <= last_int:
                err(label, "starts_at", a, f"word-index anchors must increase (previous scene starts at {last_int})")
            last_int = a
        else:
            last_int = None
        if "title" in sc and not _nonempty_str(sc["title"]):
            err(label, "title", sc["title"], "must be a non-empty string when present")
        if "direction" in sc:
            _validate_direction(label, sc["direction"], registry, mode, opt_in, allow_ambient, err)
    return issues


def _validate_brief(brief, registry, err):
    opt_in, allow_ambient = [], False
    if not isinstance(brief, dict):
        err("(brief)", "brief", brief, "must be an object")
        return opt_in, allow_ambient
    for k in brief:
        if k not in _BRIEF_KEYS:
            err("(brief)", f"brief.{k}", brief[k], f"unknown field; allowed: {list(_BRIEF_KEYS)}")
    for k in ("audience", "takeaway", "tone"):
        if k in brief and not _nonempty_str(brief[k]):
            err("(brief)", f"brief.{k}", brief[k], "must be a non-empty string")
    if "personality" in brief and brief["personality"] not in PERSONALITIES:
        err("(brief)", "brief.personality", brief["personality"], f"must be one of {list(PERSONALITIES)}")
    if "renderer" in brief and brief["renderer"] != "hyperframes":
        err("(brief)", "brief.renderer", brief["renderer"], "HyperFrames is the only renderer; use 'hyperframes' or omit")
    if "arc" in brief:
        arc = brief["arc"]
        if not (isinstance(arc, list) and arc and all(a in PURPOSES for a in arc)):
            err("(brief)", "brief.arc", arc, f"must be a non-empty list drawn from {list(PURPOSES)}")
    if "allow_ambient" in brief:
        if isinstance(brief["allow_ambient"], bool):
            allow_ambient = brief["allow_ambient"]
        else:
            err("(brief)", "brief.allow_ambient", brief["allow_ambient"], "must be true or false")
    if "opt_in" in brief:
        raw = brief["opt_in"]
        if not (isinstance(raw, list) and all(isinstance(x, str) for x in raw)):
            err("(brief)", "brief.opt_in", raw, "must be a list of capability ids")
        else:
            for n, cid in enumerate(raw):
                e = registry.get(cid)
                if e is None:
                    err("(brief)", f"brief.opt_in[{n}]", cid, _unknown_msg(cid, registry))
                elif e["status"] not in ("available", "candidate"):
                    err("(brief)", f"brief.opt_in[{n}]", cid, f"status is {e['status']!r}; opt-in applies only to 'available' or 'candidate' capabilities")
                else:
                    opt_in.append(cid)
    return opt_in, allow_ambient


def _unknown_msg(cid, registry):
    close = difflib.get_close_matches(str(cid), sorted(registry.entries), n=3, cutoff=0.6)
    hint = f"; did you mean {close}?" if close else ""
    return f"unknown capability id{hint} (ids come from config/capabilities.json)"


def _validate_direction(label, d, registry, mode, opt_in, allow_ambient, err):
    if not isinstance(d, dict):
        err(label, "direction", d, "must be an object")
        return
    for k in d:
        if k not in _DIRECTION_REQUIRED + _DIRECTION_OPTIONAL:
            err(label, f"direction.{k}", d[k], f"unknown field; allowed: {list(_DIRECTION_REQUIRED + _DIRECTION_OPTIONAL)}")
    for k in _DIRECTION_REQUIRED:
        if k not in d:
            err(label, f"direction.{k}", None, "required field is missing")
    if "purpose" in d and d["purpose"] not in PURPOSES:
        err(label, "direction.purpose", d["purpose"], f"must be one of {list(PURPOSES)}")
    if "treatment" in d and d["treatment"] not in TREATMENTS:
        err(label, "direction.treatment", d["treatment"], f"must be one of {list(TREATMENTS)}")
    if "takeaway" in d:
        t = d["takeaway"]
        if not _nonempty_str(t):
            err(label, "direction.takeaway", t, "must be a non-empty string")
        elif len(t.split()) > MAX_TAKEAWAY_WORDS:
            err(label, "direction.takeaway", t, f"at most {MAX_TAKEAWAY_WORDS} words; one scene, one takeaway")
    experimental = d.get("experimental", False)
    if not isinstance(experimental, bool):
        err(label, "direction.experimental", experimental, "must be true or false")
        experimental = False
    if experimental and mode == "production":
        err(label, "direction.experimental", True, "experimental scenes are not allowed in production mode; validate with mode='experimental' or remove the flag")
    for k in ("focal", "exit", "text_zone"):
        if k in d and not _nonempty_str(d[k]):
            err(label, f"direction.{k}", d[k], "must be a non-empty string when present")
    needs_fallback = False
    tech = d.get("technique")
    if "technique" in d:
        if not (isinstance(tech, list) and tech and all(isinstance(x, str) for x in tech)):
            err(label, "direction.technique", tech, "must be a non-empty list of capability ids")
        else:
            if len(set(tech)) != len(tech):
                err(label, "direction.technique", tech, "duplicate capability id")
            for n, cid in enumerate(tech):
                needs_fallback |= _check_ref(label, f"direction.technique[{n}]", cid, registry, mode, experimental, opt_in, err, technique=True)
    if "why" in d and not _nonempty_str(d["why"]):
        err(label, "direction.why", d["why"], "must be a non-empty string when present")
    elif "why" not in d and (experimental or d.get("treatment") in ("handdrawn", "footage") or "substituted_from" in d
                             or (isinstance(d.get("motion"), dict) and d["motion"].get("secondary"))):
        err(label, "direction.why", None, "required for experimental scenes, handdrawn/footage treatments, recorded substitutions and scenes with secondary motion: say why")
    fb = d.get("fallback")
    if "fallback" in d:
        if not isinstance(fb, str):
            err(label, "direction.fallback", fb, "must be a capability id")
        else:
            e = registry.get(fb)
            if e is None:
                err(label, "direction.fallback", fb, _unknown_msg(fb, registry))
            elif e["status"] != "installed":
                err(label, "direction.fallback", fb, f"fallback must be installed (is {e['status']!r})")
    elif needs_fallback:
        err(label, "direction.fallback", None, "required when a technique is 'available' or 'candidate': name an installed fallback capability")
    if "camera" in d and not (isinstance(d["camera"], str) and _CAMERA.match(d["camera"])):
        err(label, "direction.camera", d["camera"], "must be 'hold', 'push', 'pull-back' or 'pan-to:<element id>'; one move per scene")
    if "motion" in d:
        m = d["motion"]
        if not isinstance(m, dict):
            err(label, "direction.motion", m, "must be an object with primary/secondary/ambient")
        else:
            for k in m:
                if k not in ("primary", "secondary", "ambient"):
                    err(label, f"direction.motion.{k}", m[k], "unknown field; allowed: primary, secondary, ambient")
                elif not _nonempty_str(m[k]):
                    err(label, f"direction.motion.{k}", m[k], "must be a non-empty string")
            if m.get("ambient", "none") != "none" and not allow_ambient:
                err(label, "direction.motion.ambient", m["ambient"], "house rule R4: ambient motion is 'none' unless brief.allow_ambient is true")
    if "cues" in d:
        cues = d["cues"]
        if not isinstance(cues, list):
            err(label, "direction.cues", cues, "must be a list of {at, do}")
        else:
            for n, c in enumerate(cues):
                if not isinstance(c, dict) or set(c) != {"at", "do"}:
                    err(label, f"direction.cues[{n}]", c, "must be an object with exactly 'at' and 'do'")
                    continue
                if not _is_anchor(c["at"]):
                    err(label, f"direction.cues[{n}].at", c["at"], "must be a word index >= 0 or a non-empty narration phrase")
                if not _nonempty_str(c["do"]):
                    err(label, f"direction.cues[{n}].do", c["do"], "must be a non-empty string")
    if "assets" in d:
        assets = d["assets"]
        if not isinstance(assets, list):
            err(label, "direction.assets", assets, "must be a list of {ref, source, license}")
        else:
            for n, a in enumerate(assets):
                if not isinstance(a, dict) or set(a) != {"ref", "source", "license"}:
                    err(label, f"direction.assets[{n}]", a, "must be an object with exactly 'ref', 'source' and 'license'")
                    continue
                for k in ("ref", "source", "license"):
                    if not _nonempty_str(a[k]):
                        err(label, f"direction.assets[{n}].{k}", a[k], "must be a non-empty string")
                if _nonempty_str(a["license"]) and a["license"].strip().lower() == "unknown":
                    err(label, f"direction.assets[{n}].license", a["license"], "unknown licence blocks the scene; record the real licence or drop the asset")
    if "reframe" in d:
        rf = d["reframe"]
        if not (isinstance(rf, dict) and set(rf) == {"16:9", "9:16"} and all(_nonempty_str(v) for v in rf.values())):
            err(label, "direction.reframe", rf, "must be an object with exactly '16:9' and '9:16', each a non-empty composition note")
    if "verify" in d:
        vf = d["verify"]
        if not (isinstance(vf, list) and all(_nonempty_str(x) for x in vf)) or (isinstance(vf, list) and len(set(vf)) != len(vf)):
            err(label, "direction.verify", vf, "must be a list of unique non-empty strings (claims or details to fact-check)")
    if "substituted_from" in d:
        sf = d["substituted_from"]
        e = registry.get(sf) if isinstance(sf, str) else None
        if e is None:
            err(label, "direction.substituted_from", sf, _unknown_msg(sf, registry) if isinstance(sf, str) else "must be a capability id")
        elif e["status"] == "installed":
            err(label, "direction.substituted_from", sf, "an installed capability needs no substitution; remove this field or name the capability that was unavailable")
        elif isinstance(tech, list) and sf in tech:
            err(label, "direction.substituted_from", sf, "the substituted capability must not also be selected in technique")
    if "checks" in d:
        ch = d["checks"]
        if not (isinstance(ch, list) and all(_nonempty_str(x) for x in ch)) or (isinstance(ch, list) and len(set(ch)) != len(ch)):
            err(label, "direction.checks", ch, "must be a list of unique non-empty strings")


def _check_ref(label, field, cid, registry, mode, experimental, opt_in, err, technique):
    """Check one capability reference. Returns True when the capability needs a fallback (available/candidate)."""
    e = registry.get(cid)
    if e is None:
        err(label, field, cid, _unknown_msg(cid, registry))
        return False
    if technique and e["kind"] not in TECHNIQUE_KINDS and e["status"] != "unavailable":
        err(label, field, cid, f"kind {e['kind']!r} cannot be a scene technique; allowed kinds: {list(TECHNIQUE_KINDS)}")
    status = e["status"]
    if status == "unavailable":
        err(label, field, cid, f"unavailable: {e['status_reason']}")
        return False
    if status == "candidate":
        if mode != "experimental":
            err(label, field, cid, f"candidate capability is rejected in production mode: {e['status_reason']}")
        elif not experimental:
            err(label, field, cid, "candidate capability requires direction.experimental = true on this scene")
        return True
    if status == "available":
        if cid not in opt_in:
            err(label, field, cid, f"available only after a prerequisite ({e['status_reason']}); acknowledge it by listing the id in brief.opt_in")
        return True
    problem = registry.path_problem(cid)
    if problem:
        err(label, field, cid, f"registered as installed but {problem}")
    return False


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m contentos.production.direction", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="validate a scene plan (read-only)")
    v.add_argument("plan")
    v.add_argument("--mode", choices=MODES, default="production")
    v.add_argument("--registry", default=None)
    r = sub.add_parser("registry", help="check the capability registry against files on disk")
    r.add_argument("--registry", default=None)
    args = ap.parse_args(argv)
    try:
        reg = load_registry(args.registry)
    except RegistryError as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.cmd == "registry":
        problems = check_registry(reg)
        print("registry: " + ", ".join(f"{n} {s}" for s, n in reg.counts().items()))
        for p in problems:
            print("  -", p)
        return 1 if problems else 0
    try:
        plan = load_plan(args.plan)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read plan {args.plan}: {exc}", file=sys.stderr)
        return 2
    issues = validate_plan(plan, reg, mode=args.mode)
    for i in issues:
        print(i)
    print(f"{'OK' if not issues else 'FAILED'}: {len(issues)} issue(s) [{args.mode} mode]")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(_main())
