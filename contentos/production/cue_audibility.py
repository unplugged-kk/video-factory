"""cue-audibility/1: measure cue stem audibility and voice masking (report-only).

Honest limits:
- Needs two separate WAV stems (voice-only and cues-only). On videos mixed to
  a single mix.wav, this tool has nothing to measure until stems are rendered.
- RMS in dBFS over the cue window is a loudness proxy, not perceived loudness
  (no LUFS, no auditory masking model). Thresholds are provisional and uncalibrated.
- Supports uncompressed 16-bit PCM WAV (mono or stereo) only, via standard wave module.

  python -m contentos.production.cue_audibility --voice V.wav --cues C.wav --timeline TL.json [--strict]
"""
from __future__ import annotations

import argparse
import array
import json
import math
import sys
import wave
from pathlib import Path

SCHEMA = "cue-audibility/1"
MIN_CUE_DB = -45.0
MAX_OVER_VOICE_DB = -3.0
VOICE_ACTIVE_DB = -40.0
FLOOR_DB = -90.0


def read_wav(path: Path | str) -> tuple[int, list[float]]:
    """Read a 16-bit PCM WAV file and return (sample_rate, normalized_samples)."""
    p = Path(path)
    if not p.is_file():
        raise OSError(f"audio file not found: {p}")
    with wave.open(str(p), "rb") as wf:
        if wf.getsampwidth() != 2:
            raise ValueError(f"{p}: only 16-bit PCM WAV is supported (sampwidth={wf.getsampwidth()})")
        channels = wf.getnchannels()
        if channels not in (1, 2):
            raise ValueError(f"{p}: only mono or stereo WAV supported (channels={channels})")
        rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    arr = array.array("h")
    arr.frombytes(raw)
    if sys.byteorder != "little":
        arr.byteswap()

    if channels == 1:
        samples = [s / 32768.0 for s in arr]
    else:
        samples = [(arr[i] + arr[i + 1]) / (2.0 * 32768.0) for i in range(0, len(arr), 2)]
    return rate, samples


def rms_db(samples: list[float], rate: int, t0: float, t1: float, floor_db: float = FLOOR_DB) -> float:
    """Calculate RMS dBFS of samples in window [t0, t1]. Returns floor_db if empty or silent."""
    i0 = max(0, int(round(t0 * rate)))
    i1 = min(len(samples), int(round(t1 * rate)))
    if i1 <= i0:
        return floor_db
    window = samples[i0:i1]
    mean_sq = sum(x * x for x in window) / len(window)
    if mean_sq <= 0.0:
        return floor_db
    return max(20.0 * math.log10(math.sqrt(mean_sq)), floor_db)


def measure(voice_wav: Path | str, cues_wav: Path | str, audio_cues: list[dict], *,
            min_cue_db: float = MIN_CUE_DB, max_over_voice_db: float = MAX_OVER_VOICE_DB,
            voice_active_db: float = VOICE_ACTIVE_DB, floor_db: float = FLOOR_DB) -> dict:
    """Measure audibility and speech masking for all sfx cues."""
    v_rate, v_samples = read_wav(voice_wav)
    c_rate, c_samples = read_wav(cues_wav)
    if v_rate != c_rate:
        raise ValueError(f"sample rate mismatch: voice {v_rate} Hz vs cues {c_rate} Hz")

    rate = v_rate
    max_dur = min(len(v_samples), len(c_samples)) / rate
    measured = []

    for cue in audio_cues:
        if cue.get("kind") != "sfx":
            continue
        cid = cue.get("id", "")
        t = cue.get("t", 0.0)
        dur = cue.get("dur_s", 0.0)
        flags = []

        if t + dur > max_dur:
            flags.append("window_clamped")
        w_end = min(t + dur, max_dur)

        c_db = rms_db(c_samples, rate, t, w_end, floor_db)
        v_db = rms_db(v_samples, rate, t, w_end, floor_db)
        active = v_db >= voice_active_db
        over = round(c_db - v_db, 1) if active else None

        if c_db < min_cue_db:
            flags.append("inaudible")
        if active and (c_db - v_db) > max_over_voice_db:
            flags.append("masks_speech")

        measured.append({
            "id": cid,
            "t": t,
            "dur_s": dur,
            "cue_db": round(c_db, 1),
            "voice_db": round(v_db, 1),
            "voice_active": active,
            "over_voice_db": over,
            "flags": flags,
        })

    summary = {
        "cues": len(measured),
        "inaudible": sum(1 for c in measured if "inaudible" in c["flags"]),
        "masks_speech": sum(1 for c in measured if "masks_speech" in c["flags"]),
    }
    return {
        "schema": SCHEMA,
        "params": {
            "min_cue_db": min_cue_db,
            "max_over_voice_db": max_over_voice_db,
            "voice_active_db": voice_active_db,
            "floor_db": floor_db,
        },
        "cues": measured,
        "summary": summary,
        "provisional": True,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", required=True, help="Voice WAV stem path")
    ap.add_argument("--cues", required=True, help="Cues WAV stem path")
    ap.add_argument("--timeline", required=True, help="Timeline JSON file containing audio_cues")
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any cue has flags")

    try:
        a = ap.parse_args(argv)
        tl_data = json.loads(Path(a.timeline).read_text(encoding="utf-8"))
        cues = tl_data.get("audio_cues", [])
        res = measure(a.voice, a.cues, cues)
        print(json.dumps(res, indent=1))
        if a.strict and any(c["flags"] for c in res["cues"]):
            return 1
        return 0
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
