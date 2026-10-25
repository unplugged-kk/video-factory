"""asset-library: index local media, let written notes describe it, search it, and never invent a description."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contentos.production import assets  # noqa: E402
from storage_helpers import make_video  # noqa: E402


def media_dir(tmp_path):
    d = tmp_path / "broll"
    d.mkdir()
    make_video(d / "night-walk.mp4", seconds=2)
    make_video(d / "kitchen.mp4", seconds=2)
    (d / "shopping-list.txt").write_text("not media, never indexed")
    return d


def test_index_reads_media_and_never_invents_a_description(tmp_path):
    idx = assets.index_dir(media_dir(tmp_path), tmp_path / "frames")
    assert idx["schema"] == "assets/1"
    assert [Path(c["path"]).name for c in idx["clips"]] == ["kitchen.mp4", "night-walk.mp4"]
    c = idx["clips"][0]
    assert c["kind"] == "video" and (c["width"], c["height"]) == (1080, 1920) and c["fps"] == 30.0
    assert c["duration_s"] > 1.5 and c["has_audio"] is True and c["readable"] is True
    assert c["description"] == "" and c["tags"] == [] and c["license"] == "unknown" and c["described"] is False
    assert len(c["samples"]) == 3 and all(Path(s["file"]).exists() for s in c["samples"])


def test_notes_are_what_make_a_clip_described(tmp_path):
    idx = assets.index_dir(media_dir(tmp_path), tmp_path / "frames")
    skeleton = assets.notes_skeleton(idx)
    assert set(skeleton) == {c["path"] for c in idx["clips"]}
    assert all(v == {"description": "", "tags": [], "license": "", "source": ""} for v in skeleton.values())
    walk = next(c["path"] for c in idx["clips"] if c["path"].endswith("night-walk.mp4"))
    merged = assets.merge_notes(idx, {walk: {"description": "a person walking at night", "tags": ["night"],
                                             "license": "own"}})
    described = [c for c in merged["clips"] if c["described"]]
    assert len(described) == 1 and described[0]["license"] == "own" and described[0]["tags"] == ["night"]
    assert merged["notes_missing_from_index"] == []


def test_search_ranks_notes_over_path_and_says_why(tmp_path):
    idx = assets.index_dir(media_dir(tmp_path), tmp_path / "frames")
    walk = next(c["path"] for c in idx["clips"] if c["path"].endswith("night-walk.mp4"))
    assets.merge_notes(idx, {c["path"]: {"description": "an empty kitchen counter", "tags": ["kitchen"]}
                             for c in idx["clips"]} | {walk: {"description": "walking at night under street lights",
                                                              "tags": ["night", "walking"]}})
    hits = assets.search(idx, "walking at night")
    assert Path(hits[0]["path"]).name == "night-walk.mp4" and hits[0]["score"] > 0 and hits[0]["described"] is True
    assert {"tag:night", "tag:walking", "text:night"} <= set(hits[0]["why"])
    assert assets.search(idx, "submarine volcano") == []


def test_a_short_term_does_not_match_inside_an_unrelated_path():
    """`at` inside `private/var` used to score a hit; matching is whole-word, so it cannot."""
    idx = {"schema": "assets/1", "clips": [{"path": "/private/var/folders/kitchen.mp4", "kind": "video",
                                            "tags": [], "description": "", "described": False}]}
    assert assets.search(idx, "at") == []
    assert [h["score"] for h in assets.search(idx, "var")] == [1]


def test_verify_catches_a_clip_that_left_the_disk(tmp_path):
    d = media_dir(tmp_path)
    idx = assets.index_dir(d, tmp_path / "frames")
    assert assets.verify(idx) == []
    (d / "kitchen.mp4").unlink()
    assert any("missing on disk" in e for e in assets.verify(idx))


def test_verify_catches_a_description_that_was_claimed_without_one(tmp_path):
    idx = assets.index_dir(media_dir(tmp_path), tmp_path / "frames")
    idx["clips"][0]["described"] = True
    assert any("described without a description" in e for e in assets.verify(idx))


def test_writing_inside_the_repo_is_refused(tmp_path):
    idx = assets.index_dir(media_dir(tmp_path), tmp_path / "frames")
    with pytest.raises(ValueError, match="outside the repository"):
        assets.write_index(idx, assets.ROOT / "workspace" / "oops.json")


def test_cli_index_writes_a_skeleton_then_merges_it(tmp_path, capsys):
    d = media_dir(tmp_path)
    out = tmp_path / "index.json"
    assert assets.main(["index", str(d), "--out", str(out), "--samples", "1"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["clips"] == 2 and first["undescribed"] == 2 and first["unreadable"] == []
    assert Path(first["notes"]).exists()
    assert all(not c["described"] for c in json.loads(out.read_text())["clips"])

    skeleton = json.loads(Path(first["notes"]).read_text())
    skeleton[next(iter(skeleton))] = {"description": "a test clip", "tags": ["test"]}
    filled = tmp_path / "filled.json"
    filled.write_text(json.dumps(skeleton))
    assert assets.main(["index", str(d), "--out", str(out), "--samples", "1", "--notes", str(filled)]) == 0
    assert sum(1 for c in json.loads(out.read_text())["clips"] if c["described"]) == 1

    assert assets.main(["search", str(out), "test"]) == 0
    assert "\"hits\"" in capsys.readouterr().out
    assert assets.main(["search", str(out), "submarine"]) == 1
    assert assets.main(["verify", str(out)]) == 0
    assert assets.main(["verify", str(tmp_path / "nope.json")]) == 2


def test_cli_refuses_an_index_inside_the_repo(tmp_path, capsys):
    d = media_dir(tmp_path)
    assert assets.main(["index", str(d), "--out", str(assets.ROOT / "workspace" / "x.json")]) == 2
    assert "outside the repository" in capsys.readouterr().err
    assert not (assets.ROOT / "workspace" / f"frames-{d.name}").exists()
