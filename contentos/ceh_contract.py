"""Read-only CEH catalog contract. No imports, installs, subprocesses or code loading.

Digests detect mutation, not publisher identity. Consumers bind the whole catalog
through an independently configured expected digest and keep integration opt-in.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from pathlib import Path

SCHEMA = "ceh-video-factory-catalog/2"
MAX_BYTES = 2_000_000
HEX = re.compile(r"[0-9a-f]{64}")
VERSION = re.compile(r"[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
RESTRICTED_LICENCE = re.compile(r"noncommercial|non-commercial|CC-BY-NC|NOASSERTION|^NONE$|unknown|unlicensed|not verified", re.I)
ENTRY_KEYS = {
    "id", "name", "description", "version", "status", "capabilities", "categories", "tags", "resources", "skills",
    "approval", "licence", "requirements", "renderers", "agents", "inputs", "outputs", "assets", "compatibility",
    "evaluation", "limitations", "deprecation", "workflow", "digest",
}


def digest(value: dict) -> str:
    payload = {k: v for k, v in value.items() if k != "digest"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def seal_entry(entry: dict) -> dict:
    return {**entry, "digest": digest(entry)}


def seal_catalog(entries: list[dict], *, generated: str) -> dict:
    value = {"schema": SCHEMA, "generated": generated, "entries": sorted(entries, key=lambda e: (e["id"], e["version"]))}
    return {**value, "digest": digest(value)}


def _strings(value, *, nonempty=False) -> bool:
    return isinstance(value, list) and (bool(value) or not nonempty) and all(isinstance(v, str) and v.strip() for v in value)


def _object(value, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _version(value) -> bool:
    return isinstance(value, str) and VERSION.fullmatch(value) is not None


def _constraint(value) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"(?:>=|<=|==|>|<)?[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}(?:,(?:>=|<=|==|>|<)?[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6})*", value))


def _entry_errors(e: dict) -> list[str]:
    errors = []
    if not _object(e, ENTRY_KEYS):
        return ["entry fields do not match schema"]
    for key in ("id", "name", "description"):
        if not _text(e[key]):
            errors.append(f"{key} must be nonempty text")
    if not isinstance(e["id"], str) or not ID.fullmatch(e["id"]):
        errors.append("invalid id")
    if not _version(e["version"]):
        errors.append("version must be numeric major.minor.patch")
    if e["status"] != "APPROVED":
        errors.append("entry is not explicitly APPROVED")
    for key in ("capabilities", "categories", "tags", "renderers", "agents", "outputs", "limitations"):
        if not _strings(e[key], nonempty=key in ("capabilities", "renderers", "outputs")):
            errors.append(f"invalid {key}")
    if not isinstance(e["resources"], list) or not e["resources"]:
        errors.append("at least one pinned resource source required")
    else:
        for source in e["resources"]:
            if not _object(source, {"id", "url", "pinned_commit"}) or not _text(source.get("id")) or not isinstance(source.get("url"), str) \
                    or not source["url"].startswith("https://") or not isinstance(source.get("pinned_commit"), str) \
                    or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", source["pinned_commit"]):
                errors.append("source provenance requires HTTPS URL and full pinned commit")
    if not isinstance(e["skills"], list) or not e["skills"]:
        errors.append("at least one versioned skill reference required")
    else:
        for skill in e["skills"]:
            if not _object(skill, {"name", "version", "digest"}) or not _text(skill.get("name")) \
                    or not _version(skill.get("version")) or not isinstance(skill.get("digest"), str) or not HEX.fullmatch(skill["digest"]):
                errors.append("invalid skill reference")
    a = e["approval"]
    if not _object(a, {"status", "by", "at", "evidence"}) or a.get("status") != "APPROVED" \
            or not _text(a.get("by")) or not _text(a.get("at")) or not _strings(a.get("evidence"), nonempty=True):
        errors.append("explicit approval actor, timestamp and evidence required")
    lic = e["licence"]
    if not _object(lic, {"spdx", "commercial", "restrictions", "review_evidence"}) or not _text(lic.get("spdx")) \
            or lic.get("commercial") is not True or not _strings(lic.get("restrictions")) \
            or not _strings(lic.get("review_evidence"), nonempty=True):
        errors.append("commercial licence review required")
    elif RESTRICTED_LICENCE.search(lic["spdx"]):
        errors.append("restricted or unknown licence is not consumable")
    req = e["requirements"]
    if not _object(req, {"runtimes", "dependencies"}):
        errors.append("invalid requirements")
    else:
        for group in req:
            if not isinstance(req[group], dict) or not all(_text(k) and _constraint(v) for k, v in req[group].items()):
                errors.append(f"invalid {group} version constraints")
    if not isinstance(e["inputs"], dict):
        errors.append("invalid inputs")
    else:
        for name, spec in e["inputs"].items():
            if not _text(name) or not _object(spec, {"type", "required"}) or spec.get("type") not in ("string", "number", "boolean", "object", "array") \
                    or type(spec.get("required")) is not bool:
                errors.append("invalid input specification")
    if not isinstance(e["assets"], list):
        errors.append("invalid assets")
    else:
        for asset in e["assets"]:
            if not _object(asset, {"id", "required", "attribution", "licence"}) or not _text(asset.get("id")) \
                    or type(asset.get("required")) is not bool or not _text(asset.get("attribution")) or not _text(asset.get("licence")):
                errors.append("invalid asset attribution")
            elif RESTRICTED_LICENCE.search(asset["licence"]):
                errors.append("restricted or unknown asset licence is not consumable")
    c = e["compatibility"]
    if not _object(c, {"languages", "output_formats"}) or not _strings(c.get("languages")) or not _strings(c.get("output_formats")):
        errors.append("invalid compatibility")
    ev = e["evaluation"]
    if not _object(ev, {"evidence", "benchmarks", "visual_quality", "performance"}) \
            or not _strings(ev.get("evidence"), nonempty=True) or not _strings(ev.get("benchmarks"), nonempty=True):
        errors.append("evaluation and benchmark evidence required")
    elif any(v is not None and (type(v) not in (int, float) or not 0 <= v <= 5) for v in (ev["visual_quality"], ev["performance"])):
        errors.append("scores must be null or between 0 and 5")
    dep = e["deprecation"]
    if not _object(dep, {"deprecated", "replacement", "reason"}) or dep.get("deprecated") is not False \
            or not isinstance(dep.get("replacement"), (str, type(None))) or not isinstance(dep.get("reason"), str):
        errors.append("deprecated capability is not consumable")
    w = e["workflow"]
    if not _object(w, {"kind", "steps"}) or w.get("kind") != "guidance" or not _strings(w.get("steps"), nonempty=True):
        errors.append("only descriptive guidance workflows are supported")
    if not isinstance(e["digest"], str) or not HEX.fullmatch(e["digest"]) or not hmac.compare_digest(e["digest"], digest(e)):
        errors.append("entry digest mismatch")
    return errors


def validate_catalog(doc) -> list[str]:
    """Validate strict v2 shape, governance and integrity; no schema package needed."""
    if not _object(doc, {"schema", "generated", "entries", "digest"}):
        return ["catalog fields do not match schema"]
    errors = []
    if doc["schema"] != SCHEMA:
        errors.append("unsupported catalog schema")
    if not _text(doc["generated"]):
        errors.append("generated timestamp required")
    if not isinstance(doc["entries"], list):
        return errors + ["entries must be a list"]
    seen = set()
    try:
        for entry in doc["entries"]:
            problems = _entry_errors(entry)
            label = entry.get("id", "?") if isinstance(entry, dict) else "?"
            errors.extend(f"{label}: {p}" for p in problems)
            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                if entry["id"] in seen:
                    errors.append(f"{label}: duplicate or conflicting capability versions")
                seen.add(entry["id"])
        if not isinstance(doc["digest"], str) or not HEX.fullmatch(doc["digest"]) or not hmac.compare_digest(doc["digest"], digest(doc)):
            errors.append("catalog digest mismatch")
    except (TypeError, ValueError, OverflowError):
        errors.append("catalog contains invalid JSON values")
    return errors


def _unique_object(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError(f"duplicate JSON key: {k}")
        result[k] = v
    return result


def load_catalog(path: Path | str | None, *, enabled=False, expected_digest: str | None = None) -> dict:
    """Fail closed and return diagnostics. No network, file discovery or mutation."""
    if not enabled:
        return {"available": False, "entries": [], "errors": ["CEH integration disabled"]}
    if not isinstance(expected_digest, str) or not HEX.fullmatch(expected_digest):
        return {"available": False, "entries": [], "errors": ["trusted expected catalog digest required"]}
    try:
        with Path(path).open("rb") as f:
            payload = f.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("catalog exceeds size limit")
        doc = json.loads(payload, object_pairs_hook=_unique_object, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
        errors = validate_catalog(doc)
        if not errors and not hmac.compare_digest(doc["digest"], expected_digest):
            errors.append("catalog does not match trusted digest")
        return {"available": not errors, "entries": [] if errors else doc["entries"], "errors": errors, "catalog": None if errors else doc}
    except (OSError, ValueError, TypeError, RecursionError) as e:
        return {"available": False, "entries": [], "errors": [f"catalog unavailable: {e}"]}


def _satisfies(actual: str, constraint: str) -> bool:
    if not _version(actual):
        return False
    value = tuple(map(int, actual.split(".")))
    for part in constraint.split(","):
        match = re.fullmatch(r"(>=|<=|==|>|<)?(\d+\.\d+\.\d+)", part)
        op, version = match.groups()
        wanted = tuple(map(int, version.split(".")))
        if not {None: value == wanted, "==": value == wanted, ">=": value >= wanted, "<=": value <= wanted,
                ">": value > wanted, "<": value < wanted}[op]:
            return False
    return True


def select_capabilities(doc: dict, *, task: str, renderer: str, runtimes: dict | None = None,
                        dependencies: dict | None = None, inputs: dict | None = None, assets: list[str] | None = None,
                        agent: str | None = None, language: str | None = None, output_format: str | None = None,
                        commercial: bool = True) -> dict:
    """Deterministic, non-executing plan. Call only after load_catalog binds trust."""
    errors = validate_catalog(doc)
    for name, value in (("runtimes", runtimes), ("dependencies", dependencies), ("inputs", inputs)):
        if value is not None and not isinstance(value, dict):
            errors.append(f"{name} environment must be an object")
    if assets is not None and not _strings(assets):
        errors.append("available assets must be a list of identifiers")
    if not _text(task) or not _text(renderer):
        errors.append("task and renderer must be nonempty strings")
    if any(v is not None and not _text(v) for v in (agent, language, output_format)) or type(commercial) is not bool:
        errors.append("invalid selection options")
    if errors:
        return {"selected": [], "rejected": [], "errors": errors}
    selected, rejected = [], []
    inputs, assets = inputs or {}, assets or []
    for entry in sorted(doc["entries"], key=lambda e: e["id"]):
        reasons = []
        normalized_task = " ".join(re.findall(r"[a-z0-9]+", task.lower()))
        phrases = [" ".join(re.findall(r"[a-z0-9]+", text.lower()))
                   for text in [entry["name"], *entry["capabilities"], *entry["tags"]]]
        if not any(phrase and f" {phrase} " in f" {normalized_task} " for phrase in phrases):
            reasons.append("task does not match capability")
        if renderer not in entry["renderers"]:
            reasons.append(f"unsupported renderer: {renderer}")
        if agent is not None and agent not in entry["agents"]:
            reasons.append(f"unsupported agent: {agent}")
        for group, available in (("runtimes", runtimes or {}), ("dependencies", dependencies or {})):
            for name, constraint in entry["requirements"][group].items():
                if name not in available or not isinstance(available[name], str) or not _satisfies(available[name], constraint):
                    reasons.append(f"{group}: {name} requires {constraint}")
        types = {"string": str, "number": (int, float), "boolean": bool, "object": dict, "array": list}
        for name, spec in entry["inputs"].items():
            if name not in inputs:
                if spec["required"]:
                    reasons.append(f"missing input: {name}")
            elif not isinstance(inputs[name], types[spec["type"]]) or (spec["type"] == "number" and isinstance(inputs[name], bool)):
                reasons.append(f"invalid input type: {name}")
        for asset in entry["assets"]:
            if asset["required"] and asset["id"] not in assets:
                reasons.append(f"missing asset: {asset['id']}")
        for key, requested in (("languages", language), ("output_formats", output_format)):
            supported = entry["compatibility"][key]
            if requested is not None and requested not in supported:
                reasons.append(f"unsupported {key}: {requested}")
        if commercial and not entry["licence"]["commercial"]:
            reasons.append("commercial use prohibited")
        if reasons:
            rejected.append({"id": entry["id"], "reasons": reasons})
        else:
            selected.append({"id": entry["id"], "version": entry["version"], "digest": entry["digest"], "renderer": renderer,
                             "skills": entry["skills"], "workflow": entry["workflow"], "limitations": entry["limitations"],
                             "why": "approved, integrity verified, task and declared compatibility satisfied"})
    return {"selected": selected, "rejected": rejected, "errors": []}
