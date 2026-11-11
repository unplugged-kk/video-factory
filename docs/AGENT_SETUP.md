# Agent setup

Read this before the first video on a new machine. Then run one script. Do not ask a person to install ffmpeg, Node, Python, Whisper, or the voice models. The script does that. Stop and report only if the script exits non-zero.

## Which script

| Machine | Command | What becomes ready |
|---|---|---|
| Apple Silicon Mac | `./scripts/bootstrap-mac.sh` | English, Hindi, Hinglish. Odia stays blocked. |
| Ubuntu | `./scripts/bootstrap-linux.sh` | English only. Hindi and Hinglish are not installed. |

Both scripts are idempotent. Run them again after a partial failure. They do not publish, do not spend money, and do not create `~/.voice-clone-venv`.

The Ubuntu script was not executed on an Ubuntu machine in this repo. It is the command list the factory needs. If a package name or the Whisper build path fails, stop and report the command output. Do not switch the voice stack to a paid API to get past it.

## What the Mac script installs

- Homebrew packages if missing: ffmpeg, yt-dlp, whisper-cpp, node.
- The pinned HyperFrames install from `package.json` (`npm ci`).
- `~/.contentos/venv` with PyYAML, pytest, kokoro-onnx, and soundfile.
- `~/.contentos/venv-mlx-audio` with `mlx-audio==0.6.4`. This is the Hindi and Hinglish voice runtime. It is not the production venv.
- Whisper models into `~/.cache/hyperframes/whisper/models/` when missing. English uses `ggml-small.en.bin`. Hindi and Hinglish use `ggml-large-v3-turbo-q5_0.bin`.
- Chatterbox weights into `~/.cache/contentos/huggingface` (about 3 GB, first run only).
- A synthetic Hindi reference clip at `~/.contentos/voices/hi_reference.wav` if that file is absent. It is a Kokoro clip, not a real person's voice.
- Workspace `~/Desktop/VideoFactory-Workspace` and publishing library `~/Desktop/Video-Publishing`.

Then it runs `python -m contentos.lang setup` and `./contentos.sh doctor --require tts,stt,render`. `--require` makes the script fail only when voice, captions, or rendering have no healthy provider. The llm, YouTube read, publish, and decision providers are optional, so their `NOT_INSTALLED` rows no longer fail setup.

## What the Ubuntu script installs

- apt packages when missing and passwordless sudo is available: ffmpeg, git, curl, a C compiler, and cmake.
- Node 20 or newer, from NodeSource, if the current Node is older.
- `uv`, a production venv, Kokoro, HyperFrames, and a local `whisper-cli` built from ggml-org/whisper.cpp when it is not already on `PATH`.
- The English Whisper model and the same workspace folders.
- HyperFrames' headless Chrome through `hyperframes browser ensure`. If Ubuntu lacks a shared library Chrome needs, the script prints each missing library from `ldd` and stops. Install the apt packages that provide them and rerun. Package names differ by Ubuntu release, so the script does not guess them.

It does not install MLX, Chatterbox, or an Odia model. `python -m contentos.lang setup` treats that as success when English is ready.

## After setup

```bash
export PATH="/opt/homebrew/bin:$HOME/.local/bin:$PATH"
export HYPERFRAMES_PYTHON="$HOME/.contentos/venv/bin/python"
./contentos.sh doctor
"$HYPERFRAMES_PYTHON" -m contentos.lang doctor --require en,hi,hi-en   # Ubuntu: --require en
"$HYPERFRAMES_PYTHON" -m contentos.lang matrix
./contentos.sh storage paths --check
```

On a Mac, English, Hindi, and Hinglish must print READY. Odia must print NOT READY with `backend_blocked`. That is the expected end state, not a failed setup. On Ubuntu, only English must print READY.

Job folders are `jobs/YYYY/MM/DD/<content_id>/` under the workspace. Do not look in `jobs/YYYY/MM/<content_id>/`. That older path made finished cloud jobs look missing.

## What setup will not do

- Publish a video.
- Mark Hindi or Hinglish production-ready. A fluent listener has not approved the audio.
- Install Odia. Both voice candidates are gated on Hugging Face and need PyTorch. See `docs/MULTILINGUAL.md`.
- Produce a Hindi video from an English subject. The script itself must be in Devanagari.

Next, read `docs/CAPABILITIES.md` for what the factory can do and the commands that use it. The production rules stay in `AGENTS.md` and `docs/AGENT_BRIEF.md`.
