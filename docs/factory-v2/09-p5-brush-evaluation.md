# 09 — p5.brush evaluation for hand-drawn video scenes

Date: 2026-10-10 · Scope: research + isolated proof of concept only · Experiment: `workspace/experiments/p5brush-001/` (git-ignored)
(Note: an earlier brief named this file `08-p5-brush-evaluation.md`; the latest brief asks for `09-`, so `09-` is the one written.)

## 1. Executive verdict

**KEEP EXPERIMENTAL. Do not integrate into the ContentOS builder yet; do not reject.**

- p5.brush is real, MIT-licensed, small (77 KB standalone), has no network calls, and runs headless in the Chrome that HyperFrames already ships. It produces strokes that look genuinely hand-drawn (pressure-tapered pen, grainy charcoal, watercolour fills with bleed, hatch lines) in a way that native SVG with `feTurbulence` jitter does not.
- But in this PoC the *drawing-on*, camera, labels, transitions and audio sync all came from HyperFrames/GSAP masks in **both** variants. p5.brush changed only the **texture of the marks**. It cannot animate a stroke by itself in a frame-seekable way, it has no true alpha layers, and its pixels differ between GPU and software back-ends. So the honest advantage is "more authentic ink/paper texture", bought with a pre-render step, ~4× larger project assets and a back-end-pinning rule.
- Whether that texture is "meaningful enough" is a **human judgement that is still pending**: look at `sheets/ab-landscape.png` and the MP4 pairs (section 6). My own read is yes for a deliberate hand-drawn series or Shorts hooks, no as a default.

Recommended next step: wait for your review of the A/B; if you like it, build the small opt-in design in section 4 (not implemented here).

## 2. Verified findings (source-checked or tested; assumptions are labelled)

### Repository, version, licence
| Item | Finding | Basis |
|---|---|---|
| Upstream | `acamposuribe/p5.brush` | cloned and inspected |
| Version | npm **2.2.3** (published 2026-09-20); `main` package.json = 2.2.3; newest git tag is v2.2.2 (tag lags npm) | npm registry + repo |
| Licence | **MIT** (Copyright 2023-2026 Alejandro Campos Uribe); copy at `vendor/p5.brush.LICENSE.md` | LICENSE file |
| Bundle | `dist/brush.js` standalone, 77,522 bytes, **byte-identical to the npm 2.2.3 tarball** (sha256 `952c1853b7699e6052b9f53d917cd09ea7c35f79d9f5b25e8665a937c618caae`) | checksum |
| Dependencies | standalone bundles simplex-noise (MIT) and spectral.js colour mixing; needs only **WebGL2** | bundle inspection |
| Network/eval | static scan of bundle + src: no fetch/XHR/WebSocket/eval/URLs | grep scan |
| p5.js route | p5 2.x is **LGPL-2.1**. **Not tested** (not needed); standalone avoids that dependency | assumption, untested |
| README drift | README names brushes `marker2`, `hatch_brush`; 2.2.3 `brush.box()` actually lists pen, rotring, 2B, HB, 2H, cpencil, pastel, crayon, charcoal, spray, marker | tested |

Install scripts: none executed. The tarball was only unpacked (`_dl/`) and compared; the pinned file is loaded locally via `<script>` content, never from a CDN. Nothing installed globally.

### Capability tests (each was run, not assumed)
| Capability | Result | Evidence |
|---|---|---|
| WebGL2 in HyperFrames' headless Chrome (chrome-headless-shell 152) | **Works** on Metal (Apple M5 Pro) and SwiftShader software; auto mode falls back with a deprecation warning | `probe-*.json/png` |
| Brushes / fills | pen, rotring, charcoal, marker, crayon…; watercolour `fill` + `fillBleed`; flat `wash`; `hatch` with style/angle/rand | `poc/brush-catalog.png` |
| Deterministic output | same seed + same calls ⇒ **pixel-identical**, even after other draws, 16/16 snapshots, per back-end | `lab-stability-*.json`, `logs/repro-assets.json` |
| Same pixels across back-ends | **No.** Metal vs SwiftShader: only 4/16 snapshots bit-identical, PSNR ≈ 56.8 dB (visually indistinguishable, not byte-equal) ⇒ pin one back-end per project | `logs/verify-repro.out` |
| Progressive draw-on by re-rendering partial strokes | **No (prefix-unstable).** A longer stroke reshuffles ~96 % of ink pixels vs the shorter one | `lab-stability.mjs` |
| Frame seeking / animation clock | None built in: `brush` is an immediate-mode painter, not a timeline. "Seek to t" means: pre-draw once, then reveal with the host renderer | tested |
| Transparent background | **Not a true alpha layer**: `clear()` yields invalid premultiplied white, drawn pixels get binary alpha with colour baked toward white; difference-matting shifts washes' hue | `lab-alpha*`, `lab-matte*` |
| Resolution / aspect | Any canvas size; 16:9 (1920×1080) and 9:16 (1080×1920) both done at 1.5× super-sampling (2880×1620 / 1620×2880) | manifests |
| Headless automation | puppeteer-core (already a HyperFrames dependency), `preserveDrawingBuffer:true`, PNG via 2-D canvas copy | `poc/render-assets.mjs` |

Consequence that shaped the architecture: render on the **real paper colour** as cumulative "painter" snapshots (one seed per element), then reveal each snapshot with an SVG path mask animated by GSAP. HyperFrames stays the renderer and timeline owner; the HyperFrames render stage never touches WebGL, only PNGs + SVG.

## 3. Use-case suitability

Ratings reflect what was actually shown (one explainer-style scene) plus reasoning; "unproven" means not tested here.

| Use case | Rating | Why / where something simpler wins |
|---|---|---|
| AI & technical explainers (agent loops, server/network diagrams, arrows, callouts) | **Medium–high** | The tested case. Pen arrows, charcoal boxes, hatched fills read as a deliberate sketchbook style and differ visibly from the SVG control. Plain SVG/CSS is simpler and cleaner for *precise* diagrams, tables, code and anything with text; keep all text in HTML. Use p5.brush only for the marks. |
| Documentaries & stories (sketchbook scenes, maps, objects) | **Medium / unproven** | Texture fits, but the ink-fill and wash behaviour (no alpha, pigment mixing) makes layered illustration harder; story illustration would likely want hand-made raster art or a purpose-built paint tool. Not tested beyond one diagram. |
| Podcast explainers (drawn annotations timed to speech) | **Medium** | Cue sync works (section 8) because the reveal mask is driven by word timings, which exist already (`align`). Annotations are small, so the texture benefit is modest; an SVG underline/circle with a displacement filter is often enough. |
| Music / lyric videos (ink, textured abstract, watercolour backgrounds) | **Unproven** | Watercolour fills and washes are p5.brush's strength, but I tested none of lyric accents, long loops or audio-reactive visuals; the no-alpha and heavy-snapshot constraints matter more for 3–4 minute pieces. |
| YouTube Shorts (hand-drawn hook, transition) | **Medium–high** | A 9.6 s sample rendered cleanly in 9:16; the vermilion brush-wipe transition worked and is a distinctive hook. Cheap to ship as a one-off, because only a few snapshots are needed. |

Where simpler tools win: precise diagrams and text (SVG/HTML), solid colour blocks/wipes (CSS/SVG — the transition bands here are flat `wash` fills, i.e. nothing a CSS clip-path couldn't do), stock/photo imagery (existing assets), and any scene that has to be re-timed often (p5.brush assets are pre-baked, so changing layout means regenerating snapshots). It should **never** be a house style applied to every scene.

## 4. Recommended architecture and integration point (design only — not implemented)

**p5.brush is a specialist asset generator, not a renderer.** HyperFrames remains the renderer, timeline owner and the only thing that produces the MP4.

```
storyboard scene { treatment: "handdrawn", preset, seed }     (explicit opt-in; default = off)
   └─ spec compiler  (nodes/arrows/labels -> ops + reveal paths + word-timed cues)   <- reuse contentos align/sceneplan timings
        └─ asset generator (node + puppeteer-core + pinned brush-2.2.3.js, one pinned back-end)
             -> cumulative PNG snapshots + manifest {brush version, back-end, seed, sha256}   (cached by spec hash)
        └─ HyperFrames fragment: <image> snapshots + <mask> reveal paths (GSAP, 1000-unit path length), labels as HTML text, camera on #stage
   fallback: WebGL2/browser unavailable, asset step fails, or treatment off  ->  native SVG treatment (the control used here)
```

Proposed home: an optional module beside the existing production helpers (e.g. `contentos/production/handdrawn/`), selected per scene; presets = brush/colour/weight tables (this PoC's palette and pen/charcoal/rotring choices are the first preset). Guards: opt-in flag, no auto-application, deterministic inputs recorded in the manifest, aspect-aware spec (landscape and portrait are *separate* specs — positions differ), preview through the existing `contentos preview`, tests for spec determinism, mask generation, disabled-by-default and fallback. The ordinary pipeline is untouched when the flag is absent. Because the HyperFrames stage consumes only PNG + SVG, WebGL2 is needed solely at asset-generation time, not on the render machine.

## 5. Proof of concept

Source: `workspace/experiments/p5brush-001/poc/` (`spec.mjs`, `render-assets.mjs`, `build-hf.mjs`; `run-all.sh` reproduces everything offline in ~3 minutes).

The 9.6 s scene, "the model asks, the app runs", uses the first 9.6 s of Pilot 001's narration (copied, original untouched; cues from its word timings):
1. **Ink stroke drawing itself** — a tapering pen swash on the word "your".
2. **Technical illustration** — charcoal "model" box with watercolour fill and a hatched teal "tool" circle, joined by an ink "asks" arrow and a vermilion "result" arrow with spark marks (varied weights: pen 2.0–2.4, charcoal 1.0, rotring hatch 1.6).
3. **Textured/hatched shape + composition change** — a slow push-in (1.10×) on the loop, held, then released inside the transition.
4. **Explainer transition** — three tilted vermilion brush bands wipe in, then clean-paper bands wipe them out (a "chain restart" so scene 2 is drawn on fresh paper).
5. **Final composition** — hand-drawn sun with rays, "72°F" with a vermilion underline and check, caption "the app ran it". Palette: paper `#f4efe4`, ink `#1b2a3a`, vermilion `#c8452d`, ochre, teal; generous negative space.

Both variants share **the same spec, reveal masks, camera moves, labels (Outfit), audio and timings**; only the marks differ:
- **A (control, `svg`)**: native SVG — seeded jitter polylines, `feTurbulence`+`feDisplacementMap` wobble, clip-path hatching, blurred displaced washes.
- **B (`brush`)**: p5.brush snapshots (16 landscape / 17 portrait elements, one seed each) revealed through the same masks.

## 6. Outputs (all under `workspace/experiments/p5brush-001/`)

| What | Path |
|---|---|
| Landscape MP4 A / B | `renders/svg-landscape.mp4`, `renders/brush-landscape.mp4` (1920×1080, 30 fps, 9.6 s, 288 frames, AAC audio) |
| Portrait MP4 A / B | `renders/svg-portrait.mp4`, `renders/brush-portrait.mp4` (1080×1920, 30 fps, 9.6 s) |
| A/B contact sheets (pairs side by side: A, B) | `sheets/ab-landscape.png`, `sheets/ab-portrait.png` |
| Timelines (12 frames each) | `sheets/timeline-{svg,brush}-{landscape,portrait}.png` |
| Draw-on detail (stroke growing frame by frame) | `sheets/drawon-{svg,brush}-landscape.png` |
| Representative stills | `frames/{svg,brush}-{landscape,portrait}-t{1.6,3.4,5.0,6.3,7.0,7.5,8.5,9.4}.png` |
| p5.brush snapshots + manifests | `out/{landscape,portrait}/` (`manifest.json` has sha256, ms, bytes, renderer string) |
| Capability labs | `probe*.png/json`, `lab-*.png/json`, `poc/brush-catalog.png` |

## 7. A/B comparison (control A = native SVG, experiment B = p5.brush)

**Verdict on visual preference: pending your review.** What I can state from the evidence:

| Dimension | A: native SVG | B: p5.brush | Evidence |
|---|---|---|---|
| Authenticity of the hand-drawn look | Reads as "vector with wobble": uniform stroke width, zig-zag jitter on short rays, flat fills | Clearly more authentic: tapered pen, grainy charcoal outline, watercolour fill with bleed and paper-white variation, ruled hatching | `sheets/closeup-landscape-t5.0.png` (A top, B bottom) |
| Animation quality | Draw-on by mask, same timing | Same mask, same timing — **no difference** (the animation is the host renderer's) | `sheets/drawon-*.png` |
| Motion supports narration | Yes | Yes (identical) | cue sync, section 8 |
| Phone readability (360 px wide) | Bolder, higher contrast; flat fills carry colour | Thinner pen lines and paler watercolour fills lose some punch; the teal fill under the hatching is effectively invisible; needs heavier weights/saturation tuning | `sheets/phone-portrait-t5.0.png` |
| Like-for-like caveat | — | B's fills are paler than A's by nature of spectral pigment mixing, so colour weight is not identical between variants | same |
| Integration complexity | One generator, no extra step | Extra pre-render step (puppeteer + WebGL2), snapshot cache, back-end pinning, per-aspect specs | `poc/` |
| Project size | 2.3 MB per aspect | **~8.9–9.5 MB** per aspect (16–17 full-frame PNGs ≈ 6.0–6.6 MB) | `du`, manifests |
| Output MP4 size | 1.98 / 2.09 MB | 2.64 / 2.67 MB | ffprobe/stat |
| HyperFrames render time | ≈10 s (idle) | ≈10 s (idle) — no measurable difference; loaded-machine runs ranged 10–40 s for *both* | `logs/render-timing.txt` |
| Peak memory (render) | ≈0.76 GB | ≈1.06–1.13 GB (+~0.3–0.35 GB) | `/usr/bin/time -l` logs |
| Asset generation | none | 1.0–1.3 s on Metal; 6–20 s on SwiftShader depending on machine load (3 runs each) | `logs/asset-timing.txt` |
| Reliability / reproducibility | HyperFrames re-render identical | HyperFrames re-render **identical (288/288 frames)**; snapshots identical per back-end, **not** across back-ends | `logs/verify-repro.out` |
| Maintenance | Nothing external | Pinned third-party lib (MIT, single maintainer, README drift, tag lags npm) + WebGL2 dependency | section 2 |
| Fallback | n/a | Fall back to A when WebGL2/browser is unavailable (design in section 4) | design only |

Is the improvement meaningful enough? The texture difference is **obvious without reading code**, and is exactly what a hand-drawn series would want. It is, however, a *texture* upgrade on top of host-driven animation, at the price of heavier assets, an extra step and a pinned back-end. That trade is worth making per-series by choice, not as a default.

## 8. Test results and measured resource use

All measured on the actual MP4s / outputs, not on source.

| Check | Result |
|---|---|
| `hyperframes lint` / `check` (4 projects) | Lint 0 errors, 0 warnings on all four; contrast 11/11 AA; "Check passed" on all four. B: 0 layout warnings. A: 7–8 layout `container_overflow` warnings because the SVG wipe bands intentionally extend past the canvas (cosmetic, passes). Lint first warned about un-baselined `fromTo` camera tweens; fixed with `immediateRender:false` |
| Dimensions / fps / duration | landscape 1920×1080, portrait 1080×1920; 30 fps; 288 frames; 9.6 s; h264 yuv420p bt709; AAC audio 9.6 s (ffprobe) — all four renders |
| Blank/frozen stretches | no black frames (`blackdetect`); `freezedetect` (very sensitive, −60 dB) flags only 0–0.97 s (blank paper until the first word, then a thin opening stroke) and a 0.67 s hold at 1.6 s between "model" and "tool" — both narration-driven, not glitches |
| Animation actually animates | verified after a real bug (below); stroke grows frame by frame in `drawon-*.png` |
| Cue sync (first ink in an element's region vs word time, measured in the MP4) | swash +33 ms, model +37 ms, tool +23 ms, ask +40 ms, final sun +33 ms: within **1 frame** (33 ms) for both variants and both aspects. "Underline" reads −100 ms only because its region overlaps the "72°F" label fading in earlier (label, not stroke) |
| Repeatability — snapshots | 16/16 identical, run-to-run, SwiftShader; Metal vs SwiftShader 4/16 identical, PSNR 56.8 dB |
| Repeatability — HyperFrames render | brush-landscape rendered twice: **288/288 frames identical**, PSNR ∞ |
| Back-end speed | Metal ≈1.0–1.3 s vs SwiftShader 6.0–20 s for all snapshots (CPU-bound, load-sensitive) |
| Memory | JS heap 2–3 MB during generation; render peak RSS ≈0.76 GB (A) vs ≈1.06–1.13 GB (B) |
| CPU/GPU | HyperFrames auto mode used Metal for the page; p5.brush runs on either, at least 3× faster on GPU |
| Ordinary pipeline without the capability | Nothing in contentos/tests references the experiment; no tracked file was edited by this task. Pilot 001: **0 files modified** (checked by mtime against the start of this task; 286 files incl. 3 Finder `.DS_Store`, i.e. the 283 real files from the audit are unchanged). `motion-ab-001`: 0 files modified |
| Production tests | None added: **no production code was written** (evaluation only, per brief). Existing suite re-run after the experiment: `~/.contentos/venv/bin/python -m pytest tests` → **66 passed** (same as the previous audit) |

**Bug found by inspecting the render (worth remembering for any HyperFrames draw-on):** GSAP rounds `stroke-dashoffset` to whole pixels, so a normalised `pathLength="1"` with offsets 1→0 produced a *pop*, not a draw-on — lint and check both passed. Fix: `pathLength="1000"`, dasharray `1000 2000`, offsets 1000→0. Also: an SVG filter on a mask path was clipped to the path's thin bounding box, shrinking transition bands to lines; fixed with `filterUnits="userSpaceOnUse"`. Both were found only by looking at frames.

## 9. Limitations and unresolved risks

- **Visual verdict unreviewed by a human** (me judging is not enough). One 9.6 s scene, one palette, one style.
- No native animation: p5.brush strokes cannot be grown by redrawing (not prefix-stable); all motion is a mask in the host renderer. A live-canvas mode (WebGL inside the HyperFrames page, seeked via its adapter events) was **not tested** and would also tie rendering to a GPU back-end.
- No true transparency; layered compositing means cumulative snapshots, so editing one element invalidates later ones.
- Pixel output depends on back-end (Metal vs SwiftShader) — fine visually, not byte-reproducible across machines; pin the back-end and record it in the manifest.
- Weight/saturation tuning is needed for phone readability; watercolour bleed can spill past outlines.
- Snapshots are large (6+ MB per aspect for 16 elements); a longer video needs a budget and cache cleanup.
- Single-maintainer library with README drift; behaviour may change between versions — pin and re-verify on upgrade.
- Not tested: p5.js 2.x + p5.brush route; Hindi/Odia text (text stays HTML here, so likely unaffected); long durations; music-video use.
- Machine load during measurement (load average 17–36 from other apps) made single timings unreliable; conclusions use repeated runs and ranges.

## 10. Files changed and dependencies added

**Tracked repository files changed: none.** `git status` before and after: the same 17 pre-existing uncommitted entries (no remote configured). Nothing committed, pushed, stashed or reset.

New (untracked) by this task:
- `docs/factory-v2/09-p5-brush-evaluation.md` (this report)
- `workspace/experiments/p5brush-001/**` (git-ignored; see its `README.md` for the layout and `FILES.md` for the list)

Dependencies added: **none** to the repo, `package.json`, lockfiles, or global tools. The pinned upstream build lives inside the experiment (`vendor/brush-2.2.3.js`, MIT). Puppeteer-core and the Chrome headless shell are the ones HyperFrames 0.8.114 already ships. A scratch clone/tarball was examined in a cloud sandbox and `_dl/` on the Mac; neither is part of the project.

Not touched: Pilot 001, `motion-ab-001`, global skills / the `~/.claude/skills` symlink, ContentOS builder, default renderer. Nothing uploaded or published; no paid or network service used at render time.

## 11. Recommended next engineering step

1. You review `sheets/ab-*.png` and the four MP4s.
2. If B is worth it: implement the opt-in design in section 4 as a small module with tests (spec determinism, mask generation, fallback to SVG, disabled-by-default), after tuning a "phone-safe" preset (heavier pen, more saturated fills).
3. If not: archive the experiment; the SVG treatment plus the draw-on pattern (including the GSAP rounding fix above) is the cheap win and could be adopted on its own.

## 12. Decisions needed from the owner

- Judge the visual difference: is B's texture worth heavier assets and a pre-render step? (Verdict stays "pending review" until you answer.)
- If yes: approve building the optional module (nothing is built yet), and whether a GPU back-end (Metal) or software (SwiftShader) should be pinned for reproducibility.
- Unchanged carry-overs from earlier phases, still awaiting you: A/B review of `motion-ab-001`, approval to repair the `~/.claude/skills` symlink, and approval to fold motion rules into the builder. I have not touched any of them.
