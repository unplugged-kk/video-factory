"""supplied-audio/1 (G3): provenance + rights record for a supplied voiceover, and the publication block for unknown rights.

Synthetic ffmpeg audio only, built in tmp dirs (nothing committed). Offline: no network, no ASR, no paid service.
Slice scope: the supplied take is RECORDED, not yet consumed by compose; a job holding one stops at `voice` explicitly."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contentos import export, pipeline, storage  # noqa: E402
from contentos.production import supplied_audio as sa  # noqa: E402
from storage_helpers import make_video  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="ffmpeg/ffprobe not installed")


def _audio(path, ext=".wav", seconds=1, freq=440):
    path = Path(path).with_suffix(ext)
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={seconds}", str(path)], check=True)
    return path


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture
def job(tmp_path):
    d = tmp_path / "job"
    d.mkdir()
    return d


@pytest.fixture
def take(tmp_path):
    return _audio(tmp_path / "in" / "voiceover")


# ---- valid inputs -----------------------------------------------------------------------------------------------------

def test_owned_is_recorded_with_hash_and_evidence(job, take):
    rec = sa.ingest(take, job, rights="owned", evidence="recorded by me, 2026-10-11", holder="Kishore")
    assert rec["schema"] == "supplied-audio/1"
    assert rec["source"]["sha256"] == rec["original"]["sha256"] == _sha(take)
    assert rec["rights"]["status"] == "owned" and rec["rights"]["evidence"] == "recorded by me, 2026-10-11"
    assert rec["rights"]["verified"] is False                          # self-declared, never claimed as verified
    assert rec["probe"]["duration_s"] > 0 and rec["probe"]["sample_rate"]
    assert sa.verify(job)["rights"]["status"] == "owned"
    assert sa.publish_blockers(job) == []


def test_licensed_needs_licence_and_is_accepted(job, take):
    with pytest.raises(sa.SuppliedAudioError, match="licence"):
        sa.ingest(take, job, rights="licensed", evidence="purchase receipt 123")
    rec = sa.ingest(take, job, rights="licensed", evidence="purchase receipt 123", licence="CC-BY-4.0")
    assert rec["rights"]["licence"] == "CC-BY-4.0" and sa.publish_blockers(job) == []


def test_other_audio_formats_are_accepted(job, tmp_path):
    flac = _audio(tmp_path / "in" / "take2", ".flac")
    assert sa.ingest(flac, job, rights="owned", evidence="mine")["probe"]["codec"] == "flac"


# ---- rights enforcement -----------------------------------------------------------------------------------------------

def test_unknown_rights_is_recorded_and_blocks_publication(job, take):
    rec = sa.ingest(take, job)                                         # default: unknown
    assert rec["rights"]["status"] == "unknown"
    blockers = sa.publish_blockers(job)
    assert len(blockers) == 1 and "unknown" in blockers[0]


def test_owned_without_evidence_is_refused(job, take):
    with pytest.raises(sa.SuppliedAudioError, match="evidence"):
        sa.ingest(take, job, rights="owned")
    assert not sa.has_record(job)


def test_bad_rights_value_is_refused(job, take):
    with pytest.raises(sa.SuppliedAudioError, match="rights must be"):
        sa.ingest(take, job, rights="public-domain", evidence="x")


def test_unknown_can_be_upgraded_and_history_is_kept(job, take):
    sa.ingest(take, job)
    rec = sa.ingest(take, job, rights="owned", evidence="my own recording")
    assert rec["rights"]["status"] == "owned" and rec["rights_history"][0]["status"] == "unknown"
    assert sa.publish_blockers(job) == []


def test_downgrade_to_unknown_blocks_again(job, take):
    sa.ingest(take, job, rights="owned", evidence="mine")
    sa.ingest(take, job, rights="unknown")
    assert sa.publish_blockers(job)


# ---- bad inputs -------------------------------------------------------------------------------------------------------

def test_missing_file(job, tmp_path):
    with pytest.raises(sa.SuppliedAudioError, match="not found"):
        sa.ingest(tmp_path / "nope.wav", job)


def test_empty_file(job, tmp_path):
    p = tmp_path / "empty.wav"
    p.write_bytes(b"")
    with pytest.raises(sa.SuppliedAudioError, match="empty"):
        sa.ingest(p, job)


def test_unsupported_extension(job, tmp_path):
    p = tmp_path / "notes.txt"
    p.write_text("hello")
    with pytest.raises(sa.SuppliedAudioError, match="unsupported"):
        sa.ingest(p, job)


def test_invalid_audio_with_audio_extension(job, tmp_path):
    p = tmp_path / "fake.wav"
    p.write_bytes(b"this is not audio at all" * 20)
    with pytest.raises(sa.SuppliedAudioError, match="not a readable media file"):
        sa.ingest(p, job)
    assert not sa.has_record(job)


def test_video_container_is_refused(job, tmp_path):
    v = make_video(tmp_path / "clip.mp4", seconds=1, w=320, h=240)
    p = v.with_suffix(".m4a")                                          # a footage file renamed to look like audio
    shutil.copy(v, p)
    with pytest.raises(sa.SuppliedAudioError, match="video stream"):
        sa.ingest(p, job)


def test_missing_job_dir(take, tmp_path):
    with pytest.raises(sa.SuppliedAudioError, match="job directory"):
        sa.ingest(take, tmp_path / "no-such-job")


# ---- malformed record and hash mismatch -------------------------------------------------------------------------------

def test_malformed_record_is_reported_and_blocks(job, take):
    sa.ingest(take, job, rights="owned", evidence="mine")
    sa.record_path(job).write_text("{not json")
    with pytest.raises(sa.SuppliedAudioError, match="unreadable"):
        sa.verify(job)
    assert sa.publish_blockers(job)                                    # fails closed


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(schema="supplied-audio/9"),
    lambda r: r["rights"].update(status="public"),
    lambda r: r["original"].update(sha256="xyz"),
    lambda r: r["original"].update(path="../../etc/passwd"),
    lambda r: r["rights"].update(status="licensed", licence=""),
    lambda r: r.pop("probe"),
])
def test_schema_violations_are_detected(job, take, mutate):
    sa.ingest(take, job, rights="licensed", evidence="receipt", licence="CC-BY-4.0")
    rec = json.loads(sa.record_path(job).read_text())
    mutate(rec)
    sa.record_path(job).write_text(json.dumps(rec))
    with pytest.raises(sa.SuppliedAudioError, match="malformed"):
        sa.load_record(job)
    assert sa.publish_blockers(job)


def test_hash_mismatch_is_detected_and_blocks(job, take):
    rec = sa.ingest(take, job, rights="owned", evidence="mine")
    stored = job / rec["original"]["path"]
    stored.chmod(0o644)
    stored.write_bytes(stored.read_bytes() + b"\0")                    # tamper with the stored original
    with pytest.raises(sa.SuppliedAudioError, match="hash mismatch"):
        sa.verify(job)
    assert "hash mismatch" in sa.publish_blockers(job)[0]


def test_missing_stored_original_is_detected(job, take):
    rec = sa.ingest(take, job, rights="owned", evidence="mine")
    (job / rec["original"]["path"]).chmod(0o644)
    (job / rec["original"]["path"]).unlink()
    with pytest.raises(sa.SuppliedAudioError, match="missing"):
        sa.verify(job)


# ---- immutability and working copy ------------------------------------------------------------------------------------

def test_source_is_untouched_and_original_is_byte_identical(job, take):
    before, mtime = take.read_bytes(), take.stat().st_mtime_ns
    rec = sa.ingest(take, job, rights="owned", evidence="mine")
    assert take.read_bytes() == before and take.stat().st_mtime_ns == mtime
    stored = job / rec["original"]["path"]
    assert stored.read_bytes() == before and stored != take
    assert not (stored.stat().st_mode & 0o222)                          # read-only


def test_a_different_file_never_replaces_the_original(job, take, tmp_path):
    rec = sa.ingest(take, job, rights="owned", evidence="mine")
    other = _audio(tmp_path / "in" / "other", freq=880)
    with pytest.raises(sa.SuppliedAudioError, match="different supplied audio"):
        sa.ingest(other, job, rights="owned", evidence="mine")
    assert _sha(job / rec["original"]["path"]) == rec["original"]["sha256"]


def test_same_name_different_content_is_not_overwritten(job, take, tmp_path):
    sa.ingest(take, job, rights="owned", evidence="mine")
    clash = _audio(tmp_path / "other-dir" / "voiceover", freq=660)       # same file name, different bytes
    with pytest.raises(sa.SuppliedAudioError):
        sa.ingest(clash, job, rights="owned", evidence="mine")


def test_reingest_is_idempotent(job, take):
    a = sa.ingest(take, job, rights="owned", evidence="mine")
    b = sa.ingest(take, job, rights="owned", evidence="mine")
    assert a["original"] == b["original"] and b["rights_history"] == []


def test_working_copy_is_separate_and_traceable(job, take):
    rec = sa.ingest(take, job, rights="owned", evidence="mine", working_copy=True)
    wc = rec["working_copy"]
    assert wc["path"] != rec["original"]["path"] and (job / wc["path"]).is_file()
    assert wc["derived_from_sha256"] == rec["original"]["sha256"] == _sha(take)
    assert _sha(job / rec["original"]["path"]) == rec["original"]["sha256"]       # original untouched by the derivation
    assert sa.verify(job)["working_copy"]["sha256"] == _sha(job / wc["path"])


def test_tampered_working_copy_is_detected(job, take):
    rec = sa.ingest(take, job, rights="owned", evidence="mine", working_copy=True)
    wc = job / rec["working_copy"]["path"]
    wc.write_bytes(wc.read_bytes() + b"\0")
    with pytest.raises(sa.SuppliedAudioError, match="working copy hash mismatch"):
        sa.verify(job)


# ---- compatibility with approval and artifact conventions -------------------------------------------------------------

@pytest.fixture
def pipe(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    spec = {"content_id": "sj", "title": "Supplied Job", "project": "Demo", "script": [{"say": "Hi there.", "headline": "Hi"}]}
    sp = tmp_path / "spec.yaml"
    sp.write_text(yaml.safe_dump(spec))
    storage.preflight()
    d, _ = storage.open_job("sj", spec)
    shutil.copy(make_video(tmp_path / "v.mp4", seconds=1), d / "video.mp4")
    return sp, spec, d, tmp_path / "pub"


def test_job_without_supplied_audio_is_unaffected(pipe):
    sp, spec, d, pub = pipe
    _, report = pipeline.run(sp, only="export")
    assert report[0][:2] == ("export", "OK") and len(list((pub / "ready").rglob("*.mp4"))) == 1


def test_unknown_rights_stop_the_export_stage_as_blocked_not_crashed(pipe, take):
    sp, spec, d, pub = pipe
    sa.ingest(take, d)                                                  # unknown
    _, report = pipeline.run(sp, only="export")
    assert report[0][0] == "export" and report[0][1].startswith("BLOCKED") and "unknown" in report[0][1]
    assert list((pub / "ready").rglob("*")) == []
    assert storage.read_manifest(d)["status"] != "failed"               # a gate-style stop, not a failure


def test_export_job_itself_also_refuses_unknown_rights(pipe, take):
    sp, spec, d, pub = pipe
    sa.ingest(take, d)
    with pytest.raises(export.ExportRefused, match="supplied audio blocks publication"):
        export.export_job("sj")
    assert list((pub / "ready").rglob("*")) == []


def test_rights_fix_then_export_succeeds(pipe, take):
    sp, spec, d, pub = pipe
    sa.ingest(take, d)
    assert pipeline.run(sp, only="export")[1][0][1].startswith("BLOCKED")
    sa.ingest(take, d, rights="owned", evidence="my own recording")
    assert pipeline.run(sp, only="export")[1][0][:2] == ("export", "OK")
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1


def test_tampered_audio_blocks_export_even_when_owned(pipe, take):
    sp, spec, d, pub = pipe
    rec = sa.ingest(take, d, rights="owned", evidence="mine")
    f = d / rec["original"]["path"]
    f.chmod(0o644)
    f.write_bytes(f.read_bytes() + b"\0")
    assert pipeline.run(sp, only="export")[1][0][1].startswith("BLOCKED")
    assert list((pub / "ready").rglob("*")) == []


def test_voice_stage_stops_explicitly_instead_of_generating_a_different_voice(pipe, take):
    sp, spec, d, pub = pipe
    sa.ingest(take, d, rights="owned", evidence="mine")
    ctx = {"id": "sj", "dir": d, "spec": spec, "allow_paid": False, "res": (1080, 1920)}
    with pytest.raises(pipeline.Blocked, match="supplied audio"):
        pipeline.s_voice(ctx)
    assert not (d / "audio").exists()                                   # nothing was synthesised


def test_artifacts_are_recorded_in_the_manifest_with_relative_paths(pipe, take):
    sp, spec, d, pub = pipe
    sa.ingest(take, d, rights="owned", evidence="mine", working_copy=True)
    files = storage.read_manifest(d)["artifacts"]["supplied_audio"]
    assert all(not f.startswith("/") for f in files) and "supplied-audio/supplied-audio.json" in files


def test_enabled_publish_is_blocked_by_unknown_rights(pipe, take, monkeypatch):
    sp, spec, d, pub = pipe
    sa.ingest(take, d)
    monkeypatch.setattr(pipeline.providers, "load", lambda name: {"publish": {"enabled": True}})
    with pytest.raises(pipeline.Blocked, match="supplied audio blocks publication"):
        pipeline.s_publish({"id": "sj", "dir": d, "spec": spec})


def test_dry_run_publish_is_unchanged(pipe, take, monkeypatch):
    sp, spec, d, pub = pipe
    sa.ingest(take, d)                                                  # unknown rights: dry run is not publication
    monkeypatch.setattr(pipeline.providers, "load", lambda name: {"publish": {"enabled": False}})
    prov, arts = pipeline.s_publish({"id": "sj", "dir": d, "spec": spec})
    assert prov == "dry-run"


# ---- CLI --------------------------------------------------------------------------------------------------------------

def test_cli_ingest_status_verify_exit_codes(job, take, capsys):
    assert sa.main(["ingest", str(take), "--job-dir", str(job)]) == 0              # unknown is accepted as a record
    assert sa.main(["status", "--job-dir", str(job)]) == 1                         # ... but blocks publication
    assert sa.main(["ingest", str(take), "--job-dir", str(job), "--rights", "owned", "--evidence", "mine"]) == 0
    assert sa.main(["status", "--job-dir", str(job)]) == 0
    assert sa.main(["verify", "--job-dir", str(job)]) == 0
    assert sa.main(["ingest", str(job / "missing.wav"), "--job-dir", str(job)]) == 2
    capsys.readouterr()
