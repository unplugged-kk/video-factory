import array
import json
import math
import os
import sys
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import module under test (will fail before module is implemented)
from contentos.production import cue_audibility  # noqa: E402


def make_tone_wav(path, seconds=2.0, freq=440.0, amp=0.5, rate=16000, sampwidth=2):
    p = Path(path)
    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        n_samples = int(seconds * rate)
        if sampwidth == 2:
            data = array.array("h")
            for i in range(n_samples):
                val = int(amp * 32767.0 * math.sin(2.0 * math.pi * freq * (i / rate)))
                data.append(max(-32768, min(32767, val)))
            wf.writeframes(data.tobytes())
        elif sampwidth == 1:
            raw = bytes([int(128 + 127 * amp * math.sin(2.0 * math.pi * freq * (i / rate))) for i in range(n_samples)])
            wf.writeframes(raw)
    return str(p)


def make_silence_wav(path, seconds=2.0, rate=16000):
    return make_tone_wav(path, seconds=seconds, freq=0.0, amp=0.0, rate=rate)


def test_audible_cue_over_quiet_voice_is_not_flagged_inaudible(tmp_path):
    # Cue at amp 0.1 (-23 dBFS), voice at amp 0.02 (-37 dBFS)
    # Cue is audible (not < -45 dBFS)
    cues_wav = make_tone_wav(tmp_path / "cues.wav", amp=0.1)
    voice_wav = make_tone_wav(tmp_path / "voice.wav", amp=0.02)
    cues = [{"id": "c1", "kind": "sfx", "t": 0.5, "dur_s": 0.5}]

    res = cue_audibility.measure(voice_wav, cues_wav, cues)
    c0 = res["cues"][0]
    assert "inaudible" not in c0["flags"]


def test_silent_cue_stem_is_flagged_inaudible(tmp_path):
    # Silent cue stem -> cue_db will hit floor (-90 dBFS < -45 dBFS)
    cues_wav = make_silence_wav(tmp_path / "cues.wav")
    voice_wav = make_tone_wav(tmp_path / "voice.wav", amp=0.1)
    cues = [{"id": "c1", "kind": "sfx", "t": 0.5, "dur_s": 0.5}]

    res = cue_audibility.measure(voice_wav, cues_wav, cues)
    c0 = res["cues"][0]
    assert "inaudible" in c0["flags"]
    assert res["summary"]["inaudible"] == 1


def test_loud_cue_over_speech_is_flagged_masks_speech(tmp_path):
    # Voice amp 0.1 (~ -23 dBFS), Cue amp 0.2 (~ -17 dBFS)
    # over_voice_db = -17 - (-23) = +6 dB > -3 dB
    cues_wav = make_tone_wav(tmp_path / "cues.wav", amp=0.2)
    voice_wav = make_tone_wav(tmp_path / "voice.wav", amp=0.1)
    cues = [{"id": "c1", "kind": "sfx", "t": 0.5, "dur_s": 0.5}]

    res = cue_audibility.measure(voice_wav, cues_wav, cues)
    c0 = res["cues"][0]
    assert "masks_speech" in c0["flags"]
    assert res["summary"]["masks_speech"] == 1


def test_quiet_cue_under_speech_is_clean(tmp_path):
    # Voice amp 0.1 (~ -23 dBFS), Cue amp 0.02 (~ -37 dBFS)
    # over_voice_db = -37 - (-23) = -14 dB <= -3 dB; cue_db > -45 dBFS
    cues_wav = make_tone_wav(tmp_path / "cues.wav", amp=0.02)
    voice_wav = make_tone_wav(tmp_path / "voice.wav", amp=0.1)
    cues = [{"id": "c1", "kind": "sfx", "t": 0.5, "dur_s": 0.5}]

    res = cue_audibility.measure(voice_wav, cues_wav, cues)
    c0 = res["cues"][0]
    assert c0["flags"] == []
    assert res["summary"]["masks_speech"] == 0
    assert res["summary"]["inaudible"] == 0


def test_cue_over_silent_voice_has_no_over_voice_value_and_cannot_mask(tmp_path):
    cues_wav = make_tone_wav(tmp_path / "cues.wav", amp=0.2)
    voice_wav = make_silence_wav(tmp_path / "voice.wav")
    cues = [{"id": "c1", "kind": "sfx", "t": 0.5, "dur_s": 0.5}]

    res = cue_audibility.measure(voice_wav, cues_wav, cues)
    c0 = res["cues"][0]
    assert c0["voice_active"] is False
    assert c0["over_voice_db"] is None
    assert "masks_speech" not in c0["flags"]


def test_duck_and_music_cues_are_ignored(tmp_path):
    cues_wav = make_tone_wav(tmp_path / "cues.wav", amp=0.5)
    voice_wav = make_tone_wav(tmp_path / "voice.wav", amp=0.1)
    cues = [
        {"id": "d1", "kind": "duck", "t": 0.5, "dur_s": 0.5},
        {"id": "m1", "kind": "music", "t": 0.5, "dur_s": 0.5},
    ]

    res = cue_audibility.measure(voice_wav, cues_wav, cues)
    assert len(res["cues"]) == 0
    assert res["summary"]["cues"] == 0


def test_window_beyond_file_is_clamped_and_flagged(tmp_path):
    # 2-second file, cue extends to 3.0s
    cues_wav = make_tone_wav(tmp_path / "cues.wav", seconds=2.0, amp=0.02)
    voice_wav = make_tone_wav(tmp_path / "voice.wav", seconds=2.0, amp=0.1)
    cues = [{"id": "c1", "kind": "sfx", "t": 1.5, "dur_s": 1.5}]

    res = cue_audibility.measure(voice_wav, cues_wav, cues)
    c0 = res["cues"][0]
    assert "window_clamped" in c0["flags"]


def test_sample_rate_mismatch_raises(tmp_path):
    cues_wav = make_tone_wav(tmp_path / "cues.wav", rate=16000)
    voice_wav = make_tone_wav(tmp_path / "voice.wav", rate=24000)
    cues = [{"id": "c1", "kind": "sfx", "t": 0.5, "dur_s": 0.5}]

    with pytest.raises(ValueError, match="rate mismatch"):
        cue_audibility.measure(voice_wav, cues_wav, cues)


def test_non_16bit_raises(tmp_path):
    cues_wav = make_tone_wav(tmp_path / "cues.wav", sampwidth=1)
    voice_wav = make_tone_wav(tmp_path / "voice.wav", sampwidth=2)
    cues = [{"id": "c1", "kind": "sfx", "t": 0.5, "dur_s": 0.5}]

    with pytest.raises(ValueError, match="16-bit"):
        cue_audibility.measure(voice_wav, cues_wav, cues)


def test_values_match_hand_computed_dbfs_within_0_2_db(tmp_path):
    # Sine wave amp=0.5 -> expected RMS dBFS is 20*log10(0.5 / sqrt(2)) = -9.03 dBFS
    wav = make_tone_wav(tmp_path / "test.wav", amp=0.5, seconds=1.0)
    rate, samples = cue_audibility.read_wav(wav)
    calc_db = cue_audibility.rms_db(samples, rate, 0.0, 1.0, -90.0)
    expected_db = 20.0 * math.log10(0.5 / math.sqrt(2))
    assert abs(calc_db - expected_db) <= 0.2


def test_cli_report_only_exit_zero_and_strict_exit_one(tmp_path):
    cues_wav = make_tone_wav(tmp_path / "cues.wav", amp=0.5)
    voice_wav = make_tone_wav(tmp_path / "voice.wav", amp=0.05)  # masks speech
    tl_file = tmp_path / "timeline.json"
    tl_file.write_text(json.dumps({
        "audio_cues": [{"id": "c1", "kind": "sfx", "t": 0.5, "dur_s": 0.5}]
    }), encoding="utf-8")

    # Report-only exits 0 even when flags present
    rc_rep = cue_audibility.main(["--voice", voice_wav, "--cues", cues_wav, "--timeline", str(tl_file)])
    assert rc_rep == 0

    # Strict exits 1 when flags present
    rc_strict = cue_audibility.main(["--voice", voice_wav, "--cues", cues_wav, "--timeline", str(tl_file), "--strict"])
    assert rc_strict == 1


def test_no_repo_files_written(tmp_path):
    cues_wav = make_tone_wav(tmp_path / "cues.wav", amp=0.02)
    voice_wav = make_tone_wav(tmp_path / "voice.wav", amp=0.1)
    tl_file = tmp_path / "timeline.json"
    tl_file.write_text(json.dumps({
        "audio_cues": [{"id": "c1", "kind": "sfx", "t": 0.5, "dur_s": 0.5}]
    }), encoding="utf-8")

    before = os.listdir(tmp_path)
    cue_audibility.main(["--voice", voice_wav, "--cues", cues_wav, "--timeline", str(tl_file)])
    after = os.listdir(tmp_path)
    assert sorted(before) == sorted(after)
