#!/usr/bin/env bash
# Mac visual-reliability experiment: three 9:16 arms (cut control / css push / shader sdf-iris) built from one
# code-editorial scene set. Run from the repo root on the Mac:   bash workspace/spike-design-library/mac-experiment/run.sh
#
# Every run writes a NEW folder (never overwrites earlier evidence). Per arm it records the exact command, render exit code,
# render seconds and output path, then runs the visual gate on that arm's own output. A failing arm is reported as failed;
# the exit status is 0 only if all three arms rendered and were gated. Findings (hard cut, black) are results, not errors.
# Compatible with macOS bash 3.2. Installs nothing. Not a cloud tool: results from a non-Mac machine must not be called Mac results.
set -u
REPO="$(pwd)"
PKG="$REPO/workspace/spike-design-library/mac-experiment"
export PATH="/opt/homebrew/bin:$PATH"                       # arm64 ffmpeg first, as contentos.sh does
HF="${HF:-$REPO/node_modules/.bin/hyperframes}"              # the repo's pinned hyperframes
PY="${PYTHON:-${HYPERFRAMES_PYTHON:-$HOME/.contentos/venv/bin/python}}"
[ -x "$PY" ] || PY="$(command -v python3)"
for need in "$HF" "$PY"; do [ -x "$need" ] || { echo "missing $need; not installing anything"; exit 2; }; done
for tool in ffmpeg ffprobe; do command -v $tool >/dev/null || { echo "missing $tool"; exit 2; }; done
[ -f "$REPO/contentos/production/visual_gate.py" ] || { echo "run from the repo root (contentos/production/visual_gate.py not found)"; exit 2; }
"$PY" "$PKG/build.py" >/dev/null || { echo "build.py failed"; exit 2; }
mkdir -p "$PKG/results"
OUT="$(mktemp -d "$PKG/results/run-$(date +%Y%m%d-%H%M%S)-XXXXXX")" || exit 2   # unique even for two runs in one second
{
  echo "date_utc: $(date -u +%FT%TZ)"; echo "uname: $(uname -a)"; echo "sw_vers: $(sw_vers 2>/dev/null | tr '\n' ' ')"
  echo "chip: $(sysctl -n machdep.cpu.brand_string 2>/dev/null)"; echo "ram_bytes: $(sysctl -n hw.memsize 2>/dev/null)"
  echo "hyperframes_binary: $HF"; echo "hyperframes: $("$HF" --version 2>&1 | head -1)"
  echo "node: $(node -v 2>&1)"; echo "python: $PY $("$PY" -V 2>&1)"; echo "ffmpeg: $(ffmpeg -version 2>&1 | head -1)"
  echo "repo_head: $(git -C "$REPO" rev-parse HEAD 2>&1)"; echo "repo_dirty_files: $(git -C "$REPO" status --short 2>/dev/null | wc -l | tr -d ' ')"
  echo "env HF_PAGE_SIDE_COMPOSITING=${HF_PAGE_SIDE_COMPOSITING-unset} HYPERFRAMES_BROWSER_PATH=${HYPERFRAMES_BROWSER_PATH-unset} HF_DE_PARALLEL_ROUTER=${HF_DE_PARALLEL_ROUTER-unset}"
  echo "pkg_sha256: $(cat "$PKG"/cut/index.html "$PKG"/css/index.html "$PKG"/shader/index.html | shasum -a 256 | cut -c1-16)"
} > "$OUT/environment.txt"
CAPWIN="$("$PY" -c "print(','.join('%s:%.3f' % (t, t + 0.001) for t in range(1, 12)))")"
window_for() { case "$1" in shader) echo "5.7:0.6:shader";; *) echo "5.55:0.45:css";; esac; }
for arm in cut css shader; do
  D="$PKG/$arm"; V="$OUT/$arm.mp4"; L="$OUT/$arm.render.log"; S="$OUT/$arm.summary.txt"; W="$(window_for $arm)"
  echo "== $arm"
  ( cd "$D" && "$HF" check ) > "$OUT/$arm.check.log" 2>&1; echo $? > "$OUT/$arm.check.rc"
  echo "check command: (cd $D && $HF check)  exit $(cat "$OUT/$arm.check.rc")" | tee -a "$S"
  start=$(date +%s)
  ( cd "$D" && "$HF" render --quality draft --output "$V" ) > "$L" 2>&1; echo $? > "$OUT/$arm.render.rc"
  echo $(( $(date +%s) - start )) > "$OUT/$arm.seconds.rc"
  echo "render command: (cd $D && $HF render --quality draft --output $V)" | tee -a "$S"
  echo "render exit $(cat "$OUT/$arm.render.rc"), seconds $(cat "$OUT/$arm.seconds.rc"), output $V" | tee -a "$S"
  if [ ! -s "$V" ]; then echo "NO OUTPUT for $arm: gate not run for it" | tee -a "$S"; continue; fi
  "$PY" -m contentos.production.visual_gate log "$L" > "$OUT/$arm.gate-log.json" 2>"$OUT/$arm.gate-log.err"
  "$PY" -m contentos.production.visual_gate transitions "$V" --at "$W" > "$OUT/$arm.gate-transition.json" 2>"$OUT/$arm.gate-transition.err"
  echo "gate transition window $W exit $?" | tee -a "$S"
  "$PY" -m contentos.production.visual_gate captions "$V" --project "$D" --canvas 1080x1920 --windows "$CAPWIN" > "$OUT/$arm.gate-captions.json" 2>"$OUT/$arm.gate-captions.err"
  TWIN="$("$PY" -c "import sys; s,d,_=sys.argv[1].split(':'); s=float(s); n=int(round(float(d)/0.05)); print(','.join('%.3f:%.4f' % (s+0.05*i, s+0.05*i+0.001) for i in range(n+1)))" "$W")"
  "$PY" -m contentos.production.visual_gate captions "$V" --project "$D" --canvas 1080x1920 --windows "$TWIN" > "$OUT/$arm.gate-captions-window.json" 2>"$OUT/$arm.gate-captions-window.err"
  "$PY" -m contentos.production.visual_gate layers "$D" > "$OUT/$arm.gate-layers.json" 2>"$OUT/$arm.gate-layers.err"
  for t in 2 5.7 5.85 6.0 6.15 9; do ffmpeg -v error -y -ss $t -i "$V" -frames:v 1 -vf scale=360:640 "$OUT/${arm}_$t.png"; done
done
echo; echo "results folder: $OUT"; echo
"$PY" "$PKG/summarize.py" "$OUT"; status=$?
echo
echo "Return to Claude: $OUT/{environment.txt,SUMMARY.txt,SUMMARY.json,*.summary.txt,*.render.log,*.check.log,*.gate-*.json}"
echo "and the PNG frames (small). Do not edit them. The .mp4 files are not needed."
exit $status
