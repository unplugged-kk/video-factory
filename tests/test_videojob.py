import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contentos import videojob as vj  # noqa: E402


def ids(res):
    return [c["id"] for c in res["capabilities"]]


def sel(kinds, **kw):
    return vj.select([{"kind": k} for k in kinds], **kw)


def test_topic_only_explainer_researches_voices_and_times():
    r = sel(["topic"])
    assert r["intent"] == "create" and not r["blockers"]
    assert ids(r)[:3] == ["research", "voice", "video-understanding"]
    assert "lyric-video-engine" not in ids(r) and "talking-head-editor" not in ids(r)


def test_lyric_video_uses_alignment_not_research():
    r = sel(["audio", "lyrics"])
    assert r["intent"] == "lyric" and not r["blockers"] and not r["warnings"]
    assert "lyric-video-engine" in ids(r) and "research" not in ids(r) and "talking-head-editor" not in ids(r)


def test_lyric_without_lyrics_warns_and_does_not_invent():
    r = sel(["audio"], intent="lyric")
    assert any("transcription" in w for w in r["warnings"])


def test_lyric_without_audio_blocks():
    assert sel(["lyrics"], intent="lyric")["blockers"]


def test_talking_head_edit_with_broll():
    r = sel(["video", "broll"])
    assert r["intent"] == "edit"
    assert ids(r)[:3] == ["video-understanding", "talking-head-editor", "asset-library"]
    assert "voice" not in ids(r)


def test_long_video_is_repurpose():
    assert sel(["video"], duration_s=1800)["intent"] == "repurpose"
    assert sel(["video"], duration_s=60)["intent"] == "edit"


def test_podcast_audio_to_explainer_skips_voice():
    r = sel(["audio"], intent="create")
    assert "video-understanding" in ids(r) and "voice" not in ids(r)


def test_news_needs_sources_and_researches():
    assert sel(["script"], intent="news")["blockers"]
    r = sel(["links"], intent="news")
    assert ids(r)[0] == "research" and not r["blockers"]


def test_data_chart_animates_supplied_data():
    r = sel(["data"])
    assert not r["blockers"] and "research" not in ids(r) and "motion-graphics-engine" in ids(r)


def test_product_video_from_photos_and_screens_reuses_assets():
    r = sel(["images", "screen"])
    assert "asset-library" in ids(r) and "talking-head-editor" not in ids(r)


def test_asset_search_runs_only_the_library():
    r = sel(["broll"], intent="assets")
    assert ids(r) == ["asset-library"]
    assert sel([], intent="assets")["blockers"]


def test_every_media_workflow_ends_with_render_and_qc():
    for kinds, kw in ((["topic"], {}), (["audio", "lyrics"], {}), (["video"], {}), (["data"], {})):
        assert ids(sel(kinds, **kw))[-2:] == ["video-renderer", "video-quality-checker"]


def test_unknown_kind_and_intent_rejected():
    with pytest.raises(ValueError):
        sel(["hologram"])
    with pytest.raises(ValueError):
        sel(["topic"], intent="juggle")


def test_new_job_validates_and_writes_once(tmp_path):
    m = vj.new_job("j1", "explain operators", [{"kind": "topic", "ref": "k8s operators"}],
                   output={"aspect": ["9:16", "16:9"], "duration_s": 60}, style={"look": "blueprint"})
    assert vj.validate(m) == []
    p = vj.write(m, tmp_path / "job")
    assert json.loads(p.read_text())["job_id"] == "j1"
    with pytest.raises(FileExistsError):
        vj.write(m, tmp_path / "job")


def test_write_refuses_in_repo_dir():
    m = vj.new_job("j2", "x", [{"kind": "topic"}])
    with pytest.raises(ValueError, match="outside the repository"):
        vj.write(m, vj.ROOT / "workspace" / "oops")


def test_validate_catches_bad_manifests():
    m = vj.new_job("j3", "x", [{"kind": "topic"}])
    m["bogus"] = 1
    m["status"] = "done"
    m["timing"] = {"granularity": "word"}
    m["workflow"]["capabilities"].append({"id": "magic"})
    errs = " ".join(vj.validate(m))
    for needle in ("unknown key: bogus", "status must", "tool", "magic"):
        assert needle in errs


def test_cli_select_exit_codes(capsys):
    assert vj.main(["select", "--input", "topic:k8s"]) == 0
    assert vj.main(["select", "--intent", "lyric", "--input", "lyrics:l.txt"]) == 1
    assert vj.main(["select", "--input", "hologram"]) == 2


SKILLS = Path(__file__).resolve().parent.parent / ".claude" / "skills"


@pytest.mark.parametrize("name", ["create-video", "edit-video", "make-lyric-video", "repurpose-video", "video-assets"])
def test_entry_skills_have_matching_frontmatter(name):
    head = (SKILLS / name / "SKILL.md").read_text().split("---")[1]
    assert f"name: {name}" in head and "description:" in head


def test_thin_commands_pass_a_known_intent_and_defer():
    # `lyric-video` is a vendored creative recipe name, so the thin shortcut is `make-lyric-video`.
    for name, intent in (("edit-video", "edit"), ("make-lyric-video", "lyric"), ("repurpose-video", "repurpose"),
                         ("video-assets", "assets")):
        text = (SKILLS / name / "SKILL.md").read_text()
        assert intent in vj.INTENTS and f"--intent {intent}" in text and "create-video/SKILL.md" in text


def test_implemented_by_covers_every_capability():
    assert set(vj.IMPLEMENTED_BY) == set(vj.CAPABILITIES)
    for cap, info in vj.IMPLEMENTED_BY.items():
        assert info["state"] in ("exists", "planned"), cap
        if info["state"] == "exists":
            assert info["by"] and (vj.ROOT / info["by"]).exists(), f"{cap}: {info['by']} is not in the repo"
        else:
            assert info["by"] is None, cap


def test_select_reports_state_and_implementer_for_every_capability():
    for kinds, kw in ((["topic"], {}), (["audio", "lyrics"], {}), (["video", "broll"], {}), (["data"], {})):
        for c in sel(kinds, **kw)["capabilities"]:
            assert c["why"] and c["state"] in ("exists", "planned") and "by" in c


def test_planned_capabilities_are_named_as_planned_not_hidden():
    caps = {c["id"]: c for c in sel(["video"], intent="edit")["capabilities"]}
    assert caps["talking-head-editor"]["state"] == "planned" and caps["talking-head-editor"]["by"] is None


def _skill_table_rows(name):
    rows = []
    for line in (SKILLS / name / "SKILL.md").read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == 2 and set(cells) - {"---", ":---", "---:"}:
            rows.append(cells)
    return rows


def test_skill_table_names_every_capability_and_keeps_no_second_state_copy():
    """The skill lists what each capability covers; its state lives only in IMPLEMENTED_BY, so the two cannot drift."""
    rows = _skill_table_rows("create-video")
    assert {r[0] for r in rows} >= set(vj.CAPABILITIES)
    assert not any(r[1] in ("exists", "planned") for r in rows)


def test_look_tag_is_not_confusable_with_the_shipped_look_ledger():
    """`look/1` names two shapes: a design preset and the export stage's shipped-look record. They must not merge."""
    from contentos import pipeline
    from contentos.intelligence import looks
    assert pipeline.LOOK_SCHEMA == looks.SCHEMA
    record = {"schema": pipeline.LOOK_SCHEMA, "content_id": "j1", "series": None, "signature": None, "verdict": "ok"}
    assert looks.check(record), "a shipped-look record must not pass as a preset"
    preset = looks.load_dir()["anime-cel"]
    assert "content_id" not in preset and "verdict" not in preset
