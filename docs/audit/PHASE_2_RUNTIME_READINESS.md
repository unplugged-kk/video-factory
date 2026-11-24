# Phase 2 runtime readiness - initial Mac audit

2026-11-24, branch `feat/phase2-foundation`, baseline `849ea6a`. This is runtime discovery and executable startup evidence, not a production certification. Raw commands/results: `/tmp/video-factory-phase2-baseline.Nl2Zuoid/runtime.log` and `runtime-executables.log` in the same directory.

| Capability | Observed | Not established |
|---|---|---|
| Host | `arm64`, 24 GiB RAM (`hw.memsize`), ~560 GiB available at measurement | Safe parallel-render memory budget |
| Python | Python 3.12.16; an isolated venv installed the CI Python dependencies `pytest`, `PyYAML`, `numpy` from public PyPI | Reproducible without public package registries or local runtime assets |
| Node | `/Users/kishore/.local/bin/node` v24.22.1, npm 11.19.1; offline `npm ci` lacked cached Prettier; public registry install with scripts disabled succeeded, Node tests 66/66 | Exact hosted CI environment (Node 22, standard `npm ci`) |
| FFmpeg / ffprobe | Resolved to `~/.local/bin/{ffmpeg,ffprobe}`, v8.1.2 | Render fidelity from binary/version checks alone |
| HyperFrames | Isolated worktree `node_modules/.bin/hyperframes --version` returned the expected `0.8.114`; factory doctor probe passed | New creative benchmark or a confined production render |
| Kokoro | Factory doctor import probe passed; offline English narration smoke generated a 2.667 s WAV in 2.99 s | Human listening, sustained narration and production quality |
| Chatterbox MLX | Standalone route imports `mlx-audio` 0.6.4 from `~/.contentos/venv-mlx-audio/bin/python`. Offline Hindi smoke generated a 4.04 s WAV in 6.5 s without fallback (reported MLX peak 4.73 GB). General doctor checks a different, missing venv. | Hinglish synthesis, comparative benchmark and fluent listener sign-off |
| ASR | `/opt/homebrew/bin/whisper-cli`, whisper.cpp 1.9.5 (Homebrew `1.9.5_2`); English small and multilingual turbo-Q5 model files present (487,614,201 and 574,041,195 bytes); large-v3 also present | Model checksum revalidation in this checkpoint |
| Fonts | System `Kohinoor.ttc` present | New Devanagari render and inspected frames |
| Docker / MPT | `/opt/homebrew/bin/docker` client 29.10.0 and daemon 29.6.1 responded; factory MPT HTTP probe refused connection | Stock providers and actual MPT container render. No stack installed or started. |
| Remotion | Shared CLI symlink exists. `remotion versions` from the factory root reported no Remotion packages in that project and a zod mismatch. | Correct project-local package compatibility or a lane render |
| Ollama | Not found on PATH | Running local model |
| yt-dlp | `/usr/local/bin/yt-dlp` present but factory probe got `Bad CPU type` | Working binary on this host |
| YouTube OAuth / ContentForge gateway | Doctor reported not configured; no credential files inspected and no gateway calls made | OAuth, access, publication, or gateway workflow. Publishing is disabled. |
| Workspace | `./contentos.sh storage paths --check` passed against two isolated scratch roots | User library operation was not re-tested or modified |

Both narration smoke commands exited 0 and produced 24 kHz mono PCM WAVs in the isolated workspace. Single-sentence timings are not a benchmark. Evidence: `/tmp/video-factory-phase2-baseline.Nl2Zuoid/tts-smoke.log`.

`./contentos.sh doctor` and `python -m contentos.lang doctor` exited 1. The latter printed `READY` for `en`, `hi`, and `hi-en`, and expected `NOT READY` for Odia. They probe different Chatterbox environments. The language doctor's path/cache checks alone are not a model-load or synthesis probe (G-06 remains open). `python -m contentos.scenekit.lookmap report` exited 0, 17 compiled and 13 blocked. Compiled does not mean routed to the builder or render-verified.
