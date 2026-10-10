# 07 - The two guides vs. the contentos implementation (and Pilot 001)

Date: 2026-10-10. Method: read the actual code (`contentos/pipeline.py`, `qa.py`, `production/core.py`, `adapters/v1/scene-derivation.mjs`, `cli.py`) and compared it with the workflow in `02-guides-analysis.md`. "Verified" below means I read the code or ran it; nothing is assumed.

## Not adopted on purpose
- **Podcast guide step 2 (rip audio from a YouTube link via a converter site):** not implemented and not adopted. No audio-download code exists in the pipeline. `yt-dlp` is declared in `providers.yaml` and used by `competitor.py` for public-video metadata/transcripts (per its docstring), not for sourcing audio to re-animate.
- **Lyric guide with a third-party song:** not adopted. The lyric template may only take music we own, generate, or hold written permission for (recorded in the asset/rights ledger). Pilot 001 uses voice we synthesize locally (Kokoro) and a music bed we synthesize ourselves.
- The guides' anecdotal timings and sizes are not treated as facts; Pilot 001 measures its own.

## The eight principles

| # | Principle | Already in contentos (verified in code) | Missing before this change | Pilot 001 / small change made |
|---|-----------|------------------------------------------|----------------------------|-------------------------------|
| 1 | Transcription + accurate word/line timing | `pipeline.words_for()` runs whisper.cpp through `hyperframes transcribe`; per-line timings drive caption highlights | Script words were mapped onto ASR words by *proportional index*, so one inserted/dropped ASR word shifts every later caption; silent fallback to even spacing; no transcript-vs-script check | **Added `contentos/production/align.py`** (sequence alignment + WER). Pilot transcribes the whole narration once, aligns, stores `captions/word-timings.json` and the WER in the QA report |
| 2 | Timestamped storyboard mapping narration to scenes | `adapters/v1/scene-derivation.mjs` splits a storyboard into blocks; spec scripts carry per-line `headline`/`tag` | No scene plan with timestamps; scenes were one-per-script-line, not anchored to words; no storyboard document | **Added `contentos/production/sceneplan.py`**: scenes anchor to narration words, `resolve()` computes real times from the audio, `storyboard_md()` writes the storyboard from the resolved plan, so it cannot drift from the voice |
| 3 | Meaningful animated visual explanations (not captions over a static background) | Nothing: the current `s_compose` template is a headline plus word-highlighted caption over a gradient, which is exactly the pattern to avoid | Any diagram/animation primitive | Pilot builds an animated diagram per idea (agent, tools, your app, external system, request/result packets, loop). Per-video scene visuals live in the project's `src/`; shared pieces are the new modules |
| 4 | Narrative continuity, metaphors, transitions, camera movement | Opacity fade in/out between scenes only | Persistent actors across scenes, camera moves | Pilot keeps the same three actors on one stage for the whole video and moves a camera (scale/translate) to each idea; one visual metaphor (a request packet travelling out, a result returning) |
| 5 | Preview frames and visual inspection before the final render | `hyperframes lint` only | No frame generation step; nothing writes contact sheets; no check after render | **Added `contentos/production/preview.py` and `contentos preview`**: frames at exact times from a project (pre-render) or an MP4 (post-render) plus a contact sheet. Pilot inspects frames before rendering and again from the final MP4s |
| 6 | Iterative, timestamp-directed corrections; verify final MP4 | `qa.py` verifies the MP4 (ffprobe, resolution, fps, duration, EBU R128 loudness, peak, black frames, freezes); ledger records stage runs | No revision log of "at 0:12 do X" fixes; no versioned snapshot before big edits | Pilot keeps `qa/revisions.md` (timestamp, problem, fix, evidence) and a `src/` snapshot per iteration; final MP4s run through `qa.py` plus extra ffmpeg checks |
| 7 | Properly recomposed 16:9 and 9:16, readable captions, platform-safe layouts | A spec renders one aspect ratio; type scales with the short side; fixed bottom padding of 16% | No separate layout per format; no safe-zone constants; no check that captions fit | Pilot composes two layouts from the *same* scene plan and timings. 9:16: graphic top, captions in a lower-middle band clear of the platform UI. Safe zones are conservative heuristics, not published platform specs, and are flagged for manual check on a phone |
| 8 | Preserve source, scene plans, timing, assets, reusable templates | Per-content project directory, ledger, resumable stage artifacts, `manifest.json` | Word timings and scene plan not persisted; no per-project asset/licence manifest; no reusable explainer template | Pilot saves scene plan, word timings, generator source, both HyperFrames projects, asset/licence manifest and project manifest with SHA-256 hashes. The generator is documented as the reference template for the next explainer |

## What this pilot deliberately does not do
- It does not rewire the contentos stage engine (`STAGES`, resume, gates). The pilot runs on shared modules plus its own builder, and its outputs are registered as a normal project directory. Folding the explainer builder into `pipeline.py` as a stage is a follow-up once the pilot has been reviewed.
- No lip-synced host, no lyric workflow, no new dependency (numpy already lives in `~/.contentos/venv`; Kokoro, whisper.cpp, HyperFrames and ffmpeg are the existing components).

## Verification of the small changes
`~/.contentos/venv/bin/python -m pytest -q tests` -> 45 passed (39 baseline + 6 new in `tests/test_align_sceneplan.py`: exact match, ASR insertion, missing word, WER on wrong audio, scene anchors, bad anchor).

## Verified on Pilot 001 (evidence, 2026-10-10)
Project: `workspace/projects/pilot-001-agent-tool-use/`

| # | Principle | Evidence in the pilot | Status |
|---|---|---|---|
| 1 | Transcription and word timing | whisper.cpp transcript of the narration; `captions/word-timings.json` (135 words, 135/135 matched, WER 0.0); final-audio cross-correlation puts audio at +0.35 s = designed lead-in, corr 0.966 | Done. Residual: whisper word-boundary jitter, flagged for a human check |
| 2 | Timestamped storyboard mapped to narration | `src/scene-plan.json` (anchors are narration words) -> `storyboard/storyboard.md` generated from real audio times; 7 scenes, 3.6-11.2 s each | Done |
| 3 | Meaningful animated explanations | Animated agent / your-app / external-system diagram, request and result packets, tool list, JSON and terminal panels, id match, decision fork, loop ring; no static-caption scenes | Done |
| 4 | Continuity, metaphors, transitions, camera | Same three actors persist across scenes; packet travels out and back as the visual metaphor; per-scene camera push/pan/pull-back; cross-fades and slides between panels | Done (modest camera; more could be added) |
| 5 | Preview frames and inspection before rendering | `contentos preview`: 24 frames x 2 formats x 3 iterations in `preview/`, viewed and fixed (13 logged fixes), then frames pulled from the final MP4s | Done |
| 6 | Timestamp-directed corrections and final-MP4 verification | `qa/revisions.md` (time, problem, fix, evidence); `qa/QUALITY-REPORT.md` from ffprobe/ebur128/blackdetect/freezedetect/silencedetect on the final files | Done |
| 7 | Properly recomposed 16:9 and 9:16 | Two builders' geometry from one plan: different node layout (row vs column), packet lane, panel sequencing and slide, caption size and chunking (9 vs 5 words), safe-zone margins | Done. Safe zones are heuristics; check on a phone |
| 8 | Preserve source, plans, timing, assets, templates | `src/` (incl. `history/` builder versions), scene plan, word timings, both HyperFrames projects, `assets/`, `manifest.json` with SHA-256, asset/licence manifest | Done. The scene visuals are per-video; reusable parts live in `contentos/production/` |

Not adopted, as instructed: audio ripping from a YouTube link; unlicensed music for lyric videos.
