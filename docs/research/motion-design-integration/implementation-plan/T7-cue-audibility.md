# T7 — Cue-audibility measurement (report-only; off by default)

**Goal:** given a narration stem, a cue stem, and the `audio_cues` list from T5, measure whether each sound cue is (a) audible at all and (b) not drowning the voice. Numbers only; it is **not** wired into export or any gate, and it makes no claim about how things *sound*.
**Prereq:** T0 CLEARED, T5 DONE, T6 DONE (so you can reuse the seeded-fault idea on this check).
**You create:** `contentos/production/cue_audibility.py`, `tests/test_cue_audibility.py`. **You modify:** nothing.

## 1. Honest limits (put these in the module docstring)
- Needs **two separate WAV stems** (voice-only, cues-only). The current pipeline mixes into one `mix.wav`; stems do not exist yet, so on today's videos this tool has nothing to measure. It becomes useful when a future task renders stems (T8 produces such stems for the experiment).
- RMS in dBFS over the cue window is a *loudness proxy*, not perceived loudness (no LUFS, no masking model). Thresholds below are **provisional and uncalibrated**; calibrate them with T8's listening results before trusting them.
- Supports uncompressed 16-bit PCM WAV (mono or stereo) only, via the standard `wave` module. Anything else → clear error.

## 2. Read first
`contentos/export.py` (read-only) to see how `mix.wav`/ducking is produced today; `T5` fields (`audio_cues[].t`, `dur_s`). Do not edit `export.py`.

## 3. Snapshot
`before-T7.txt`.

## 4. Behaviour

```
measure(voice_wav, cues_wav, audio_cues, *, min_cue_db=-45.0, max_over_voice_db=-3.0, voice_active_db=-40.0, floor_db=-90.0) -> dict
```
For each `audio_cue` with `kind == "sfx"` (ignore `duck`, `music`):
- `cue_db` = RMS dBFS of the cues stem over `[t, t+dur_s]` (clamped to file length; `floor_db` if silent or empty).
- `voice_db` = RMS dBFS of the voice stem over the same window.
- `voice_active` = `voice_db >= voice_active_db`.
- `over_voice_db` = `cue_db - voice_db` if `voice_active` else `None`.
- flags: `"inaudible"` if `cue_db < min_cue_db`; `"masks_speech"` if `voice_active and over_voice_db > max_over_voice_db` (the cue is louder than 3 dB below the voice).
Return:
```json
{"schema": "cue-audibility/1", "params": {…}, "cues": [{"id": "a01", "t": 4.31, "dur_s": 0.4, "cue_db": -22.1, "voice_db": -19.8, "voice_active": true, "over_voice_db": -2.3, "flags": ["masks_speech"]}], "summary": {"cues": 3, "inaudible": 0, "masks_speech": 1}, "provisional": true}
```
Edge rules: `rate` of the two WAVs must match (else `ValueError`); a window beyond the file → clamp and add flag `"window_clamped"`; zero cues → empty list, summary zeros.

CLI: `python -m contentos.production.cue_audibility --voice V.wav --cues C.wav --timeline timeline.json [--strict]` → prints JSON; exit 0 normally; with `--strict` exit 1 if any flag; exit 2 on unreadable/unsupported input.

## 5. Implementation guide (stdlib only; ~120 lines)
- `read_wav(path) -> (rate, [float samples -1..1])` using `wave` + `array('h')` (little-endian; use `sys.byteorder` swap if needed); average channels for stereo; reject `sampwidth != 2`.
- `rms_db(samples, rate, t0, t1, floor_db)`: slice by `int(t*rate)`, `sqrt(mean(x²))`, `20*log10(rms)` (floor if rms==0).
- Keep functions pure; no globals; round outputs to 1 decimal.

## 6. Tests first — synthetic audio only (`tmp_path`; generate WAVs with `wave` + `math.sin`)
Helper `tone(path, seconds, freq, amp, rate=16000)` and `silence(...)`.
1. `test_audible_cue_over_quiet_voice_is_not_flagged_inaudible` (cue amp 0.2, voice amp 0.05? then masks — design the amplitudes so each test has one intended outcome; compute expected dB by hand: `20*log10(amp/sqrt(2))` for a sine).
2. `test_silent_cue_stem_is_flagged_inaudible` (negative control).
3. `test_loud_cue_over_speech_is_flagged_masks_speech` (negative control).
4. `test_quiet_cue_under_speech_is_clean` (positive control).
5. `test_cue_over_silent_voice_has_no_over_voice_value_and_cannot_mask`.
6. `test_duck_and_music_cues_are_ignored`.
7. `test_window_beyond_file_is_clamped_and_flagged`.
8. `test_sample_rate_mismatch_raises`; `test_non_16bit_raises`.
9. `test_values_match_hand_computed_dbfs_within_0_2_db`.
10. `test_cli_report_only_exit_zero_and_strict_exit_one`.
11. `test_no_repo_files_written` (cwd listing of repo `contentos/` unchanged — or simply assert the tool writes nothing: run with `tmp_path` and compare `os.listdir`).

## 7. Verify
```bash
~/.contentos/venv/bin/python -m pytest tests/test_cue_audibility.py -q
~/.contentos/venv/bin/python -m pytest tests -q
bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/after-T7.txt && diff $HOME/audit-scratch/before-T7.txt $HOME/audit-scratch/after-T7.txt
```
Smoke: generate three tiny WAVs in `$HOME/audit-scratch/t7/` and run the CLI once; paste the JSON.

## 8. Acceptance / Rollback / Do not
Tests pass; two new repo files only; docstring states the limits in §1; summary `provisional: true`. Rollback: `rm` the two files. Do not hook into `export.py`/`pipeline.py`; do not add numpy/ffmpeg dependencies; do not describe results as "sounds good/bad".
