# Local runtime report — actual machine state

Measured 2026-11-18 on the working copy, branch `feat/p1-1-lookmap`, HEAD `86eeaa2`.
Every line is a command I ran, not a claim from the docs.

## Host

| Fact | Value | How |
|---|---|---|
| Arch / OS | arm64, macOS 27.2.1 (build 26B131) | `uname -m`, `sw_vers` |
| Memory | 24 GB | `sysctl -n hw.memsize` |
| Free disk | 572 GB of 926 GB | `df -h /` |
| Repo size | 2.1 GB (includes `vendor/`) | `du -sh .` |
| Python | 3.12.16 at `~/.contentos/venv/bin/python` | venv interpreter |
| Node / npm | v24.22.1 / 11.19.1 | `node --version` |
| Homebrew prefix | `/opt/homebrew` exists (`brew` present) | `ls /opt/homebrew/bin` |

## Toolchain

| Tool | State | Evidence |
|---|---|---|
| HyperFrames | PASS, pinned 0.8.114 | `doctor`; `package.json` |
| ffmpeg | PASS, **arm64**, ffmpeg 8.1.2 at `~/.local/bin/ffmpeg` | `file` |
| ffmpeg at `/usr/local/bin` | **x86_64, dead** — never resolved | `file`, `doctor` |
| ffmpeg at `/opt/homebrew/bin` | **does not exist** | `ls` |
| `timeout` | **broken**: `/usr/local/bin/timeout` is x86_64 and is what PATH resolves first | `file`, `which -a` |
| drawtext / freetype | **works** on the 8.1.2 build | `ffmpeg -filters`, produced a PNG |
| yt-dlp | **broken**: x86_64 Cellar python, `Bad CPU type` | `doctor`, `file` |
| whisper.cpp | installed during this audit (1.9.5_2, arm64) | `brew list --versions` |
| Python venv for TTS | `kokoro_onnx` importable (PASS) | `doctor` |

### Two corrections to `AGENTS.md`

1. `contentos.sh:5` prepends `/opt/homebrew/bin` with the comment *"arm64 ffmpeg/yt-dlp before dead x86
   /usr/local/bin"*. **That directory holds no ffmpeg and no yt-dlp on this machine**, so the prepend
   changes nothing. What actually serves ffmpeg is `~/.local/bin/ffmpeg` (arm64, real drawtext). The
   comment describes an intent that is not true here.
2. `AGENTS.md` §10 says the homebrew ffmpeg build has no freetype, so labelled contact sheets fail closed.
   There is no homebrew ffmpeg; the 8.1.2 build in use **has** `drawtext`. That limitation should be
   re-measured before `sheet.py` stays gated behind it.

`timeout` is the one genuinely broken utility. `doctor` worked only because I dropped `timeout` from the
command.

## Models present

| Model | Size | Path |
|---|---|---|
| `ggml-small.en.bin` | 466 MB | `~/.cache/hyperframes/whisper/models/` |
| `ggml-large-v3-turbo-q5_0.bin` | 548 MB | same |
| `ggml-large-v3.bin` | 2.9 GB | same |
| `ggml-vaani-odia.bin` | **absent** | same (Odia ASR not ready, as documented) |

## Provider readiness (`./contentos.sh doctor`)

| Capability | Selected | State |
|---|---|---|
| tts | `kokoro_local` | PASS |
| tts | `chatterbox_mlx` | **NOT_INSTALLED** — `~/.voice-clone-venv` does not exist |
| tts | `elevenlabs` | OPTIONAL — env `ELEVENLABS_API_KEY` only; **no adapter is implemented** (see gap G-17) |
| stt | `hyperframes_transcribe` | PASS (only after whisper.cpp landed mid-audit) |
| render | `hyperframes` | PASS |
| render | `mpt` | NOT_INSTALLED — docker compose not up |
| llm | all | NOT_INSTALLED / OPTIONAL |
| youtube_read | `ytdlp` | broken; `youtube_data_api` needs a key |

## The contradiction worth acting on

`python -m contentos.lang doctor` reports:

```
en     READY  tts=kokoro        asr=whisper_small_en
hi     READY  tts=chatterbox_v3 asr=whisper_turbo_q5
hi-en  READY  tts=chatterbox_v3 asr=whisper_turbo_q5
```

`hi` and `hi-en` are reported **READY while `chatterbox_mlx` is NOT_INSTALLED**. The language doctor is
reading its route table, not the backend it depends on. A Hindi job therefore looks ready and fails later
at the voice stage. This is the single most misleading status line in the system, and it is the reason
Hindi must stay labelled experimental until the language doctor probes the backend.

## Test baseline (measured, not quoted)

| Suite | Result |
|---|---|
| `pytest tests` before my changes | **1166 passed, 1 failed, 8 skipped** |
| that 1 failure | `test_lang.py::test_real_hindi_audio_transcribes_*` — `whisper-cli not found` |
| same suite after whisper.cpp installed by a subagent | 1168 passed, 8 skipped |
| `pytest tests` after my export fix + fixtures | **1169 passed, 8 skipped, 0 failed** |
| `node --test contentos/adapters/v1/*.test.mjs` | **66 pass, 0 fail** |

The handover's "1,084 Python tests" was a stale figure; the real count today is 1,169.

## What a subagent changed on this machine (disclosed)

While the open-source research agent was running, `brew` installed `whisper.cpp`, `llama.cpp`, `sdl3` and
`sdl2-compat` at 19:47. That is what turned STT from `NOT_INSTALLED` to `PASS` and made the one failing
test pass. It was not part of the brief I gave that agent and it is a real, unrequested machine change.
It is benign (arm64, local, no paid service) but it must not be mistaken for something the repo did.
