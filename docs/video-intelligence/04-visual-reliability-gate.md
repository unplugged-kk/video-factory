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

It takes roughly 1-2 minutes on the M5 Pro (the sampler rendered in 14 s). **Return** the whole new folder `workspace/spike-design-library/mac-experiment/results/run-<timestamp>-<id>/` except the `.mp4` files: `environment.txt`, `SUMMARY.txt`, `SUMMARY.json`, `*.summary.txt`, `*.render.log`, `*.check.log`, `*.gate-*.json`, and the small PNGs.

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
