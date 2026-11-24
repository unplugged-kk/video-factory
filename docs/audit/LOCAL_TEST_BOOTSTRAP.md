# Fresh worktree tests on macOS

The hosted workflow (`.github/workflows/ci.yml`) uses Python 3.12, Node 22, FFmpeg, `npm ci`, and an isolated pair of storage roots. It asserts a clean tree after tests to catch unignored artifacts, not because pytest requires a clean tree. Start from a disposable worktree so pre-existing edits do not obscure that check. Do not use `git clean` or remove user media.

In the worktree, with Python 3.12, Node 22 and a working Apple Silicon FFmpeg on PATH:

```sh
set -eu
export PATH="/opt/homebrew/bin:$PATH"
scratch=$(mktemp -d "${TMPDIR:-/tmp}/vf-ci.XXXXXXXX")
export VIDEO_FACTORY_WORKSPACE="$scratch/workspace"
export VIDEO_FACTORY_PUBLISH_DIR="$scratch/publish"
mkdir -p "$VIDEO_FACTORY_WORKSPACE" "$VIDEO_FACTORY_PUBLISH_DIR"
python3.12 -m venv "$scratch/venv"
"$scratch/venv/bin/python" -m pip install pytest pyyaml numpy
npm ci
"$scratch/venv/bin/python" -m pytest tests -q -rs
node --test contentos/adapters/v1/*.test.mjs
test -z "$(git status --porcelain)" || { git status --short; exit 1; }
```

The 2026-11-24 local validation used Node 24.22.1 and `npm ci --ignore-scripts --no-audit --no-fund --fetch-retries=0`, after offline install failed with `ENOTCACHED` for Prettier. The Node suite passed 66/66 both before and after dependency installation. An isolated Python 3.12.16 venv with only the CI Python dependencies passed 1,211, skipped 17. Optional local assets (including installed ASR models and the existing Hindi fixture) were visible on this Mac, so this was not a blank system or a hosted CI run.

Optional skips include unsynced protected skills, gitignored experiment fixtures and opt-in real renders. The real Hindi ASR test also requires the model, audio sample, and `whisper-cli`; it must skip only a missing prerequisite, not a failed transcription. To exercise the binary-absent case without manipulating Homebrew, use a child Python process with `contentos.lang.asr.BREW` pointed at a nonexistent directory and `PATH=/usr/bin:/bin`, then invoke the one real Hindi pytest case. Full-suite results, including the first failed run before the routing test fix, are indexed in `docs/project-intelligence/VERIFICATION_EVIDENCE.md`.
