"""Motion catalogue: which technique solves which communication problem, ranked with the reasons shown.

config/motion-catalogue.json (Git, seed) is joined to config/capabilities.json (Git, the validated registry, never
modified). Run evidence lives in <workspace>/intelligence/catalogue-evidence.json and overrides the seed's confidence and
evidence_count for the ids it names; without it every entry stays `unverified`.

  python -m contentos.intelligence.catalogue validate
  python -m contentos.intelligence.catalogue query --purpose difference --content-type explainer --aspect 9:16
  python -m contentos.intelligence.catalogue show hf.blueprint:comparison-split

Ranking is plain addition of visible components (printed with every result), not a learned score:
  purpose match +3 each, content type match +2, aspect supported +1, simpler technique +1/0/-1 (low/medium/high),
  confidence bonus preferred +3, validated +2, experimental +1, unverified 0.
Unavailable, paid-when-not-allowed, or deprecated entries are excluded (deprecated with --include-deprecated)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import storage

REPO = Path(__file__).resolve().parent.parent.parent
SEED = REPO / "config" / "motion-catalogue.json"
CAPABILITIES = REPO / "config" / "capabilities.json"
SCHEMA = "motion-catalogue/1"
CONFIDENCE = ("unverified", "experimental", "validated", "preferred", "deprecated")
CONF_BONUS = {"preferred": 3, "validated": 2, "experimental": 1, "unverified": 0}
COMPLEXITY_BONUS = {"low": 1, "medium": 0, "high": -1}
ENTRY_FIELDS = {"purposes", "content_types", "aspects", "complexity", "accessibility", "validation", "evidence_count",
                "confidence", "seeded_by", "reviewed", "examples"}
USABLE = ("installed",)


class CatalogueError(Exception):
    pass


def _read(path, what):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CatalogueError(f"cannot read {what} {path}: {exc}") from exc


def evidence_path():
    return storage.workspace_root() / "intelligence" / "catalogue-evidence.json"


def load(seed=SEED, capabilities=CAPABILITIES, overlay=None):
    """Seed + evidence overlay, joined to the capability registry. Returns {id: entry-with-capability}."""
    doc, caps = _read(seed, "catalogue"), _read(capabilities, "capability registry")
    by_id = {c["id"]: c for c in caps["capabilities"]}
    if overlay is None:
        try:
            p = evidence_path()
            overlay = _read(p, "evidence overlay").get("entries", {}) if p.exists() else {}
        except storage.StorageError:
            overlay = {}
    out = {}
    for cid, e in doc["entries"].items():
        e = {**e, **{k: v for k, v in (overlay.get(cid) or {}).items() if k in ("confidence", "evidence_count", "examples")}}
        out[cid] = {**e, "id": cid, "capability": by_id.get(cid)}
    return out


def validate(seed=SEED, capabilities=CAPABILITIES):
    """Problems as strings: schema, unknown ids, missing coverage, bad vocabulary, impossible confidence."""
    doc, caps = _read(seed, "catalogue"), _read(capabilities, "capability registry")
    problems = []
    if doc.get("schema") != SCHEMA:
        problems.append(f"schema must be {SCHEMA!r}")
    vocab = doc.get("vocabulary", {})
    by_id = {c["id"]: c for c in caps["capabilities"]}
    want = {i for i, c in by_id.items() if c["kind"] in ("rule", "blueprint")}
    have = set(doc.get("entries", {}))
    for i in sorted(have - set(by_id)):
        problems.append(f"{i}: not in config/capabilities.json")
    for i in sorted(have & set(by_id) - want):
        problems.append(f"{i}: only rules and blueprints are catalogued (kind {by_id[i]['kind']})")
    for i in sorted(want - have):
        problems.append(f"{i}: in the registry but missing from the catalogue")
    for cid, e in doc.get("entries", {}).items():
        for k in e:
            if k not in ENTRY_FIELDS:
                problems.append(f"{cid}: unknown field {k!r}")
        for k in ENTRY_FIELDS - set(e):
            problems.append(f"{cid}: missing field {k!r}")
        for field, allowed in (("purposes", "purposes"), ("content_types", "content_types")):
            for v in e.get(field, []):
                if v not in vocab.get(allowed, []):
                    problems.append(f"{cid}: {field} value {v!r} is not in the vocabulary")
        if not e.get("purposes"):
            problems.append(f"{cid}: needs at least one purpose")
        if e.get("complexity") not in vocab.get("complexity", []):
            problems.append(f"{cid}: bad complexity {e.get('complexity')!r}")
        c = e.get("confidence")
        if c not in CONFIDENCE:
            problems.append(f"{cid}: bad confidence {c!r}")
        elif c != "unverified" and not e.get("evidence_count"):
            problems.append(f"{cid}: confidence {c!r} needs evidence_count > 0")
        if e.get("seeded_by", "").startswith("heuristic") and c in ("validated", "preferred") and not e.get("reviewed"):
            problems.append(f"{cid}: a heuristic seed cannot be {c!r} without review")
    return problems


def query(entries, *, purposes=(), content_type=None, aspect=None, allow_paid=False, include_deprecated=False, limit=10):
    """Ranked candidates, each with the components that produced its score."""
    ranked = []
    for cid, e in entries.items():
        cap = e["capability"]
        if cap is None or cap["status"] not in USABLE:
            continue
        if cap.get("paid") and not allow_paid:
            continue
        if e["confidence"] == "deprecated" and not include_deprecated:
            continue
        parts = {}
        hits = [p for p in purposes if p in e["purposes"]]
        if purposes and not hits:
            continue
        if hits:
            parts["purpose"] = 3 * len(hits)
        if content_type:
            if content_type in e["content_types"]:
                parts["content_type"] = 2
        if aspect and aspect in e["aspects"]:
            parts["aspect"] = 1
        parts["complexity"] = COMPLEXITY_BONUS[e["complexity"]]
        parts["confidence"] = CONF_BONUS.get(e["confidence"], 0)
        ranked.append({"id": cid, "name": cap["name"], "score": sum(parts.values()), "components": parts,
                       "purposes": e["purposes"], "complexity": e["complexity"], "confidence": e["confidence"],
                       "evidence_count": e["evidence_count"], "accessibility": e["accessibility"],
                       "fallback": cap.get("fallback")})
    ranked.sort(key=lambda r: (-r["score"], len(r["purposes"]), r["id"]))   # ties: the more specialised technique first
    return ranked[:limit]


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m contentos.intelligence.catalogue", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    q = sub.add_parser("query")
    q.add_argument("--purpose", action="append", default=[])
    q.add_argument("--content-type")
    q.add_argument("--aspect")
    q.add_argument("--allow-paid", action="store_true")
    q.add_argument("--include-deprecated", action="store_true")
    q.add_argument("--limit", type=int, default=8)
    q.add_argument("--json", action="store_true")
    s = sub.add_parser("show")
    s.add_argument("id")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "validate":
            problems = validate()
            for p in problems:
                print(p)
            print(f"{len(problems)} problem(s)")
            return 1 if problems else 0
        entries = load()
        if a.cmd == "show":
            e = entries.get(a.id)
            if not e:
                print(f"unknown id {a.id!r}", file=sys.stderr)
                return 2
            print(json.dumps({k: v for k, v in e.items() if k != "capability"}, indent=2))
            return 0
        rows = query(entries, purposes=a.purpose, content_type=a.content_type, aspect=a.aspect,
                     allow_paid=a.allow_paid, include_deprecated=a.include_deprecated, limit=a.limit)
        if a.json:
            print(json.dumps(rows, indent=2))
        for r in rows:
            if not a.json:
                comp = " ".join(f"{k}{v:+d}" for k, v in r["components"].items())
                print(f"{r['score']:>3}  {r['id']:46} {r['complexity']:6} {r['confidence']:12} ev={r['evidence_count']}  [{comp}]")
        return 0 if rows else 1
    except (CatalogueError, storage.StorageError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(_main())
