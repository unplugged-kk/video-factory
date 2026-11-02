import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from contentos import specs


def valid_spec(**changes):
    value = {
        "content_id": "creator-short-1",
        "title": "A useful short",
        "format": "9:16",
        "voice": "af_heart",
        "render": "hyperframes",
        "script": [
            {"say": "One two three four five.", "headline": "Count", "tag": "HOOK"},
            {"say": "Six seven eight nine ten."},
        ],
    }
    value.update(changes)
    return value


def test_valid_track_a_spec_reports_narration_estimate():
    result = specs.validate_spec(valid_spec())

    assert result == {
        "ok": True,
        "errors": [],
        "narration": {
            "word_count": 10,
            "estimated_seconds": 4.0,
            "words_per_second": 2.5,
        },
    }


@pytest.mark.parametrize("format_value", ["9:16", "16:9"])
def test_accepts_supported_formats(format_value):
    assert specs.validate_spec(valid_spec(format=format_value))["ok"] is True


def test_returns_field_paths_for_all_invalid_creator_fields():
    result = specs.validate_spec({
        "content_id": "../escape",
        "title": " ",
        "format": "1:1",
        "voice": "unknown",
        "render": "mpt",
        "script": [
            {"say": "", "headline": "", "tts": "hidden"},
            "not a line",
        ],
        "description": "not part of the MVP creator",
    })

    assert result["ok"] is False
    assert {error["path"] for error in result["errors"]} == {
        "content_id",
        "title",
        "format",
        "voice",
        "render",
        "script[0].say",
        "script[0].headline",
        "script[0].tts",
        "script[1]",
        "description",
    }
    assert all(set(error) == {"path", "message"} for error in result["errors"])


@pytest.mark.parametrize(
    "content_id",
    ["", ".hidden", "two..dots", "slash/name", "x" * 129, None],
)
def test_rejects_content_ids_outside_storage_rules(content_id):
    result = specs.validate_spec(valid_spec(content_id=content_id))
    assert any(error["path"] == "content_id" for error in result["errors"])


def test_rejects_empty_or_missing_script_lines():
    assert specs.validate_spec(valid_spec(script=[]))["errors"] == [
        {"path": "script", "message": "script must contain at least one line"}
    ]
    result = specs.validate_spec(valid_spec(script=[{}, {"headline": "No narration"}]))
    assert [error["path"] for error in result["errors"]] == ["script[0].say", "script[1].say"]


def test_python_loads_the_shared_adapter_voice_ids():
    shared = json.loads(specs.VOICE_IDS_FILE.read_text(encoding="utf-8"))
    assert specs.KOKORO_VOICE_IDS == frozenset(shared)
    assert len(shared) == 12
    assert all(specs.validate_spec(valid_spec(voice=voice_id))["ok"] for voice_id in shared)


def test_save_is_workspace_scoped_atomic_and_idempotent(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(workspace))
    spec = valid_spec()

    path = specs.save_spec(spec)
    first_stat = path.stat()
    same_path = specs.save_spec(spec)

    assert path == workspace / "specs" / "creator-short-1.yaml"
    assert same_path == path
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == spec
    assert same_path.stat().st_mtime_ns == first_stat.st_mtime_ns
    assert not list(path.parent.glob(".spec-*"))


def test_save_rejects_invalid_specs_and_changed_collisions(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(tmp_path / "workspace"))
    with pytest.raises(specs.SpecValidationError) as invalid:
        specs.save_spec(valid_spec(content_id="../escape"))
    assert invalid.value.errors[0]["path"] == "content_id"

    specs.save_spec(valid_spec())
    with pytest.raises(specs.SpecCollisionError, match="different saved spec"):
        specs.save_spec(valid_spec(title="Changed title"))


def test_save_never_follows_an_existing_spec_symlink(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    specs_dir = workspace / "specs"
    specs_dir.mkdir(parents=True)
    outside = tmp_path / "outside.yaml"
    outside.write_text(yaml.safe_dump(valid_spec()), encoding="utf-8")
    (specs_dir / "creator-short-1.yaml").symlink_to(outside)
    monkeypatch.setenv("VIDEO_FACTORY_WORKSPACE", str(workspace))

    with pytest.raises(specs.SpecCollisionError, match="must not be a symlink"):
        specs.save_spec(valid_spec())


def run_validate(path: Path, workspace: Path):
    env = {**os.environ, "VIDEO_FACTORY_WORKSPACE": str(workspace)}
    return subprocess.run(
        [sys.executable, "-m", "contentos", "validate", str(path), "--json"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_validate_cli_emits_only_json_and_useful_exit_codes(tmp_path):
    good = tmp_path / "good.yaml"
    bad = tmp_path / "bad.yaml"
    malformed = tmp_path / "malformed.yaml"
    good.write_text(yaml.safe_dump(valid_spec()), encoding="utf-8")
    bad.write_text(yaml.safe_dump(valid_spec(format="1:1")), encoding="utf-8")
    malformed.write_text("script: [", encoding="utf-8")

    valid = run_validate(good, tmp_path / "workspace")
    invalid = run_validate(bad, tmp_path / "workspace")
    unreadable = run_validate(malformed, tmp_path / "workspace")

    assert valid.returncode == 0
    assert json.loads(valid.stdout)["ok"] is True
    assert valid.stderr == ""
    assert invalid.returncode == 1
    assert json.loads(invalid.stdout)["errors"][0]["path"] == "format"
    assert invalid.stderr == ""
    assert unreadable.returncode == 2
    assert json.loads(unreadable.stdout)["errors"][0]["path"] == "$"
    assert unreadable.stderr == ""
