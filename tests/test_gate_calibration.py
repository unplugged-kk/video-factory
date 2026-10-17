"""Gate calibration: which quality gates actually FAIL on a deliberately bad video, and PASS on a good one.

Owner rule: a gate is trusted only after it is shown to fail on a deliberately bad render. This file builds tiny synthetic
clips with ffmpeg at test time (nothing is committed; media is gitignored) and runs the existing gates on them:

  * contentos.qa.run_qa           the nine in-pipeline checks (render_integrity, resolution, frame_rate, duration,
                                  audio_track, loudness, clipping, black_frames, frozen_frames)
  * contentos.finalcheck.validate_video   the export-time wrapper
  * contentos.production.visual_gate      captions, transitions, safezone, layers, log

Gate code was fixed in lane L8 (gatefix); fixed gaps are test_fixed_*. Where a gate does NOT fail on a clip that is plainly bad, or does something
surprising, the test is named `test_gap_*` and asserts what the gate ACTUALLY does today (a characterization), with a comment
saying what a trustworthy gate would do. If a gate is later fixed, that test fails on purpose and should be flipped.

Set CALIBRATION_MATRIX_OUT=/path/matrix.json to dump every (gate, clip, expected, observed) row for the evidence file.
No HyperFrames, no pipeline run, no network."""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

from contentos import finalcheck, qa
from contentos.production import visual_gate as vg

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not installed; gate calibration needs both to build and probe synthetic clips")

_MATRIX: list[dict] = []


@pytest.fixture(scope="module", autouse=True)
def _dump_matrix():
    yield
    out = os.environ.get("CALIBRATION_MATRIX_OUT")
    if out:
        with open(out, "w") as f:
            json.dump(_MATRIX, f, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))


def _rec(gate, clip, expected, observed, note=""):
    _MATRIX.append({"gate": gate, "clip": clip, "expected": expected, "observed": observed, "note": note,
                    "match": str(expected) == str(observed)})


def _ff(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-nostdin", *args], check=True, capture_output=True)


# ---- clip builders (QA clips, 9:16 1080x1920) ------------------------------------------------------------------------

def _qa_clip(out, *, dur=5.0, fps=25, size="1080x1920", vf=None, audio="good", freeze_tail=0.0, freeze_mid=0.0):
    """testsrc2 is bright and always moving, so by default the picture is neither black nor frozen."""
    chain = [vf] if vf else []
    if freeze_mid:                                   # repeat frame 1 s in, for freeze_mid seconds, then carry on moving
        chain.append(f"loop=loop={int(freeze_mid * fps)}:size=1:start={int(fps)}")
    if freeze_tail:                                  # clone the last frame: the picture stays frozen until end of file
        chain.append(f"tpad=stop_mode=clone:stop_duration={freeze_tail}")
    chain.append("format=yuv420p")
    total = dur + freeze_tail + freeze_mid
    args = ["-f", "lavfi", "-i", f"testsrc2=s={size}:r={fps}:d={dur}"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=f=440:r=48000:d={total}"]
    args += ["-vf", ",".join(chain)]
    if audio == "good":
        args += ["-af", "volume=7.5dB"]                              # sine is -18 dBFS peak by default -> about -10 dBFS, ~-14 LUFS
    elif audio == "clipped":
        args += ["-af", "volume=30dB,aformat=sample_fmts=s16"]       # hard-clipped at conversion
    elif audio == "silent":
        args += ["-af", "volume=0"]
    if audio:
        args += ["-c:a", "aac", "-b:a", "128k"]
    else:
        args += ["-an"]
    args += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-r", str(fps), "-t", str(total), str(out)]
    _ff(args)
    return out


BLACK_1_5S = "drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='between(t,1,2.5)'"
BLACK_0_3S = "drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='between(t,1,1.3)'"


@pytest.fixture(scope="module")
def qa_clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("qa")
    c = {}
    c["good"] = _qa_clip(d / "good.mp4")
    c["black_1_5s"] = _qa_clip(d / "black_1_5s.mp4", vf=BLACK_1_5S)
    c["black_blink_0_3s"] = _qa_clip(d / "black_blink_0_3s.mp4", vf=BLACK_0_3S)
    c["frozen_4s"] = _qa_clip(d / "frozen_4s.mp4", dur=4.0, freeze_mid=4.0)
    c["frozen_2s"] = _qa_clip(d / "frozen_2s.mp4", dur=4.0, freeze_mid=2.0)
    c["frozen_tail_4s"] = _qa_clip(d / "frozen_tail_4s.mp4", dur=2.0, freeze_tail=4.0)
    c["clipped_audio"] = _qa_clip(d / "clipped_audio.mp4", audio="clipped")
    c["no_audio"] = _qa_clip(d / "no_audio.mp4", audio=None)
    c["silent_audio"] = _qa_clip(d / "silent_audio.mp4", audio="silent")
    c["fps_12"] = _qa_clip(d / "fps_12.mp4", fps=12)
    c["res_720x1280"] = _qa_clip(d / "res_720x1280.mp4", size="720x1280")
    c["res_1920x1080"] = _qa_clip(d / "res_1920x1080.mp4", size="1920x1080")
    return c


def _by_check(rows):
    return {name: (status, detail) for name, status, detail in rows}


def _status(clip_name, rows, check):
    got = _by_check(rows).get(check, ("ABSENT", ""))[0]
    return got


def _assert_qa(rows, clip, expect):
    """expect: {check: status}. Records every pair for the evidence matrix and asserts all of them."""
    for check, want in expect.items():
        got = _status(clip, rows, check)
        _rec(f"qa.{check}", clip, want, got)
        assert got == want, f"{clip}: {check} expected {want}, got {got} ({_by_check(rows).get(check)})"


GOOD_ALL_PASS = {"render_integrity": "PASS", "resolution": "PASS", "frame_rate": "PASS", "duration": "PASS", "audio_track": "PASS",
                 "loudness": "PASS", "clipping": "PASS", "black_frames": "PASS", "frozen_frames": "PASS"}


# ---- qa.run_qa --------------------------------------------------------------------------------------------------------

def test_qa_good_clip_passes_every_check(qa_clips):
    rows = qa.run_qa(qa_clips["good"], "9:16")
    assert [r[0] for r in rows] == list(GOOD_ALL_PASS)                      # all nine checks ran, in order
    _assert_qa(rows, "good", GOOD_ALL_PASS)


def test_qa_black_segment_over_limit_fails_black_frames(qa_clips):
    rows = qa.run_qa(qa_clips["black_1_5s"])
    _assert_qa(rows, "black_1_5s", {**GOOD_ALL_PASS, "black_frames": "FAIL"})


def test_qa_short_black_blink_under_limit_passes(qa_clips):
    # 0.3 s black is under max_black_seconds (0.5): by design this must not fail.
    _assert_qa(qa.run_qa(qa_clips["black_blink_0_3s"]), "black_blink_0_3s", GOOD_ALL_PASS)


def test_qa_frozen_segment_over_limit_warns_not_fails(qa_clips):
    rows = qa.run_qa(qa_clips["frozen_4s"])
    _assert_qa(rows, "frozen_4s", {**GOOD_ALL_PASS, "frozen_frames": "WARN"})     # WARN-only gate: never FAIL
    assert "FAIL" not in {s for _, s, _ in rows}


def test_qa_frozen_segment_under_limit_passes(qa_clips):
    _assert_qa(qa.run_qa(qa_clips["frozen_2s"]), "frozen_2s", GOOD_ALL_PASS)


def test_qa_clipped_audio_fails_clipping_and_warns_loudness(qa_clips):
    rows = qa.run_qa(qa_clips["clipped_audio"])
    _assert_qa(rows, "clipped_audio", {**GOOD_ALL_PASS, "clipping": "FAIL", "loudness": "WARN"})


def test_qa_missing_audio_track_fails(qa_clips):
    rows = qa.run_qa(qa_clips["no_audio"])
    assert [r[0] for r in rows if r[0] in ("loudness", "clipping")] == []         # audio checks are skipped, not passed
    _assert_qa(rows, "no_audio", {"audio_track": "FAIL", "resolution": "PASS", "black_frames": "PASS"})


def test_qa_frame_rate_below_24_fails(qa_clips):
    _assert_qa(qa.run_qa(qa_clips["fps_12"]), "fps_12", {**GOOD_ALL_PASS, "frame_rate": "FAIL"})


@pytest.mark.parametrize("name", ["res_720x1280", "res_1920x1080"])
def test_qa_wrong_resolution_fails(qa_clips, name):
    _assert_qa(qa.run_qa(qa_clips[name]), name, {**GOOD_ALL_PASS, "resolution": "FAIL"})


def test_qa_landscape_clip_checked_as_16_9_passes_resolution(qa_clips):
    _assert_qa(qa.run_qa(qa_clips["res_1920x1080"], "16:9"), "res_1920x1080@16:9", {"resolution": "PASS"})


def test_qa_over_duration_limit_fails(tmp_path):
    # 181 s > 180 s cap for 9:16. One moving second then a cloned tail keeps encoding cheap (the tail is frozen, which frozen_frames does not report; see the gap test).
    p = _qa_clip(tmp_path / "long.mp4", dur=1.0, fps=24, freeze_tail=180.0)
    rows = qa.run_qa(p)
    _assert_qa(rows, "duration_181s", {"duration": "FAIL", "resolution": "PASS", "frame_rate": "PASS"})


def test_qa_unreadable_file_fails_render_integrity(tmp_path):
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"this is not a video" * 100)
    rows = qa.run_qa(junk)
    assert rows == [("render_integrity", "FAIL", "ffprobe cannot read file")]
    _rec("qa.render_integrity", "garbage_bytes", "FAIL", rows[0][1])


def test_qa_truncated_file_fails_render_integrity(qa_clips, tmp_path):
    data = qa_clips["good"].read_bytes()
    cut = tmp_path / "truncated.mp4"
    cut.write_bytes(data[: len(data) // 3])                                         # moov atom is at the end: file is unplayable
    rows = qa.run_qa(cut)
    _assert_qa(rows, "truncated_mp4", {"render_integrity": "FAIL"})


def test_qa_empty_file_fails_render_integrity(tmp_path):
    p = tmp_path / "empty.mp4"
    p.write_bytes(b"")
    _assert_qa(qa.run_qa(p), "empty_file", {"render_integrity": "FAIL"})


# ---- qa.run_qa: gaps (behaviour that is not what a trustworthy gate would do) ------------------------------------------

def test_fixed_silent_audio_track_fails_loudness_and_has_clipping_row(qa_clips):
    """A track of pure silence is present (audio_track PASS) but must FAIL loudness (about -70 LUFS, at or under -60) and the
    clipping row must exist (ffmpeg prints 'Peak: -inf dBFS'). Loudness for audible audio stays WARN-only."""
    rows = qa.run_qa(qa_clips["silent_audio"])
    d = _by_check(rows)
    _rec("qa.loudness", "silent_audio", "FAIL", d["loudness"][0], "fixed: silent track fails")
    assert d["audio_track"][0] == "PASS"
    assert d["loudness"][0] == "FAIL" and "silent" in d["loudness"][1]
    assert d["clipping"][0] == "PASS"
    fc = finalcheck.validate_video(qa_clips["silent_audio"])
    assert fc["status"] == "failed" and _fc(fc)["loudness"] == "FAIL"


def test_fixed_frozen_until_end_of_file_is_reported(qa_clips):
    """A freeze that runs to the END of the file has freeze_start but no freeze_duration; frozen_frames now counts it (WARN)."""
    rows = qa.run_qa(qa_clips["frozen_tail_4s"])
    got = _status("frozen_tail_4s", rows, "frozen_frames")
    _rec("qa.frozen_frames", "frozen_tail_4s", "WARN", got, "fixed")
    assert got == "WARN"
    assert _status("good", qa.run_qa(qa_clips["good"]), "frozen_frames") == "PASS"


def test_fixed_audio_only_file_fails_render_integrity(tmp_path):
    """No video stream: a clean render_integrity FAIL row, never a TypeError."""
    p = tmp_path / "audio_only.m4a"
    _ff(["-f", "lavfi", "-i", "sine=f=440:d=1", "-c:a", "aac", str(p)])
    rows = qa.run_qa(p)
    assert rows[0][:2] == ("render_integrity", "FAIL") and "no video stream" in rows[0][2]
    _rec("qa.run_qa", "audio_only_no_video_stream", "FAIL row", rows[0][1], "fixed")


# ---- finalcheck.validate_video ----------------------------------------------------------------------------------------

def _fc(result):
    return {c["check"]: c["status"] for c in result["checks"]}


def test_finalcheck_good_clip_passes(qa_clips):
    r = finalcheck.validate_video(qa_clips["good"])
    _rec("finalcheck.status", "good", "passed", r["status"])
    assert r["status"] == "passed"
    assert (r["width"], r["height"]) == (1080, 1920)
    assert _fc(r)["file_exists"] == "PASS" and _fc(r)["file_readable"] == "PASS"


@pytest.mark.parametrize("name,failing", [
    ("black_1_5s", "black_frames"), ("clipped_audio", "clipping"), ("no_audio", "audio_track"),
    ("fps_12", "frame_rate"), ("res_720x1280", "resolution"), ("res_1920x1080", "resolution")])
def test_finalcheck_bad_clips_fail(qa_clips, name, failing):
    r = finalcheck.validate_video(qa_clips[name])
    _rec("finalcheck.status", name, "failed", r["status"], f"via {failing}")
    assert r["status"] == "failed"
    assert _fc(r)[failing] == "FAIL"


def test_finalcheck_frozen_only_is_warn_and_still_passes(qa_clips):
    r = finalcheck.validate_video(qa_clips["frozen_4s"])
    _rec("finalcheck.status", "frozen_4s", "passed (WARN recorded)", r["status"])
    assert _fc(r)["frozen_frames"] == "WARN" and r["status"] == "passed"


def test_finalcheck_no_audio_is_warn_when_audio_not_required(qa_clips):
    r = finalcheck.validate_video(qa_clips["no_audio"], require_audio=False)
    _rec("finalcheck.status", "no_audio(require_audio=False)", "passed", r["status"])
    assert _fc(r)["audio_track"] == "WARN" and r["status"] == "passed"


def test_finalcheck_missing_empty_and_garbage_files_fail(tmp_path):
    r = finalcheck.validate_video(tmp_path / "nope.mp4")
    assert r["status"] == "failed" and _fc(r) == {"file_exists": "FAIL"}
    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    r = finalcheck.validate_video(empty)
    assert r["status"] == "failed" and _fc(r)["file_non_empty"] == "FAIL"
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"not a video" * 50)
    r = finalcheck.validate_video(junk)
    assert r["status"] == "failed" and _fc(r)["render_integrity"] == "FAIL"
    _rec("finalcheck.status", "missing/empty/garbage", "failed", "failed")


def test_finalcheck_unknown_format_fails_closed(qa_clips):
    r = finalcheck.validate_video(qa_clips["good"], fmt="4:3")
    _rec("finalcheck.status", "good(fmt=4:3)", "failed", r["status"])
    assert r["status"] == "failed" and _fc(r)["tooling"] == "FAIL"


def test_fixed_finalcheck_audio_only_file_fails_cleanly(tmp_path):
    """validate_video never raises for a bad video: a file with no video stream gives a failed result."""
    p = tmp_path / "audio_only.m4a"
    _ff(["-f", "lavfi", "-i", "sine=f=440:d=1", "-c:a", "aac", str(p)])
    r = finalcheck.validate_video(p)
    assert r["status"] == "failed" and _fc(r)["render_integrity"] == "FAIL"
    _rec("finalcheck.validate_video", "audio_only_no_video_stream", "failed result", r["status"], "fixed")


# ======================================================================================================================
# production/visual_gate.py  (standalone; not called by the pipeline)
# ======================================================================================================================

def _vg_clip(out, srcs, vf=None, *, fc=None, dur=4.0, fps=10):
    args = []
    for s in srcs:
        args += ["-f", "lavfi", "-i", s]
    if fc:
        args += ["-filter_complex", fc]
    elif vf:
        args += ["-vf", vf]
    _ff([*args, "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-r", str(fps), "-t", str(dur), str(out)])
    return out


CAN = (540, 960)
CAP_REGION = (60, 700, 420, 160)
CAP_WINDOWS = [(0.4, 0.6), (1.4, 1.6), (2.4, 2.6), (3.4, 3.6)]
BG = "color=c=0x303030:s=540x960:r=10:d=4"


def _ink(color="white", cond=""):
    """Six text-like boxes in the caption region (no drawtext in this ffmpeg build; boxes give the same kind of ink)."""
    return ",".join(f"drawbox=x={70 + i * 65}:y=730:w=40:h=60:color={color}:t=fill{cond}" for i in range(6))


@pytest.fixture(scope="module")
def cap_clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("caps")
    c = {}
    c["visible"] = _vg_clip(d / "visible.mp4", [BG], _ink())
    c["absent"] = _vg_clip(d / "absent.mp4", [BG], None)
    c["hidden_all_but_first"] = _vg_clip(d / "hidden_all_but_first.mp4", [BG],
                                         _ink() + ",drawbox=x=60:y=700:w=420:h=160:color=0x1040a0:t=fill:enable='gte(t,1)'")
    c["hidden_1s_only"] = _vg_clip(d / "hidden_1s_only.mp4", [BG],
                                   _ink() + ",drawbox=x=60:y=700:w=420:h=160:color=0x1040a0:t=fill:enable='between(t,1,2)'")
    c["wrong_place"] = _vg_clip(d / "wrong_place.mp4", [BG], ",".join(f"drawbox=x={70 + i * 65}:y=100:w=40:h=60:color=white:t=fill" for i in range(6)))
    c["low_contrast"] = _vg_clip(d / "low_contrast.mp4", [BG], _ink("0x383838"))
    c["busy_bg_no_captions"] = _vg_clip(d / "busy_bg_no_captions.mp4", ["testsrc2=s=540x960:r=10:d=4"], None)
    return c


def _caps(v):
    return vg.check_captions(v, CAP_WINDOWS, CAN, CAP_REGION)


def test_captions_visible_passes(cap_clips):
    r = _caps(cap_clips["visible"])
    _rec("visual_gate.captions", "visible", True, r["ok"])
    assert r["ok"] and r["visible_ratio"] == 1.0


@pytest.mark.parametrize("name", ["absent", "hidden_all_but_first", "wrong_place", "low_contrast"])
def test_captions_missing_or_hidden_fails(cap_clips, name):
    r = _caps(cap_clips[name])
    _rec("visual_gate.captions", name, False, r["ok"], f"visible_ratio={r['visible_ratio']}")
    assert not r["ok"]


def test_captions_hidden_for_one_of_four_windows_still_passes_by_design(cap_clips):
    # 3 of 4 windows visible = 0.75 >= 0.70: tolerated on purpose (narration gaps). A 1 s blackout of captions is accepted.
    r = _caps(cap_clips["hidden_1s_only"])
    _rec("visual_gate.captions", "hidden_1s_only", "True (tolerated, ratio 0.75)", r["ok"], f"visible_ratio={r['visible_ratio']}")
    assert r["visible_ratio"] == 0.75 and r["ok"]


def test_fixed_captions_absent_over_busy_background_fails(cap_clips):
    """A busy background with NO captions deviates from the median almost everywhere; ink above MAX_TEXT_FRACTION is texture,
    not caption text, so the gate fails. (The single-hidden-window tolerance, 3 of 4 windows, is intentional and unchanged.)"""
    r = _caps(cap_clips["busy_bg_no_captions"])
    _rec("visual_gate.captions", "busy_bg_no_captions", False, r["ok"], f"fixed visible_ratio={r['visible_ratio']}")
    assert r["ok"] is False


def test_captions_no_windows_fails_closed():
    r = vg.check_captions("unused.mp4", [], CAN, CAP_REGION)
    assert r["ok"] is False


# ---- transitions -------------------------------------------------------------------------------------------------------

def _col(c, d, size="270x480"):
    return f"color=c={c}:s={size}:r=10:d={d}"


@pytest.fixture(scope="module")
def tr_clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("trans")
    c = {}
    c["blend"] = _vg_clip(d / "blend.mp4", [_col("red", 1.5), _col("blue", 1.5)], fc="[0][1]xfade=transition=fade:duration=0.5:offset=1.0", dur=3)
    c["hard_cut"] = _vg_clip(d / "hard_cut.mp4", [_col("red", 1.5), _col("blue", 1.5)], fc="[0][1]concat=n=2:v=1:a=0", dur=3)
    c["black_gap"] = _vg_clip(d / "black_gap.mp4", [_col("red", 1.2), _col("black", 0.8), _col("blue", 1.2)], fc="[0][1][2]concat=n=3:v=1:a=0", dur=3.2)
    c["dip_to_black"] = _vg_clip(d / "dip.mp4", [_col("red", 1.5), _col("blue", 1.5)],
                                 fc="[0]fade=t=out:st=1.1:d=0.4[a];[1]fade=t=in:st=0:d=0.4[b];[a][b]concat=n=2:v=1:a=0", dur=3)
    c["same_picture"] = _vg_clip(d / "same.mp4", [_col("red", 1.5), _col("red", 1.5)], fc="[0][1]concat=n=2:v=1:a=0", dur=3)
    c["blend_with_black_flash"] = _vg_clip(
        d / "flash.mp4", [_col("red", 2), _col("blue", 2)],
        fc="[0][1]xfade=transition=fade:duration=1.0:offset=1.0,drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='between(t,1.39,1.41)'", dur=3)
    return c


def test_transition_real_blend_passes(tr_clips):
    r = vg.check_transition(tr_clips["blend"], 1.0, 0.5)
    _rec("visual_gate.transitions", "blend", "blend", r["verdict"])
    assert r["ok"] and r["verdict"] == "blend"


def test_transition_hard_cut_where_blend_expected_fails(tr_clips):
    r = vg.check_transition(tr_clips["hard_cut"], 1.25, 0.5)
    _rec("visual_gate.transitions", "hard_cut", "hard_cut", r["verdict"])
    assert not r["ok"] and r["verdict"] == "hard_cut"


def test_transition_black_frames_fail(tr_clips):
    r = vg.check_transition(tr_clips["black_gap"], 1.2, 0.8)
    _rec("visual_gate.transitions", "black_gap", "black", r["verdict"])
    assert not r["ok"] and r["verdict"] == "black"


def test_transition_dip_to_black_fails_unless_dip_allowed(tr_clips):
    r = vg.check_transition(tr_clips["dip_to_black"], 1.1, 0.8)
    r2 = vg.check_transition(tr_clips["dip_to_black"], 1.1, 0.8, allow_dip=True)
    _rec("visual_gate.transitions", "dip_to_black", "black", r["verdict"])
    _rec("visual_gate.transitions", "dip_to_black(allow_dip)", "blend", r2["verdict"])
    assert not r["ok"] and r["verdict"] == "black"
    assert r2["ok"] and r2["verdict"] == "blend"


def test_transition_black_gap_with_allow_dip_still_not_ok(tr_clips):
    # allow_dip must not turn a hard cut into a pass: a black gap that has no fade is still not a blend.
    r = vg.check_transition(tr_clips["black_gap"], 1.2, 0.8, allow_dip=True)
    _rec("visual_gate.transitions", "black_gap(allow_dip)", "not ok", "ok" if r["ok"] else f"not ok ({r['verdict']})")
    assert not r["ok"]


def test_transition_identical_neighbours_is_inconclusive_and_not_ok(tr_clips):
    r = vg.check_transition(tr_clips["same_picture"], 1.25, 0.5)
    _rec("visual_gate.transitions", "same_picture", "inconclusive", r["verdict"])
    assert r["verdict"] == "inconclusive" and not r["ok"]


def test_fixed_transition_single_black_frame_inside_a_blend_is_a_black_gap(tr_clips):
    """A single full-black frame (0.1 s at 10 fps) inside a 1 s blend lands on one sample; any black sample now makes the
    verdict black. (A flash that falls between samples is still not seen; documented in the result.)"""
    r = vg.check_transition(tr_clips["blend_with_black_flash"], 1.0, 1.0)
    blacks = sum(s["black"] for s in r["samples"])
    _rec("visual_gate.transitions", "blend_with_black_frame(1 frame)", "black", r["verdict"], "fixed")
    assert r["verdict"] == "black" and not r["ok"] and blacks == 1
    assert vg.check_transition(tr_clips["blend_with_black_flash"], 1.0, 1.0, allow_dip=True)["verdict"] == "blend"


def test_transition_cli_exit_codes(tr_clips, capsys):
    assert vg.main(["transitions", str(tr_clips["blend"]), "--at", "1.0:0.5"]) == 0
    assert vg.main(["transitions", str(tr_clips["hard_cut"]), "--at", "1.25:0.5"]) == 1
    assert vg.main(["transitions", str(tr_clips["blend"]).replace("blend.mp4", "nope.mp4"), "--at", "1.0:0.5"]) == 2


# ---- safe zone ----------------------------------------------------------------------------------------------------------

SZ_BG = "color=c=0x203060:s=540x960:r=10:d=4"
CENTRE = "drawbox=x=150:y=400:w=240:h=100:color=white:t=fill"


def _bars(x0, y0, step_x=0, step_y=0, n=6, w=40, h=50):
    return ",".join(f"drawbox=x={x0 + i * step_x}:y={y0 + i * step_y}:w={w}:h={h}:color=white:t=fill" for i in range(n))


@pytest.fixture(scope="module")
def sz_clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("safezone")
    c = {}
    c["clean"] = _vg_clip(d / "clean.mp4", [SZ_BG], CENTRE)
    c["bottom"] = _vg_clip(d / "bottom.mp4", [SZ_BG], CENTRE + "," + _bars(60, 830, 70))
    c["top"] = _vg_clip(d / "top.mp4", [SZ_BG], CENTRE + "," + _bars(60, 12, 70, h=40))
    c["right"] = _vg_clip(d / "right.mp4", [SZ_BG], CENTRE + "," + _bars(455, 520, 0, 40, n=6, w=60, h=30))
    c["late_content_bottom"] = _vg_clip(d / "late.mp4", [SZ_BG], CENTRE + "," + _bars(60, 830, 70).replace(":t=fill", ":t=fill:enable='gte(t,3)'"))
    c["low_contrast_bottom"] = _vg_clip(d / "lowc.mp4", [SZ_BG], CENTRE + "," + _bars(60, 830, 70).replace("color=white", "color=0x28386c"))
    c["landscape"] = _vg_clip(d / "land.mp4", ["color=c=0x203060:s=960x540:r=10:d=4"], "drawbox=x=40:y=480:w=800:h=40:color=white:t=fill")
    return c


TIMES = [1.0, 2.0]


@pytest.mark.parametrize("name,zone", [("bottom", "bottom"), ("top", "top"), ("right", "right")])
def test_safezone_content_in_zone_is_flagged(sz_clips, name, zone):
    r = vg.check_safe_zones(sz_clips[name], TIMES, CAN)
    flagged = {f["zone"] for f in r["flagged"]}
    _rec("visual_gate.safezone", f"content_in_{zone}", f"flagged {zone}", f"flagged {sorted(flagged)}" if flagged else "ok")
    assert not r["ok"] and flagged == {zone}


def test_safezone_clean_frame_passes(sz_clips):
    r = vg.check_safe_zones(sz_clips["clean"], TIMES, CAN)
    _rec("visual_gate.safezone", "clean", True, r["ok"])
    assert r["ok"] and not r["flagged"]


def test_safezone_only_sees_the_moments_it_samples(sz_clips):
    # content that appears at t=3 is caught when t=3.5 is sampled and missed when only 1.0 and 2.0 are
    assert vg.check_safe_zones(sz_clips["late_content_bottom"], TIMES, CAN)["ok"] is True
    r = vg.check_safe_zones(sz_clips["late_content_bottom"], [3.5], CAN)
    _rec("visual_gate.safezone", "late_content_bottom@3.5", False, r["ok"], "sampled-time dependent: @1,2 passes")
    assert r["ok"] is False


# INTENTIONALLY NOT FIXED: the edge threshold EDGE_JUMP is a documented provisional design value; catching faint content
# would need a threshold change, which is out of scope. Characterization test kept.
def test_gap_safezone_low_contrast_content_in_zone_is_not_flagged(sz_clips):
    """Content with a luma step under EDGE_JUMP (0.2) is not 'content' to this gate. A faint caption/logo in the zone passes."""
    r = vg.check_safe_zones(sz_clips["low_contrast_bottom"], TIMES, CAN)
    _rec("visual_gate.safezone", "low_contrast_in_bottom", False, r["ok"], "GAP: faint content under luma step 0.2 not seen")
    assert r["ok"] is True


def test_fixed_safezone_landscape_is_explicitly_not_applicable(sz_clips):
    """Nothing was checked on a landscape canvas: the result says so (status not_applicable, vacuous, checked False). `ok`
    stays True only because tests/test_safe_zone.py (outside this lane's allow-list) pins ok+applicable False."""
    r = vg.check_safe_zones(sz_clips["landscape"], TIMES, (960, 540))
    _rec("visual_gate.safezone", "landscape_with_content", "not applicable", f"ok={r['ok']} applicable={r['applicable']}", "fixed")
    assert r["applicable"] is False and r["status"] == "not_applicable" and r["vacuous"] is True and r["checked"] is False
    assert r["samples"] == [] and r["zones"] == []


def test_safezone_wrong_canvas_is_an_error_not_a_result(sz_clips):
    with pytest.raises(vg.GateError):
        vg.check_safe_zones(sz_clips["clean"], TIMES, (1080, 1920))
    assert vg.main(["safezone", str(sz_clips["clean"]), "--canvas", "1080x1920", "--times", "1"]) == 2
    assert vg.main(["safezone", str(sz_clips["bottom"]), "--canvas", "540x960", "--times", "1,2"]) == 1
    assert vg.main(["safezone", str(sz_clips["clean"]), "--canvas", "540x960", "--times", "1,2"]) == 0


# ---- layers (static CSS) and log ---------------------------------------------------------------------------------------

SCENE_INLINE_Z20 = '<div class="scene" id="s-a" style="z-index:20"></div><div id="captions"></div>'


def _layers(css, html=""):
    return vg.check_caption_layering(css, html)


def test_layers_captions_above_opaque_scenes_passes():
    css = ".scene{background:#101820;z-index:1} #captions{z-index:50}"
    r = _layers(css, '<div class="scene" id="s-a"></div><div id="captions"></div>')
    _rec("visual_gate.layers", "captions_above_scenes", True, r["ok"])
    assert r["ok"]


def test_layers_opaque_scene_above_captions_fails():
    css = ".scene{background:#101820} #captions{z-index:5}"
    r = _layers(css, SCENE_INLINE_Z20)
    _rec("visual_gate.layers", "opaque_scene_above_captions(inline z-index)", False, r["ok"])
    assert not r["ok"] and r["findings"][0]["code"] == "opaque_scene_above_captions"


def test_layers_declared_intent_is_not_an_error_but_requires_a_rendered_check():
    css = ".scene{background:#101820} #captions{z-index:5}"
    r = _layers(css, SCENE_INLINE_Z20.replace('id="captions"', 'id="captions" data-captions-intent="behind"'))
    assert r["ok"] and r["rendered_check_required"] and r["findings"][0]["severity"] == "declared"


@pytest.mark.parametrize("bg", ["black", "navy", "linear-gradient(black, navy)", "hsl(220, 40%, 10%)", "hsla(220, 40%, 10%, 1)",
                                "linear-gradient(to right, transparent, #000)", "#000f", "rgb(0 0 0 / 100%)"])
def test_fixed_layers_opaque_background_in_any_css_colour_syntax_is_caught(bg):
    """Named colours, hsl(), gradients (conservative: opaque if ANY stop is opaque) and 4/8-digit hex are recognised."""
    css = ".scene{background:%s} #captions{z-index:5}" % bg
    r = _layers(css, SCENE_INLINE_Z20)
    _rec("visual_gate.layers", f"opaque_scene_above_captions[background:{bg}]", False, r["ok"], "fixed")
    assert r["ok"] is False


@pytest.mark.parametrize("bg", ["transparent", "none", "rgba(0,0,0,0.5)", "hsla(220, 40%, 10%, 0.4)",
                                "linear-gradient(transparent, rgba(0,0,0,.3))", "rgb(0 0 0 / 50%)", "#0008"])
def test_layers_translucent_or_absent_background_is_not_opaque(bg):
    css = ".scene{background:%s} #captions{z-index:5}" % bg
    assert _layers(css, SCENE_INLINE_Z20)["ok"] is True


def test_fixed_layers_css_z_index_is_honoured_once_html_is_given():
    """CSS z-index counts when the html scene has no inline z-index; an inline z-index still wins over the CSS rule."""
    css = ".scene{background:#101820;z-index:20} #captions{z-index:5}"
    with_html = _layers(css, '<div class="scene" id="s-a"></div><div id="captions"></div>')
    css_only = _layers("#s-a{background:#101820;z-index:20} #captions{z-index:5}", "")
    _rec("visual_gate.layers", "opaque_scene_above_captions(css z-index, html given)", False, with_html["ok"], "fixed")
    assert with_html["ok"] is False and css_only["ok"] is False
    low_inline = _layers(css, '<div class="scene" id="s-a" style="z-index:1"></div><div id="captions"></div>')
    assert low_inline["ok"] is True


def test_layers_no_caption_rule_is_info_only():
    r = _layers(".scene{background:#000}", '<div class="scene" id="s-a"></div>')
    assert r["ok"] and r["findings"][0]["code"] == "no_caption_layer_found"


def _page(rules, z):
    return (f"<style>{rules}</style>"
            f'<div class="scene" id="s-a" style="z-index:{z}"></div><div id="captions"></div>')


def test_layers_cli_on_project_dir(tmp_path):
    # a leading `body{}` rule is a workaround for the gap below
    bad = _page("body{margin:0} .scene{background:#000} #captions{z-index:1}", 9)
    good = _page("body{margin:0} .scene{background:#000} #captions{z-index:9}", 1)
    (tmp_path / "index.html").write_text(bad)
    assert vg.main(["layers", str(tmp_path)]) == 1
    (tmp_path / "index.html").write_text(good)
    assert vg.main(["layers", str(tmp_path)]) == 0
    assert vg.main(["layers", str(tmp_path / "missing")]) == 2


def test_fixed_layers_cli_keeps_the_first_css_rule_of_a_style_block(tmp_path):
    """The first rule of a <style> block (here #captions) is parsed; a real violation exits 1."""
    (tmp_path / "index.html").write_text(_page("#captions{z-index:1} .scene{background:#000}", 9))
    rc = vg.main(["layers", str(tmp_path)])
    _rec("visual_gate.layers", "cli: #captions first rule in <style>, opaque scene above", 1, rc, "fixed")
    assert rc == 1


BAD_LOG = '{"hasShaderTransitions": true}\nWARN falling back to opacity-flip\nStreaming encoder exited unexpectedly\n'
GOOD_LOG = '{"hasShaderTransitions": true}\nrender complete\n'


def test_log_gate_fails_on_shader_fallback_and_encoder_exit_and_passes_clean_log(tmp_path):
    bad = vg.scan_render_log(BAD_LOG)
    good = vg.scan_render_log(GOOD_LOG)
    codes = {f["code"] for f in bad}
    _rec("visual_gate.log", "shader_fallback+encoder_exit", {"shader_fallback_opacity_flip", "encoder_exited"}, codes)
    _rec("visual_gate.log", "clean_log", [], good)
    assert codes == {"shader_fallback_opacity_flip", "encoder_exited"} and good == []
    p = tmp_path / "render.log"
    p.write_text(BAD_LOG)
    assert vg.main(["log", str(p)]) == 1
    p.write_text(GOOD_LOG)
    assert vg.main(["log", str(p)]) == 0


def test_fixed_log_shader_fallback_detected_without_the_shader_marker():
    """A fallback line is itself proof shaders were requested: reported without hasShaderTransitions:true. Generic
    shader-compile noise is still gated on the marker."""
    f = vg.scan_render_log("WARN falling back to opacity-flip\n")
    _rec("visual_gate.log", "fallback_without_marker", "error finding", f and f[0]["code"], "fixed")
    assert [x["code"] for x in f] == ["shader_fallback_opacity_flip"] and f[0]["severity"] == "error"
    assert vg.scan_render_log("failed to compile\n") == []
    assert vg.scan_render_log("WARN falling back to opacity-flip\n", uses_shaders=False) == []      # explicit caller override wins
    assert vg.main(["log", "/dev/null"]) == 0
