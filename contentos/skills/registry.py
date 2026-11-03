"""Creative-skill registry: build from the vendored bundle, validate, discover, route, and report.

Source inputs (vendored byte-for-byte, hash-verified): contentos/skills/library/{MANIFEST.json, config/skill-catalog.json,
config/style-registry.yaml, skills/*/SKILL.md, core-skills/*/SKILL.md}. Output: config/creative-skills.json.

Stable ids: creative skills keep the bundle's catalog id (1-79). Core workflow skills get string ids `core:<name>` so they
never renumber the creative shortcuts. The registry is a build product: run `python -m contentos.skills build` after
changing the library or a probe-relevant dependency; `verify` fails if the checked-in file is stale.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

from . import classify, probe as probe_mod

ROOT = Path(__file__).resolve().parent.parent.parent
LIB = Path(__file__).resolve().parent / "library"
REGISTRY = ROOT / "config/creative-skills.json"
SCHEMA = "creative-skills/1"
STATUSES = ("integrated-and-tested", "integrated-but-not-fully-tested", "already-supported", "adapted-with-fallback",
            "blocked-by-dependency", "blocked-by-incompatibility", "not-integrated")

# Recorded render evidence. A skill appears here only after a real render was inspected; see docs/video-intelligence/09-*.md.
# Fill via `python -m contentos.skills evidence --skill X --job J --note N`; build merges config/creative-skills.evidence.json.
EVIDENCE_FILE = ROOT / "config/creative-skills.evidence.json"

CORE = {   # bundle core skill -> (status, existing implementation, note)
    "video-director": ("already-supported", [".claude/skills/video-director/SKILL.md", "contentos/production/direction.py", "contentos/production/director.py"],
                       "The factory's own video-director (sceneplan/1 + registry validation) is authoritative. The bundle copy is a reference only and is NOT installed under .claude/skills (name collision)."),
    "script-to-storyboard": ("already-supported", ["contentos/production/sceneplan.py", "contentos/scenekit/planner.py"],
                             "Script lines become timed scenes with intent classification, authored visuals and a visual-plan.json; word alignment via production/align.py."),
    "style-architect": ("already-supported", ["contentos/intelligence/designs.py", "contentos/intelligence/styles.py", "contentos/scenekit/styles.py", "config/design-library.json"],
                        "Three registries already exist (design library, style cards, scenekit styles). The bundle style-registry is mapped onto them (`styles` section), not added as a fourth."),
    "reference-video-analyzer": ("adapted-with-fallback", ["contentos/skills/analyze.py", "contentos/competitor.py"],
                                 "Local file analysis implemented (cuts, pacing, loudness, palette, contact sheet). URL analysis needs yt-dlp, whose installed binary is broken (x86 'bad CPU type'); no typography/OCR or transcript extraction."),
    "factory-skill-integrator": ("integrated-and-tested", ["contentos/skills/registry.py", "contentos/skills/probe.py", "tests/test_creative_skills.py"],
                                 "This registry, probe, router and verifier are the integrator."),
    "video-qa-critic": ("already-supported", ["contentos/production/critic.py", "contentos/qa.py", "contentos/production/visual_gate.py", ".claude/skills/explainer-visual-qa/SKILL.md"],
                        "Existing critic, 9-check QA and visual gate are authoritative; scenekit adds variety-report.json. No second QA system was added."),
    "publishing-packager": ("adapted-with-fallback", ["contentos/pipeline.py", "contentos/export.py", "contentos/production/platforms.py"],
                            "s_package/s_export write title, description, tags, sidecar; publish is a dry run. Thumbnail images are not built (capabilities.json: planned)."),
}

# bundle style-registry id -> factory implementation (scenekit style, style card, design-library entry) or None
STYLE_MAP = {
    "technical-explainer": {"scenekit": "clean-explainer"},
    "code-first": {"scenekit": "code-first"},
    "cinematic-documentary": {"scenekit": "cinematic-documentary", "card": "slow-parallax-story"},
    "kinetic-type": {"scenekit": "kinetic-type", "card": "kinetic-typography"},
    "editorial-collage": {"scenekit": "editorial-magazine", "note": "editorial layout only; paper collage texture and cutout transitions are not built"},
    "data-visualization": {"scenekit": "blueprint-architecture", "card": "blueprint-diagram"},
    "illustrated-story": {"scenekit": None, "note": "no illustration/character primitives exist; Track B agent-authored only"},
    "music-lyric": {"scenekit": None, "note": "needs audio-synchronised lyric timing; no lyric scene type exists; Track B agent-authored with supplied audio"},
    "news-editorial": {"scenekit": "kinetic-type", "note": "approximation only; no lower third / ticker primitive"},
    "experimental-motion": {"scenekit": None, "note": "experiments only, outside production"},
}

_STOP = set("a an the of to and or in on with for your you my me is are be it its as at by from that this into over like every each new one two how what".split())


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_library() -> list[str]:
    """Return problems; empty = every vendored file matches the bundle MANIFEST and nothing extra is present."""
    m = json.loads((LIB / "MANIFEST.json").read_text())
    problems = []
    listed = {f["path"] for f in m["files"]}
    for f in m["files"]:
        p = LIB / f["path"]
        if not p.exists():
            problems.append(f"missing {f['path']}")
        elif _sha(p) != f["sha256"]:
            problems.append(f"modified {f['path']}")
    for p in LIB.rglob("*"):
        rel = p.relative_to(LIB).as_posix()
        if p.is_file() and rel not in listed and rel != "MANIFEST.json" and p.name != ".DS_Store":
            problems.append(f"unlisted {rel}")
    return problems


def _tags(entry: dict, text_desc: str) -> list[str]:
    words = re.findall(r"[a-z][a-z0-9\-]{2,}", f"{entry['name'].replace('-', ' ')} {text_desc} {entry['category'].replace('-', ' ')}".lower())
    return sorted({w for w in words if w not in _STOP})[:24]


def build(probe: dict | None = None) -> dict:
    probe = probe or probe_mod.probe()
    cat = json.loads((LIB / "config/skill-catalog.json").read_text())
    evidence = json.loads(EVIDENCE_FILE.read_text()) if EVIDENCE_FILE.exists() else {}
    skills = []
    for e in cat["skills"]:
        p = LIB / e["path"]
        text = p.read_text()
        c = classify.classify(e, text)
        d = classify.decide(c, probe)
        ev = evidence.get(e["name"])
        status = d["status"]
        if c["scenekit"] and status != "blocked-by-dependency":
            status = "adapted-with-fallback"
            d["fallbacks_used"].append({"capability": "render.scenekit", "fallback": f"scenekit style `{c['scenekit'][0]}`: {c['scenekit'][1]}"})
        if ev and status in ("integrated-but-not-fully-tested",) and ev.get("fidelity") == "full":
            status = "integrated-and-tested"
        skills.append({
            "id": e["id"], "name": e["name"], "kind": "creative", "category": e["category"], "role": c["role"],
            "description": e["description"], "tags": _tags(e, e["description"]),
            "path": f"contentos/skills/library/{e['path']}", "sha256": _sha(p),
            "inputs_required": c["inputs_required"], "requires": c["requires"], "missing": d["missing"],
            "execution": "track-a-scenekit" if c["scenekit"] else "track-b-agent-authored",
            "scenekit_style": c["scenekit"][0] if c["scenekit"] else None,
            "renderer": "hyperframes", "status": status, "readiness": classify.readiness(c, status), "fallbacks": d["fallbacks_used"], "blockers": d["blockers"],
            "limitations": d["limitations"] + ([f"approximation: {c['scenekit'][1]}"] if c["scenekit"] else [])
            + ([] if ev or e["id"] == 0 else ["recipe registered and routable, but never rendered by this integration: treat its output quality as unknown"]),
            "ip_sensitive": c["ip_sensitive"], "evidence": ev,
            "invoke": (f"python -m contentos.skills plan --skill {e['name']} --script SPEC.yaml" if c["scenekit"]
                       else f"agent: read {e['path']} then author a HyperFrames composition (Track B); inputs: {', '.join(c['inputs_required']) or 'script'}"),
        })
    for name, (status, impl, note) in CORE.items():
        p = LIB / "core-skills" / name / "SKILL.md"
        fm = yaml.safe_load(p.read_text().split("---")[1])
        skills.append({"id": f"core:{name}", "name": name, "kind": "core-workflow", "category": "core-workflow", "role": "workflow",
                       "description": fm["description"], "tags": _tags({"name": name, "category": "core workflow"}, fm["description"]),
                       "path": f"contentos/skills/library/core-skills/{name}/SKILL.md", "sha256": _sha(p), "inputs_required": [],
                       "requires": ["render.hyperframes"], "missing": [], "execution": "existing-implementation", "renderer": "hyperframes",
                       "status": status, "readiness": "ready-to-run", "fallbacks": [], "blockers": [], "limitations": [note], "implementation": impl,
                       "ip_sensitive": None, "evidence": evidence.get(f"core:{name}"), "invoke": f"see implementation: {impl[0]}"})
    st = yaml.safe_load((LIB / "config/style-registry.yaml").read_text())
    styles = [{**s, "factory": STYLE_MAP.get(s["id"], {"scenekit": None, "note": "unmapped"})} for s in st["styles"]]
    return {"schema": SCHEMA, "bundle": json.loads((LIB / "MANIFEST.json").read_text())["bundle_version"],
            "bundle_manifest_sha256": _sha(LIB / "MANIFEST.json"), "numbering": cat["numbering"],
            "probe": probe, "skills": skills, "styles": styles}


def load(path: Path = REGISTRY) -> dict:
    return json.loads(path.read_text())


def validate(reg: dict) -> list[str]:
    errs = []
    ids = [s["id"] for s in reg["skills"]]
    names = [s["name"] for s in reg["skills"]]
    if len(set(ids)) != len(ids): errs.append("duplicate ids")
    if len(set(names)) != len(names): errs.append("duplicate names")
    creative = sorted(i for i in ids if isinstance(i, int))
    if creative != list(range(1, len(creative) + 1)): errs.append("creative ids are not a contiguous 1..N run (renumbered?)")
    probe_caps = set(reg["probe"])
    for s in reg["skills"]:
        w = f"skill {s['id']} {s['name']}"
        if s["status"] not in STATUSES: errs.append(f"{w}: bad status {s['status']}")
        if not (ROOT / s["path"]).exists(): errs.append(f"{w}: path missing")
        elif _sha(ROOT / s["path"]) != s["sha256"]: errs.append(f"{w}: SKILL.md changed since registry build")
        for r in s["requires"]:
            if r not in probe_caps: errs.append(f"{w}: requires unknown capability {r}")
        if s["status"] in ("blocked-by-dependency", "blocked-by-incompatibility", "not-integrated") and not s["blockers"] and not s["limitations"]:
            errs.append(f"{w}: {s['status']} needs a stated reason")
        if s["status"] == "integrated-and-tested" and not (s.get("evidence") or s["kind"] == "core-workflow"):
            errs.append(f"{w}: integrated-and-tested without evidence")
        if s["status"] == "adapted-with-fallback" and not (s["fallbacks"] or s["kind"] == "core-workflow"):
            errs.append(f"{w}: adapted-with-fallback without a fallback")
        if s["execution"] == "track-a-scenekit":
            from ..scenekit import styles as sk
            if s["scenekit_style"] not in sk.STYLES: errs.append(f"{w}: unknown scenekit style")
        for imp in s.get("implementation", []):
            if not (ROOT / imp).exists(): errs.append(f"{w}: implementation {imp} missing")
    for st in reg["styles"]:
        sk_id = st["factory"].get("scenekit")
        if sk_id:
            from ..scenekit import styles as sk
            if sk_id not in sk.STYLES: errs.append(f"style {st['id']}: unknown scenekit style {sk_id}")
    return errs


def stale(reg: dict) -> bool:
    """True if rebuilding now (same probe) would give a different registry body than the checked-in one."""
    now = build(probe=reg["probe"])
    return now != reg


# ---- discovery and routing -----------------------------------------------------------------------------------------

def find(reg: dict, ref) -> dict | None:
    for s in reg["skills"]:
        if str(s["id"]) == str(ref) or s["name"] == str(ref) or s["id"] == f"core:{ref}":
            return s
    return None


def route(reg: dict, request: str, have: list[str] | None = None, include_blocked: bool = False, limit: int = 5) -> list[dict]:
    """Rank creative skills for a free-text request. `have` lists input kinds the user can supply (song, footage, ...).
    Never auto-picks: returns candidates with reasons, missing inputs and fallbacks so the director can recommend then ask."""
    q = set(re.findall(r"[a-z][a-z0-9\-]{2,}", request.lower())) - _STOP
    m = re.fullmatch(r"\s*(?:/numbered-video\s+)?#?(\d+)\s*", request)
    if m:
        s = find(reg, int(m.group(1)))
        return [{"id": s["id"], "name": s["name"], "score": 100, "reasons": ["numbered request resolved via catalog"], **_brief(s, have)}] if s else []
    out = []
    for s in reg["skills"]:
        if s["kind"] != "creative":
            continue
        if s["status"].startswith("blocked") and not include_blocked:
            continue
        hit = sorted(q & set(s["tags"]))
        name_hit = [w for w in q if w in s["name"]]
        score = len(hit) + 3 * len(name_hit)
        if q & {"explainer", "explain"} and s["category"] == "explainers-and-motion-graphics": score += 2
        if not score:
            continue
        out.append({"id": s["id"], "name": s["name"], "score": score, "reasons": [f"matches: {', '.join(hit[:6])}"] + ([f"name: {', '.join(name_hit)}"] if name_hit else []),
                    **_brief(s, have)})
    return sorted(out, key=lambda r: (-r["score"], bool(r["missing_inputs"]), str(r["id"])))[:limit]


def _brief(s, have):
    have = set(have or [])
    miss = [i for i in s["inputs_required"] if i not in have and not (i == "script_or_topic" and "script" in have)]
    return {"status": s["status"], "readiness": s["readiness"], "execution": s["execution"], "missing_inputs": miss, "missing_capabilities": s["missing"],
            "fallbacks": [f["fallback"] for f in s["fallbacks"]], "blockers": s["blockers"], "limitations": s["limitations"]}


EFFECT_GROUPS = {   # effects that fight over the same pixels cannot stack
    "behind-subject": {"depth-ui-reel", "magazine-cover", "hindi-pastel-reel-edit", "instagram-ui-hinglish", "red-kinetic-collage-edit"},
    "grade-and-frame": {"rgb-glitch-live", "neon-outline", "cinema-scope", "dark-red-timeline-motion-graphics", "red-kinetic-collage-edit"},
    "caption-layout": {"kinetic-talking-head-edit", "personal-short-form-reels", "talking-head-edit", "podcast-reel-edit"},
}


def compat(reg: dict, names: list[str]) -> dict:
    ss = [find(reg, n) for n in names]
    unknown = [n for n, s in zip(names, ss) if s is None]
    if unknown:
        return {"compatible": False, "reasons": [f"unknown skill: {', '.join(unknown)}"]}
    why = []
    fmts = [s["name"] for s in ss if s["role"] == "format"]
    if len(fmts) > 1: why.append(f"two whole-video formats ({', '.join(fmts)}): pick one; formats own the scene grammar")
    for g, members in EFFECT_GROUPS.items():
        hit = [s["name"] for s in ss if s["name"] in members]
        if len(hit) > 1: why.append(f"{', '.join(hit)} compete for the same layer ({g})")
    foot = [s["name"] for s in ss if "footage" in s["inputs_required"]]
    plain = [s["name"] for s in ss if s["role"] == "format" and "footage" not in s["inputs_required"]]
    if foot and plain:
        why.append(f"footage-based {', '.join(foot)} cannot ride on {', '.join(plain)}, which has no footage")
    if len([s for s in ss if s["role"] == "effect"]) > 3: why.append("more than 3 stacked effects: readability risk")
    blocked = [s["name"] for s in ss if s["status"].startswith("blocked")]
    if blocked: why.append(f"blocked: {', '.join(blocked)}")
    return {"compatible": not why, "reasons": why or ["no conflict found by the group rules (this is a rule check, not a render test)"],
            "combined_requires": sorted({r for s in ss for r in s["requires"]}),
            "combined_inputs": sorted({i for s in ss for i in s["inputs_required"]})}


def ledger_markdown(reg: dict) -> str:
    rows = ["| id | skill | category | status | readiness | execution | inputs needed | missing capability / blocker | evidence |", "|---|---|---|---|---|---|---|---|---|"]
    for s in sorted(reg["skills"], key=lambda s: (s["kind"] != "creative", str(s["id"]).zfill(3))):
        gap = "; ".join(s["blockers"]) or ", ".join(f"{m}" for m in s["missing"]) or "-"
        ev = (s["evidence"] or {}).get("job") if s.get("evidence") else None
        rows.append(f"| {s['id']} | {s['name']} | {s['category']} | `{s['status']}` | {s['readiness']} | {s['execution']} | {', '.join(s['inputs_required']) or '-'} | {gap[:160]} | {ev or '-'} |")
    return "\n".join(rows)
