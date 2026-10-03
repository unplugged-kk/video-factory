#!/usr/bin/env bash
# Idempotent. Installs only what contentos needs on Apple Silicon.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v brew >/dev/null || { echo "install Homebrew first"; exit 1; }
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
brew list yt-dlp >/dev/null 2>&1 || brew install yt-dlp
brew list whisper-cpp >/dev/null 2>&1 || brew install whisper-cpp
command -v node >/dev/null || brew install node
npm ci --no-audit --no-fund   # hyperframes, pinned by package.json + lockfile
[ -x ~/.contentos/venv/bin/python ] || uv venv ~/.contentos/venv --python 3.12
uv pip install --python ~/.contentos/venv/bin/python pyyaml pytest kokoro-onnx soundfile
mkdir -p ~/.contentos/secrets ~/.claude/youtube
chmod 700 ~/.contentos/secrets
[ -d vendor/youtube-agent-skill ] || git clone --depth 1 https://github.com/Jakeschincariol/youtube-agent-skill vendor/youtube-agent-skill
cp -rn vendor/youtube-agent-skill/skills/yt-* ~/.claude/skills/
cp -n vendor/youtube-agent-skill/templates/voice.md ~/.claude/youtube/voice.md || true
chmod +x contentos.sh
./contentos.sh doctor
