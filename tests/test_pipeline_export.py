"""The pipeline's export stage: a validated render reaches ready/; a bad one never does; retries add nothing.
Also: `--force` must reach export, and two runs of one job must not interleave."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contentos import export, handoff, pipeline, storage  # noqa: E402
from contentos.intelligence import visual  # noqa: E402
from contentos.production import supplied_audio  # noqa: E402
from storage_helpers import make_video  # noqa: E402


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("VIDEO_FACTORY_PUBLISH_DIR", str(tmp_path / "pub"))
    spec = tmp_path / "spec.yaml"
    spec.write_text(yaml.safe_dump({"content_id": "pj", "title": "Pipeline Job", "project": "Demo", "script": [{"say": "Hi there."}]}))
    return spec, tmp_path / "pub"


def stage(spec, video):
    storage.preflight()
    d, _ = storage.open_job("pj", yaml.safe_load(spec.read_text()))
    shutil.copy(video, d / "video.mp4")
    return d


def test_export_stage_publishes_and_is_idempotent(setup, tmp_path):
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "ok.mp4", seconds=1))
    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "OK")
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1
    pipeline.run(spec, only="export", force=True)                      # forced re-run: still one copy
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1
    assert storage.read_manifest(d)["status"] == "exported"


def test_export_stage_failure_is_recorded_and_ready_stays_empty(setup, tmp_path):
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "bad.mp4", w=320, h=240, seconds=1))
    _, report = pipeline.run(spec, only="export")
    assert report[0][1].startswith("FAIL")
    assert list((pub / "ready").rglob("*")) == []
    assert storage.read_manifest(d)["status"] == "failed"


def test_stage_order_has_export_before_publish():
    assert pipeline.STAGES.index("package") < pipeline.STAGES.index("export") < pipeline.STAGES.index("publish")


# ---- --force must reach export (it used to dead-end there) and must not go too far ----

def test_forced_rerun_replaces_superseded_export(setup, tmp_path):
    """A re-render that changes the bytes must be exportable with --force. This is the case that used to fail."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v1.mp4", seconds=1))
    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "OK")
    first = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())

    shutil.copy(make_video(tmp_path / "v2.mp4", seconds=3), d / "video.mp4")
    _, report = pipeline.run(spec, only="export", force=True)
    assert report[0][:2] == ("export", "OK")
    sidecars = list((pub / "ready").rglob("*.publish.json"))
    assert len(sidecars) == 1                                        # replaced in place, not duplicated
    second = json.loads(sidecars[0].read_text())
    assert second["video_sha256"] == export.sha256_file(d / "video.mp4")
    assert second["video_sha256"] != first["video_sha256"]
    assert storage.read_manifest(d)["status"] == "exported"


def test_rerun_without_force_refuses_superseded_export(setup, tmp_path):
    """Without --force the old refusal stands, and the already-exported video is left untouched.

    The export stage's resume sentinel is removed first to reach the stage at all - see the skip test below for why a
    plain re-run never gets this far.
    """
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v1.mp4", seconds=1))
    pipeline.run(spec, only="export")
    shutil.copy(make_video(tmp_path / "v2.mp4", seconds=3), d / "video.mp4")
    (d / "export-result.json").unlink()          # the sentinel the pipeline itself deletes when a stage fails

    _, report = pipeline.run(spec, only="export")
    assert report[0][1].startswith("FAIL")
    assert "force" in report[0][1]
    assert len(list((pub / "ready").rglob("*.mp4"))) == 1
    sc = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    assert sc["video_sha256"] != export.sha256_file(d / "video.mp4")  # nothing was replaced


# ---- a resumed export is only "done" when the render still matches what was exported ----

def test_a_matching_render_still_resumes_silently(setup, tmp_path):
    """Normal resume must be untouched: same render, so the skip is honest."""
    spec, pub = setup
    stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    pipeline.run(spec, only="export")

    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "SKIP(resume)")


def test_a_stale_render_blocks_the_resume_instead_of_reporting_success(setup, tmp_path):
    """The gap this closes: a re-render must not be reported as a successful export resume."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v1.mp4", seconds=1))
    pipeline.run(spec, only="export")
    first = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    shutil.copy(make_video(tmp_path / "v2.mp4", seconds=3), d / "video.mp4")

    _, report = pipeline.run(spec, only="export")
    assert report[0][0] == "export" and report[0][1].startswith("BLOCKED")
    assert "render changed since it was exported" in report[0][1]
    assert "--force" in report[0][1]
    assert (d / "export-result.json").exists()                    # the sentinel is kept, so no later run self-authorises
    sc = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    assert sc["video_sha256"] == first["video_sha256"]            # ready/ still holds the older, exported render
    assert [r["job_id"] for r in export.divergence()["superseded"]] == ["pj"]

    _, report = pipeline.run(spec, only="export", force=True)      # the explicit path still replaces it
    assert report[0][:2] == ("export", "OK")
    sc = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    assert sc["video_sha256"] == export.sha256_file(d / "video.mp4")


def test_a_claimed_export_that_still_matches_resumes(setup, tmp_path):
    """A claim protects replacement without adding a false block: an unchanged render still resumes."""
    spec, pub = setup
    stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    pipeline.run(spec, only="export")
    handoff.claim(pub, "pj", "scheduler")

    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "SKIP(resume)")


def test_a_resume_that_cannot_be_verified_is_blocked(setup, tmp_path):
    """Lost export metadata must block with a diagnostic, never resume as a pass and never re-export."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    pipeline.run(spec, only="export")
    next((pub / "ready").rglob("*.publish.json")).unlink()
    (pub / ".state" / "exports" / "pj.json").unlink()
    before = sorted(p.relative_to(pub).as_posix() for p in pub.rglob("*") if p.is_file())

    _, report = pipeline.run(spec, only="export")
    assert report[0][0] == "export" and report[0][1].startswith("BLOCKED")
    assert "cannot verify" in report[0][1] and "--force" in report[0][1]
    assert (d / "export-result.json").exists()
    assert sorted(p.relative_to(pub).as_posix() for p in pub.rglob("*") if p.is_file()) == before


# Not covered here: a manifest that is not jobmanifest/1. `run()` calls `storage.open_job` before the stage loop and that
# raises StorageError, so a legacy job never reaches the resume guard; its own handling of that input is covered by
# tests/test_export_divergence.py, which calls resume_blocker directly and asserts a diagnostic rather than a raise.
# (Out of scope for this change: the pre-existing open_job failure, whose documented remedy is `contentos storage adopt`.)


def test_an_archived_job_and_a_job_without_a_video_still_resume(setup, tmp_path):
    """Neither is a stale export: an archived job was handed off deliberately, and a job with no workspace video has
    nothing to compare. Blocking either would be noise and would mark the archived job failed."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    pipeline.run(spec, only="export")
    handoff.claim(pub, "pj", "scheduler")
    handoff.transition(pub, "pj", "published", "scheduler")
    handoff.archive(pub, "pj")

    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "SKIP(resume)")            # archived

    (d / "video.mp4").unlink()                                   # nothing to compare
    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "SKIP(resume)")


# ---- the export stage records the look in the shipped-look ledger ----

# Three stacked radial gradients read as structure "mesh", which is unlike either entry in the shipped seed
# (ep2-tool-call-failure is paper/warm/light; pilot-001-agent-tool-use is radial/cool/grid with accents [1, 5]) - so a
# test that wants a look Rule B accepts must not use the flat radial default, which collides with pilot-001.
MESH = ("radial-gradient(circle at 20% 20%,#0e3a32,#061410),"
        "radial-gradient(circle at 80% 30%,#123f36,#061410),"
        "radial-gradient(circle at 50% 80%,#0b2f2a,#061410)")


def composition(d, *, bg="radial-gradient(circle at 50% 20%,#1a1e36,#08090e)", body="#0b1020",
                a1="#f6c344", a2="#3fa9f5"):
    """A minimal HyperFrames composition whose CSS the signature extractor can read."""
    (d / "project").mkdir(parents=True, exist_ok=True)
    (d / "project" / "index.html").write_text(
        "<!DOCTYPE html><html><head><style>"
        f":root{{--bg:{body};--accent:{a1};--accent2:{a2}}}"
        f"body{{background:{body}}}"
        f"#root{{background:{bg}}}"
        '</style></head><body><div id="root" data-composition-id="root"></div></body></html>')
    return d / "project" / "index.html"


def stage_as(spec, video, job_id):
    storage.preflight()
    d, _ = storage.open_job(job_id, yaml.safe_load(spec.read_text()))
    shutil.copy(video, d / "video.mp4")
    return d


def ledger_of(ws):
    p = ws / "intelligence" / "visual-languages.json"
    return json.loads(p.read_text())["entries"] if p.exists() else []


def test_export_records_the_look_in_the_ledger(setup, tmp_path):
    spec, pub = setup
    spec.write_text(yaml.safe_dump({"content_id": "pj", "title": "Pipeline Job", "project": "Demo",
                                    "script": [{"say": "Hi there."}]}))
    d = stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    composition(d, bg=MESH, body="#061410", a1="#ff6b6b", a2="#c084fc")

    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "OK")

    entries = ledger_of(tmp_path / "ws")
    assert [e["content_id"] for e in entries] == ["pj"]
    assert entries[0]["series"] == "demo"                         # derived from the manifest's project_id
    assert entries[0]["source"] == "claim"
    assert set(entries[0]["signature"]) == {"structure", "temperature", "texture", "base", "accents"}

    look = json.loads((d / "look.json").read_text())
    assert look["schema"] == "look/1" and look["status"] == "recorded" and look["reason"] is None
    assert look["verdict"]["ok"] is True and look["verdict"]["duplicates"] == []


def test_a_missing_composition_still_exports_and_reports_the_skip(setup, tmp_path):
    """A spent render must never be lost because the look could not be read."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v.mp4", seconds=1))     # no project/index.html

    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "OK")
    assert ledger_of(tmp_path / "ws") == []
    look = json.loads((d / "look.json").read_text())
    assert look["status"] == "skipped" and "no composition" in look["reason"]


def test_a_duplicate_look_is_recorded_so_the_next_check_can_see_it(setup, tmp_path):
    """The ledger is the history of what shipped: a duplicate that shipped must be in it, or Rule B cannot see it."""
    spec, pub = setup
    first = stage(spec, make_video(tmp_path / "v1.mp4", seconds=1))
    composition(first)
    pipeline.run(spec, only="export")

    spec.write_text(yaml.safe_dump({"content_id": "pj2", "title": "Second Job", "project": "Demo",
                                    "script": [{"say": "Hi there."}]}))
    second = stage_as(spec, make_video(tmp_path / "v2.mp4", seconds=1), "pj2")
    composition(second)                                            # the same look: a Rule B duplicate
    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "OK")

    assert sorted(e["content_id"] for e in ledger_of(tmp_path / "ws")) == ["pj", "pj2"]
    look = json.loads((second / "look.json").read_text())
    assert look["status"] == "recorded"                            # recorded anyway
    assert look["verdict"]["ok"] is False
    assert "pj" in look["verdict"]["duplicates"]                   # the video it repeats is named
    assert "pilot-001-agent-tool-use" in look["verdict"]["duplicates"]   # and the seed look it also repeats


def test_recording_the_look_never_fails_the_export(setup, tmp_path, monkeypatch):
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    composition(d)

    def boom(*a, **k):
        raise RuntimeError("ledger is unwritable")

    monkeypatch.setattr(visual, "claim", boom)
    _, report = pipeline.run(spec, only="export")
    assert report[0][:2] == ("export", "OK")                       # the export is untouched
    look = json.loads((d / "look.json").read_text())
    assert look["status"] == "skipped" and "unwritable" in look["reason"]


def test_a_bespoke_composition_yields_a_meaningful_signature(tmp_path):
    """The shipped videos are hand-authored, not template output, so the extractor has to read their own CSS vocabulary
    rather than fall back to one constant (which would make the ledger meaningless)."""
    cool, warm = tmp_path / "cool", tmp_path / "warm"
    cool.mkdir(); warm.mkdir()
    composition(cool, bg="radial-gradient(circle at 50% 20%,#141c30,#05070b)", a1="#22d3ee", a2="#fbbf24")
    composition(warm, bg="linear-gradient(180deg,#2a0b3a,#12051c)", body="#2a0b3a", a1="#ff2bd6", a2="#b6ff3b")

    a, b = visual.signature_of(cool), visual.signature_of(warm)
    assert a != b                                                  # distinct, not a constant default
    assert (a["structure"], b["structure"]) == ("radial", "linear")
    assert a["base"]["tier"] == b["base"]["tier"] == "dark"
    assert a["accents"] and b["accents"] and visual.differing(a, b)


def test_forced_rerun_cannot_replace_a_claimed_export(setup, tmp_path):
    """force supersedes an unclaimed export only. A scheduler's claim must still refuse."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v1.mp4", seconds=1))
    pipeline.run(spec, only="export")
    handoff.claim(pub, "pj", "scheduler")
    shutil.copy(make_video(tmp_path / "v2.mp4", seconds=3), d / "video.mp4")

    _, report = pipeline.run(spec, only="export", force=True)
    assert report[0][1].startswith("FAIL")
    assert "claimed" in report[0][1]
    sc = json.loads(next((pub / "ready").rglob("*.publish.json")).read_text())
    assert sc["video_sha256"] != export.sha256_file(d / "video.mp4")


def test_forced_rerun_of_identical_video_is_a_no_op(setup, tmp_path):
    """force must not rewrite an export that is already current."""
    spec, pub = setup
    stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    pipeline.run(spec, only="export")
    snapshot = sorted(p.relative_to(pub).as_posix() for p in pub.rglob("*") if p.is_file())

    _, report = pipeline.run(spec, only="export", force=True)
    assert report[0][:2] == ("export", "OK")
    assert sorted(p.relative_to(pub).as_posix() for p in pub.rglob("*") if p.is_file()) == snapshot


def test_second_run_refuses_while_the_run_lock_is_held(setup, tmp_path):
    """Two runs of one job must not interleave: the second is refused by name, before any stage runs."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    with storage.file_lock(d / ".run.lock"):
        with pytest.raises(storage.StorageError, match=r"\.run\.lock is held by another process"):
            pipeline.run(spec, only="export")
    _, report = pipeline.run(spec, only="export")                    # free again once the holder released it
    assert report[0][:2] == ("export", "OK")


def test_force_does_not_bypass_a_supplied_audio_blocker(setup, tmp_path):
    """force replaces an export; it must never carry rights-unclear audio into ready/."""
    spec, pub = setup
    d = stage(spec, make_video(tmp_path / "v.mp4", seconds=1))
    take = tmp_path / "take.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(take)], check=True)
    supplied_audio.ingest(take, d, rights="unknown")

    _, report = pipeline.run(spec, only="export", force=True)
    assert report[0][1].startswith("BLOCKED")
    assert "supplied audio" in report[0][1]
    assert list((pub / "ready").rglob("*.mp4")) == []
