# End-to-end feature verification (2026-10-19)

What this records: the first end-to-end run of the pipeline with the M2/M3 feature flags enabled, the
two wiring defects it confirmed and fixed, the defects found and left alone, and the stale-branch
cleanup of the same day.

Before this pass **no test called `pipeline.run()` end to end with `features:` enabled**. The only
full-pipeline tests were `only="export"` (`tests/test_pipeline_export.py`, `tests/test_approval_binding.py`,
`tests/test_supplied_audio.py`), and the six specs in `tests/fixtures/m3/` had no consumer at all.

## 1. How to reproduce

```bash
cd /Users/kishore/git/video-factory

# the real end-to-end suite: six fixtures, real renders, both lanes (about 5 minutes)
CONTENTOS_E2E=1 ~/.contentos/venv/bin/python -m pytest tests/test_e2e_features.py -v

# one job through the CLI, for a persistent job directory to inspect
./contentos.sh pipeline run tests/fixtures/m3/m3-sample-01-hf-sketch.yaml --approve-private
```

The E2E tests are opt-in because they need Chrome, ffmpeg and local TTS and they render for real. They
stay skipped in CI and in the default suite.

## 2. Environment at the time of the run

| Component | State |
|---|---|
| ffmpeg / ffprobe | arm64 Homebrew, on PATH via `contentos.sh:5` |
| hyperframes | `node_modules/.bin/hyperframes`, pinned 0.8.114 |
| Chrome | `/Applications/Google Chrome.app` |
| Kokoro TTS | `kokoro_onnx` in `~/.contentos/venv`; weights at `~/.cache/hyperframes/tts/models/kokoro-v1.0.onnx` |
| Remotion | installed at `~/.contentos/remotion`. `docs/factory-v2/01-inventory.md:15` says it is missing; that is stale |
| skill tools | `vendor/youtube-agent-skill/skills/{yt-script/hookscore.py,yt-package/title.py}` |
| `doctor` | exits 1 because `[llm]` has no provider. Expected here, and not a render blocker |

## 3. Result: six of six fixtures pass end to end

```
tests/test_e2e_features.py::test_fixture_runs_end_to_end[m3-sample-01-hf-sketch] PASSED
tests/test_e2e_features.py::test_fixture_runs_end_to_end[m3-sample-02-hf-product] PASSED
tests/test_e2e_features.py::test_fixture_runs_end_to_end[m3-sample-03-hf-spatial] PASSED
tests/test_e2e_features.py::test_fixture_runs_end_to_end[m3-sample-04-remotion-kinetic] PASSED
tests/test_e2e_features.py::test_fixture_runs_end_to_end[m3-sample-05-remotion-data] PASSED
tests/test_e2e_features.py::test_fixture_runs_end_to_end[m3-sample-06-remotion-hybrid] PASSED

6 passed in 288.17s (0:04:48)
```

The three remotion fixtures are the **first end-to-end exercise of the remotion lane** on this machine.

## 4. One job in detail

`./contentos.sh pipeline run tests/fixtures/m3/m3-sample-01-hf-sketch.yaml --approve-private`:

```
run bc47af821e4a
  brief     OK  (0.0s)     render    OK  (27.8s)
  script    OK  (0.1s)     qa        OK  (3.6s)
  voice     OK  (15.1s)    package   OK  (0.1s)
  compose   OK  (5.5s)     export    OK  (2.0s)
                           publish   OK  (0.0s)
```

Job directory: `~/Desktop/VideoFactory-Workspace/jobs/2026/10/19/m3-sample-01-hf-sketch/`
Rendered video: `video.mp4`, 5.3 MB, 32.5 s, 1080x1920, 30 fps.
Exported: `ready/unassigned/2026/10/month.../how-autonomous-agents-maintain-state__m3-sample-01-hf-sketch.mp4`,
sha256 `9a1aff7cdb67ba6497166c623a5f12320b3995656e08742090c7025334909cb0`, with its `.publish.json` sidecar.

All twelve QA checks passed:

| Check | Status | Detail |
|---|---|---|
| render_integrity | PASS | 32.5s |
| resolution | PASS | 1080x1920 |
| frame_rate | PASS | 30.0fps |
| duration | PASS | 32.5s <= 180s |
| audio_track | PASS | aac |
| loudness | PASS | -13.6 LUFS (target -14) |
| clipping | PASS | peak -1.5 dBFS |
| black_frames | PASS | 0 segments >0.5s |
| frozen_frames | PASS | 0 segments >3.0s |
| extra_silence_gaps | PASS | no silence gaps exceeding 0.4s |
| extra_end_hold | PASS | end hold duration within standard pacing (video total 32.50s) |
| extra_blank_field | PASS | no frozen runs exceeding 4.0s |

Note there was no `frozen_frames` WARN on this job, contrary to the expectation that text slides always
produce one.

Feature-by-feature, from that job's artifacts:

| Feature | Evidence |
|---|---|
| style_card + creative decision | `creative-decision.json`, schema `creative-decision/1`, `chosen` = `sketch-hand-drawn` (the value the spec asked for) |
| visual_layer | 6 `class="visual-decor"` cards in `project/index.html`, one per scene, plus the rewritten backdrop |
| captions_hook | `EXPLAINER` and `UP NEXT` present, zero `>HOOK<`, `190px` side padding applied |
| qa_extra | the three `extra_*` rows above appear in `qa.json` |
| audio_bed | the render stage's remux ran; loudness and audio track pass |
| scene_plan | **no observable output** - see section 6 |

## 5. Two defects confirmed and fixed

Both fixes carry regression tests in `tests/test_feature_regressions.py`, and both were shown red
against the unfixed code before being applied (3 failed, 3 passed).

**F1: `contentos/features/visual_layer.py:61` read a key that is never set.**
`ctx["style_card"]` is assigned in exactly one place, `contentos/features/style_card.py:117`, and it is
the chosen card **dict whose key is `id`**. The hook asked for `.get("chosen")`, so every style-family
container style (sketch, product, kinetic, data, spatial, hybrid) was unreachable and the default style
was always used. Fixed to `.get("id")`.

Evidence in real output, which the old code could not produce:

```
border:2px dashed rgba(255,255,255,0.22)      # sketch family style, now present in project/index.html
```

**F2: `contentos/features/registry.py` half-wired its own alias.**
`contentos/features/extra_gates.py:93` registers `extra_gates` as well as `qa_extra`, but `_PASS_THROUGH`
had no `extra_gates` entry, so `get("extra_gates", spec)` raised `KeyError: 'extra_gates'` whenever the
flag was off. One line added. Behaviour-neutral: the pipeline only ever asks for `qa_extra`
(`contentos/pipeline.py:241`).

## 6. Found, deliberately not fixed

- **`scene_plan` is inert.** `contentos/pipeline.py:166-167` calls the hook and stores `ctx['_scene_plan']`,
  which nothing reads. All six fixtures enable it for zero effect. This is a design decision to take, not
  a typo.
- **`features: {extra_gates: true}` silently does nothing.** The pipeline asks only for `qa_extra`, so the
  spec-level alias never enables the hook. The hook itself accepts either key
  (`extra_gates.py:71`), so the gap is one line in `registry.get`.
- **`qa_extra` cannot fail a job.** All three checks return `PASS` or `WARN` (`extra_gates.py:33-62`) and
  `s_qa` raises only on `FAIL` (`pipeline.py:244-246`). `check_end_hold` returns `PASS` unconditionally
  (`extra_gates.py:38-47`), so it is a stub.
- **`style_card` fails a job loudly** on any card problem (`style_card.py:48-49`), although T2/T3 were
  designed as advisory.
- **`config/capabilities.json` registers none of the T2-T7 modules**, so no style card or plan can name
  them and `python -m contentos.production.direction registry` never reports them.
- **`ci.yml:28` skips the pinned skills**, yet `tests/test_styles.py` validates card `ease_sources` by
  reading `.claude/skills/explainer-motion-craft/SKILL.md`, so style-card validation depends on a
  gitignored tree.
- **The remotion lane does not call `visual_layer` or `scene_plan`** (`contentos/renderers/remotion.py`
  calls style_card at :78, captions_hook at :134, audio_bed at :393 only), so those two features are
  hyperframes-only today. The fixtures enable them regardless.

## 7. Test suite position

| Suite | Before | After |
|---|---|---|
| `pytest tests -q` | 817 passed, 1 skipped | **823 passed, 7 skipped** |
| `node --test contentos/adapters/v1/*.test.mjs` | 44 pass, 0 fail | 44 pass, 0 fail |

+6 are the new regression tests. The +6 skips are the opt-in E2E cases.

## 8. Stale branch cleanup (2026-10-19)

Executed after this change merged. Every branch below was proven an ancestor of `main`
(`git branch --merged=main`) or, for the two squash-merged branches, content-identical to it. Tips are
recorded so any branch can be restored.

Local, in `/Users/kishore/git/video-factory`:

| Branch | Tip |
|---|---|
| gnhf/test-9f86d0 | 910710a |
| m3/integration | d111238 |
| m2/integration | 06887de |
| m2/A | 9089875 |
| m2/B | 3576384 |
| m2/C | 4e299ae |
| m2/D | c6c99c9 |
| m2/E | 04ee6bb |
| m2/F | c009108 |
| m2/F0 | e56510e |

Removed with them: the seven lane worktrees at `/Users/kishore/git/video-factory-lanes/{A,B,C,D,E,F,F0}`,
whose only working-tree content was an untracked `node_modules`.

On `origin`:

| Branch | Tip | Basis |
|---|---|---|
| fm/vf-motion-t3a-t7 | 2407603 | squash-merged as PR #3; tree identical to main |
| fm/vf-w1-approval | b8fedcd | squash-merged as PR #2; differs from main only by the T3a-T7 files main already has |
| fm/vf-w0-baseline | cd620b5 | ancestor of main |
| feature/labelled-contact-sheets | efc0860 | ancestor of main |
| video-intelligence | b199a39 | ancestor of main |
| factory-v2 | e92dd42 | ancestor of main |

In the firstmate clone `/Users/kishore/git/firstmate/projects/video-factory`: `main` fast-forwarded to
the merge commit; `fm/vf-motion-t3a-t7` and its treehouse lane 2 worktree removed; `fm/vf-w1-approval`
and `fm/vf-w0-baseline` removed.

**Deliberately preserved:** `fm/vf-w2-jobstate` (73931aa, ten unmerged jobstate and cancel commits) and
its treehouse lane 1 worktree. Do not delete either without deciding what happens to that work.

Trade-off: deleting the two squash-merged branches loses their individual commits (`a43bf68`, `8592ed3`,
`2407603`). Their content is in `main`, whose merge commit message lists all three.
