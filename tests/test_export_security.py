"""P0-1b: export trusts the ledger, never the job manifest.

Every test here is an attack on the approval-to-export chain. Each one asserts on state - ready/ is byte-for-byte
unchanged, nothing new was published - not only on the refusal message. The chain under test:

    spec + composition + audio --digests--> approvals (ledger)
    render --attestation (ledger): video sha + the digests it was made under--> export
"""
import json
import shutil
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contentos import cli, export, ledger, pipeline, storage, storage_cli, track_b, ui_api  # noqa: E402
from storage_helpers import make_video  # noqa: E402

GATES = ("SCRIPT_APPROVED", "PRODUCTION_APPROVED")


@pytest.fixture(scope="module")
def videos(tmp_path_factory):
    root = tmp_path_factory.mktemp("sec")
    return SimpleNamespace(good=make_video(root / "good.mp4", seconds=1), other=make_video(root / "other.mp4", seconds=2))


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    monkeypatch.delenv("VIDEO_FACTORY_EXPORT_MODE", raising=False)
    storage.preflight()
    return SimpleNamespace(ws=tmp_path / "ws", pub=tmp_path / "pub", tmp=tmp_path)


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in Path(root).rglob("*") if p.is_file()} if Path(root).exists() else {}


def published(env):
    return sorted((env.pub / "ready").rglob("*.mp4"))


def owner_approves(job, gate, spec=None):
    """The real `contentos approve`, which binds the grant to the content on disk."""
    return cli.cmd_approve(SimpleNamespace(content_id=job, gate=gate, note="", spec=str(spec) if spec else None))


def spec_doc(job, say="One approved thing."):
    return {"content_id": job, "title": "Approved title", "project": "Demo", "kind": "short", "script": [{"say": say}]}


def track_a(env, videos, job="a1"):
    """A Track A job in the state the pipeline leaves it after an approved render: spec, composition and audio
    approved by the owner, then the render attested exactly as pipeline._stages does it."""
    sp = env.ws / "specs" / f"{job}.yaml"
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(yaml.safe_dump(spec_doc(job)))
    d, _ = storage.open_job(job, spec_doc(job))
    storage.update_manifest(d, source_spec=str(sp))
    (d / "project").mkdir()
    (d / "project" / "index.html").write_text("<html>approved composition</html>")
    (d / "audio").mkdir()
    (d / "audio" / "01.wav").write_bytes(b"RIFF approved take")
    for g in GATES:
        owner_approves(job, g, sp)
    spec = yaml.safe_load(sp.read_text())
    subjects = pipeline.render_subjects(d, spec, "pipeline")
    shutil.copy(videos.good, d / "video.mp4")
    ledger.attest_render(job, export.sha256_file(d / "video.mp4"), "pipeline", str(sp),
                         subjects["SCRIPT_APPROVED"], subjects["PRODUCTION_APPROVED"])
    return SimpleNamespace(id=job, d=d, spec=sp)


def refused(env, job, **kw):
    """Export must refuse, and leave the library exactly as it was."""
    before = tree(env.pub / "ready")
    with pytest.raises(export.ExportRefused) as exc:
        export.export_job(job, force=True, **kw)
    assert tree(env.pub / "ready") == before
    return str(exc.value)


# ---- the baseline: the honest path exports ----

def test_an_approved_attested_render_exports(env, videos):
    j = track_a(env, videos)
    assert export.export_job(j.id)["status"] == "exported"
    assert export.sha256_file(published(env)[0]) == export.sha256_file(videos.good)


# ---- Attack A and B: the manifest's source_spec ----

def test_attack_a_deleting_source_spec_does_not_downgrade_the_check(env, videos):
    j = track_a(env, videos)
    j.spec.write_text(yaml.safe_dump(spec_doc(j.id, say="Something never approved.")))  # the real edit
    m = storage.read_manifest(j.d)
    m.pop("source_spec")                                   # the cover-up that used to reduce the gate to "a grant exists"
    storage.write_manifest(j.d, m)
    assert "changed after this render" in refused(env, j.id)
    assert published(env) == []


def test_attack_a_deleting_source_spec_with_a_swapped_video_is_refused(env, videos):
    j = track_a(env, videos)
    shutil.copy(videos.other, j.d / "video.mp4")
    m = storage.read_manifest(j.d)
    m.pop("source_spec")
    storage.write_manifest(j.d, m)
    assert "not a render the factory recorded" in refused(env, j.id)


def test_attack_b_pointing_source_spec_at_a_pristine_copy_is_refused(env, videos):
    j = track_a(env, videos)
    pristine = env.tmp / "pristine.yaml"
    shutil.copy(j.spec, pristine)
    j.spec.write_text(yaml.safe_dump(spec_doc(j.id, say="Something never approved.")))
    storage.update_manifest(j.d, source_spec=str(pristine))  # the manifest now vouches for the old text
    assert "changed after this render" in refused(env, j.id)


def test_the_manifest_is_not_consulted_at_all(env, videos):
    """The converse: with the manifest gutted of every approval-related field, an honest job still exports."""
    j = track_a(env, videos)
    m = storage.read_manifest(j.d)
    for key in ("source_spec", "final_video_sha256", "artifacts"):
        m.pop(key, None)
    storage.write_manifest(j.d, m)
    assert export.export_job(j.id)["status"] == "exported"


# ---- the specification ----

def test_spec_edited_after_approval_and_before_render_blocks_the_render(env, videos):
    j = track_a(env, videos)
    edited = spec_doc(j.id, say="Edited before render.")
    j.spec.write_text(yaml.safe_dump(edited))
    with pytest.raises(pipeline.Blocked, match="approved for different content"):
        pipeline._check_gate(j.id, "SCRIPT_APPROVED", j.d, edited)


def test_spec_edited_after_render_is_refused(env, videos):
    j = track_a(env, videos)
    j.spec.write_text(yaml.safe_dump(spec_doc(j.id, say="Edited after render.")))
    assert "SCRIPT_APPROVED" in refused(env, j.id)


def test_spec_replaced_by_another_valid_spec_is_refused(env, videos):
    j = track_a(env, videos)
    other = {"content_id": "someone-else", "title": "A different video", "project": "Other",
             "script": [{"say": "A complete, valid, different script."}]}
    j.spec.write_text(yaml.safe_dump(other))
    assert "changed after this render" in refused(env, j.id)


def test_spec_deleted_after_render_is_refused(env, videos):
    j = track_a(env, videos)
    j.spec.unlink()
    assert "can no longer be read" in refused(env, j.id)


def test_composition_or_audio_edited_after_render_is_refused(env, videos):
    j = track_a(env, videos)
    (j.d / "audio" / "01.wav").write_bytes(b"RIFF a different take")
    assert "PRODUCTION_APPROVED" in refused(env, j.id)


# ---- approval records ----

def test_approval_metadata_in_the_manifest_grants_nothing(env, videos):
    j = track_a(env, videos)
    with ledger.db() as c:
        c.execute("DELETE FROM approvals WHERE content_id=?", (j.id,))
    storage.update_manifest(j.d, approvals={g: {"approved": True} for g in GATES}, status="ready")
    assert "not exported until SCRIPT_APPROVED and PRODUCTION_APPROVED" in refused(env, j.id)


def test_tampered_approval_digest_in_the_ledger_is_refused(env, videos):
    j = track_a(env, videos)
    with ledger.db() as c:
        c.execute("UPDATE approvals SET subject_sha256='0'||substr(subject_sha256,2) WHERE content_id=? AND gate=?",
                  (j.id, "PRODUCTION_APPROVED"))
    assert "granted for different content" in refused(env, j.id)


def test_an_unbound_grant_does_not_satisfy_export(env, videos):
    j = track_a(env, videos)
    with ledger.db() as c:
        c.execute("DELETE FROM approvals WHERE content_id=?", (j.id,))
    for g in GATES:
        ledger.approve(j.id, g, by="legacy")              # existence-only grants, the shape attack A downgraded to
    assert "an unbound grant does not count" in refused(env, j.id)


def test_replaying_an_approval_from_a_previous_version_is_refused(env, videos):
    """v1 approved; v2 composed and rendered; only v1's grants exist. The render is genuine, the approvals are real,
    they just cover other content."""
    j = track_a(env, videos)
    (j.d / "project" / "index.html").write_text("<html>v2 composition</html>")
    spec = yaml.safe_load(j.spec.read_text())
    v2 = pipeline.render_subjects(j.d, spec, "pipeline")
    shutil.copy(videos.other, j.d / "video.mp4")
    ledger.attest_render(j.id, export.sha256_file(j.d / "video.mp4"), "pipeline", str(j.spec),
                         v2["SCRIPT_APPROVED"], v2["PRODUCTION_APPROVED"])
    assert "PRODUCTION_APPROVED was granted for different content" in refused(env, j.id)
    owner_approves(j.id, "PRODUCTION_APPROVED", j.spec)  # the documented remedy: review v2 and approve it
    assert export.export_job(j.id, force=True)["status"] == "exported"


def test_an_approval_for_another_job_does_not_transfer(env, videos):
    j = track_a(env, videos)
    with ledger.db() as c:
        c.execute("UPDATE approvals SET content_id='other-job' WHERE content_id=?", (j.id,))
    assert "not exported until" in refused(env, j.id)


# ---- the render ----

def test_a_replaced_video_is_refused_even_when_the_manifest_vouches_for_it(env, videos):
    j = track_a(env, videos)
    assert export.export_job(j.id)["status"] == "exported"
    shutil.copy(videos.other, j.d / "video.mp4")
    storage.update_manifest(j.d, final_video_sha256=export.sha256_file(j.d / "video.mp4"))  # the old trust anchor
    assert "not a render the factory recorded" in refused(env, j.id)
    assert export.sha256_file(published(env)[0]) == export.sha256_file(videos.good)          # ready/ kept the approved one


def test_a_manifest_replaced_after_rendering_changes_nothing(env, videos):
    j = track_a(env, videos)
    shutil.copy(videos.other, j.d / "video.mp4")
    forged = {**storage.read_manifest(j.d), "track": "B", "source_spec": None, "status": "ready",
              "final_video_sha256": export.sha256_file(j.d / "video.mp4"), "renderer": "hand-built"}
    (j.d / "manifest.json").write_text(json.dumps(forged))
    assert "not a render the factory recorded" in refused(env, j.id)


def test_a_video_swapped_during_export_is_refused(env, videos, monkeypatch):
    """The bytes checked are the bytes copied: a swap between the check and the copy is caught inside the lock."""
    j = track_a(env, videos)
    real = export.approval_refusal

    def check_then_swap(*a, **k):
        out = real(*a, **k)
        shutil.copy(videos.other, j.d / "video.mp4")
        return out

    monkeypatch.setattr(export, "approval_refusal", check_then_swap)
    assert "changed while it was being exported" in refused(env, j.id)


# ---- missing authoritative records ----

def test_no_render_attestation_is_refused(env, videos):
    j = track_a(env, videos)
    with ledger.db() as c:
        c.execute("DELETE FROM renders WHERE content_id=?", (j.id,))
    assert "not a render the factory recorded" in refused(env, j.id)


def test_a_lost_ledger_is_refused(env, videos):
    j = track_a(env, videos)
    (env.ws / "ledger.db").unlink()
    assert "not a render the factory recorded" in refused(env, j.id)


# ---- every route out of the workspace ----

def test_every_export_route_refuses_the_same_attack(env, videos, capsys):
    j = track_a(env, videos)
    shutil.copy(videos.other, j.d / "video.mp4")
    before = tree(env.pub / "ready")

    with pytest.raises(export.ExportRefused):
        export.export_job(j.id)
    assert storage_cli.cmd_export(SimpleNamespace(job_id=j.id, force=True, mode=None)) == 1
    assert "not a render the factory recorded" in capsys.readouterr().out
    resp = ui_api._export(j.id, {"confirm": True, "force": True})
    assert resp.status == 409 and resp.body["error"]["code"] == "EXPORT_REFUSED"
    _, report = pipeline.run(j.spec, only="export", force=True)
    assert report[0][0] == "export" and report[0][1].startswith("FAIL")
    assert "not a render the factory recorded" in report[0][1]

    assert tree(env.pub / "ready") == before == {}


# ---- the pipeline writes the attestation it is judged by ----

def test_the_render_stage_attests_what_it_rendered(env, videos, monkeypatch):
    j = track_a(env, videos)
    with ledger.db() as c:
        c.execute("DELETE FROM renders")

    def fake_render(ctx):
        shutil.copy(videos.other, ctx["dir"] / "video.mp4")
        return "fake", [ctx["dir"] / "video.mp4"]

    monkeypatch.setitem(pipeline.FN, "render", fake_render)
    _, report = pipeline.run(j.spec, only="render", force=True)
    assert report[0][:2] == ("render", "OK"), report
    rec = ledger.render_record(j.id, export.sha256_file(j.d / "video.mp4"))
    assert rec["source"] == "pipeline" and rec["spec_path"] == str(j.spec.resolve())
    assert export.export_job(j.id)["status"] == "exported"


def test_the_render_stage_does_not_render_unapproved_content(env, videos, monkeypatch):
    j = track_a(env, videos)
    (j.d / "project" / "index.html").write_text("<html>edited after approval</html>")
    monkeypatch.setitem(pipeline.FN, "render", lambda ctx: pytest.fail("render ran past a stale approval"))
    _, report = pipeline.run(j.spec, only="render", force=True)
    assert report[0][1].startswith("BLOCKED")
    assert ledger.render_record(j.id)["video_sha256"] == export.sha256_file(videos.good)  # no new attestation


# ---- Track B ----

@pytest.fixture
def registered(env, videos):
    d = storage.job_dir("tb1")
    shutil.copy(videos.good, d / "video.mp4")
    (d / "script.yaml").write_text(yaml.safe_dump({"title": "Hand built", "script": [{"say": "Hand written line."}]}))
    assert cli.cmd_job_register(SimpleNamespace(path=str(d), track="B", title=None, project=None, project_name=None)) == 0
    for g in GATES:
        owner_approves("tb1", g)
    return d


def test_a_registered_render_exports_once_approved(env, registered):
    assert export.export_job("tb1")["status"] == "exported"


def test_track_b_swapped_video_is_refused(env, videos, registered):
    shutil.copy(videos.other, registered / "video.mp4")
    assert "not a render the factory recorded" in refused(env, "tb1")


def test_track_b_swap_then_re_register_needs_a_fresh_approval(env, videos, registered):
    """Registering is not approving: the production grant covers the exact bytes of a hand-built render."""
    shutil.copy(videos.other, registered / "video.mp4")
    track_b.register("tb1")
    assert "PRODUCTION_APPROVED was granted for different content" in refused(env, "tb1")
    owner_approves("tb1", "PRODUCTION_APPROVED")
    assert export.export_job("tb1", force=True)["status"] == "exported"


def test_track_b_script_edited_after_approval_is_refused(env, registered):
    (registered / "script.yaml").write_text(yaml.safe_dump({"title": "Hand built", "script": [{"say": "Changed."}]}))
    assert "changed after this render" in refused(env, "tb1")


def test_track_b_factory_render_is_bound_to_the_composition(env, videos, monkeypatch):
    """A Track B render made by the factory (track_b.render) is attested against the composition it was gated on."""
    d = storage.job_dir("tb2")
    (d / "project").mkdir()
    (d / "project" / "index.html").write_text("<html>tb2</html>")
    (d / "script.yaml").write_text(yaml.safe_dump({"title": "TB2", "script": [{"say": "Line."}]}))
    track_b.intake("tb2")
    for g in GATES:
        owner_approves("tb2", g)

    def fake_render(ctx):
        shutil.copy(videos.good, ctx["dir"] / "video.mp4")
        return "fake", [ctx["dir"] / "video.mp4"]

    monkeypatch.setattr(pipeline, "s_render", fake_render)
    track_b.render("tb2")
    assert ledger.render_record("tb2")["source"] == "track-b"
    assert export.export_job("tb2")["status"] == "exported"
    (d / "project" / "index.html").write_text("<html>tb2 edited</html>")
    assert "PRODUCTION_APPROVED" in refused(env, "tb2")


def test_registering_a_factory_render_keeps_the_stronger_record(env, videos, monkeypatch):
    d = storage.job_dir("tb3")
    (d / "project").mkdir()
    (d / "project" / "index.html").write_text("<html>tb3</html>")
    (d / "script.yaml").write_text(yaml.safe_dump({"title": "TB3", "script": [{"say": "Line."}]}))
    track_b.intake("tb3")
    for g in GATES:
        owner_approves("tb3", g)
    monkeypatch.setattr(pipeline, "s_render", lambda ctx: (shutil.copy(videos.good, ctx["dir"] / "video.mp4"), ("fake", []))[1])
    track_b.render("tb3")
    track_b.register("tb3")
    assert ledger.render_record("tb3")["source"] == "track-b"
    assert export.export_job("tb3")["status"] == "exported"


def test_the_renders_table_is_append_only_in_practice(env, videos):
    """Re-attesting never rewrites history: an older attestation stays, a newer one is preferred."""
    j = track_a(env, videos)
    rows = sqlite3.connect(env.ws / "ledger.db").execute("SELECT count(*) FROM renders").fetchone()[0]
    ledger.attest_render(j.id, "f" * 64, "pipeline", str(j.spec), "s", "p")
    assert sqlite3.connect(env.ws / "ledger.db").execute("SELECT count(*) FROM renders").fetchone()[0] == rows + 1
    assert ledger.render_record(j.id)["video_sha256"] == "f" * 64
    assert ledger.render_record(j.id, export.sha256_file(j.d / "video.mp4"))["source"] == "pipeline"


# ---- independent review (POTATO_FINAL_SECURITY_REVIEW.md) follow-ups ----

@pytest.mark.parametrize("rel", ["project/assets/voice/01.wav", "project/gsap.min.js", "project/hyperframes.json"])
def test_pf01_every_file_the_renderer_reads_is_bound(env, videos, rel):
    """PF-01: the renderer plays project/assets/voice/*.wav and runs the project's scripts and config, so changing any
    of them after PRODUCTION_APPROVED must be caught - at the render gate and at export."""
    j = track_a(env, videos)
    target = j.d / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"swapped after approval")
    spec = yaml.safe_load(j.spec.read_text())
    with pytest.raises(pipeline.Blocked, match="approved for different content"):
        pipeline._check_gate(j.id, "PRODUCTION_APPROVED", j.d, spec)
    assert "PRODUCTION_APPROVED" in refused(env, j.id)


def test_pf21_files_behind_a_symlinked_directory_are_bound(env, videos):
    """PF-21: a project folder that is a symlink must not be a way around the binding - the files behind it are what
    the renderer reads, so changing one after approval is refused."""
    outside = env.tmp / "outside-assets"
    outside.mkdir()
    (outside / "take.wav").write_bytes(b"RIFF approved take")
    j = track_a(env, videos)
    (j.d / "project" / "assets").symlink_to(outside, target_is_directory=True)
    spec = yaml.safe_load(j.spec.read_text())
    for g in GATES:
        owner_approves(j.id, g, j.spec)
    subjects = pipeline.render_subjects(j.d, spec, "pipeline")
    ledger.attest_render(j.id, export.sha256_file(j.d / "video.mp4"), "pipeline", str(j.spec),
                         subjects["SCRIPT_APPROVED"], subjects["PRODUCTION_APPROVED"])
    assert export.export_job(j.id)["status"] == "exported"
    (outside / "take.wav").write_bytes(b"RIFF swapped behind the link")
    assert "PRODUCTION_APPROVED" in refused(env, j.id)


def test_pf21_a_symlink_loop_terminates(env, videos):
    j = track_a(env, videos)
    (j.d / "project" / "loop").symlink_to(j.d / "project", target_is_directory=True)
    assert pipeline.production_digest(j.d, yaml.safe_load(j.spec.read_text()))


def test_pf24_a_shared_node_modules_link_is_bound_by_target_only(env, videos):
    """Accepted risk PF-24: Remotion's shared toolchain (project_remotion/node_modules) is linked, not reviewed.
    Its link target is bound, its tree is not."""
    j = track_a(env, videos)
    spec = {**yaml.safe_load(j.spec.read_text()), "render": "remotion"}
    src = j.d / "project_remotion" / "src"
    src.mkdir(parents=True)
    (src / "Video.tsx").write_text("export const Video = () => null;")
    tools = env.tmp / "toolchain"
    tools.mkdir()
    (j.d / "project_remotion" / "node_modules").symlink_to(tools, target_is_directory=True)
    before = pipeline.production_digest(j.d, spec)
    (tools / "lib.js").write_text("changed toolchain")
    assert pipeline.production_digest(j.d, spec) == before
    (src / "Video.tsx").write_text("export const Video = () => 'edited';")
    assert pipeline.production_digest(j.d, spec) != before


def test_pf04_a_manifest_naming_another_job_is_refused(env, videos):
    """PF-04: the manifest's job_id names the export destination, so a forged one could overwrite another job's
    export or, with '..', write outside ready/."""
    victim = track_a(env, videos, job="victim")
    assert export.export_job(victim.id)["status"] == "exported"
    j = track_a(env, videos, job="a1")
    before = tree(env.pub)
    for forged in ("victim", "../../escape"):
        storage.write_manifest(j.d, {**storage.read_manifest(j.d), "job_id": forged})
        with pytest.raises(export.ExportRefused, match="names a different job"):
            export.export_job(j.id, force=True)
        assert tree(env.pub) == before
    assert not (env.tmp / "escape.mp4").exists() and not list(env.tmp.glob("*escape*"))


def test_pf05_content_swapped_during_the_render_is_not_attested(env, videos, monkeypatch):
    """PF-05: the gate is checked before a render that takes minutes. A composition changed inside that window
    must not be attested as if it were the approved one."""
    j = track_a(env, videos)
    with ledger.db() as c:
        c.execute("DELETE FROM renders")

    def render_while_someone_edits(ctx):
        (ctx["dir"] / "project" / "index.html").write_text("<html>swapped mid-render</html>")
        shutil.copy(videos.other, ctx["dir"] / "video.mp4")
        return "fake", [ctx["dir"] / "video.mp4"]

    monkeypatch.setitem(pipeline.FN, "render", render_while_someone_edits)
    _, report = pipeline.run(j.spec, only="render", force=True)
    assert report[0][1].startswith("BLOCKED") and "changed while it was rendering" in report[0][1]
    assert ledger.render_record(j.id) is None
    assert not (j.d / "video.mp4").exists()                 # the suspect render is removed, not left to be registered


def test_pf06_the_render_audio_bed_does_not_invalidate_an_honest_render(env, videos, monkeypatch):
    """PF-06 (regression in the first P0-1b cut): features.audio_bed writes audio/ambient_bed.wav after rendering.
    That is a render output, not reviewed content, so it must not change the production digest."""
    j = track_a(env, videos)

    def render_with_bed(ctx):
        shutil.copy(videos.other, ctx["dir"] / "video.mp4")
        (ctx["dir"] / "audio" / "ambient_bed.wav").write_bytes(b"RIFF generated bed")
        return "fake", [ctx["dir"] / "video.mp4"]

    monkeypatch.setitem(pipeline.FN, "render", render_with_bed)
    _, report = pipeline.run(j.spec, only="render", force=True)
    assert report[0][:2] == ("render", "OK"), report
    assert export.export_job(j.id)["status"] == "exported"


def test_pf10_track_b_render_needs_the_script_approval_too(env, videos, monkeypatch):
    d = storage.job_dir("tb4")
    (d / "project").mkdir()
    (d / "project" / "index.html").write_text("<html>tb4</html>")
    (d / "script.yaml").write_text(yaml.safe_dump({"title": "TB4", "script": [{"say": "Approved line."}]}))
    track_b.intake("tb4")
    for g in GATES:
        owner_approves("tb4", g)
    (d / "script.yaml").write_text(yaml.safe_dump({"title": "TB4", "script": [{"say": "Edited line."}]}))
    monkeypatch.setattr(pipeline, "s_render", lambda ctx: pytest.fail("rendered an unapproved script"))
    with pytest.raises(track_b.TrackBError, match="SCRIPT_APPROVED"):
        track_b.render("tb4")


def test_pf11_registering_an_intake_without_a_video_does_not_crash(env, capsys):
    d = storage.job_dir("tb5")
    (d / "project").mkdir()
    (d / "project" / "index.html").write_text("<html>tb5</html>")
    (d / "script.yaml").write_text(yaml.safe_dump({"title": "TB5", "script": [{"say": "Line."}]}))
    track_b.intake("tb5")
    assert cli.cmd_job_register(SimpleNamespace(path=str(d), track="B", title=None, project=None, project_name=None)) == 0
    assert ledger.render_record("tb5") is None


def test_pf02_approve_shows_what_it_binds_before_recording(env, videos, capsys):
    """PF-02 mitigation: --show prints the spec path, title and every spoken line with the digest and records nothing;
    --expect grants only if the content still has the digest the approver was shown."""
    j = track_a(env, videos)
    with ledger.db() as c:
        c.execute("DELETE FROM approvals WHERE content_id=?", (j.id,))
    capsys.readouterr()
    assert cli.cmd_approve(SimpleNamespace(content_id=j.id, gate="SCRIPT_APPROVED", note="", spec=None, show=True, expect=None)) == 0
    out = capsys.readouterr().out
    assert str(j.spec) in out and "Approved title" in out and "| One approved thing." in out
    assert not ledger.approved(j.id, "SCRIPT_APPROVED")                      # --show recorded nothing
    shown = out.split("digest: ")[1].split()[0]

    j.spec.write_text(yaml.safe_dump(spec_doc(j.id, say="Swapped in after the owner looked.")))
    assert cli.cmd_approve(SimpleNamespace(content_id=j.id, gate="SCRIPT_APPROVED", note="", spec=None, show=False, expect=shown)) == 1
    assert not ledger.approved(j.id, "SCRIPT_APPROVED")                      # a changed subject is not granted

    j.spec.write_text(yaml.safe_dump(spec_doc(j.id)))
    assert cli.cmd_approve(SimpleNamespace(content_id=j.id, gate="SCRIPT_APPROVED", note="", spec=None, show=False, expect=shown)) == 0
    assert ledger.check_gate(j.id, "SCRIPT_APPROVED", shown)[0] == "ok"


def test_pf02_cli_parses_show_and_expect(env, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["contentos", "approve", "x", "SCRIPT_APPROVED", "--show", "--expect", "ab"])
    parsed = {}
    monkeypatch.setattr(cli, "cmd_approve", lambda a: parsed.update(vars(a)) or 0)
    with pytest.raises(SystemExit):
        cli.main()
    assert parsed.get("show") is True and parsed.get("expect") == "ab"


def test_pf25_a_track_b_render_blocked_mid_render_leaves_no_video(env, videos, monkeypatch):
    d = storage.job_dir("tb6")
    (d / "project").mkdir()
    (d / "project" / "index.html").write_text("<html>tb6</html>")
    (d / "script.yaml").write_text(yaml.safe_dump({"title": "TB6", "script": [{"say": "Line."}]}))
    track_b.intake("tb6")
    for g in GATES:
        owner_approves("tb6", g)

    def render_while_someone_edits(ctx):
        (ctx["dir"] / "project" / "index.html").write_text("<html>swapped mid-render</html>")
        shutil.copy(videos.other, ctx["dir"] / "video.mp4")
        return "fake", [ctx["dir"] / "video.mp4"]

    monkeypatch.setattr(pipeline, "s_render", render_while_someone_edits)
    with pytest.raises(track_b.TrackBError, match="changed while it was rendering"):
        track_b.render("tb6")
    assert ledger.render_record("tb6") is None and not (d / "video.mp4").exists()


def test_pf20_a_forged_export_record_cannot_aim_force_at_another_file(env, videos):
    j = track_a(env, videos)
    victim = env.tmp / "precious.txt"
    victim.write_text("keep me")
    st = env.pub / ".state" / "exports" / f"{j.id}.json"
    st.parent.mkdir(parents=True, exist_ok=True)
    st.write_text(json.dumps({"video": "../precious.txt", "sidecar": "../precious.json"}))
    assert export.export_job(j.id, force=True)["status"] == "exported"
    assert victim.read_text() == "keep me"


def test_pf26_show_prints_what_the_voice_will_speak(env, videos, capsys):
    j = track_a(env, videos)
    j.spec.write_text(yaml.safe_dump({**spec_doc(j.id), "script": [{"say": "Nice words.", "tts": "Different words."}]}))
    capsys.readouterr()
    cli.cmd_approve(SimpleNamespace(content_id=j.id, gate="SCRIPT_APPROVED", note="", spec=None, show=True, expect=None))
    assert "spoken as: Different words." in capsys.readouterr().out


def test_pf27_only_remotions_top_level_node_modules_is_exempt(env, videos):
    j = track_a(env, videos)
    spec = yaml.safe_load(j.spec.read_text())
    hidden = env.tmp / "hidden"
    hidden.mkdir()
    (hidden / "voice.wav").write_bytes(b"approved")
    (j.d / "project" / "node_modules").symlink_to(hidden, target_is_directory=True)
    before = pipeline.production_digest(j.d, spec)
    (hidden / "voice.wav").write_bytes(b"swapped")
    assert pipeline.production_digest(j.d, spec) != before


def test_pf28_a_fifo_in_the_project_cannot_be_approved(env, videos):
    import os
    j = track_a(env, videos)
    os.mkfifo(j.d / "project" / "stream.wav")
    assert pipeline.production_digest(j.d, yaml.safe_load(j.spec.read_text())) is None
    assert "PRODUCTION_APPROVED" in refused(env, j.id)


def test_pf29_an_empty_expect_is_an_expectation(env, videos):
    j = track_a(env, videos)
    with ledger.db() as c:
        c.execute("DELETE FROM approvals WHERE content_id=?", (j.id,))
    assert cli.cmd_approve(SimpleNamespace(content_id=j.id, gate="SCRIPT_APPROVED", note="", spec=None, show=False, expect="")) == 1
    assert not ledger.approved(j.id, "SCRIPT_APPROVED")


def test_a_fifo_audio_take_cannot_be_approved_and_does_not_hang(env, videos):
    import os
    j = track_a(env, videos)
    os.mkfifo(j.d / "audio" / "02.wav")
    assert pipeline.production_digest(j.d, yaml.safe_load(j.spec.read_text())) is None


def test_show_lists_the_files_production_binds_and_an_empty_tts(env, videos, capsys):
    j = track_a(env, videos)
    j.spec.write_text(yaml.safe_dump({**spec_doc(j.id), "script": [{"say": "Words.", "tts": ""}]}))
    capsys.readouterr()
    cli.cmd_approve(SimpleNamespace(content_id=j.id, gate="SCRIPT_APPROVED", note="", spec=None, show=True, expect=None))
    assert "spoken as: " in capsys.readouterr().out
    cli.cmd_approve(SimpleNamespace(content_id=j.id, gate="PRODUCTION_APPROVED", note="", spec=None, show=True, expect=None))
    out = capsys.readouterr().out
    assert "project/index.html" in out and "audio/01.wav" in out
