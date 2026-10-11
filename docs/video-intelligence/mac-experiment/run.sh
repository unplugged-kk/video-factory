#!/usr/bin/env bash
# Mac visual-reliability experiment: three 9:16 arms (cut control / css push / shader sdf-iris), same code-editorial scenes.
# Run from the repo root:   bash workspace/spike-design-library/mac-experiment/run.sh
# Records, per arm: command, backend flags, output path, render seconds, exit status, full render log, and gate JSON.
# Nothing here changes production defaults. Do NOT run this in the cloud and call it a Mac result.
set -u
REPO="$(pwd)"
PKG="$REPO/workspace/spike-design-library/mac-experiment"
HF="$REPO/node_modules/.bin/hyperframes"
OUT="$PKG/results/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
python3 "$PKG/build.py" >/dev/null || { echo "build.py failed"; exit 2; }
[ -x "$HF" ] || { echo "missing $HF (pinned hyperframes); not installing anything"; exit 2; }
{
  echo "date: $(date -u +%FT%TZ)"; echo "uname: $(uname -a)"; echo "sw_vers: $(sw_vers 2>/dev/null | tr '\n' ' ')"
  echo "chip: $(sysctl -n machdep.cpu.brand_string 2>/dev/null)"; echo "ram_bytes: $(sysctl -n hw.memsize 2>/dev/null)"
  echo "hyperframes: $("$HF" --version 2>&1 | head -1)"; echo "ffmpeg: $(ffmpeg -version 2>&1 | head -1)"
  echo "env HF_PAGE_SIDE_COMPOSITING=${HF_PAGE_SIDE_COMPOSITING-unset} HYPERFRAMES_BROWSER_PATH=${HYPERFRAMES_BROWSER_PATH-unset}"
} > "$OUT/environment.txt"
PY="${PYTHON:-python3}"
declare -A WIN=( [cut]="5.55:0.45:css" [css]="5.55:0.45:css" [shader]="5.7:0.6:shader" )
CAPWIN=$(python3 -c "print(','.join(f'{t}:{t+0.001:.3f}' for t in range(1,12)))")
for arm in cut css shader; do
  D="$PKG/$arm"; V="$OUT/$arm.mp4"; L="$OUT/$arm.render.log"
  echo "== $arm"
  ( cd "$D" && "$HF" check ) > "$OUT/$arm.check.log" 2>&1; echo "check exit $?" | tee -a "$OUT/$arm.summary.txt"
  s=$(date +%s)
  ( cd "$D" && "$HF" render --quality draft --output "$V" ) > "$L" 2>&1; rc=$?
  e=$(( $(date +%s) - s ))
  echo "render command: (cd $D && $HF render --quality draft --output $V)" | tee -a "$OUT/$arm.summary.txt"
  echo "render exit $rc, seconds $e, output $V" | tee -a "$OUT/$arm.summary.txt"
  [ -f "$V" ] || { echo "no output for $arm"; continue; }
  "$PY" -m contentos.production.visual_gate log "$L" > "$OUT/$arm.gate-log.json"; echo "gate log exit $?" | tee -a "$OUT/$arm.summary.txt"
  "$PY" -m contentos.production.visual_gate transitions "$V" --at "${WIN[$arm]}" > "$OUT/$arm.gate-transition.json"; echo "gate transition exit $? (${WIN[$arm]})" | tee -a "$OUT/$arm.summary.txt"
  "$PY" -m contentos.production.visual_gate captions "$V" --project "$D" --canvas 1080x1920 --windows "$CAPWIN" > "$OUT/$arm.gate-captions.json"; echo "gate captions exit $?" | tee -a "$OUT/$arm.summary.txt"
  "$PY" -m contentos.production.visual_gate layers "$D" > "$OUT/$arm.gate-layers.json"; echo "gate layers exit $?" | tee -a "$OUT/$arm.summary.txt"
  for t in 2 5.7 5.85 6.0 6.15 9; do ffmpeg -v error -y -ss $t -i "$V" -frames:v 1 -vf scale=360:640 "$OUT/${arm}_$t.png"; done
done
echo "results: $OUT"
echo "EXPECTED if the cloud findings hold on the Mac: cut=hard_cut (control), css=blend, shader=hard_cut or black. Anything else is the finding."
