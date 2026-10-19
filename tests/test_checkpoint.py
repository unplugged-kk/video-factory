import hashlib
import inspect
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# The module under test will be imported. In the initial test-first run,
# it does not exist yet so this will raise ImportError.
from contentos.production import checkpoint  # noqa: E402


def make_frame(tmp_path, name="f1.png", content=b"\x89PNG\r\n\x1a\n\x00\x00\x00"):
    # The module checks extension and existence, not image decoding.
    p = tmp_path / name
    p.write_bytes(content)
    return str(p)


def test_request_ok_full_and_lite(tmp_path):
    f1 = make_frame(tmp_path, "f1.png", b"frame-1")
    f2 = make_frame(tmp_path, "f2.jpg", b"frame-2")
    f3 = make_frame(tmp_path, "f3.jpeg", b"frame-3")

    out_full = tmp_path / "ckpt_full.json"
    res_full = checkpoint.request(
        job="job-test-1",
        style="blueprint-diagram",
        frames=[f1, f2, f3],
        shot_list=["s1: intro", "s2: body", "s3: conclusion"],
        out=str(out_full),
        mode="full",
    )

    assert res_full["schema"] == "style-checkpoint/1"
    assert res_full["job"] == "job-test-1"
    assert res_full["style"] == "blueprint-diagram"
    assert res_full["mode"] == "full"
    assert res_full["status"] == "pending"
    assert res_full["decision"] is None
    assert res_full["advisory"] is True
    assert len(res_full["frames"]) == 3
    assert res_full["frames"][0]["path"] == f1
    assert res_full["frames"][0]["sha256"] == hashlib.sha256(b"frame-1").hexdigest()

    saved_full = json.loads(out_full.read_text(encoding="utf-8"))
    assert saved_full == res_full

    # Lite mode: 1 frame, 1 shot
    out_lite = tmp_path / "ckpt_lite.json"
    res_lite = checkpoint.request(
        job="job-test-2",
        style="punch-split",
        frames=[f1],
        shot_list=["single shot for short"],
        out=str(out_lite),
        mode="lite",
    )
    assert res_lite["mode"] == "lite"
    assert len(res_lite["frames"]) == 1
    assert len(res_lite["shot_list"]) == 1
    assert res_lite["status"] == "pending"


def test_request_refuses_invalid_inputs(tmp_path):
    f1 = make_frame(tmp_path, "f1.png")
    f2 = make_frame(tmp_path, "f2.png")
    f3 = make_frame(tmp_path, "f3.png")
    shots = ["s1", "s2", "s3"]

    # Missing frame
    with pytest.raises(ValueError, match="not found|missing|exist"):
        checkpoint.request("j1", "blueprint-diagram", [f1, f2, str(tmp_path / "missing.png")], shots, str(tmp_path / "out.json"))

    # Wrong extension
    bad_ext = tmp_path / "f.gif"
    bad_ext.write_bytes(b"gif")
    with pytest.raises(ValueError, match="extension|format"):
        checkpoint.request("j1", "blueprint-diagram", [f1, f2, str(bad_ext)], shots, str(tmp_path / "out.json"))

    # 2 frames in full mode
    with pytest.raises(ValueError, match="3-8"):
        checkpoint.request("j1", "blueprint-diagram", [f1, f2], shots, str(tmp_path / "out.json"), mode="full")

    # 9 frames in full mode
    extra_frames = [make_frame(tmp_path, f"extra_{i}.png") for i in range(9)]
    with pytest.raises(ValueError, match="3-8"):
        checkpoint.request("j1", "blueprint-diagram", extra_frames, shots, str(tmp_path / "out.json"), mode="full")

    # 2 frames in lite mode
    with pytest.raises(ValueError, match="lite mode requires exactly 1 frame"):
        checkpoint.request("j1", "blueprint-diagram", [f1, f2], ["shot1"], str(tmp_path / "out.json"), mode="lite")

    # Empty shot list
    with pytest.raises(ValueError, match="shot_list"):
        checkpoint.request("j1", "blueprint-diagram", [f1, f2, f3], [], str(tmp_path / "out.json"))

    # Fewer than 3 shot list items in full mode
    with pytest.raises(ValueError, match="full mode requires at least 3"):
        checkpoint.request("j1", "blueprint-diagram", [f1, f2, f3], ["only one shot"], str(tmp_path / "out.json"), mode="full")

    # Unknown style id
    with pytest.raises(ValueError, match="unknown style"):
        checkpoint.request("j1", "non-existent-style", [f1, f2, f3], shots, str(tmp_path / "out.json"))

    # Bad job id
    with pytest.raises(ValueError, match="job"):
        checkpoint.request("bad job!", "blueprint-diagram", [f1, f2, f3], shots, str(tmp_path / "out.json"))

    # Existing out file (refuse overwrite)
    out_file = tmp_path / "existing.json"
    out_file.write_text("existing", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing to overwrite|exists"):
        checkpoint.request("j1", "blueprint-diagram", [f1, f2, f3], shots, str(out_file))


def test_decide_approve_with_human(tmp_path):
    f1 = make_frame(tmp_path, "f1.png")
    f2 = make_frame(tmp_path, "f2.png")
    f3 = make_frame(tmp_path, "f3.png")
    ckpt_path = tmp_path / "ckpt.json"

    checkpoint.request("j1", "blueprint-diagram", [f1, f2, f3], ["s1", "s2", "s3"], str(ckpt_path))

    dec = checkpoint.decide(
        path=str(ckpt_path),
        decision="approved",
        by="Kishore",
        human=True,
        note="looks great",
        at="2026-10-19",
    )

    assert dec["status"] == "approved"
    assert dec["decision"] == {
        "by": "Kishore",
        "at": "2026-10-19",
        "note": "looks great",
    }

    on_disk = json.loads(ckpt_path.read_text(encoding="utf-8"))
    assert on_disk["status"] == "approved"
    assert on_disk["decision"] == dec["decision"]


def test_decide_refuses_invalid_conditions(tmp_path):
    f1 = make_frame(tmp_path, "f1.png")
    f2 = make_frame(tmp_path, "f2.png")
    f3 = make_frame(tmp_path, "f3.png")
    ckpt_path = tmp_path / "ckpt.json"

    checkpoint.request("j1", "blueprint-diagram", [f1, f2, f3], ["s1", "s2", "s3"], str(ckpt_path))

    # Missing human=True
    with pytest.raises(ValueError, match="human"):
        checkpoint.decide(str(ckpt_path), decision="approved", by="Kishore", human=False)

    # Empty by
    with pytest.raises(ValueError, match="by"):
        checkpoint.decide(str(ckpt_path), decision="approved", by="   ", human=True)

    # Invalid decision value
    with pytest.raises(ValueError, match="decision"):
        checkpoint.decide(str(ckpt_path), decision="maybe", by="Kishore", human=True)

    # Redirect with short note (< 8 chars)
    with pytest.raises(ValueError, match="note"):
        checkpoint.decide(str(ckpt_path), decision="redirect", by="Kishore", human=True, note="short")

    # Rejected with short note (< 8 chars)
    with pytest.raises(ValueError, match="note"):
        checkpoint.decide(str(ckpt_path), decision="rejected", by="Kishore", human=True, note="1234567")

    # Approve once
    checkpoint.decide(str(ckpt_path), decision="approved", by="Kishore", human=True)

    # Subsequent decide from non-pending status fails
    with pytest.raises(ValueError, match="pending"):
        checkpoint.decide(str(ckpt_path), decision="approved", by="Kishore", human=True)


def test_verify_detects_changed_and_deleted_frames(tmp_path):
    f1 = make_frame(tmp_path, "f1.png", b"original-1")
    f2 = make_frame(tmp_path, "f2.png", b"original-2")
    f3 = make_frame(tmp_path, "f3.png", b"original-3")
    ckpt_path = tmp_path / "ckpt.json"

    checkpoint.request("j1", "blueprint-diagram", [f1, f2, f3], ["s1", "s2", "s3"], str(ckpt_path))

    v_clean = checkpoint.verify(str(ckpt_path))
    assert v_clean["stale"] is False
    assert v_clean["changed"] == []
    assert v_clean["missing"] == []

    # Modify f2
    Path(f2).write_bytes(b"tampered-2")
    v_changed = checkpoint.verify(str(ckpt_path))
    assert v_changed["stale"] is True
    assert f2 in v_changed["changed"]

    # Verify did NOT mutate the file on disk
    on_disk = json.loads(ckpt_path.read_text(encoding="utf-8"))
    assert on_disk["status"] == "pending"

    # Delete f3
    Path(f3).unlink()
    v_missing = checkpoint.verify(str(ckpt_path))
    assert v_missing["stale"] is True
    assert f3 in v_missing["missing"]


def test_decide_on_stale_checkpoint_is_refused(tmp_path):
    f1 = make_frame(tmp_path, "f1.png", b"data1")
    f2 = make_frame(tmp_path, "f2.png", b"data2")
    f3 = make_frame(tmp_path, "f3.png", b"data3")
    ckpt_path = tmp_path / "ckpt.json"

    checkpoint.request("j1", "blueprint-diagram", [f1, f2, f3], ["s1", "s2", "s3"], str(ckpt_path))

    # Mutate a frame
    Path(f1).write_bytes(b"data1-modified")

    with pytest.raises(ValueError, match="stale.*re-request|re-request"):
        checkpoint.decide(str(ckpt_path), decision="approved", by="Kishore", human=True)


def test_module_has_no_gate_or_pipeline_imports():
    src = inspect.getsource(checkpoint)
    forbidden = ["pipeline", "approve(", "SCRIPT_APPROVED", "PRODUCTION_APPROVED", "PUBLISH_APPROVED"]
    for word in forbidden:
        assert word not in src, f"forbidden gate/pipeline reference {word!r} found in checkpoint.py"


def test_cli_commands_and_exit_codes(tmp_path):
    f1 = make_frame(tmp_path, "f1.png")
    f2 = make_frame(tmp_path, "f2.png")
    f3 = make_frame(tmp_path, "f3.png")
    ckpt_path = tmp_path / "cli_ckpt.json"

    # 1. CLI request ok -> 0
    rc = checkpoint.main([
        "request",
        "--job", "cli-job-1",
        "--style", "blueprint-diagram",
        "--frame", f1,
        "--frame", f2,
        "--frame", f3,
        "--shot", "shot 1",
        "--shot", "shot 2",
        "--shot", "shot 3",
        "--out", str(ckpt_path),
    ])
    assert rc == 0

    # 2. CLI request refusal (duplicate out) -> 1
    rc_refusal = checkpoint.main([
        "request",
        "--job", "cli-job-1",
        "--style", "blueprint-diagram",
        "--frame", f1,
        "--frame", f2,
        "--frame", f3,
        "--shot", "shot 1",
        "--shot", "shot 2",
        "--shot", "shot 3",
        "--out", str(ckpt_path),
    ])
    assert rc_refusal == 1

    # 3. CLI verify ok -> 0
    rc_v = checkpoint.main(["verify", str(ckpt_path)])
    assert rc_v == 0

    # 4. CLI decide without --human -> 1
    rc_no_human = checkpoint.main([
        "decide", str(ckpt_path),
        "--decision", "approved",
        "--by", "Kishore",
    ])
    assert rc_no_human == 1

    # 5. CLI decide with --human -> 0
    rc_decide = checkpoint.main([
        "decide", str(ckpt_path),
        "--decision", "approved",
        "--by", "Kishore",
        "--human",
        "--note", "approved successfully",
    ])
    assert rc_decide == 0

    # 6. CLI unreadable file -> 2
    rc_bad_file = checkpoint.main(["verify", str(tmp_path / "nonexistent.json")])
    assert rc_bad_file == 2
