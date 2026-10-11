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

---

# Addendum, 2026-10-11: Rule B decision, Mac readiness, Variant E review

Original sections 1-9 above are unchanged. Approved decisions applied here: (1) Rule B uses the duration-dominant backdrop, (2) a warning stays whenever more than one backdrop is present, (3) the time distribution is reported and ties are flagged, (4) `sampler-mac.mp4` is not treated as Mac-validated, (5) the CTA text "YOUR AI BUDDY" is a candidate only.

## A. Rule B: duration-dominant backdrop

**Data model, checked first.** Rule B reads CSS only; scene durations are not in the CSS. The real shapes are: ep3 `audio/timing.json` `scenes[]{id,start,dur}` with CSS `#s-<id>`; ep2 `scenes.json` `scenes[]{id,start,end}`; pilot-001 `timing.json` has no `scenes` at all. Backdrop identity is the normalised resolved background declaration of the scene's own rule; a scene with no own rule inherits the global (`#root`/`.scene`/`body`) backdrop. A scene's rule is looked up as `#s-<id>`, `#scene-<id>`, `#<id>`, `.scene-<id>` or `[data-scene=<id>]`. Selector lists (`#s-a, #s-b {}`) are not parsed (limitation).

**Semantics.**
- Duration = `dur`, else `end - start`. Missing id, non-number, bool, NaN/inf, zero or negative durations are reported (`timing_invalid_duration` etc.) and that scene is left out; duplicate ids are flagged but both count.
- Total seconds and share are computed per backdrop; the signature is that of the backdrop with the most total seconds. Equal seconds: the backdrop that appears first.
- **Ambiguity:** the top two within 5 percentage points of total duration are "ambiguous" (`dominant_backdrop_ambiguous`). The winner is still chosen deterministically, but it is flagged and `check` also evaluates Rule B for each tied candidate (`tie_sensitivity`) so you can see whether the pick matters.
- Two or more backdrops always raise `multiple_backdrops` (with dominant share and seconds). `claim` therefore still refuses to record unless `--acknowledge-warnings`; the ledger entry now also stores `basis`.
- No usable durations: falls back to the old global-rule signature and says so (`per_scene_backdrops_not_in_signature` + `scene_durations_unavailable`).
- New option `--timing PATH` on `used/check/claim`; otherwise timing is discovered next to the composition (`<job>/audio/timing.json`, `<job>/scenes.json`).

**Verified on real data.** Signatures are identical to the previous code for ep3 baseline, ep2 and pilot-001 (global backdrop; pilot-001 has no timing). Real ep3 variant A (six backdrops): hook 19.1%, bigidea 19.0%, contrast 21.1%, outputs 18.1%, llm 14.9%, cta 7.8%. Dominant = contrast (flat charcoal) but **ambiguous** (four backdrops within 5 points). That is the honest outcome: six near-equal backdrops make "dominant" a weak summary, which is why the flag exists.

**Behaviour changes.** (1) Per-scene videos with timing now get the dominant backdrop's signature instead of `#root`'s. (2) `used` prints warnings to stderr. (3) `claim` records `basis`. (4) `signature_from_css` gained an optional `decl_override`; with no override it behaves as before (texture detection of 1px gradients is scoped to the override when one is given). Not changed: the old `.scene{background-color}` quirk (the existing `_decl` ignores `background-color`; flagged, left alone because fixing it would change existing signatures).

**Tests** (`tests/test_visual_dominant_backdrop.py`, 21): durations (dur, end-start, invalid, no scenes, duplicates), global backdrop unchanged, no-timing fallback, ep3 real distribution, dominant follows backdrop not root, unequal durations aggregated across scenes, inheritance of the global backdrop, stale root no longer deciding, warnings, exact tie, near-tie, clear winner, determinism independent of CSS order, all-invalid and partly-invalid durations, timing discovery incl. pilot-001 shape, claim guard + `basis`, CLI `check` output (distribution, ties, sensitivity).

## B. Mac experiment readiness

Reviewed `run.sh` and the package. Defects found and fixed:
1. **`declare -A` (bash 4+) fails on macOS's default bash 3.2.** Replaced with a `case` function.
2. **Result folder collided within the same second** (`date` only). Now `mktemp -d results/run-<timestamp>-XXXXXX`; earlier folders are never reused.
3. **Exit status said success even if arms failed.** Added `summarize.py`: per-arm table, `harness_ok` (all three arms rendered and gated), `control_valid` (cut must read `hard_cut`, css `blend`, else the shader verdict is suspect). Exit 0 only if `harness_ok`; findings (hard cut, black) are results, not errors.
4. Python was bare `python3`; now `$PYTHON`, else `$HYPERFRAMES_PYTHON`, else `~/.contentos/venv/bin/python` (same default as `contentos.sh`), plus `/opt/homebrew/bin` on PATH.
5. Environment record extended (node, python, repo HEAD, dirty file count, package hash, HF env vars). Per-arm exit codes and seconds are saved as files, not only printed.
6. Preflight stops with exit 2 if the pinned hyperframes, python, ffmpeg or `visual_gate.py` is missing; it installs nothing.

Confirmed present: three arms (cut control, css push at 5.55 s, shader sdf-iris at 5.7 s), `common/` with gsap, shader-transitions.js and all six vendored woff2 fonts plus licences, arms rebuilt each run by `build.py`, gate run per arm on that arm's own output (log scan, transition window, caption ink, layer order), frames at 2, 5.7, 5.85, 6.0, 6.15, 9 s.

**Harness test, done in the cloud and labelled as such (not a Mac result):** full run with the three arms gave cut=hard_cut, css=blend, shader=hard_cut with fallback log codes, `harness_ok=True`; a second run with a simulated shader render crash (exit 7) gave the shader row as "did not render/gate", the other two arms intact, `harness_ok=False`, script exit 1, and both result folders were kept. That test found and fixed a bug in my first `summarize.py`.

**Not run on a Mac.** The device shell is a Linux VM.

**Run this from the Mac repo checkout** (`/Users/kishore/git/video-factory`; the package is already in the folder):

```
cd ~/git/video-factory && bash workspace/spike-design-library/mac-experiment/run.sh
```

Expect a few minutes (the 18 s sampler rendered in 14 s on your Mac; these arms are 12 s each, so this is an estimate, not a measurement). **Return** the whole new folder `workspace/spike-design-library/mac-experiment/results/run-<timestamp>-<id>/` except the `.mp4` files: `environment.txt`, `SUMMARY.txt`, `SUMMARY.json`, `*.summary.txt`, `*.render.log`, `*.check.log`, `*.gate-*.json`, and the small PNGs.

**On `sampler-mac.mp4` provenance.** Your pasted terminal log is Mac-generated evidence: platform darwin arm64, Apple M5 Pro, hardware GPU (ANGLE Metal), hyperframes 0.8.114 (the "update available" line), "Page-side compositing enabled", 15 fps, 270 frames, 3.7 MB, 18.0 s, rendered in 14.0 s, output path `workspace/spike-design-library/sampler-mac.mp4`. Those match the file in the workspace (3,885,025 bytes, 18.0 s, 1080x1920, 15 fps). That supports provenance but does not bind the file to the machine, so I recorded the 14 shaders in the library as **partial** (not validated) at the Mac environment, with that provenance text and an owner-to-confirm note. They stay **failed** in the cloud environment. Validation needs a captions run, `hyperframes check`, and the new experiment on the Mac. The log also shows why the environments differ: the Mac runs a hardware GPU with page-side compositing available, the cloud container does not.

## C. Variant E review (candidate; baseline and E sources untouched; CTA not approved)

Evidence files in `workspace/spike-design-library/ep3e/`: `matched-review.png` (baseline top, E bottom, six scenes, caption band cyan, bottom UI zone red line), `phone-size-390w.png` (contrast and outputs scenes at 390 px width), `capbar-vs-captions.png`, `measure.json`. Frames taken late in each scene (9, 19, 30, 40, 48, 52 s) so animations have settled. Contrast ratios are WCAG against the sampled backdrop at the element's row; the "ink extent" figures are a row-median mask and approximate.

| Item | Baseline | Variant E | Reading |
| --- | --- | --- | --- |
| Illustration scale | lattice 612 px tall, contrast block 885, outputs 895, llm 703 | 659, 954, 959, 760 (+7 to +8%) | Modestly larger. The block is already near full width in most scenes, so the gain is height, not width |
| Illustration box | x 70-940, bottom at y 1360 | x 40-970, bottom at y 1428-1434 | **The scaled box now reaches into the caption band (top y 1374) by ~55 px.** Side gutter is 40 px left (70 before) |
| Crowding | ~25 px gap between the "DIFFERENT CAPABILITY" bar and the caption word | gap ~0 (bar touches the caption text line) | No pixel overlap and `check` did not flag it, but it is tight. See `capbar-vs-captions.png` |
| Secondary text, phone size (390 pt wide) | kicker 10.5 pt, rail card 9.0, pane label 9.0, spine tag 8.7, ghost/bubble 9.4 | 12.3, 10.5, 10.8, 10.1, 10.8 | Improved; spine tag (10.1) and a few labels remain just under 11 pt |
| Secondary contrast | kicker 6.7:1, keys 5.5, rail card 5.3, row label 6.5 | 10.9, 9.9, 8.7, 9.1 | Clearly better |
| Contrast that fell | subline 10.5, spine tag 11.3, handle 10.8, pill 11.8 | 8.9, 7.4, 8.9, 8.5 | Lighter backdrops cost the cyan/amber accents some contrast; all still >= 7:1 |
| CTA | handle 34 px cyan above an 84 px message | `YOUR AI BUDDY` 62 px white / handle 38 px light cyan / message 84 px | Name now outranks the handle, message still dominant; the lockup is 88 px taller. Candidate only |
| Safe zones | nothing in y > 1594 | nothing in y > 1594 | Bottom UI zone intact in both (0.0% ink) |
| Caption visibility | 32/32 samples | 32/32 samples | Visible in both |
| Caption word contrast (inactive #9aa6bf, unchanged in E) | 8.15:1 on every scene | 7.97, 7.44, **5.71** (contrast scene), 6.61, 7.02 | Still above AA 4.5 but lowest on the lighter teal; the caption colour was not lifted along with the other secondary text |
| Transitions, 19.962 s and 40.95 s windows (0.45 s) | inconclusive (backdrops too similar to judge), hard_cut | blend, blend; 7 intermediate samples each, 0 black | E's blends are correct. The baseline has none, so this is a feature of E/D, not of the text refinements |
| `hyperframes check` | passes | passes, 99/99 contrast; same two `content_overlap` warnings in the blur window | Unchanged from D |

**Conclusion.** E fixes the faint-label problem and gives scene-to-scene continuity, and the two CSS transitions are correct. The 1.07 illustration scale is the weak part: it buys ~7% height at the cost of crowding the caption band. Suggested next variant (not applied, since you asked me not to silently change the candidate): scale 1.03-1.04 or reduce the viz top margin instead, lift the caption base colour to about `#b7c2d8`, and keep the CTA lockup as a separate yes/no decision. The CTA remains a candidate, not approved, and nothing here touches production defaults.

## D. Test results

- Targeted (`test_visual_dominant_backdrop` 21, `test_visual_scene_backdrops` 11, `test_visual_language`, `test_visual_gate` 23, `test_designs` 22): **99 passed.**
- Full `pytest tests`: **363 passed, 1 failed, 2 skipped.** Previous commit's full run: 341 passed, 1 failed, 2 skipped; the difference is +21 dominant-backdrop tests and +1 library test.
- The 1 failure, `tests/test_core.py::test_local_beats_paid_even_when_both_healthy`, **reproduces on an unchanged export of commit `9f806e3`** (taken with `git archive`, no checkout or stash): `1 failed, 4 passed` in `tests/test_core.py`. Unrelated to this work.
- ruff: new files clean; `visual.py` has only the 3 findings that predate this work (lines 185, 479, 542).
- Not tested: nothing was run on a Mac; the harness logic was exercised in the cloud only.

## E. Remaining risks

1. Real ep3 is a six-way near-tie, so Rule B's dominant backdrop is a weak summary there; the ambiguity flag and tie sensitivity are the safeguard, and selector lists in CSS are not parsed.
2. Shader evidence on the Mac is one render of a captionless sampler; shaders stay unvalidated until the experiment returns.
3. The 5-point tie band and the gate thresholds were chosen on this data, not tuned on a corpus.
4. `claim` now always needs `--acknowledge-warnings` for per-scene videos; that is deliberate but adds friction.
5. Variant E scale crowding the caption band (section C) is not caught by `hyperframes check`.
6. Spike media still sits under `workspace/spike-design-library/` inside the repo checkout (git-ignored); it is not in any publishing handoff directory.

## F. Files changed in this addendum and final status

Modified: `contentos/intelligence/visual.py`, `config/design-library.json` (14 shader Mac records), `tests/test_designs.py`, `docs/video-intelligence/04-visual-reliability-gate.md`, `docs/video-intelligence/mac-experiment/run.sh`. New: `tests/test_visual_dominant_backdrop.py`, `docs/video-intelligence/mac-experiment/summarize.py`. Git-ignored workspace files: `mac-experiment/{run.sh,summarize.py}`, `ep3e/{matched-review.png,phone-size-390w.png,capbar-vs-captions.png,measure.json}`. Final repository status is committed on `video-intelligence` as a new commit after `e195728`; not pushed; `9f806e3` and `e195728` untouched; untracked `docs/research/` preserved; no stashes.

## G. Five-arm Mac caption run (2026-10-11; supersedes E.2)

The 3-arm run left `shader:sdf-iris` failing `captions_visible` with "cause not investigated" and one open question: can captions be kept visible over a shader? The harness was extended to five arms and re-run, once per caption arrangement, on the same scene pair.

**Run.** `workspace/spike-design-library/mac-experiment/results/run-20261011-082039-P0sx7o` - Darwin arm64, Apple M5 Pro, macOS 27.0.1, hyperframes 0.8.114, node v24.19.0, ffmpeg 9.0.2, repo HEAD `8d4a337`, 9 dirty files, `pkg_sha256: bb40b33909b5b7bd`, `harness_ok=True`, `control_valid=True`. A first pass of the same five arms, `run-20261011-081746-EMxZfN`, is kept but not citable: its ink-caption check errored on every arm (see the harness fix below).

| arm | caption placement | check | transition | black | ink captions | in-window (ink) | caption text | layers | render s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cut | control, no transition | 0 | hard_cut | 0.0 | 1.0 | 1.0 | 1.0 | True | 6 |
| css | root layer, push at 5.55 s | 0 | blend | 0.0 | 1.0 | 1.0 | 1.0 | True | 7 |
| shader | root layer, z-index 20 | 0 | blend | 0.0 | 0.909 | 0.154 | 0.368 | True | 11 |
| shader-zi | root layer, z-index 200 | 0 | blend | 0.0 | 0.909 | 0.154 | 0.368 | True | 12 |
| shader-in | inside each scene | 0 | blend | 0.0 | 1.0 | 1.0 | 0.947 | True | 12 |

1. **The caption layer is not composited into a shader transition.** Probing the caption region (870x214 at 70,1374) as pixels: at 5.70 and 5.80 s it is 0% light with mean 19-32, the bare dark backdrop with no plate at all, and the glyph score is 0 in all 12 in-window samples (5.70-6.30 s). The caption is absent for the whole 0.6 s, not faded.
2. **Stacking order is not the cause.** `shader-zi`, at z-index 200 above the canvas HyperShader injects at z-index 100, scores identically to `shader` at every sample. The shader path does not honour root-level stacking.
3. **Scene-embedded captions survive, with one bad sample.** `shader-in` reads 1.0 on the ink checks and 0.947 on the text check, because the caption is captured with its scene into the transition texture. The single failure is 5.85 s, the transition midpoint: the plate is present (78% light) but the glyph score collapses to 31 against a reference floor of 1590, so the text is washed out for about one sample (50 ms at this sampling rate). That is a contrast loss, not a missing layer.
4. **Nothing is promoted.** No shader arm passes blend plus caption visibility, so `shader:sdf-iris` stays **failed** at `mac-hf0.8.114` and the other 13 stay **partial**. `css-transition:push-slide` remains the only Mac-validated transition, re-confirmed here at 1.0/1.0/1.0, blend, check exit 0. The cut arm read hard_cut and the css arm blend, so the gate discriminated.

**Harness fix.** The extended `build.py` moved the caption geometry from a px-sized `#captions` rule to `.capbox`, so `visual_gate captions --project` could no longer derive the region and errored on all five arms ("give --region x,y,w,h or --project with a px-sized #captions rule"); `harness_ok` was false in the first pass even though every arm rendered and gated. `run.sh` now passes `--region 70,1374,870,214`, the region its caption-strip crop already assumed.

**Reading the checks.** The ink check is the one production QA runs, and here it is fooled in both directions: it called the 5.85 s frame visible in the 3-arm run because the bright iris counts as ink, and it reads `shader-in` as 1.0 while the text check finds the washed-out sample. `caption_window.py` (dark glyphs flanked by light plate pixels) is what separates the three cases; the ink check should not be used alone to judge captions across a shader.

**Still not measured.** One shader of fourteen, one transition window, one scene pair, draft quality, 9:16 only, no phone review. The z-index hypothesis is closed for `sdf-iris` only; the other 13 shaders have no captions run at all and may composite differently.

**Implication.** A shader transition needs its captions inside the scene tree to keep them on screen, and even then the midpoint can wash them out. That is a per-transition design constraint, not a renderer defect; until it is met for a given shader, the validated transitions stay CSS.

**Files changed by this section.** `config/design-library.json` (the `shader:sdf-iris` Mac record: cause, both run folders, the two new arms), `docs/video-intelligence/mac-experiment/run.sh` (explicit `--region`, synced to the git-ignored workspace copy), this section.

## H. Addendum 3 (2026-10-11): shader caption cause, Variant E2, CTA review

Written after the decisions "keep CSS push-slide validated, investigate shaders without promoting them, improve Variant E before approval, do not push". Section G above reports the same five-arm Mac run from another working session; this section adds the checker I built for it, an independent reading of the frames, and Variant E2.

**H.1 Why captions vanish over a shader (Mac, run-20261011-082039-P0sx7o).** Reading `caption_window.py` (dark glyph pixels flanked by light plate pixels, so a bright blob cannot pass as text) over 5.55-6.45 s at 0.05 s steps on the genuine Mac videos:

| arm | caption text visible in window | hidden samples |
| --- | --- | --- |
| cut, css (controls) | 1.0 | none |
| shader (root layer z-index 20) | 0.368 | 5.70-5.95 and 6.05-6.30 s (a single legible sample at 6.00 s) |
| shader-zi (root layer z-index 200) | 0.368, sample-for-sample identical to shader | same |
| shader-in (inside each scene) | 0.947 | 5.85 s only |

A root-level caption layer is not part of what HyperShader composites, so z-index is irrelevant; the same checker run on the first Mac run's videos showed the same 5.70-6.30 s gap (the 3-arm videos' own cut/css caption gap at 5.9-6.15 s was the old script's non-contiguous captions, fixed in `build.py`). Reading the 5.85 s `shader-in` frame (`shader-in_5.85.png`, `shader-in_caption-strip.png`) as an image: the text "Learned, not written" is present and readable but grey on a near-white blob, with the plate edge lost; the previous glyph threshold (dark <= 90) counts greyed glyphs as absent. So 5.85 s is a low-contrast sample, not a missing layer, and the strict check still fails it. Whether one 30 fps frame of low contrast is acceptable is a product decision; the check as written says fail.

**H.2 Status.** `shader:sdf-iris` stays failed (strict check) and the other 13 stay partial. `css-transition:push-slide` keeps its Mac validation, re-confirmed at text visibility 1.0. Possible next experiments, not run: a darker caption plate inside the scene so the iris flash cannot wash it out; or a shader without a white flash. Neither changes anything until a run shows it.

**H.3 The static layer check cannot see this.** `visual_gate layers` returned ok on all five arms, including the two that lose their captions, because HyperShader injects its canvas (z-index 100) from JavaScript and the check reads only CSS and inline styles. The failure is invisible to static checks; only a render shows it.

**H.4 Variant E2 (candidate, not approved).** Folder `workspace/spike-design-library/ep3e2/`; E and the baseline are untouched. Changes from E: inactive caption colour `#9aa6bf` to `#b7c2d8` (CSS `.cw` and the JS `BASE`), and illustration scale 1.07 to 1.04 on three scenes.

- A uniform 1.04 still intrudes: with the transform origin at the top, the content of the two full-height scenes ends at y 1401 (bigidea) and 1409 (contrast), inside the caption band that starts at y 1374, and the "DIFFERENT CAPABILITY" bar ends at 1409 against a two-line caption starting near 1407. There is no room to grow upward either (46 px gap to the headline, 4% is about 40 px). So 1.04 is applied to hook, outputs and llm, and bigidea and contrast stay at 1.0.
- Measured over each scene's visible life (every 0.5 s): lowest content bottom 1288 (hook), 1360 (bigidea), 1366 (contrast, the bar), 1332 (outputs), 1143 (llm). Nothing enters the band; the bar is 41 px above a two-line caption.
- Inactive caption contrast against the scene backgrounds rises from 5.6-7.9:1 to 7.7-10.8:1. Trade-off found: `#b7c2d8` has the same luminance as the active cyan word (ratio 1.01; 1.07 against amber; previously 1.35 and 1.47), so the active-word highlight now rests on hue alone, which is weaker on a phone and for colour-blind viewers. Alternatives: `#a6b2ca` (6.5:1 on the teal scene, 1.18 against cyan) or `#adb8ce` (7.0:1, 1.10). Left at the requested value pending review.
- `hyperframes check` on E2 in headless Chromium in the cloud container (not the Mac): contrast 99/99 AA, 0 errors, 2 overlap warnings at the intentional blur-crossfade near 41 s, 1 info. The critic was not run; no render of E2 was produced.
- Evidence: `phone-sheet-baseline-vs-E2.png` (six scenes at 390 px width, original look above, E2 below), `measure.json`.

**H.5 CTA "YOUR AI BUDDY" (candidate only).** In the composition at phone width: channel name 62 px/900 white, handle 38 px/700 pale cyan, headline "FOLLOW TO UNDERSTAND HOW IT ALL WORKS" 84 px/900 near-white, FOLLOW pill 36 px. The channel name and the headline are both heavy white type, ratio 0.74, stacked with the small handle between them, so the name competes with the headline instead of leading into it, and the handle becomes the weak middle line. It does not touch the captions (none run on the end card). Not approved. If pursued: reduce the channel line (about 44-50 px, lighter weight or colour) so the headline stays dominant, keep it as one lockup with the handle. Not applied.

**H.6 Tests.** New `tests/test_caption_window.py` (5 tests, pass). On the Mac-side VM's Python 3.10, `pytest tests --continue-on-collection-errors`: 333 passed, 1 failed (the known `test_core::test_local_beats_paid_even_when_both_healthy`, which reproduces on a clean export of 9f806e3), 5 modules cannot be imported under 3.10 because `contentos/pipeline.py` uses a 3.12-only f-string (pre-existing, unrelated). On Python 3.13 in the cloud container from a tracked-files-only export: 356 passed, 10 skipped, 5 failed: the same baseline failure and four that need git metadata or the git-ignored vendored `.claude/skills`, which an export lacks (`test_director` x2, `test_motion_catalogue`, `test_storage::test_gitignore_blocks_media`). The five suites that cover this work (caption window, designs, visual gate, scene backdrops, dominant backdrop) pass together: 82 passed. No clean single-environment total with the vendored skills present was produced in this session.

**H.7 Tree state.** Nothing was committed in this addendum. The working tree also holds changes from another working session that I did not make and left as found: `contentos/pipeline.py`, `tests/test_pipeline_captions.py`, docs `05`, `06`, `07`, section G above, the 5-arm update to the `shader:sdf-iris` record in `config/design-library.json`, and the `--region` fix in `run.sh`. My files: `docs/video-intelligence/mac-experiment/{build.py,summarize.py,caption_window.py}` (and the shared `run.sh`), `tests/test_caption_window.py`, this section, and git-ignored `workspace/spike-design-library/ep3e2/`. Not pushed. A scratch archive `workspace/.tmp-src/src.tgz` (git-ignored) was left by me and can be deleted.

## I. Addendum 4 (2026-10-11): E2 revision 2 and the darker-plate experiment (prepared; Mac result pending)

**I.1 Decisions applied.** Inactive caption colour `#adb8ce` (contrast 6.99:1 on the teal scene, 6.87:1 on the end card), CTA channel name 62 px to 48 px with the 84 px headline unchanged. E2 only; E and the baseline are untouched. Both remain candidates.

**I.2 E2 revision 2 findings** (headless Chromium in the cloud container, not a Mac; `hyperframes check` passed, contrast 99/99, 2 overlap warnings at the intentional blur-crossfade). The active caption word is amber `#fbbf24` (cyan is not used for caption words, which corrects the wording in H.4): luminance ratio inactive/active is 1.20 (original `#9aa6bf` 1.47, `#b7c2d8` 1.07). In colour the highlight is clear; in a greyscale render the active word is only slightly lighter than its neighbours, so it relies on the blue-grey/amber hue difference rather than luminance. No non-colour cue (weight, scale, underline) was added. CTA: the 48 px channel name now sits clearly under the 84 px headline; with the 38 px handle it reads as one small lockup above the headline, not a weak middle line, though the handle is about 14 px at phone width. Not approved. Evidence: `ep3e2/phone-sheet-E2-rev2.png`, `ep3e2/caption-bands-E2-rev2.png`, `ep3e2/measure.json`.

**I.3 Darker-plate experiment.** `build.py` gained three arms: `shader-in-dark` (captions inside each scene on a dark plate `#2b2a27` with `#FAF9F5` text) and its matched controls `cut-dark` and `css-dark`; the five existing arms are unchanged. `caption_window.py` gained `--polarity light-on-dark` (the glyph check mirrored for a dark plate; calibrated on the cut arms: 4295/3911 for the light plate, 4595/4279 for the dark plate in a browser frame; a white blob scores 0 in both modes). `run.sh` selects the mode per arm and also saves frames at 5.8 s and 5.9 s. Judgement rule: the strict check is not relaxed; the 5.85 s frame is also read as an image.

## J. Darker-plate experiment result (2026-10-11, genuine Mac run)

**Run.** `workspace/spike-design-library/mac-experiment/results/run-20261011-083452-aZuLT5`: Apple M5 Pro, hyperframes 0.8.114, repo HEAD `8d4a337`, 13 dirty files, eight arms, `harness_ok=True`, `control_valid=True` (cut and cut-dark hard_cut; css and css-dark blend; every control reads 1.0 on all caption measures). Run by the user from the repo root with the command in the package header.

| arm | transition | black | caption text visible (strict) | hidden samples (50 ms steps) |
| --- | --- | --- | --- | --- |
| shader (root, z 20) | blend | 0.0 | 0.368 | 5.70-6.30 s (12) |
| shader-zi (root, z 200) | blend | 0.0 | 0.368 | 5.70-6.30 s (12), identical to shader |
| shader-in (in scene, light plate) | blend | 0.0 | 0.947 | 5.85 s |
| shader-in-dark (in scene, dark plate) | blend | 0.0 | 0.895 | 5.85 and 5.90 s |

The first three rows reproduce the earlier run sample for sample. The dark plate did not fix the strict miss: it hides two samples, not one.

**Reading the frames** (`review-5.85-shader-in-vs-dark.png`, `shader-in-dark_caption-strip.png` in the run folder). In `shader-in-dark` at 5.85 and 5.90 s the caption is present as a translucent mid-grey plate with light text over the white iris; the plate is clearly visible (the light-plate arm loses its plate and shows faint grey text). The strict checker reads those samples as hidden because the blended plate is no longer dark enough to pass its plate test. A rough local contrast estimate from the 360 px preview PNGs (text-line crop, glyph percentile against median background; approximate, not the gate): light plate 4.2:1 at 5.85 s and 10:1 at 5.90 s; dark plate 3.0:1 at 5.85 s and 7.3:1 at 5.90 s; every other sampled frame is above 11:1. So the worst frame is weaker with the dark plate (about 3:1) than with the light plate (about 4:1).

**Conclusion.** Neither arrangement is genuinely unreadable at its worst frame (both are around or above 3:1, the large-text threshold, for 100 ms or less), and neither passes the strict gate. The darker plate does not improve the outcome: it adds a second hidden sample and a lower worst-frame contrast. The gate was not relaxed, so `shader:sdf-iris` stays failed at `mac-hf0.8.114` and the other 13 shaders stay partial. `css-transition:push-slide` remains the only Mac-validated transition and keeps 1.0 on every caption measure. The experiment narrows the limit: a shader with a white flash at its midpoint will wash out captions at that instant whichever plate is used; I recommend stopping shader work here, and the decision is the user's. A shader with no bright flash would be a different experiment.

**Not changed.** `config/design-library.json` was not edited for this result (the shader record is part of the other session's uncommitted changes); it needs one line noting the dark-plate run if it is to carry this evidence. Nothing committed or pushed.

## K. E2 revision 3 (2026-10-11): non-colour active-word cue; Mac render prepared

Decisions applied: shader work stopped (statuses unchanged: push-slide validated; sdf-iris failed; other 13 partial; blur-crossfade not Mac-validated); the other session owns the design-library record and the shared commit; E2 gets a render, a critic pass and a non-colour cue. The active caption word is amber `#fbbf24` (it was never cyan); the colour is unchanged.

**Cue.** The active word is underlined (5 px, offset 9 px, same colour, no skip-ink) and the underline is removed when the word ends, in `ep3e2/styles.css` (`.cw`) and `ep3e2/index.html` (the GSAP set that already switched the colour). An underline was chosen over a weight change because it does not alter glyph widths, so the caption chunks do not reflow. In a greyscale render of four captions the underlined word is clearly distinguishable (`ep3e2/caption-bands-E2-rev3.png`, colour left, greyscale right). Measured in headless Chromium in the cloud container; the rendered video on the Mac is the real test. `#adb8ce` stays the inactive-colour candidate.

**Mac render.** `workspace/spike-design-library/ep3e2/render-e2-mac.sh` renders E2 (default quality) into a new `ep3e2/results/run-*` folder using a copy of the ep3 assets, then runs: `hyperframes check`, the render-log scan, `visual_gate transitions` on the two CSS transitions (19.962 s push, 40.95 s blur-crossfade), blackdetect over the whole video, a dense caption-band check every 0.25 s, mobile-size frames, a contact sheet and a caption-band sheet. Pending: the user runs it and returns the folder; then the independent critic pass and the mobile-size review.

## L. E2 Mac render and critic pass (2026-10-11)

**Render.** `workspace/spike-design-library/ep3e2/results/run-20261011-084146-ALBc80`, run by the user: Apple M5 Pro, hyperframes 0.8.114, repo HEAD `8d4a337`, 13 dirty files; `hyperframes check` exit 0 (contrast 0 errors; the 2 overlap warnings are at the intentional blur-crossfade near 41 s); render exit 0 in 48 s at default quality; 1080x1920, 30 fps, h264 + aac, 53.6 s.

**Objective gates.** Both CSS transitions read blend (push at 19.962 s: 6 intermediate samples; blur-crossfade at 40.95 s: 7), black fraction 0.0; blackdetect over the whole video found 0 black segments; render-log scan clean. Caption band every 0.25 s: ratio 0.929, hidden samples are 10.25 s (the intended hard cut into scene 2) and 49.50-52.75 s (the end card, which by the storyboard has no captions). Every other caption sample shows text, including through both transitions.

**Frames at mobile size** (contact sheet, 12 scene frames, both transitions every 0.1 s): illustrations end above the caption band in all five scenes (the bar in scene 3 is closest); the amber word is underlined and readable in colour and without it; the inactive words are clearly lighter than before.

**Independent critic** (a separate agent given only frames, brief, narration timing and the rubric; report saved as `critic-report.json` in the run folder and accepted by `python -m contentos.production.critic`: well-formed, verdict matches scores). Verdict **revise**: hook 8, concept 7, readability 6, composition 6, motion 7, continuity 6, av-sync 7 (not judged from stills), restraint 8; average 6.9; no hard failures. Its findings, which I have not all verified: small text in the scene 2-3 panels and rule cards; dead stage around 8-12 s and in the lower part of scenes 3 and 5; the scene 3 layout differs from the storyboard (stacked panes, no SAME COMPUTER label); the push-slide shows a visible seam and a near-empty incoming scene for 0.3-0.4 s; the blur-crossfade dips to a near-empty stage with briefly overlapping kicker text; the previous caption stays dimly on across both transitions; the handle is smaller than caption size (the storyboard asks for caption size) and the end card has a fourth element (the "YOUR AI BUDDY" line) that the storyboard's three-element card does not. It judged the channel name not seriously competing with the headline, the illustration/caption band clear, and the underline cue effective.

**Reading it.** Against the acceptance table: no illustration/caption-band overlap (met); active word distinguishable by colour and underline (met); no unintended hard cuts or black frames (met); hierarchy on mobile (mostly met; handle small and faint); critic: not met (revise, though no hard failure). Most revise points describe the episode's composition and storyboard fit, which the E2 refinements did not touch; they apply to the baseline and E as well. E2 remains a candidate, not approved. Not committed; not pushed.

## M. Ep3 E3 / E3b revision, Mac render and independent review (candidate, not approved)

M.1 What was changed (E2 preserved; E3 and E3b in `workspace/spike-design-library/ep3e3/` and `ep3e3b/`, git-ignored). E3: end card back to the storyboard's three elements ("YOUR AI BUDDY" removed, handle 62 px); larger scene 2, 3 and 5 text; panels arrive during the push-slide; blur cross-fade text hand-off without kicker overlap; scene 3 headline "SAME COMPUTER". E3b: scene 3 bar now two lines "SAME COMPUTER" / "DIFFERENT CAPABILITY" (40 px / 34 px at 1080 wide, bar bottom unchanged at y=1360, caption band top 1374); blur cross-fade timing tightened (outgoing text 0.10 s, incoming 0.05-0.13 s earlier).

M.2 Decisions recorded (user): scene 3 keeps the stacked panes as a deliberate deviation from the storyboard's side-by-side layout, for phone legibility, with the SAME COMPUTER label added to the bar; do not restore side-by-side if it makes the text too small. "YOUR AI BUDDY" stays removed from the end card; no storyboard amendment needed. Captions are a fixed root-level layer, so the previous caption staying on screen across a transition is treated as intentional.

M.3 Mac evidence (Apple M5 Pro). E3 `ep3e3/results/run-20261011-085437-u9lBvO`: check 0, render 0 (48 s), 0 black segments, push-slide blend (5 intermediate samples), blur blend (5), caption ratio 0.929. E3b `ep3e3b/results/run-20261011-085931-45ikdA`: check 0, render 0 (47 s), 0 black segments, push blend (5), blur blend (4), caption ratio 0.929. Frame check on the E3b render: the two-line bar is visible at 31.2 s and ends clear of the caption band; blur frames 40.9-41.5 s show content in every frame (no fully empty stage), but the blend is a dissolve with ghost content, not a carried-over element. Not claimed: any shader validation, any approval.

M.4 Independent review of E3b (fresh agent, frames + storyboard + rubric, no builder conclusions; `ep3e3b/results/run-20261011-085931-45ikdA/critic-report.json`, validated with `python -m contentos.production.critic`): verdict revise, scores 8/7/6/6/7/6/7/8 (same as E2), no hard failures. Resolved or confirmed: three-element end card present and readable; active caption word identifiable by amber and underline; no caption-band overlap. Still open: small monospace micro-labels (about 8-13 px at 540 wide) in scenes 1, 2, 4 and 5; large dead areas in the lower part of most scenes; broad storyboard deviations (scene 2 rail/tiles/lattice, scene 4 vertical list, scene 5 bubbles and layout, no pixel-burst carry-over, hook-to-scene-2 background change); hard push seam at 20.2 s; blur dissolve still shows ghosted chips lingering. The critic estimated the scene 3 bar text at ~9 px; the CSS sizes (40/34 px at 1080) are about 18/16 px at 540, so that estimate is likely low, but legibility at actual device size is unconfirmed on a phone.

M.5 Status and next step: E2 and E3b remain candidates; the style is not validated. Scores are unchanged and the remaining findings are broad layout and storyboard-fidelity issues, so per the standing decision the E-series stops here and the storyboard is to be reassessed instead of further tweaks. Objective checks (render, gate, captions) pass for both. Nothing committed or pushed.

## N. Track A caption-alignment correction: verification (2026-10-11)

N.1 Code path. `contentos/pipeline.py::s_compose` timed captions by a proportional index into the ASR list (`asr[int(k * n / len(toks))]`), so one ASR insertion, deletion or split shifted every later caption on that line. The working tree (uncommitted, from another session) replaces it with `pipeline.caption_words`, which calls the existing `production/align.py::align_words` (difflib sequence alignment, interpolation for unmatched words, monotonic output) and keeps the even-spacing fallback when ASR is unavailable. No second alignment system, no new dependency. `s_compose` is otherwise unchanged. Ep3's own `build_timings.py` already used `align_words`, so Ep3 renders were not affected; the defect was in the generic pipeline path.

N.2 Real-transcript comparison (Ep3 lines 1-6, whisper transcripts `audio/tx0N/transcript.json`, `before_after.json`). Lines 1, 2, 4, 5, 6: identical output under both methods (ASR word count equals script word count). Line 3: whisper split "spellchecker" into "spell"+"checker", so the old method mistimed 16 of 24 caption words (mean 0.43 s, max 1.11 s, all early); the aligned method matches the transcript onset exactly for every word it heard one-to-one (20 of 24; the split word is timed across both pieces).

N.3 Tests. New `tests/test_caption_alignment_real_take.py` (mine, untracked, 6 tests: real take onsets, split word, ordering with repeated A/a, trailing extra ASR word, leading ASR noise, and a guard that the old formula fails the same assertions). The other session's `tests/test_pipeline_captions.py` (6 tests) is untouched. All 12 pass on the working-tree `pipeline.py` and all 12 fail on the committed `pipeline.py` (no `caption_words`). Full suite on Python 3.13 in the cloud container: 368 passed, 10 skipped, 5 failed; the 5 are the baseline `test_core::test_local_beats_paid_even_when_both_healthy` plus `test_director` (2), `test_motion_catalogue` (1) and `test_storage::test_gitignore_blocks_media` (1), which need git metadata or vendored `.claude/skills` that the container export lacks. Py3.10 on the Mac VM still cannot import `pipeline.py` (3.12-only f-string; pre-existing).

N.4 Rendered before/after (cloud, software GPU, hyperframes 0.8.114, with the real audio). Both projects were produced by running the real `s_compose` on Ep3 line 3 twice, once with the old formula swapped in (`make_ba.py`); only the caption timings differ. Frames were sampled at 30 fps and the amber word located by pixel; word identity comes from a position map built from the AFTER render. Results (`analysis.json`, `track-a-before-after.png`): rendered onset of the highlight minus the transcript's onset, for 23 identifiable words: BEFORE mean 0.42 s, max 1.09 s, 15 words more than 150 ms off (all early, "Same" 1.09 s); AFTER mean 0.019 s, max 0.11 s, none above 150 ms. Frames where a word is lit: AFTER 285 of 285 show a word that is being spoken (+/-1.5 frames); BEFORE 56 of 301. The split word "spellchecker" is lit 0.09-1.19 s as expected in AFTER; in BEFORE "flags" lights at 0.57 s while the voice is still on "spellchecker". Repeated "a"/"A" (five occurrences) are lit at their own onsets in AFTER and drift by up to 0.82 s in BEFORE.

N.5 Audio cross-check. Whisper is the reference timing, so this is not an independent clock. ffmpeg silencedetect on the line-3 audio puts speech restarts at 2.45 s ("A"), 8.00 s ("Same") and 9.16 s ("a"), matching the transcript onsets (2.45, 7.99, 9.12) to within 0.04 s. At 4.41 s the silence ends but whisper has "can" at 4.30 s (0.11 s early). Whisper word ends are stretched across pauses (for example "mistake." to 2.42 s while the audio is silent from 1.93 s), so the highlight lingers through short pauses; that is existing behaviour of end-time based highlighting, not changed here.

N.6 Limits. One line from one episode was rendered; the other five lines produce identical timings under both methods. The render was made in the cloud container, not on the Mac: caption timing is DOM/GSAP-driven and does not depend on the GPU, but the Mac run (`track-a-captions/render-track-a-mac.sh`) has not been done and nothing here is Mac-validated. Very short words (under about 0.1 s, such as "A", "a", "write") flash for fewer than three frames; unchanged by this fix. The change and its tests are uncommitted and belong to the other session; nothing was committed or pushed.

## O. Roadmap Stage 1, G2: `timeline/1` in shadow mode (2026-10-11)

O.1 Status check before starting. Roadmap 07 Stage 0 is done as far as this work goes: G9 (Mac shader/transition run) was run (push-slide VALIDATED, `shader:sdf-iris` FAILED, 13 others PARTIAL; sections A-L) and G1 (Track A captions use `align_words`) is verified in a cloud render (section N; Mac render optional, not run). No `timeline/1` code or `timeline.json` existed in the repository before this section (searched source, tests, config and docs). 07 and 06 are untracked proposals and say no stage starts without approval; this work started on the owner's instruction to proceed with `timeline/1` in shadow mode.

O.2 What was added (new files only; `pipeline.py`, `align.py`, `sceneplan.py`, compose and every renderer are unchanged; nothing imports the new module). `contentos/production/timeline.py`: `build_timeline`, `build_from_project` (read-only over a project's existing `scene-plan.resolved.json`, `audio/timing.json`, `captions/word-timings.json`, `audio/txNN/transcript.json`), `validate` (word order, scene contiguity, words inside scenes, minimum-hold reported not squeezed, cue anchors, cues on interpolated words flagged, `timing_trust` cannot exceed `asr-derived-unverified` without verified anchors), `compare_legacy` (against the composition's `window.__T`), and a CLI `python -m contentos.production.timeline <project> [-o timeline.json]`. `tests/test_timeline_shadow.py`: 11 tests (10 synthetic plus 1 on the real Ep3 artifacts, skipped when the git-ignored workspace is absent). Both are untracked and uncommitted.

O.3 Results on Ep3 (read-only run, `workspace/experiments/timeline-shadow-001/ep3-timeline.json`, git-ignored): 130 words, 6 scenes, 24 cues; no validation issues; 415 values compared against `timings.js` with no differences; 128 words `matched` and 2 `span` ("spellchecker" heard as "spell"+"checker", "favourite" heard as "favorite"); match ratio 0.9846, WER 0.0231; `timing_trust` is `asr-derived-unverified`; audio rights `unassessed` (no rights vocabulary approved yet). The 11 new tests pass in the Py3.13 cloud container and on the Mac VM (Py3.10), alongside the 6 `align`/`sceneplan` tests.

O.4 What this does and does not show. The legacy comparison is a consistency check: `timings.js`, `word-timings.json` and the timeline all derive from the same alignment output, so agreement shows the container loses nothing, not that the timing is right. It does not demonstrate the roadmap's E1 benefit (better timing, survival of a +/-12 % re-time). "span" is an extension to the 06 spec's two source values (matched, interpolated), recorded in the module. Not built: cue resolution from word anchors with offsets (offset is fixed at 0.0), compose reading the timeline, supplied-audio ingest (G3), labelled sheets (G4), safe-zone check (G6).

O.5 Dependencies and acceptance for the next steps (from 07 section 3, thresholds still provisional and owner-confirmable). E1 needs an owner-owned 30-45 s voiceover and about 12 human-marked word onsets (without anchors timing accuracy is unmeasurable); go if median error <= 80 ms and p95 <= 160 ms, >= 90 % of cues within 2 frames, 0 manual edits after a +/-12 % re-time, and the baseline is >= 1.5x worse on median. Wiring `s_compose` to emit the shadow timeline touches `pipeline.py`, which carries the other session's uncommitted `caption_words` change, so it waits until that is committed or the owner assigns it.

## P. Timeline-labelled contact sheets (G4) — initial implementation

Status: INITIAL, on branch `feature/labelled-contact-sheets` (not merged). Isolated: `contentos/production/sheet.py` + `tests/test_sheet.py`; no `pipeline.py` change, no new renderer or dependency (ffmpeg `drawtext` only).

- Input: a video and a `timeline/1` JSON. Frames are taken just after each scene start, just before each scene end, and at each cue time plus a settle offset (default 0.15 s); points closer than 0.15 s merge.
- Each tile is labelled at its bottom-left with time, scene, the word being spoken (with its alignment source) and the cue text. Output: `sheet.png`, `sheet.json` (schema `sheet/1`, per-tile `label` and `label_full`), `frames/`.
- Fails closed if no font file or no `drawtext` is available, unless `--allow-unlabelled` is given (the manifest then says `labelled: false`).
- Evidence: 8 unit tests (one proves the label really darkens pixels and fails if labelling is skipped). A real 31-tile sheet was generated from the Ep3 E3b Mac render and the Ep3 timeline and inspected visually in the cloud container.
- Limits: label times come from the ASR-derived timeline (`timing_trust: asr-derived-unverified`), so they are review aids, not verified sync. Label placement was checked on the Ep3 portrait video only. It has not been run on the Mac.
