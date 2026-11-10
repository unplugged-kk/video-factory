"""Contract fixtures are synthetic approvals, never production promotion."""
import copy
import json

import pytest

from contentos.ceh_contract import digest, load_catalog, seal_catalog, seal_entry, select_capabilities, validate_catalog


@pytest.fixture
def entry():
    return seal_entry({
        "id": "kinetic-typography", "name": "Kinetic typography", "description": "Readable text motion guidance",
        "version": "1.0.0", "status": "APPROVED", "capabilities": ["kinetic-typography"], "categories": ["motion"], "tags": [],
        "resources": [{"id": "CEH-0001", "url": "https://example.org/source", "pinned_commit": "a" * 40}],
        "skills": [{"name": "kinetic-typography", "version": "1.0.0", "digest": "b" * 64}],
        "approval": {"status": "APPROVED", "by": "synthetic-test", "at": "2026-11-10T00:00:00Z", "evidence": ["test:approval"]},
        "licence": {"spdx": "MIT", "commercial": True, "restrictions": [], "review_evidence": ["test:licence"]},
        "requirements": {"runtimes": {"node": ">=20.0.0,<25.0.0"}, "dependencies": {"hyperframes": "0.8.114"}},
        "renderers": ["hyperframes"], "agents": ["codex"], "inputs": {"title": {"type": "string", "required": True}},
        "outputs": ["motion-plan"], "assets": [], "compatibility": {"languages": ["en"], "output_formats": ["mp4"]},
        "evaluation": {"evidence": ["test:case"], "benchmarks": ["test:render"], "visual_quality": None, "performance": None},
        "limitations": ["Synthetic fixture"], "deprecation": {"deprecated": False, "replacement": None, "reason": ""},
        "workflow": {"kind": "guidance", "steps": ["Prepare a readable title using the existing renderer."]},
    })


def catalog(entry):
    return seal_catalog([entry], generated="2026-11-10T00:00:00Z")


def select(doc, **overrides):
    args = {"task": "kinetic typography", "renderer": "hyperframes", "runtimes": {"node": "22.0.0"},
            "dependencies": {"hyperframes": "0.8.114"}, "inputs": {"title": "Hello"}, "agent": "codex",
            "language": "en", "output_format": "mp4"}
    return select_capabilities(doc, **{**args, **overrides})


def test_approved_capability_loads_and_selects_without_execution(entry, tmp_path):
    doc = catalog(entry)
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(doc))
    assert not load_catalog(path)["available"]
    assert not load_catalog(path, enabled=True)["available"]
    loaded = load_catalog(path, enabled=True, expected_digest=doc["digest"])
    assert loaded["available"] and not loaded["errors"]
    result = select(loaded["catalog"])
    assert result["selected"][0]["id"] == entry["id"]
    assert not result["rejected"]
    assert not load_catalog(path, enabled=True, expected_digest="0" * 64)["available"]


@pytest.mark.parametrize("change", [
    {"status": "CANDIDATE"},
    {"approval": {"status": "APPROVED", "by": "", "at": "x", "evidence": []}},
    {"licence": {"spdx": "PolyForm-Noncommercial-1.0.0", "commercial": True, "restrictions": [], "review_evidence": ["x"]}},
    {"licence": {"spdx": "CC-BY-NC-4.0", "commercial": True, "restrictions": [], "review_evidence": ["x"]}},
    {"deprecation": {"deprecated": True, "replacement": "new", "reason": "obsolete"}},
    {"resources": [{"id": "CEH-0001", "url": "https://example.org/source", "pinned_commit": "abc123"}]},
    {"evaluation": {"evidence": ["x"], "benchmarks": [], "visual_quality": None, "performance": None}},
    {"workflow": {"kind": "shell", "steps": ["touch /tmp/must-not-exist"]}},
    {"exec": "malicious command"},
])
def test_governance_and_schema_fail_closed_even_with_recomputed_digest(entry, change):
    doc = catalog(seal_entry({**entry, **change}))
    assert validate_catalog(doc)
    assert select(doc)["selected"] == []


@pytest.mark.parametrize("kwargs,reason", [
    ({"dependencies": {}}, "dependencies"),
    ({"dependencies": {"hyperframes": "0.9.30"}}, "dependencies"),
    ({"runtimes": {"node": "18.0.0"}}, "runtimes"),
    ({"renderer": "remotion"}, "renderer"),
    ({"inputs": {}}, "input"),
    ({"inputs": {"title": []}}, "input"),
    ({"agent": "unverified"}, "agent"),
    ({"language": "hi"}, "languages"),
    ({"output_format": "gif"}, "output_formats"),
    ({"task": "underwater footage"}, "task"),
])
def test_incompatibility_explained(entry, kwargs, reason):
    result = select(catalog(entry), **kwargs)
    assert result["selected"] == []
    assert any(reason in r for r in result["rejected"][0]["reasons"])


def test_corrupt_digest_and_duplicate_versions(entry):
    doc = catalog(entry)
    doc["entries"][0]["description"] = "tampered"
    assert any("digest" in x for x in validate_catalog(doc))
    duplicate = seal_entry({**entry, "version": "2.0.0"})
    doc = seal_catalog([entry, duplicate], generated="now")
    assert any("duplicate" in x for x in validate_catalog(doc))


@pytest.mark.parametrize("payload", ["{", 'null', '[]', '{"schema":NaN}', '{"schema":1,"schema":2}', '"' + 'x' * 2_000_001 + '"'])
def test_unavailable_or_malformed_catalog_returns_diagnostic(payload, tmp_path):
    path = tmp_path / "catalog.json"
    assert not load_catalog(path, enabled=True, expected_digest="0" * 64)["available"]
    path.write_text(payload)
    result = load_catalog(path, enabled=True, expected_digest="0" * 64)
    assert not result["available"] and result["entries"] == [] and result["errors"]


@pytest.mark.parametrize("key", ["approval", "licence", "requirements", "inputs", "evaluation", "deprecation", "workflow", "resources", "skills"])
def test_malformed_nested_types_are_diagnostics(entry, key):
    for value in (None, 12, [], "unexpected", {"unexpected": []}):
        broken = copy.deepcopy(entry)
        broken[key] = value
        assert validate_catalog(catalog(seal_entry(broken)))


def test_canonical_digest_is_order_independent(entry):
    assert digest(entry) == digest(dict(reversed(list(entry.items()))))
    doc = catalog(entry)
    assert validate_catalog(doc) == []


def test_generic_description_word_is_not_task_match(entry):
    result = select(catalog(entry), task="please plan readable sound effects")
    assert not result["selected"]
    assert result["rejected"][0]["reasons"] == ["task does not match capability"]


def test_oversized_environment_version_fails_closed(entry):
    result = select(catalog(entry), runtimes={"node": "9" * 5000 + ".0.0"})
    assert not result["selected"]
    assert "runtimes" in result["rejected"][0]["reasons"][0]


def test_oversized_catalog_version_is_invalid(entry):
    entry["version"] = "9" * 5000 + ".0.0"
    assert validate_catalog(catalog(seal_entry(entry)))


@pytest.mark.parametrize("environment", [
    {"runtimes": "node"}, {"dependencies": ["hyperframes"]}, {"inputs": "title"}, {"assets": "asset"},
    {"task": None}, {"renderer": []}, {"agent": {}}, {"language": []}, {"output_format": False}, {"commercial": "yes"},
])
def test_malformed_selection_environment_is_diagnostic(entry, environment):
    result = select(catalog(entry), **environment)
    assert not result["selected"] and result["errors"]


@pytest.mark.parametrize("licence", ["CC-BY-NC-4.0", "PolyForm-Noncommercial-1.0.0", "unknown", "NOASSERTION", "NONE", "unlicensed", "not verified"])
@pytest.mark.parametrize("required", [True, False])
def test_asset_licence_is_independent_of_code_licence(entry, licence, required):
    entry["assets"] = [{"id": "music", "required": required, "attribution": "Artist", "licence": licence}]
    doc = catalog(seal_entry(entry))
    assert any("asset licence" in error for error in validate_catalog(doc))
    assert not select(doc)["selected"]


def test_empty_provenance_is_not_consumable(entry):
    entry["resources"] = []
    assert any("pinned resource" in error for error in validate_catalog(catalog(seal_entry(entry))))
