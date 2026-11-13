# Standalone assessment (2026-11-11, branch `feat/standalone-acceptance`)

Evidence labels: **[ran]** executed this session, **[read]** read in code/docs, **[not verified]**.
CEH was not installed, imported or consulted by any step below. This branch sits on `016b5a5`, which includes the B1 merge, so
`contentos/ceh_catalog.py` and `contentos/ceh_contract.py` now exist (opt-in, disabled by default). [ran] `grep -rn "import.*ceh"`
over `contentos/` and `tests/` shows only `ceh_catalog` importing `ceh_contract`, plus the CEH tests: nothing in the pipeline, CLI or
scenekit imports them. Standalone mode is the default and the only mode any stage here used.

## 1. Capability assessment (idea to export)

| Stage | Standalone state | Evidence |
|---|---|---|
| Idea / brief | works (spec YAML; research needs `last30days`, keyless) | [ran] `brief` OK |
| Script | agent-written (no local LLM: `ollama` absent); lint + gate work | [ran] `script` OK, gate blocked until approved |
| Storyboard / scene plan | one scene per line; `visual:` stat/steps/diagram/compare/code. Track B `sceneplan/1` not consumed by builder | [read] |
| Assets | none generated; typography/shape visuals only; asset library indexes supplied media | [read] |
| Voice | Hindi via Chatterbox on MLX works; English Kokoro works | [ran] 54.7 s for 6 lines |
| Motion graphics | GSAP + CSS + SVG bars/steps via scenekit | [ran] |
| Composition / render | HyperFrames 0.8.114, 1080x1920/30 fps | [ran] render 29-36 s |
| QA | 9 ffprobe/ffmpeg checks; frozen-frame WARN expected | [ran] |
| Export | validated sidecar in `ready/`; publish is a dry run | [ran] |

Verdict: **a complete short can be made standalone today**. It is typographic, not cinematic. Weakest links: Hindi narration is
`experimental` (no fluent listener), no imagery/character/footage generation, no local script-writing model, a chosen look still does not
change frames (ROADMAP P1-1).

## 2. Acceptance video [ran]

Spec `examples/finance/sip-small-savings-hi.yaml`, job `sample-fin-sip-hi-001`, Hindi (Devanagari), 6 scenes, 38.3 s, 9:16.
Subject: Rs5000/month for 10 years. Numbers are labelled illustrative (arithmetic checked: 5000 x 120 = 6,00,000; FV at 1 %/month = 11.50 lakh).
Disclaimer line "no guarantee" is in the script. Owner granted gates 1 and 2 for this sample id only; nothing published.

- MP4: `~/Desktop/VideoFactory-Workspace/experiments/standalone-samples/5000__sample-fin-sip-hi-001.mp4` (3.9 MB, moved out of `ready/`), `.publish.json` beside it.
  [ran, 2026-11-11 close-out] `find ~/Desktop/Video-Publishing/ready -name '*sample-fin-sip*'` returns nothing, so the scheduler cannot claim it. Do not move it back.
- Job dir: `~/Desktop/VideoFactory-Workspace/jobs/2026/11/11/sample-fin-sip-hi-001/`.
- Stage times: voice 54.7 s, compose 6.6 s, render 29.3 s, qa 1.0 s, export 1.2 s. Whole run well under 2 minutes after voice.
- QA: 8 PASS, 1 WARN (`frozen_frames` 4 segments >3 s: static text slides, expected). 1080x1920, 30 fps, AAC 48 kHz stereo, -11.5 LUFS, peak -1.3 dBFS, 0 black frames.
- ASR round trip (whisper large-v3-turbo) on lines 2 and 3 returns the same sentence with minor matra spelling drift and correct numbers. This
  shows intelligibility to a machine, **not naturalness**. No human has listened. Hindi stays `experimental`.
- Human audio review: **not done**. Visual acceptance: **not complete**, only the engineer's inspection of 7 frames; no independent critic run.
- Frames inspected at 7 timestamps (phone-size contact sheet). Devanagari conjuncts and matras correct, nothing clipped, caption word highlight works.

Defects found by inspection and fixed in this branch (`contentos/scenekit/compose.py`, `primitives.py`, `tests/test_scenekit.py`):
1. Bar value "11.5 लाख" wrapped onto two lines. Value column widened and `white-space:nowrap`.
2. The chart footnote was hard-coded English in a Hindi video. Optional `note:` on a stat overrides it (default unchanged).
3. Bar labels and footnote were small at phone size. Font bumped (.034 to .038 U, .026 to .03 U).

Defects seen and **not** fixed (honest list):
- Scene 4 shows a large decorative "04 / scene 4 of 6" in English with no content (filler, not meaning). Root cause: the `split` branch of
  `contentos/scenekit/compose.py` hard-codes `scene {i} of {n}`. Scenes 1 and 6 leave a big empty middle band: text-only scenes (`no-stage`)
  have nothing to put there. Both confirmed by re-reading the contact sheet at close-out.
- No imagery, no character, no real motion graphic beyond bars/steps: visually a typographic slideshow. Needs P1-1 (looks) and an asset/illustration path.
- The legacy step list showed 2 of 3 steps at 32 s in one sample frame (animation still in progress; not confirmed as a bug).

## 3. TTS and language matrix

| Lang | Engine / model | Runtime | Latency (this Mac) | Offline | Licence | Quality | Status |
|---|---|---|---|---|---|---|---|
| English | Kokoro via `hyperframes tts`, `af_heart` | ~1 GB, seconds | 2.7-3.6 s per line | yes | Apache-2.0 | baseline, kept | production |
| Hindi | Chatterbox multilingual v3 on MLX (`mlx-audio 0.6.4`) | 2.7 GB weights, ~4.6 GB peak | 54.7 s for 6 lines (38 s audio) | yes | MIT (tokenizer conversion licence undeclared) | ASR round trip good; **no human review** | experimental |
| Hinglish | same, Devanagari script with Latin terms, 23-term lexicon | same | ~35 s/job | yes | same | **not re-run this session** | experimental |
| Odia | Indic Parler blocked (gated HF model + torch venv) | n/a | n/a | n/a | n/a | none | blocked |

`lang doctor` [ran]: en, hi, hi-en READY; or NOT READY (`backend_blocked`, `asr_model_missing`). Not evaluated this session: Indic Parler,
rumik-oss, ElevenLabs (paid, off), IndicF5. Provider abstraction exists (`contentos/lang/`, doctor selects among kokoro/chatterbox/elevenlabs).
Voice is a synthetic reference, no real person.

## 4. HyperFrames and rendering audit

[ran] pin 0.8.114 resolves via `npx --no-install`; render 30-36 s for a 38 s 1080x1920 short on M5 Pro (about 1x realtime). Lanes: `hyperframes`
(default, tested), `remotion` (gated on `~/.contentos/remotion`, not run), `mpt` (Docker not running, not run). Typography with Devanagari is correct
via system fonts. Safe zones: composer 460/190 px only with `captions_hook`, else 307 px bottom (docs drift item P1-9). No upgrade or migration
is justified: no demonstrated gap in HyperFrames itself. The gap is in what the builder feeds it (looks, scene plans).

## 5. Motion graphics recommendation

Small coherent system, no new engine: **GSAP + CSS + inline SVG on HyperFrames** (already integrated and deterministic). Add **Lottie**
only for pre-made icon/character loops via `lottie-web` seeked by the GSAP timeline, if a real request needs it (ROADMAP P2-3, [not verified] here).
**p5.js/p5.brush**: skip unless a generative-art look is demanded; canvas determinism needs seek-safe wrapping. FFmpeg stays for post (loudness, concat).
Do not add Remotion beyond the existing lane.

## 6. Creator Studio audit

[ran] `./contentos.sh dashboard` serves `/api/v1/jobs`: 70 jobs listed, the new job shows `state: EXPORTED`, `hasVideo: true`. [read] working: jobs, approvals,
run/resume, previews, logs, export, queue. Not done in the UI: script/storyboard editing, asset manager, voice/language/motion configuration, cancel. So a
user can inspect and gate a job but **cannot yet author one** without YAML. Keep vanilla ES modules; no framework justified. Browser E2E (Playwright)
was not run this session.

## 7. Capability inventory

| Class | Items |
|---|---|
| Native (repo code) | pipeline + gates, scenekit, HyperFrames lane, lang router (Kokoro/Chatterbox), QA, export, asset index, looks/videojob data, Studio, queue/worker |
| Existing local skills | `.claude/skills`: orchestrator, director, motion-craft, visual-qa, create-video family; vendored 79 recipes in `contentos/skills/library/` |
| External tool integration | HyperFrames, ffmpeg, whisper.cpp, mlx-audio, Remotion (optional), MoneyPrinterTurbo (optional) |
| Optional CEH | none consumed. Consumer branch `codex/ceh-catalog-consumer` metadata-only, unmerged, disabled |
| Research-only | Lottie, p5.brush, IndicF5, Indic Parler, rumik-oss |
| Missing | image/illustration generation, local script LLM, talking-head editor, lyric engine, thumbnails, uploader, Odia, reference URL download (`yt-dlp` x86 broken) |

No second registry was created; `docs/SKILLS_INVENTORY.md` remains the one inventory. `mad-poke` and `potato-agent` skills do not exist on this Mac.

## 8. Prioritized next milestones

1. **P1-1 make a look change frames** (also fixes the dead-looking scenes 1, 4, 6 seen above). Acceptance in ROADMAP.
2. **Scene visual richness without new engine**: remove English "NN scene N of M" ornament for non-English, add a meaning-carrying icon/illustration slot (SVG).
3. **P1-5 Hindi human review**: one fixed benchmark set for a fluent listener; only then lift `experimental`.
4. **P0-6/P0-7 export contract** (decision needed).
5. **Studio authoring**: new-job form with script/storyboard editing writing the same spec YAML.
6. Local script model decision (Ollama `qwen3:8b` is the doctor's suggestion; approval needed to install).

## 9. Changed files and test evidence (uncommitted on `feat/standalone-acceptance`)

`contentos/scenekit/compose.py`, `contentos/scenekit/primitives.py`, `tests/test_scenekit.py`, `examples/finance/sip-small-savings-hi.yaml`,
`docs/STANDALONE_ASSESSMENT.md`, `AGENT_HANDOVER.md`, `SESSION_LOG.md`, `docs/P1-1_LOOK_PROPOSAL.md`. (Plus the other workstream's `docs/integrations/*`.)

Tests [ran]: baseline before any edit 1084 passed / 8 skipped. **After the last code edit** (the chart CSS, the `note:` footnote override and
its test `test_stat_footer_note_overrides_default_for_non_english_videos`) the full suite
`~/.contentos/venv/bin/python -m pytest tests` gave **1085 passed, 8 skipped in 148.64 s** (log `/tmp/vf-pytest2.log`, read again at close-out).
The +1 is the new footnote test. The Node suite was not run this session.

Not run this session: Hinglish, Remotion lane, MPT lane, Playwright browser E2E of Studio, any human listening, an independent visual critic.
