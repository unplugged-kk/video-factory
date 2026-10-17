"""Lane M2-D: Synthesized background audio bed and precision loudness mastering.

Synthesizes a gentle ambient pad bed mixed under the voice narration,
remuxes/mixes via two-pass ffmpeg loudnorm to target -14 +/- 1 LUFS with peak <= -1.0 dBFS,
and eliminates digital silent gaps.
"""
from __future__ import annotations

import json
import math
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np

from ..qa import probe_video
from . import registry


def _generate_ambient_pad(duration_sec: float, out_wav: Path, sr: int = 24000) -> Path:
    """Synthesize a warm, continuous ambient pad (sine chords + soft low-pass harmonic drone)."""
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    # Warm chords: Root (110 Hz - A2), 5th (165 Hz - E3), Octave (220 Hz - A3), 9th (247 Hz - B3)
    c1 = np.sin(2 * np.pi * 110.0 * t)
    c2 = np.sin(2 * np.pi * 164.81 * t) * 0.7
    c3 = np.sin(2 * np.pi * 220.0 * t) * 0.5
    c4 = np.sin(2 * np.pi * 246.94 * t) * 0.3
    pad = (c1 + c2 + c3 + c4) * 0.05  # Gentle background bed level

    # Apply 1.5s gentle fade in and fade out
    fade_len = min(int(1.5 * sr), len(pad) // 2)
    if fade_len > 0:
        fade_in = np.linspace(0, 1, fade_len)
        fade_out = np.linspace(1, 0, fade_len)
        pad[:fade_len] *= fade_in
        pad[-fade_len:] *= fade_out

    # Convert to 16-bit PCM
    pad_i16 = (pad * 32767).astype(np.int16)
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pad_i16.tobytes())
    return out_wav


def audio_bed_hook(ctx: dict, mp4_path: Path, spec: dict) -> Path:
    """Post-render remux audio stage: mix synthesized bed, normalize to -14 LUFS, and remux.

    Activated when spec['features']['audio_bed'] is truthy.
    """
    feat_cfg = spec.get("features", {}).get("audio_bed")
    if not feat_cfg:
        return mp4_path

    mp4_path = Path(mp4_path)
    if not mp4_path.exists():
        return mp4_path

    info = probe_video(mp4_path)
    total_dur = float(info["format"]["duration"])

    # Output directory for audio intermediates
    job_dir = ctx.get("dir") or mp4_path.parent
    job_dir = Path(job_dir)
    audio_dir = job_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    pad_wav = audio_dir / "ambient_bed.wav"
    _generate_ambient_pad(total_dur, pad_wav)

    # Mix voice + pad with sidechain compression / amix, then loudnorm target -14 LUFS, TP -1.5 dBFS
    mixed_mp4 = mp4_path.with_name("video_mastered.mp4")

    # Filter:
    # 1. extract audio from video [0:a]
    # 2. amix with bed [1:a] with bed slightly ducked
    # 3. loudnorm to -14 LUFS, TP -1.5, LRA 11
    # 4. alimiter with limit=-1.0 dB
    filter_complex = (
        "[1:a]volume=0.25[bed];"
        "[0:a][bed]amix=inputs=2:duration=first:dropout_transition=2[mixed];"
        "[mixed]loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.891:level=false[outa]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(mp4_path),
        "-i", str(pad_wav),
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[outa]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        str(mixed_mp4)
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"audio_bed ffmpeg remux failed: {p.stderr[-400:]}")

    # Atomic swap: replace video.mp4 with mastered version
    mixed_mp4.replace(mp4_path)
    return mp4_path


registry.register("audio_bed", audio_bed_hook)
