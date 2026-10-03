#!/usr/bin/env bash
# usage: ./contentos.sh doctor | route tts | pipeline run examples/youtube-short.yaml --approve-private | status
cd "$(dirname "$0")" || exit 1
export HYPERFRAMES_PYTHON="${HYPERFRAMES_PYTHON:-$HOME/.contentos/venv/bin/python}"
export PATH="/opt/homebrew/bin:$PATH"   # arm64 ffmpeg/yt-dlp before dead x86 /usr/local/bin
exec "$HYPERFRAMES_PYTHON" -m contentos "$@"
