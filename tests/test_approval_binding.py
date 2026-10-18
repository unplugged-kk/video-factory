"""W1 approval safety: approvals are bound to the content they cover (G-02) and carry the authorising identity (G-07).
Hermetic: scratch workspace and publish dir, stubbed stage functions, no TTS or render."""
import re
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import cli, ledger, pipeline, storage  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
HEX64 = re.compile(r"[0-9a-f]{64}")


def spec_dict(say="Hello there friend."):
    return {"content_id": "ab1", "title": "Approval Binding", "project": "Demo", "script": [{"say": say}, {"say": "Second line."}]}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    monkeypatch.delenv("CONTENTOS_FACTORY_AUTHORIZED_BY", raising=False)
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(spec_dict()))
    calls = []

    def voice(ctx):
        calls.append("voice")
        (ctx["dir"] / "audio").mkdir(exist_ok=True)
        wav = ctx["dir"] / "audio" / "01.wav"
        wav.write_bytes(b"RIFF-take-one")
        return "stub", [wav]

    def render(ctx):
        calls.append("render")
        out = ctx["dir"] / "video.mp4"
        out.write_bytes(b"video")
        return "stub", [out]

    monkeypatch.setitem(pipeline.FN, "voice", voice)
    monkeypatch.setitem(pipeline.FN, "render", render)
    return SimpleNamespace(spec=path, calls=calls, tmp=tmp_path)


def edit_spec(env, say):
    env.spec.write_text(yaml.safe_dump(spec_dict(say)))


def run(env, only, **kw):
    return pipeline.run(env.spec, only=only, **kw)[1]


def rows(gate):
    return ledger.db().execute("SELECT by, note, subject_sha256 FROM approvals WHERE content_id='ab1' AND gate=? ORDER BY at", (gate,)).fetchall()


def stage_composition(env, html="<html>v1</html>"):
    storage.preflight()
    d, _ = storage.open_job("ab1", spec_dict())
    (d / "project").mkdir(exist_ok=True)
    (d / "project" / "index.html").write_text(html)
    (d / "audio").mkdir(exist_ok=True)
    (d / "audio" / "01.wav").write_bytes(b"RIFF-take-one")
    return d


# ---- migration ----------------------------------------------------------------------------------------------------

def test_fresh_ledger_has_subject_column_and_no_backup(env):
    cols = [r[1] for r in ledger.db().execute("PRAGMA table_info(approvals)")]
    assert "subject_sha256" in cols
    assert not (storage.workspace_root() / "recovery" / "migrations").exists() or not list((storage.workspace_root() / "recovery" / "migrations").iterdir())


def test_old_ledger_is_backed_up_then_migrated_once(env):
    ws = storage.workspace_root()
    ws.mkdir(parents=True)
    old = sqlite3.connect(ws / "ledger.db")
    old.execute("CREATE TABLE approvals(content_id TEXT, gate TEXT, by TEXT, at REAL, note TEXT)")
    old.execute("INSERT INTO approvals VALUES ('legacy','SCRIPT_APPROVED','human',1.0,'old')")
    old.commit()
    old.close()
    ledger.db()
    backups = list((ws / "recovery" / "migrations").glob("ledger*.db"))
    assert len(backups) == 1
    kept = sqlite3.connect(backups[0])
    assert "subject_sha256" not in [r[1] for r in kept.execute("PRAGMA table_info(approvals)")]   # the backup is the pre-migration file
    assert kept.execute("SELECT content_id FROM approvals").fetchall() == [("legacy",)]
    live = ledger.db().execute("SELECT content_id, subject_sha256 FROM approvals").fetchall()
    assert live == [("legacy", None)]
    assert len(list((ws / "recovery" / "migrations").glob("ledger*.db"))) == 1                       # second open: no second backup


# ---- G-02: the script gate ----------------------------------------------------------------------------------------

def test_edited_script_blocks_voice_and_names_both_digests(env):
    approved_digest = pipeline.script_digest(spec_dict())
    ledger.approve("ab1", "SCRIPT_APPROVED", subject_sha256=approved_digest)
    assert run(env, "voice")[0][1] == "OK"
    edit_spec(env, "Hello there my friend.")                      # one word
    env.calls.clear()
    status = run(env, "voice", force=True)[0][1]
    assert status.startswith("BLOCKED")
    assert approved_digest in status
    assert pipeline.script_digest(spec_dict("Hello there my friend.")) in status
    assert env.calls == []                                         # the voice stage never ran


def test_reapproving_the_edited_script_passes(env):
    ledger.approve("ab1", "SCRIPT_APPROVED", subject_sha256=pipeline.script_digest(spec_dict()))
    edit_spec(env, "Hello there my friend.")
    assert run(env, "voice")[0][1].startswith("BLOCKED")
    ledger.approve("ab1", "SCRIPT_APPROVED", subject_sha256=pipeline.script_digest(spec_dict("Hello there my friend.")))
    assert run(env, "voice")[0][1] == "OK"


def test_edit_is_caught_even_when_voice_output_already_exists(env):
    ledger.approve("ab1", "SCRIPT_APPROVED", subject_sha256=pipeline.script_digest(spec_dict()))
    assert run(env, "voice")[0][1] == "OK"
    edit_spec(env, "Hello there my friend.")
    assert run(env, "voice")[0][1].startswith("BLOCKED")           # resume must not hide an unapproved edit


def test_null_digest_approval_still_passes_with_a_visible_warning(env, capsys):
    ledger.approve("ab1", "SCRIPT_APPROVED")                       # a legacy, unbound approval
    assert run(env, "voice")[0][1] == "OK"
    err = capsys.readouterr().err.lower()
    assert "warning" in err and "unbound" in err and "script_approved" in err


def test_null_row_does_not_rescue_a_mismatching_bound_row(env):
    ledger.approve("ab1", "SCRIPT_APPROVED")
    ledger.approve("ab1", "SCRIPT_APPROVED", subject_sha256=pipeline.script_digest(spec_dict()))
    edit_spec(env, "Hello there my friend.")
    assert run(env, "voice")[0][1].startswith("BLOCKED")


def test_gate_not_granted_message_is_unchanged(env):
    assert run(env, "voice")[0][1] == "BLOCKED: gate SCRIPT_APPROVED not granted: contentos approve ab1 SCRIPT_APPROVED"


# ---- G-02: the production gate ------------------------------------------------------------------------------------

def test_edited_composition_blocks_render_and_names_both_digests(env):
    d = stage_composition(env)
    spec = spec_dict()
    approved_digest = pipeline.production_digest(d, spec)
    assert HEX64.fullmatch(approved_digest)
    ledger.approve("ab1", "PRODUCTION_APPROVED", subject_sha256=approved_digest)
    (d / "project" / "index.html").write_text("<html>v2</html>")
    status = run(env, "render")[0][1]
    assert status.startswith("BLOCKED")
    assert approved_digest in status and pipeline.production_digest(d, spec) in status
    assert env.calls == []


def test_edited_audio_changes_the_production_digest(env):
    d = stage_composition(env)
    before = pipeline.production_digest(d, spec_dict())
    (d / "audio" / "01.wav").write_bytes(b"RIFF-take-two")
    assert pipeline.production_digest(d, spec_dict()) != before


def test_matching_production_approval_renders(env):
    d = stage_composition(env)
    ledger.approve("ab1", "PRODUCTION_APPROVED", subject_sha256=pipeline.production_digest(d, spec_dict()))
    assert run(env, "render")[0][1] == "OK"


# ---- CLI approve records the digest of the current artifact -------------------------------------------------------

def approve_cli(gate, spec=None):
    return cli.cmd_approve(SimpleNamespace(content_id="ab1", gate=gate, note="", spec=spec))


def test_cli_approve_binds_script_digest_via_the_recorded_spec(env):
    assert run(env, "voice")[0][1].startswith("BLOCKED")           # the run records which spec it was given
    approve_cli("SCRIPT_APPROVED")
    assert rows("SCRIPT_APPROVED")[-1][2] == pipeline.script_digest(spec_dict())
    assert run(env, "voice")[0][1] == "OK"
    edit_spec(env, "Hello there my friend.")                       # approve now binds what is on disk, not a stale snapshot
    approve_cli("SCRIPT_APPROVED")
    assert rows("SCRIPT_APPROVED")[-1][2] == pipeline.script_digest(spec_dict("Hello there my friend."))


def test_cli_approve_accepts_an_explicit_spec(env):
    approve_cli("SCRIPT_APPROVED", spec=str(env.spec))
    assert rows("SCRIPT_APPROVED")[-1][2] == pipeline.script_digest(spec_dict())


def test_cli_approve_binds_production_digest(env):
    d = stage_composition(env)
    run(env, "render")                                             # blocked, but records the spec
    approve_cli("PRODUCTION_APPROVED")
    assert rows("PRODUCTION_APPROVED")[-1][2] == pipeline.production_digest(d, spec_dict())


def test_cli_approve_without_any_artifact_records_null_and_warns(env, capsys):
    approve_cli("SCRIPT_APPROVED")
    assert rows("SCRIPT_APPROVED")[-1][2] is None
    assert "unbound" in capsys.readouterr().err.lower()


def test_cli_approve_parses_the_spec_flag(env, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["contentos", "approve", "ab1", "SCRIPT_APPROVED", "--spec", str(env.spec)])
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 0
    assert rows("SCRIPT_APPROVED")[-1][2] == pipeline.script_digest(spec_dict())


# ---- G-07: authorising identity ----------------------------------------------------------------------------------

def test_approve_private_records_the_authorising_identity(env, monkeypatch):
    monkeypatch.setenv("CONTENTOS_FACTORY_AUTHORIZED_BY", "kishore@example.test")
    assert run(env, "voice", approve_private=True)[0][1] == "OK"
    for gate in ("RESEARCH_APPROVED", "SCRIPT_APPROVED", "PRODUCTION_APPROVED"):
        by, note, _ = rows(gate)[0]
        assert "kishore@example.test" in by
        assert by.startswith("cli --approve-private")


def test_approve_private_without_identity_is_unchanged(env):
    run(env, "voice", approve_private=True)
    assert [r[0] for r in rows("SCRIPT_APPROVED")] == ["cli --approve-private"]


def test_approve_private_binds_script_digest(env):
    run(env, "voice", approve_private=True)
    assert rows("SCRIPT_APPROVED")[0][2] == pipeline.script_digest(spec_dict())


def test_approve_private_binds_production_digest_once_the_composition_exists(env):
    d = stage_composition(env)
    assert run(env, "render", approve_private=True)[0][1] == "OK"
    bound = [r for r in rows("PRODUCTION_APPROVED") if r[2]]
    assert bound and bound[-1][2] == pipeline.production_digest(d, spec_dict())
    (d / "project" / "index.html").write_text("<html>v2</html>")
    assert run(env, "render", force=True)[0][1].startswith("BLOCKED")   # a later plain run is held to that digest


def test_identity_is_sanitised(env, monkeypatch):
    monkeypatch.setenv("CONTENTOS_FACTORY_AUTHORIZED_BY", "a\nb" + "x" * 500)
    run(env, "voice", approve_private=True)
    by = rows("SCRIPT_APPROVED")[0][0]
    assert "\n" not in by and len(by) < 300


# ---- PUBLISH_APPROVED is never granted by code --------------------------------------------------------------------

def test_no_code_path_grants_publish_approved(env, monkeypatch):
    monkeypatch.setenv("CONTENTOS_FACTORY_AUTHORIZED_BY", "someone")
    stage_composition(env)
    run(env, "voice", approve_private=True)
    run(env, "render", approve_private=True)
    assert ledger.db().execute("SELECT count(*) FROM approvals WHERE gate='PUBLISH_APPROVED'").fetchone()[0] == 0
    assert not ledger.approved("ab1", "PUBLISH_APPROVED")


def test_source_never_calls_approve_with_publish_gate():
    hits = []
    for p in list((REPO / "contentos").rglob("*.py")) + list((REPO / "contentos").rglob("*.mjs")):
        text = p.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if "PUBLISH_APPROVED" in line and re.search(r"\bapprove\(|INSERT INTO approvals", line):
                hits.append(f"{p.relative_to(REPO)}:{i}")
        if re.search(r"for g(ate)? in \([^)]*PUBLISH_APPROVED", text):
            hits.append(f"{p.relative_to(REPO)}: loops over PUBLISH_APPROVED")
    assert hits == []
    private = (REPO / "contentos" / "pipeline.py").read_text()
    grant = re.search(r"if approve_private:.*?\n    rid =", private, re.S)
    assert grant and "PUBLISH" not in grant.group(0)
