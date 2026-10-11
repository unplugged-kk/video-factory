# Visual reliability gate (ep3 spike, correctness pass)

Status: **for review. Nothing pushed, no production default changed, no shader integrated.** One decision (Rule B semantics, section 9) is needed before KF-006 can be fixed; everything else here is finished within scope.

## 1. Repository state and files changed

Before any change: branch `video-intelligence`, HEAD `9f806e3` (unpushed; not amended), working tree clean except untracked `docs/research/` (preserved, untouched). No stashes.

| File | Change |
| --- | --- |
| `contentos/production/visual_gate.py` (new) | Rendered-output verifier: transition verdicts, render-log scan, caption ink check, caption layer-order check, CLI `log / layers / captions / transitions` |
| `contentos/intelligence/visual.py` | Additive only: `scene_backdrop_warnings()`; `check`/`claim` print `warnings`; `claim` refuses to record a possibly misleading signature unless `--acknowledge-warnings`. Signature semantics unchanged |
| `contentos/intelligence/designs.py`, `config/design-library.json` | Library moved to `design-library/2`: available / validated (per named environment) / recommended (fit only) |
| `tests/test_visual_gate.py`, `tests/test_visual_scene_backdrops.py` (new), `tests/test_designs.py` | 23 + 11 + 21 tests |
| `docs/video-intelligence/04-visual-reliability-gate.md`, `docs/video-intelligence/mac-experiment/{build.py,run.sh}` (new) | This report and a reviewable copy of the Mac package |

Bulky material stays in `workspace/spike-design-library/` (git-ignored): `ep3e/`, `mac-experiment/`, `sampler-mac.mp4`. Note: that folder is inside the repo checkout, not a separate VideoFactory workspace; it is ignored by git but you may want to move it.

One process slip, disclosed: during linting I ran `git stash` by mistake and popped it immediately. The tree is identical (verified by `git status` and test results); `git stash list` is empty.

## 2. Reproduction matrix

| | Environment | Steps | Expected | Observed |
| --- | --- | --- | --- | --- |
| KF-004 default path | Cloud: Linux, 2 cores, 8 GB, SwiftShader, headless-shell 141, hyperframes 0.8.114 | Render 14-shader sampler (1080x1920) | Blends | **14/14 hard cuts** (gate); log says `falling back to opacity-flip mode` |
| KF-004 Node-side path (`HF_PAGE_SIDE_COMPOSITING=false`) | Cloud, same | Same | Blends | Effects over **black** scene textures (12/14 measured black); 13m55s for 18 s |
| KF-004 new 3-arm experiment (cut / css / shader) | Cloud, **labelled cloud** | `mac-experiment/` arms, ~10 s each | cut=hard_cut, css=blend | cut=hard_cut, css=blend (3 intermediate samples), shader=hard_cut with log codes `shader_fallback_opacity_flip`, `page_side_compositing_unavailable` |
| KF-004 file `sampler-mac.mp4` | Unknown, **provenance unconfirmed** (hyperframes 0.8.114 tag, 1080x1920, 15 fps, 18.0 s) | Gate on all 14 windows | n/a | **14/14 blend, 0 black**; contact sheet shows real domain-warp, glitch, chromatic-split, etc. |
| KF-005 | Cloud | ep3 copy with opaque per-scene backgrounds, captions without z-index | Captions visible | Caption-region ink **0.0 in 12/12 samples** (baseline 4-9%); `hyperframes check` still passed |
| KF-006 | Repo code | Per-scene backdrops (`#s-*`) with a different `#root` | Signature describes the video | Signature read from `#root` only; per-scene backdrops ignored |
| Critic composition | Cloud | Independent critic on ep3 baseline/C | n/a | ~60% frame fill, faint secondary text, handle vs channel name; baseline score moved up to 2 points between rounds |

## 3. Root cause and regression tests

**KF-004 (renderer-specific).** Cause for the hard cuts is established: the default page-side compositor needs `drawElementImage`, absent in headless-shell 141, and HyperShader logs the fallback to opacity-flip. Cause of the **black** textures on the Node-side path is *not* established (it is inside upstream's layered pipeline; I did not instrument it). The Mac outcome is not established, see section 6. A clean log is not proof of success, because the black-texture render logs nothing alarming; only frame measurement catches it.
Tests: `tests/test_visual_gate.py` (synthetic ffmpeg fixtures: blend, hard cut, black, dark-neighbour blackout, dip allowed only when declared, identical neighbours inconclusive, log codes, CLI exit codes). Two bugs in my own first version were found and fixed by those tests (black matching black; pure-blue luma 0.072 hiding a blackout).

**KF-005 (design/validation layer).** Cause established by controlled reproduction: `hyperframes check` does not evaluate paint order between opaque scene backgrounds and the caption layer; adding `#captions{z-index:20}` restores 4-9% ink. Static check `check_caption_layering` flags an opaque scene stacked above captions; `data-captions-intent="behind"` is accepted as explicit intent but still demands the rendered check. Rendered check `check_captions` measures text-like ink in the caption region over sampled windows (ratio threshold 0.70 so narration gaps pass). Limit: static check cannot see JS-set styles or shadow DOM.

**KF-006 (design/validation layer).** Cause established by reading the code: `signature_from_css` takes the first of `#root`, `.scene`, `html,body`, `body` that carries a colour. Per-scene rules are never read. A hypothesis I tested and **falsified**: that `.scene-a` is mistaken for `.scene`; `_decl` requires `{` right after the selector, so it is not (kept as a pinning test). Fixtures in `tests/test_visual_scene_backdrops.py`: global (no warning), stale root, no root, scenes equal to root, comments ignored, claim refuses / acknowledged / dry-run / no-warning unchanged.

## 4. Exact changes and limits

- Gate is **measurement**, not a fix to the renderer. For a shader that renders as a hard cut it returns `hard_cut`, exits 1, and `fallback_plan` returns data-only advice (`css-transition:push-slide` / `blur-crossfade`). It does not rewrite compositions or switch backends, so "select the fallback explicitly" is satisfied only as a recorded recommendation; wiring it into render would be a pipeline change I did not make.
- Gate thresholds (`HARD_CUT_RATIO`, `MAX_BLACK_FRACTION`, `MIN_TEXT_FRACTION` …) are calibrated on these fixtures and ep3, not on a wide corpus.
- Rule B: warning plus claim guard only. **Deliberate behaviour change to call out:** `claim` now refuses a non-dry-run record when the warning fires, unless acknowledged. `used` output is unchanged.
- Library scoring: **I removed the confidence bonus from the recommend score.** Reason (demonstrated): it let a once-used transition (`push-slide`, fit 7) rank above equal-fit alternatives (fit 7), and let validation state reorder candidates, which is exactly the conflation you asked to separate. Fit components are otherwise unchanged. Before: shutter 9, push-slide 8 (7 + experimental 1), others 7. After: shutter 9, then 3d-card-flip / circle-iris / clock-wipe / push-slide at 7 by id order, with status shown in a separate column. `--require-validated` filters instead.

## 5. Test results

- New/changed suites: `test_visual_gate` 23, `test_visual_scene_backdrops` 11, `test_designs` 21; with `test_visual_language` the four files are **77 passed**.
- Full `tests/`: **341 passed, 1 failed, 2 skipped.** Baseline before my work: 300 passed, 1 failed, 2 skipped; the extra 41 are the new tests.
- The 1 failure, `tests/test_core.py::test_local_beats_paid_even_when_both_healthy` (`'paid_api' != 'paid_api'`), is pre-existing and unrelated.
- ruff: new/changed files clean except 3 pre-existing findings in `visual.py` (lines 175, 332, 395). `vendor/` is not collected (running bare `pytest` at the repo root errors on 182 vendored tests; run `pytest tests`).
- Cloud only; I did not run these on a second machine.

## 6. Mac verification

**Not performed by me.** The device shell is a Linux VM and cannot run the pinned Mac hyperframes. I did **not** substitute cloud results.

Found but unconfirmed: `workspace/spike-design-library/sampler-mac.mp4` (written 01:27 UTC, the earlier sampler you were to run). It gates as 14/14 blend. If you confirm it is your Mac render (machine, command, flags, render time), the shader hard-cut finding is cloud-specific and shaders are plausible on the Mac, pending the full set below. Until then it is "unconfirmed provenance", and the library records nothing as validated on the Mac.

To collect (from the repo root; it installs nothing and uses `node_modules/.bin/hyperframes`):

```
bash workspace/spike-design-library/mac-experiment/run.sh
```

It builds three 9:16 arms from one code-editorial scene set (vendored EB Garamond/Inter/JetBrains Mono, cream caption card): **cut** (control), **css** (push-slide at 5.55 s), **shader** (sdf-iris at 5.7 s). Per arm it writes, under `mac-experiment/results/<timestamp>/`: `environment.txt` (macOS, chip, RAM, hyperframes and ffmpeg versions), `<arm>.summary.txt` (check exit, exact render command, exit status, seconds, output path), `<arm>.render.log`, gate JSON for log / transition / captions / layers, and frames at 2, 5.7, 5.85, 6.0, 6.15, 9 s. Expected if the cloud finding holds on the Mac: cut=hard_cut, css=blend, shader=hard_cut or black; anything else is the finding. Please send back `results/<timestamp>/` (summaries, gate JSONs, logs; PNGs are small).

Findings from building the package (cloud, `hyperframes check`):
1. The preset's coral kicker on cream scored **2.71:1** (needs 3:1) and failed the check; the package darkens it on the light scene. Preset colours are not automatically contrast-safe.
2. `check` flags `content_overlap` inside a shader window; `data-layout-allow-overlap` on the **scene** did not clear it, on the text elements it did. Mid-transition contrast samples still warn.
3. HyperShader requires `scenes = transitions + 1`.

## 7. Baseline vs variant E (ep3, isolated copy; baseline and script/narration untouched)

Variant E = D (navy/indigo/teal family, CSS push 2→3 and blur-crossfade 4→5) plus: secondary text lifted (`--dim` #8e9ab4→#b7c2d8; key/row/ghost/bubble labels #7b88a3/#8b98b3 → #aeb9cf–#d0d8e8), small mono labels 24–27 px → 28–34 px, illustration block scaled 1.07, and a CTA lockup. Matched frames at 3, 15, 25, 36, 45, 51 s: `workspace/spike-design-library/ep3e/matched-baseline-vs-E.png` (top baseline, bottom E).

Measured: `hyperframes check` passes, **99/99** contrast; caption ink visible 32/32 samples; push and blur windows gate as blend with 0 black; layer-order clean; 1080x1920, 53.6 s; render 1m57s (cloud, draft). The same two `content_overlap` warnings as D appear in the blur window.

What changed visually: continuity across scenes is visible, the secondary labels are readable at phone thumbnail size, and the illustration is modestly larger. What did not: the bottom ~17% remains empty (intentional platform-UI safe zone), and scale 1.07 is small, so the "~60% frame" finding is only partly addressed. Larger gains need re-layout of each scene, which I did not attempt.

**Needs your approval (content-adjacent):** the CTA now shows `YOUR AI BUDDY` above the unchanged `@YourAIBuddy` handle. That adds on-screen text; the narration and script are unchanged. Revert it if you prefer the handle alone.

Critic: **not re-run on E in this session**, so no new critic scores are claimed. Earlier rounds (baseline `reject`, C `revise`, A "six templates from one pack") stand as direction only.

## 8. Verification criteria (what each status now requires)

Statuses are separate. **Available**: in pinned upstream (`hyperframes@0.8.114`). **Validated**: required checks all true in one *named* environment. **Recommended**: fit score only, shown beside validation status; `--require-validated --env E` filters.

| Level | Meaning |
| --- | --- |
| structural | static only (check/lint, schema, CSS/layer parse). Proves well-formed, nothing about pixels |
| rendered | a 9:16 render was made and its frames measured with the gate |
| reviewed | rendered plus a named human reviewer. Critic scores are advisory and never sufficient |

Required checks by kind: css_transition = hyperframes_check, transition_blend, captions_visible, output_size_matches_aspect, render_time_recorded; shader_transition adds no_fallback_in_log and not_black; frame_preset = hyperframes_check, fonts_vendored, caption_skin_rendered, captions_visible, secondary_text_contrast, output size, render time; palette = check, rule_a_distinct_backdrops, captions_visible, secondary_text_contrast, size; visual_style = check, rendered_frames_inspected, captions_visible, size. A render that finishes without errors is not validation. `validate` fails a record that claims a rendered pass without every required check true, an unknown environment, no evidence, or a reviewed record without a reviewer.

Audit of the 76 (default environment = Mac, `mac-hf0.8.114`):
- Available: 76/76.
- Validated in cloud (rendered): **2**, `css-transition:push-slide` and `css-transition:blur-crossfade` (re-evidenced with the gate; blur carries layout warnings).
- Failed in cloud: **14/14 shaders** (hard cut on default path, black on Node-side path).
- Partial: 4 presets (colour tokens only; typography and caption skin untested).
- Validated on the Mac: **0.** Untested on the Mac: all 76.
- Catalogue not expanded.

## 9. Remaining risks and recommended decision

**Decision needed (Rule B stop condition).** The documentation defines the signature as one record per video, but does not say what that is for a video with per-scene backdrops. Alternatives: (a) the opening scene's backdrop (variant C differs on 3/5 fields from pilot-001, 4/5 from ep2 by this reading); (b) the duration-dominant backdrop; (c) a per-scene set, compared set to set; (d) declare the shared family explicitly and compare only what varies. I recommend (b) with the current warning kept, as the smallest change, but I have not implemented any of them. Until you choose, Rule B can mislabel per-scene videos, and `claim` is guarded.

Other risks: (1) the Mac result for shaders rests on one unconfirmed file; (2) the gate is calibrated on one episode and synthetic clips; (3) caption check sees ink, not legibility; (4) preset and palette validation is thin (no full preset rendered end to end here); (5) the removal of the confidence bonus changes ranking ties and should be reviewed.

Next: confirm `sampler-mac.mp4`, run `mac-experiment/run.sh`, then decide Rule B semantics.
