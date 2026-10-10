"""Motion catalogue: strict against the registry, honest about evidence, ranked with visible reasons."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos.intelligence import catalogue  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def docs(tmp_path):
    seed = json.loads(catalogue.SEED.read_text())
    caps = json.loads(catalogue.CAPABILITIES.read_text())
    def write(seed_doc=None, caps_doc=None):
        s, c = tmp_path / "seed.json", tmp_path / "caps.json"
        s.write_text(json.dumps(seed_doc or seed)); c.write_text(json.dumps(caps_doc or caps))
        return s, c
    return seed, caps, write


def test_shipped_catalogue_is_valid_and_complete():
    assert catalogue.validate() == []
    entries = catalogue.load(overlay={})
    assert len(entries) == 70 and all(e["capability"] for e in entries.values())


def test_every_entry_starts_unverified_with_no_invented_evidence():
    e = catalogue.load(overlay={})
    assert {x["confidence"] for x in e.values()} == {"unverified"} and sum(x["evidence_count"] for x in e.values()) == 0
    assert all(not x["reviewed"] for x in e.values())


def test_unknown_id_and_missing_coverage_are_reported(docs):
    seed, caps, write = docs
    s = copy.deepcopy(seed)
    s["entries"]["hf.rule:does-not-exist"] = s["entries"].pop("hf.rule:svg-path-draw")
    problems = catalogue.validate(*write(s))
    assert any("does-not-exist: not in config/capabilities.json" in p for p in problems)
    assert any("svg-path-draw: in the registry but missing" in p for p in problems)


def test_unknown_field_bad_vocabulary_and_unearned_confidence_are_rejected(docs):
    seed, caps, write = docs
    s = copy.deepcopy(seed)
    e = s["entries"]["hf.rule:svg-path-draw"]
    e["bonus"] = 1
    e["purposes"] = ["vibes"]
    e["confidence"] = "validated"
    problems = " | ".join(catalogue.validate(*write(s)))
    assert "unknown field 'bonus'" in problems and "'vibes' is not in the vocabulary" in problems
    assert "needs evidence_count > 0" in problems
    e["evidence_count"] = 2
    assert "cannot be 'validated' without review" in " | ".join(catalogue.validate(*write(s)))
    e["reviewed"] = True
    del e["bonus"]
    e["purposes"] = ["reveal"]
    assert not any("svg-path-draw" in p for p in catalogue.validate(*write(s)))


def test_query_shows_why_each_result_ranks_where_it_does():
    rows = catalogue.query(catalogue.load(overlay={}), purposes=["difference"], content_type="explainer", aspect="9:16")
    assert rows[0]["id"] == "hf.blueprint:comparison-split"             # most specialised of the tied best matches
    assert rows[0]["components"] == {"purpose": 3, "content_type": 2, "aspect": 1, "complexity": 0, "confidence": 0}
    assert rows[0]["score"] == sum(rows[0]["components"].values())


def test_unavailable_and_paid_techniques_are_excluded(docs):
    seed, caps, write = docs
    c = copy.deepcopy(caps)
    for cap in c["capabilities"]:
        if cap["id"] == "hf.blueprint:comparison-split":
            cap["status"] = "unavailable"
        if cap["id"] == "hf.rule:split-tilt-cards":
            cap["paid"] = True
    s, p = write(None, c)
    entries = catalogue.load(s, p, overlay={})
    ids = [r["id"] for r in catalogue.query(entries, purposes=["difference"])]
    assert "hf.blueprint:comparison-split" not in ids and "hf.rule:split-tilt-cards" not in ids and ids
    assert "hf.rule:split-tilt-cards" in [r["id"] for r in catalogue.query(entries, purposes=["difference"], allow_paid=True)]


def test_a_validated_technique_becomes_the_top_result():
    entries = catalogue.load(overlay={})
    base = [r["id"] for r in catalogue.query(entries, purposes=["difference"])]
    target = "hf.rule:stat-bars-and-fills"
    assert base[0] != target
    boosted = catalogue.load(overlay={target: {"confidence": "validated", "evidence_count": 3}})
    top = catalogue.query(boosted, purposes=["difference"])[0]
    assert top["id"] == target and top["components"]["confidence"] == 2 and top["evidence_count"] == 3


def test_repeated_observation_updates_a_row_and_never_adds_a_technique():
    entries = catalogue.load(overlay={"hf.rule:svg-path-draw": {"evidence_count": 9}, "hf.rule:invented": {"evidence_count": 5}})
    assert len(entries) == 70 and entries["hf.rule:svg-path-draw"]["evidence_count"] == 9 and "hf.rule:invented" not in entries


def test_deprecated_is_hidden_unless_asked():
    entries = catalogue.load(overlay={"hf.rule:svg-path-draw": {"confidence": "deprecated", "evidence_count": 1}})
    assert "hf.rule:svg-path-draw" not in [r["id"] for r in catalogue.query(entries, purposes=["reveal"])]
    assert "hf.rule:svg-path-draw" in [r["id"] for r in catalogue.query(entries, purposes=["reveal"], include_deprecated=True, limit=70)]


def test_a_purpose_nothing_serves_returns_nothing():
    assert catalogue.query(catalogue.load(overlay={}), purposes=["nonexistent"]) == []


def test_new_files_do_not_disturb_the_validated_registry():
    r = subprocess.run([sys.executable, "-m", "contentos.production.direction", "registry"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_cli(capsys):
    assert catalogue._main(["validate"]) == 0
    assert catalogue._main(["query", "--purpose", "difference", "--limit", "2"]) == 0
    assert catalogue._main(["show", "hf.rule:nope"]) == 2
    assert catalogue._main(["query", "--purpose", "nonexistent"]) == 1
