# Generic video system — what was verified

Measured 2026-10-25 on branch `feat/generic-video-system` (worktree `../video-factory-generic`), on this Mac
(M-series, Python 3.12, `~/.contentos/venv`). Every line below is a command that was run here, with its real output.
The rules that make this file necessary are `AGENTS.md` section 8: distinguish what was measured from what was
inferred, and do not claim completion before the artifacts exist and the checks pass.

## What the layer is

One entry point per video request instead of one skill per topic. Three layers, all of them data or thin skills:

| Layer | Artifact | State |
|---|---|---|
| Universal entry | `.claude/skills/create-video/` (+ `edit-video`, `lyric-video`, `repurpose-video`, `video-assets`, which defer to it) | built |
| Reusable capabilities | `contentos/videojob.py` selects them; each is implemented by a module or skill | 9 of 11 built |
| Configuration | `look/1` looks and effects in `config/presets/`, 51 old specs mapped in `migration-map.json` | built, nothing promoted |

## Commands and results

```
~/.contentos/venv/bin/python -m pytest tests -q -rs
    848 passed, 21 skipped in 115.33s (0:01:55)

~/.contentos/venv/bin/python -m pytest tests/test_videojob.py tests/test_looks.py tests/test_generic_cli.py -q
    41 passed in 0.35s

./contentos.sh looks validate
    {"ok": true, "problems": []}                                                 exit 0
./contentos.sh looks list --kind look   | wc -l  ->  30
./contentos.sh looks list --kind effect | wc -l  ->  27

./contentos.sh videojob select --intent create --input topic:"Explain Kubernetes operators"
    8 capabilities, each with state/by/why, no blockers                          exit 0
./contentos.sh videojob select --intent edit
    blocker "edit needs the source video", talking-head-editor state "planned"   exit 1

~/.contentos/venv/bin/python -m pytest tests/test_assets.py -q
    9 passed in 10.52s

python -m contentos.production.assets index <folder> --out <workspace>/index.json --samples 2
    1 clip indexed, 0 unreadable, notes skeleton written, exit 0
python -m contentos.production.assets search <index> "walking at night"
    1 hit, score 1, why ["path:night"], described false                          exit 0
python -m contentos.production.assets search <index> "submarine volcano"
    0 hits                                                                       exit 1
python -m contentos.production.assets verify <index>
    {"ok": true, "problems": []}                                                 exit 0
```

The 21 skips are environmental and named in the output: 6 need `node_modules/.bin/hyperframes` (`npm ci`), 3 need the
pinned `hyperframes-*` skills (`python scripts/upstream_skills.py sync`), 2 need ffmpeg *and* node *and* the
HyperFrames Chrome, 3 need a gitignored pilot workspace, 1 needs a build of ffmpeg with `drawtext` (the Homebrew
build has no freetype), and the rest need gitignored experiment artifacts.

## asset-library (the capability built in this pass)

`contentos/production/assets.py` indexes a media folder with ffprobe, samples frames per clip, and writes a fill-in
notes skeleton. **It never writes a description of its own**: a human or an agent looks at the frames and fills the
skeleton in, and a clip nobody has looked at stays `described: false` — the search result above says exactly that
about a real hit. Search is whole-word overlap over tags, description and path; it reports a miss (exit 1) rather
than the nearest guess. Exercised end to end on a generated 3-second clip and by `tests/test_assets.py`, which uses
synthetic clips only — never the owner's real footage.

That first end-to-end run found a real defect: `at` scored a hit by sitting inside `private/var`. Matching is now
whole-word, pinned by `test_a_short_term_does_not_match_inside_an_unrelated_path`.

## The ffmpeg blocker, and why the first run looked broken

The first full-suite run in this worktree was `45 failed, 614 passed, 20 skipped, 177 errors`. Every one of those 266
outcomes was the same cause — `OSError: [Errno 86] Bad CPU type in executable: 'ffmpeg'` (257) and `'ffprobe'` (9):
there was no arm64 ffmpeg on this Mac, only a dead x86_64 binary in `/usr/local/bin`, and `./contentos.sh doctor`
reported the same thing for the main checkout too. `brew install ffmpeg` (9.0.2, arm64) fixed all 266 without a code
change, which is the evidence that the failures were environmental and not the refactor's. This is worth remembering:
`contentos.sh` puts `/opt/homebrew/bin` first for exactly this reason, and a bare `pytest` does not.

## Not verified (do not read as done)

- **No render was produced by this layer.** A named `look` is still not read by the builder
  (`contentos/features/style_card.py`, and the hardcoded backdrop table in `contentos/features/visual_layer.py`), so
  "specify a style" changes no frame yet. That wiring is the next increment.
- **All 57 presets are `unvalidated`** and nothing promotes one; `looks.py` says status stays `unvalidated` until a
  real render records evidence, and no such record exists.
- **Two capabilities are `planned`** and are reported as such rather than faked: `talking-head-editor` and
  `lyric-video-engine`. `video-understanding` is `exists` but does word timing only — no beat detection, vocal
  separation or diarization.
- **No capability is registered in `config/capabilities.json`.** That file is read-only by design, and
  `create-video/SKILL.md` requires a passing smoke test and the owner's agreement before a capability is registered.
- **No end-to-end video was produced** from a `create-video` request; the selector, the manifest and the presets were
  exercised, the pipeline behind them was not run for this system.

## Two things the tests now pin

- The capability table cannot drift: `tests/test_videojob.py` checks every `exists` entry's `by` path against the
  disk, checks that `create-video/SKILL.md` names every capability and keeps no second copy of its state, and checks
  that a `planned` capability is still reported by `select`.
- `look/1` names two different shapes and they must not merge: a preset (`config/presets/`, `intelligence/looks.py`)
  and the export stage's shipped-look record (`pipeline.py`, written into a job folder). Renaming the ledger's tag
  would invalidate already-written workspace artifacts, so both keep the tag with a test that stops one passing as
  the other. Revisit when that schema is next touched.
