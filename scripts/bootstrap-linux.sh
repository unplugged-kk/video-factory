#!/usr/bin/env bash
# Idempotent Ubuntu setup for the English factory. Hindi and Hinglish are not installed here.
# Their voice runtime is MLX and runs only on Apple Silicon. See docs/AGENT_SETUP.md.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

apt_install() {
  if sudo -n true 2>/dev/null; then
    sudo -n apt-get update
    sudo -n apt-get install -y "$@"
    return
  fi
  echo "missing commands and sudo is not available without a password: $*"
  echo "install those packages, then rerun ./scripts/bootstrap-linux.sh"
  exit 1
}

missing=()
command -v ffmpeg >/dev/null || missing+=(ffmpeg)
command -v git >/dev/null || missing+=(git)
command -v curl >/dev/null || missing+=(curl)
command -v make >/dev/null || missing+=(build-essential cmake)
if [ "${#missing[@]}" -gt 0 ]; then
  apt_install "${missing[@]}"
fi

node_major=0
if command -v node >/dev/null; then
  node_major="$(node -p 'process.versions.node.split(".")[0]')"
fi
if [ "$node_major" -lt 20 ]; then
  if ! sudo -n true 2>/dev/null; then
    echo "Node 20 or newer is required. This machine has major version $node_major and sudo is not available."
    exit 1
  fi
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -n bash -
  sudo -n apt-get install -y nodejs
fi

if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v whisper-cli >/dev/null; then
  src="$HOME/.contentos/src/whisper.cpp"
  if [ ! -d "$src/.git" ]; then
    git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git "$src"
  fi
  cmake -S "$src" -B "$src/build" -DCMAKE_BUILD_TYPE=Release
  cmake --build "$src/build" -j"$(nproc)" --target whisper-cli
  mkdir -p "$HOME/.local/bin"
  ln -sfn "$src/build/bin/whisper-cli" "$HOME/.local/bin/whisper-cli"
fi

npm ci --no-audit --no-fund
[ -x "$HOME/.contentos/venv/bin/python" ] || uv venv "$HOME/.contentos/venv" --python 3.12
uv pip install --python "$HOME/.contentos/venv/bin/python" pyyaml pytest kokoro-onnx soundfile
# HyperFrames downloads its own headless Chrome. Fail loudly, with the exact libraries, if the OS lacks any of them.
npx --no-install hyperframes browser ensure
chrome="$(npx --no-install hyperframes browser path | tail -n 1)"
if command -v ldd >/dev/null && ldd "$chrome" 2>/dev/null | grep -q "not found"; then
  echo "headless Chrome is missing shared libraries:"
  ldd "$chrome" | grep "not found"
  echo "install the apt packages that provide them (apt-file search <lib>), then rerun ./scripts/bootstrap-linux.sh"
  exit 1
fi
mkdir -p "$HOME/.contentos/secrets"
chmod 700 "$HOME/.contentos/secrets"
chmod +x contentos.sh
export HYPERFRAMES_PYTHON="$HOME/.contentos/venv/bin/python"
"$HYPERFRAMES_PYTHON" -m contentos.lang setup
./contentos.sh doctor --require tts,stt,render
echo "Ubuntu setup finished for English. Hindi and Hinglish were not installed. They need an Apple Silicon Mac."
