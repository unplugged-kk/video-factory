# Verification Evidence

Append-only register. scripts/run-check.sh appends command evidence here;
add manual entries (inspection, runtime probes, screenshots) in the same shape.
Never paste secrets, tokens or personal data. Full logs live under
checkpoints/evidence/ (local).

Levels: REPORTED < INSPECTED < IMPLEMENTED < TESTED < INTEGRATION-VERIFIED
< RUNTIME-VERIFIED < PRODUCTION-VERIFIED. Record the highest level actually reached.

<!-- Entry format:

### EV-YYYYMMDD-HHMMSS
- **Claim:**
- **Evidence type:** command execution | file inspection | runtime probe | CI run | manual
- **Command:** / **Method:**
- **Result:**
- **Timestamp:**
- **Repository state:** branch, commit, tree clean|dirty
- **Agent:**
- **Level achieved:**
- **Full log:**
- **Limitations:**
-->

### EV-20261121-213541
- **Claim:** P1-1 lookmap compiles 17/30 looks and fails the rest closed
- **Evidence type:** command execution
- **Command:** `/Users/kishore/.contentos/venv/bin/python -m pytest tests/test_lookmap.py -q` (cwd: project root)
- **Result:** PASS (exit 0) in 0s
- **Timestamp:** 2026-11-21 21:35:41 IST
- **Repository state:** branch `feat/p1-1-lookmap`, commit `849ea6a`, tree DIRTY (uncommitted changes included in what was tested)
- **Agent:** pi/root
- **Level achieved:** TESTED
- **Full log:** `docs/project-intelligence/checkpoints/evidence/EV-20261121-213541.log` (local, not committed)
- **Limitations:** proves only what this command exercises; see command scope.
- **Matched lines (`passed|failed|error`):**
```
11 passed in 0.04s
```
- **Output tail:**
```
...........                                                              [100%]
11 passed in 0.04s
```

### EV-20261121-213544
- **Claim:** full pytest suite passes at 849ea6a
- **Evidence type:** command execution
- **Command:** `/Users/kishore/.contentos/venv/bin/python -m pytest tests -q` (cwd: project root)
- **Result:** FAILED (exit 1) in 176s
- **Timestamp:** 2026-11-21 21:38:40 IST
- **Repository state:** branch `feat/p1-1-lookmap`, commit `849ea6a`, tree DIRTY (uncommitted changes included in what was tested)
- **Agent:** pi/root
- **Level achieved:** none - check failed
- **Full log:** `docs/project-intelligence/checkpoints/evidence/EV-20261121-213544.log` (local, not committed)
- **Limitations:** proves only what this command exercises; see command scope.
- **Matched lines (`passed|failed|error`):**
```
E           contentos.lang.errors.LangError: [asr_binary_missing] whisper-cli not found (brew install whisper-cpp)
1 failed, 1217 passed, 8 skipped in 176.09s (0:02:56)
```
- **Output tail:**
```
    cmd = [_bin(), "-m", str(model), "-f", str(wav), "-l", language, "-ml", "1", "-sow", "-oj", "-of", str(base), "-np"]
           ^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def _bin():
        from shutil import which
        p = which("whisper-cli", path=f"{BREW}:{os.environ.get('PATH', '')}")
        if not p:
>           raise LangError("whisper-cli not found (brew install whisper-cpp)", code="asr_binary_missing")
E           contentos.lang.errors.LangError: [asr_binary_missing] whisper-cli not found (brew install whisper-cpp)

contentos/lang/asr.py:28: LangError
=========================== short test summary info ============================
FAILED tests/test_lang.py::test_real_hindi_audio_transcribes_with_valid_timestamps_and_mostly_right_text
1 failed, 1217 passed, 8 skipped in 176.09s (0:02:56)
```

### EV-20261121-213848
- **Claim:** the real-Hindi ASR test passes once whisper-cli is on PATH
- **Evidence type:** command execution
- **Command:** `/Users/kishore/.contentos/venv/bin/python -m pytest tests/test_lang.py -q` (cwd: project root)
- **Result:** PASS (exit 0) in 4s
- **Timestamp:** 2026-11-21 21:38:52 IST
- **Repository state:** branch `feat/p1-1-lookmap`, commit `849ea6a`, tree DIRTY (uncommitted changes included in what was tested)
- **Agent:** pi/root
- **Level achieved:** TESTED
- **Full log:** `docs/project-intelligence/checkpoints/evidence/EV-20261121-213848.log` (local, not committed)
- **Limitations:** proves only what this command exercises; see command scope.
- **Matched lines (`passed|failed|error`):**
```
63 passed in 3.46s
```
- **Output tail:**
```
...............................................................          [100%]
63 passed in 3.46s
```

### EV-20261121-214149
- **Claim:** full pytest suite passes (1218 passed, 8 skipped) at 849ea6a
- **Evidence type:** command execution
- **Command:** `/Users/kishore/.contentos/venv/bin/python -m pytest tests -q` (cwd: project root)
- **Result:** PASS (exit 0) in 159s
- **Timestamp:** 2026-11-21 21:44:28 IST
- **Repository state:** branch `feat/p1-1-lookmap`, commit `849ea6a`, tree DIRTY (uncommitted changes included in what was tested)
- **Agent:** pi/root
- **Level achieved:** TESTED
- **Full log:** `docs/project-intelligence/checkpoints/evidence/EV-20261121-214149.log` (local, not committed)
- **Limitations:** proves only what this command exercises; see command scope.
- **Matched lines (`passed|failed|error`):**
```
1218 passed, 8 skipped in 159.30s (0:02:39)
```
- **Output tail:**
```
..............ssssss.................................................... [ 29%]
........................................................................ [ 35%]
........................................................................ [ 41%]
........................................................................ [ 46%]
........................................................................ [ 52%]
........................................................................ [ 58%]
........................................................................ [ 64%]
........................................................................ [ 70%]
........................................................................ [ 76%]
........................................................................ [ 82%]
........................................................................ [ 88%]
......s..........................s...................................... [ 93%]
........................................................................ [ 99%]
..                                                                       [100%]
1218 passed, 8 skipped in 159.30s (0:02:39)
```

### EV-20261124-135640
- **Claim:** Post-commit verification: incomplete dependency trees and language routing
- **Evidence type:** command execution
- **Command:** `/tmp/video-factory-phase2-baseline.Nl2Zuoid/ci-venv/bin/python -m pytest tests/test_export_security.py tests/test_lang.py -q -rs` (cwd: project root)
- **Result:** PASS (exit 0) in 15s
- **Timestamp:** 2026-11-24 13:56:56 IST
- **Repository state:** branch `feat/phase2-foundation`, commit `cce972d`, tree DIRTY (uncommitted changes included in what was tested)
- **Agent:** pi/root
- **Level achieved:** TESTED
- **Full log:** `docs/project-intelligence/checkpoints/evidence/EV-20261124-135640.log` (local, not committed)
- **Limitations:** proves only what this command exercises; see command scope.
- **Matched lines (`passed|failed|skipped`):**
```
116 passed in 15.11s
```
- **Output tail:**
```
........................................................................ [ 62%]
............................................                             [100%]
116 passed in 15.11s
```

### 2026-11-24 Phase 2 launch evidence

Unless otherwise noted: working directory `~/git/video-factory-phase2-foundation`, Apple Silicon, Python 3.12.16 and Homebrew-first PATH. Start/end below are IST. Raw logs are backed up at `~/.contentos/checkpoints/video-factory-phase2-20261124/`. The full suites ran before the two product/test commits; their source changes match the subsequently committed diff. Local test assets were available; this is not remote CI.

| Evidence | Start/end | Git and tree | Command | Exit/result | Log |
|---|---|---|---|---|---|
| VF2-ASR-RED | before 13:46:08 | `849ea6a` + inventory only | Set `asr.BREW` to a nonexistent directory and `PATH=/usr/bin:/bin` in a child process; run the one real Hindi pytest test via `pytest.main` | 1; 1 failed (`asr_binary_missing`) | current Pi session command output; historical full failure also at EV-20261121-213544 |
| VF2-ASR-GREEN | 13:46:08-13:46:09 | `849ea6a` + ASR skip | same missing-binary test | 0; 1 skipped for missing `whisper-cli` | `asr-missing-binary-green.log` |
| VF2-PY-FIRST | 13:45:59-13:49:51 | `849ea6a` + ASR skip | `~/.contentos/venv/bin/python -m pytest tests -q -rs` | 1; 1 failed, 1203 passed, 22 skipped; English routing test assumed `transcribe` at argv index 1 | `python-suite.log` |
| VF2-WALK-RED | 13:47:45-13:47:49 | `849ea6a` + ASR fix and new regressions, pre-fix | `~/.contentos/venv/bin/python -m pytest tests/test_export_security.py -q -k incomplete_project` | 1; 2 failed, 51 deselected; both offered an incomplete digest | `incomplete-project-red.log` |
| VF2-SECURITY | 13:48:30-13:48:56 | `849ea6a` + dependency walk and ASR changes | `~/.contentos/venv/bin/python -m pytest tests/test_export_security.py tests/test_ui_api.py tests/test_track_b.py tests/test_mpt.py -q -rs` | 0; 96 passed, 1 skipped | `security-focused.log` |
| VF2-NODE-OFFLINE | 13:44:40-13:44:49 | `849ea6a`, Node 24.22.1 | `npm ci --offline --ignore-scripts --no-audit --no-fund`; `node --test contentos/adapters/v1/*.test.mjs` | npm 1 (Prettier not cached); Node 0, 66 passed | Pi bg monitor `vf-phase2-preflight-node` |
| VF2-NODE | 13:48:52-13:49:04 | `849ea6a` + Python changes, Node 24.22.1 | `npm ci --ignore-scripts --no-audit --no-fund --fetch-retries=0`; `node --test contentos/adapters/v1/*.test.mjs` | both 0; 66 passed, 0 failed/skipped | `node-bootstrap.log` |
| VF2-HF-FALLBACK | 13:51:48-13:51:49 | `849ea6a` + fixes | Set child process `hf.ROOT` to a nonexistent checkout, clear `HYPERFRAMES_BIN`; run the English routing pytest case via `pytest.main` | 0; 1 passed | `hyperframes-fallback-green.log` |
| VF2-PY-FRESH | 13:51:41-13:54:57 (setup + suite) | `849ea6a` + final Python diff | `python3.12 -m venv` plus CI pip deps; isolated `python -m pytest tests -q -rs` | 0; 1,211 passed, 17 skipped | `fresh-python-suite.log` |
| VF2-RUNTIME | 13:50:43-13:50:46 | `849ea6a` + Python WIP | `./contentos.sh doctor`, `python -m contentos.lang doctor`, `./contentos.sh storage paths --check`, `python -m contentos.scenekit.lookmap report` | 1, 1, 0, 0 respectively; 17 compiled, 13 blocked | `runtime.log` and `runtime-executables.log` |
| VF2-TTS | 13:54:52-13:55:08 | `849ea6a` + final Python diff | `python -m contentos.lang speak --lang en/hi --text <synthetic sentence> --out <scratch WAV>` with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, once per language | both 0; distinct Kokoro and Chatterbox outputs, no fallback or listening verdict | `tts-smoke.log` |
| VF2-RENDERS | 13:56:02-13:59:07 | `cce972d`, only docs dirty, production venv | `CONTENTOS_E2E=1 ~/.contentos/venv/bin/python -m pytest tests/test_e2e_features.py -q -rs -k 'hf-' --basetemp ~/.contentos/checkpoints/video-factory-phase2-20261124/fixture-renders` | 0; 3 passed, 3 deselected; 3 real test MP4s, dry-run publish only | `fixture-renders.log` |
| VF2-FRAMES | 13:59:17-13:59:22 | `cce972d`, only docs dirty | `ffprobe` durations, parsed `qa.json`, `./contentos.sh preview VIDEO --at 1,5,9,13,17,21 --out REVIEW --sheet`, viewed each sheet | 0; technical counts 12 PASS, 12 PASS, 11 PASS + 1 WARN; preliminary visual revise (not independent) | `fixture-review.log`; see `docs/audit/CREATIVE_QUALITY_RESULTS.md` |

### ITER-2026-11-24-002 evidence

See `docs/audit/PF23_LOCAL_STAGING.md` for the exact test command ledger, red/focused/full/Node results, and real HyperFrames regression. Raw evidence: `/Users/kishore/.contentos/checkpoints/video-factory-pf23.89gf1FNw/`. The fixture passed 12 technical checks; contact sheet at 2, 10 and 20 seconds again shows primarily text cards with a dim middle sample. No quality acceptance. `docs/audit/IMMUTABLE_RENDER_SNAPSHOT.md` records the separate Docker fixture-worker probe. It is not render verification.
