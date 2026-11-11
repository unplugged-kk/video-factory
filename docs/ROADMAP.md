# Roadmap

Single authoritative roadmap, reconciled 2026-11-11 against the code, the historical plans in
`docs/factory-v2/`, `docs/video-intelligence/`, `docs/research/` and `docs/ui-discovery/`, and the recovered
generic-video work. Historical documents remain as evidence; this file decides what happens next.

**Destination:** a reliable local-first factory where one request (topic, script, reference, audio, song or
footage) becomes one checked video in a chosen look and language, with human gates before voice, render and
publish — without rebuilding the engine per content category.

**How to use this file.** Each ticket is independently executable. A ticket is done only when its acceptance
criteria and tests pass and the evidence is recorded. Wayfinder is installed but no issue tracker is
configured, so this file is the tracker of record (see `docs/SKILLS_INVENTORY.md` §7). Do not create a second
planning system.

Status: `DONE` (in this recovery), `OPEN`, `BLOCKED` (needs owner/decision).

---

## P0 — correctness, safety, trust

### P0-1 — A blocked gate must never delete the reviewed artifact
- **Status:** DONE (commit in this mission).
- **Problem:** `pipeline._stages` ran the gate check inside the same `try` whose handler unlinks the stage
  sentinel. `--force` on an edited script could delete the previously approved `audio/01.wav` even though no
  stage ran.
- **Files:** `contentos/pipeline.py`, `tests/test_approval_binding.py`.
- **Acceptance:** a `Blocked` gate records `BLOCKED`, does not call the stage, and leaves the existing
  sentinel byte-identical. A regression test pins it.
- **Tests:** `pytest tests/test_approval_binding.py`.

### P0-2 — A partial model download must not read as ready
- **Status:** DONE.
- **Problem:** `models--.../` exists as soon as a Hugging Face download starts, so Hindi reported READY and
  failed later at model load.
- **Fix:** `tts.weights_cached` rejects `*.incomplete` blobs and an empty `snapshots/`; `setup` uses the same
  check. ASR readiness now uses one `MIN_ASR_BYTES` rule everywhere.
- **Files:** `contentos/lang/tts.py`, `contentos/lang/setup.py`, `contentos/lang/config.py`,
  `contentos/lang/__main__.py`, `contentos/lang/capabilities.py`, `contentos/lang/asr.py`,
  `tests/test_lang.py`.

### P0-3 — Resume must not drop a WAV without metadata
- **Status:** DONE.
- **Problem:** if `NN.wav` existed but `NN.tts.json` did not, `synthesize_lines` skipped regeneration and
  omitted the line from its result, so `_voice_multilingual` could index an empty list.
- **Fix:** a WAV without metadata is treated as half-finished and regenerated.
- **Tests:** `tests/test_lang.py::test_a_wav_without_metadata_is_regenerated_on_resume`.

### P0-4 — Studio must not lie about stage state
- **Status:** DONE.
- **Problems:** logs opened on `script` because `job.stages` is an array, not a map; timeline read
  `duration` while the API sends `seconds`; storage rows read `name`/`kind` while the API sends `label`;
  the polling fallback could multiply after an in-place refresh.
- **Fix:** `state.defaultLogStage`, `timeline` seconds, storage label, and a per-render watch token.
- **Tests:** `contentos/ui/state.test.mjs`, `tests/test_ui_api.py`.

### P0-5 — Remotion lane must not install or hang
- **Status:** DONE.
- **Fix:** `npx --no-install remotion`, 1800 s timeout, explicit timeout error; language routed to ASR.
- **Files:** `contentos/renderers/remotion.py`, `tests/test_renderers.py`.

### P0-6 — Decide the Track A export contract
- **Status:** OPEN.
- **Problem:** `--only export` can export a video that never passed the `qa` stage; export's own
  `finalcheck` still runs. `tests/test_pipeline_export.py` currently pins "Track A export needs no approvals".
- **Decision needed:** either (a) require `qa.json` with no `FAIL` before export, or (b) add an explicit
  `--force-unvalidated` that records the override in the manifest and sidecar. Do not silently weaken the
  existing test; change it with the decision.
- **Files:** `contentos/pipeline.py`, `contentos/export.py`, `tests/test_pipeline_export.py`,
  `docs/STORAGE.md`.
- **Acceptance:** an exported Track A job always has a recorded validation state; an unvalidated export is
  impossible without an explicit, logged override.
- **Tests:** export with no `qa.json` is refused (or logs the override); export with a PASS is unchanged;
  sidecar records the decision.

### P0-7 — Bind Track B export approvals to the current video
- **Status:** OPEN.
- **Problem:** `export_job` uses `ledger.approved` (existence) for Track B, not `check_gate` with the current
  digest.
- **Files:** `contentos/export.py`, `contentos/track_b.py`, `tests/test_job_register.py`.
- **Acceptance:** changing `video.mp4` after approval requires a fresh approval; legacy unbound grants still
  pass with a warning.
- **Tests:** edit the video, re-export -> `ExportRefused`; re-approve -> export succeeds.

### P0-8 — Resolve `RESEARCH_APPROVED`
- **Status:** OPEN (decision).
- **Problem:** the gate is written by `--approve-private` and displayed in the old dashboard, but no code
  reads it. `docs/HOW_IT_WORKS.md` now says brief has no gate.
- **Options:** remove it from grants/UI, or enforce it before `script` when a research dossier is present.
- **Files:** `contentos/pipeline.py`, `contentos/cli.py`, `contentos/dashboard.html`,
  `docs/HOW_IT_WORKS.md`.
- **Acceptance:** one answer only; docs and code agree; no dead gate in the UI.

### P0-9 — Recover killed `pipeline run` artifacts
- **Status:** OPEN.
- **Problem:** `pipeline.run(recover=False)` is the CLI default; a half-written sentinel is trusted on the
  next plain run. `production run` already passes `recover=True`.
- **Files:** `contentos/cli.py`, `contentos/pipeline.py`, `tests/test_production_core_smoke.py`.
- **Acceptance:** either `pipeline run` recovers by default or it exposes `--recover` and documents the
  difference. A killed run cannot be skipped as complete.
- **Tests:** kill after writing the compose sentinel; the next run redoes the stage.

### P0-10 — MPT preflight
- **Status:** OPEN.
- **Problem:** `MPTRenderer.preflight` is `pass`; a missing container is only discovered mid-render.
- **Files:** `contentos/renderers/mpt.py`, `contentos/mpt.py`, `tests/test_renderers.py`.
- **Acceptance:** preflight raises `Blocked` with the exact command (`docker compose up -d`) when the
  container is unavailable.

---

## P1 — core production pipeline

### P1-1 — Make one chosen look change real frames (next task)
- **Status:** OPEN. **This is the next recommended development task.**
- **Problem:** `config/presets/*.json` (30 looks, 27 effects) are validated but unread by the builder.
  Style cards only change a border/radius/background string in `features/visual_layer.py`; their axes,
  motion and dials do not reach frames.
- **Files:** `contentos/features/style_card.py`, `contentos/features/visual_layer.py`,
  `contentos/intelligence/looks.py`, `contentos/scenekit/`, `config/presets/`, `tests/`.
- **Acceptance:** composing the same script with two different look ids produces different HTML/motion; the
  look id and a digest are recorded in the job; an unknown look fails with the known ids. No new renderer and
  no new skill.
- **Tests:** a compose test comparing two looks; a real short render inspected at phone size.
- **DoD:** a named look visibly changes palette/type/texture and at least one motion choice; docs updated;
  the look remains `unvalidated` until the render evidence is recorded.

### P1-2 — Consume `sceneplan/1` in the builder
- **Status:** OPEN.
- **Problem:** `features/scene_plan.py` writes `ctx["_scene_plan"]`; nothing reads it. Track B composition is
  hand-authored.
- **Files:** `contentos/features/scene_plan.py`, `contentos/pipeline.py`, `contentos/scenekit/`,
  `contentos/production/sceneplan.py`.
- **Acceptance:** a validated plan drives scene order, anchors and chosen techniques, with a documented
  fallback when a plan is absent. Existing Track A output is unchanged when no plan is supplied.
- **Tests:** plan with three scenes composes three scenes at the resolved word times; no plan keeps the
  current output byte-identical.

### P1-3 — Complete the reference-video path, with rights
- **Status:** OPEN / partly BLOCKED.
- **Problem:** `analyze-reference` is local-file only (no URL), and `yt-dlp` is the broken x86 binary. There is
  no shot-scale/typography/OCR/face analysis, no storyboard reconstruction, and no consumer from analysis to
  spec. Rights records exist for supplied audio only.
- **Files:** `contentos/skills/analyze.py`, `contentos/competitor.py`, `contentos/production/supplied_audio.py`,
  `scripts/bootstrap-mac.sh`, `docs/video-intelligence/09-creative-skills-integration.md`.
- **Acceptance:** `brew install yt-dlp` makes URL analysis work; a reference analysis records source URL,
  rights status and a "technique, not expression" note; a storyboard can be derived from the measured shots;
  the pipeline can consume the derived brief without copying footage, music or script.
- **Tests:** a local fixture video end to end; a URL path skipped when `yt-dlp` is absent; no third-party
  asset reaches `ready/` without a rights record.
- **Guard:** do not vendor `analyze_ref.py` from onetake (non-commercial licence).

### P1-4 — Multilingual ASR on every lane
- **Status:** DONE.
- **Fix:** Remotion and Track B now pass `language` to `words_for`/`caption_words`; Track B keeps per-line
  `lang`/`voice`/`tag` through `discover_script`.
- **Tests:** `tests/test_renderers.py`, `tests/test_track_b.py`.

### P1-5 — Human review and promotion for Hindi/Hinglish
- **Status:** OPEN (owner).
- **Problem:** both are `experimental`; no fluent listener has approved pronunciation or naturalness.
- **Files:** `config/language-capabilities.evidence.json`, `docs/MULTILINGUAL.md`.
- **Acceptance:** a named reviewer listens to a fixed benchmark set; pass/fail and notes go into the evidence
  file; only then can the cap be lifted. Do not edit the status by hand without evidence.

### P1-6 — One style system, not three
- **Status:** OPEN.
- **Problem:** seed cards, catalog cards and scenekit styles overlap; the catalog is unreachable by
  `features: {style_card: true}` and cross-directory distinctness is not checked.
- **Files:** `contentos/intelligence/styles.py`, `contentos/scenekit/styles.py`, `config/styles/`.
- **Acceptance:** one documented selection path; distinctness checked across all styles; no dangling card ids.

### P1-7 — Studio hardening
- **Status:** OPEN.
- **Items:** rate-limit or authenticate `GET /health?refresh=1` and the SSE loop; show `approve_private` on a
  requeued row or clear it; make the Review approval require the digest plus preview evidence per the screen
  spec; remove or wire `approvalHistory`, `recovery`, `artifactState`; delete the unreachable
  `contentos/dashboard.html`/`/api/state` or serve it deliberately.
- **Files:** `contentos/ui_api.py`, `contentos/ui/`, `contentos/dashboard.py`, `tests/test_ui_api.py`.
- **Acceptance:** no unauthenticated expensive loop; every visible action is capability-checked; no dead
  endpoint or dead UI branch.

### P1-8 — Make the language snapshot portable
- **Status:** OPEN.
- **Problem:** `config/language-capabilities.json` embeds absolute host paths and live readiness; it is also
  what the cloud adapter trusts. `matrix --check` cannot pass on another host.
- **Acceptance:** the snapshot separates "capability declared" from "host readiness"; the cloud trusts only
  the declared status and re-checks at job time; `matrix --check` is meaningful in CI.

### P1-9 — Fix the remaining truth drift
- **Status:** OPEN.
- **Items:** `qa_extra`/`extra_gates` alias; `check_end_hold` always PASS; composer safezone 460/190 vs
  `visual_gate` 350/180; `metadata.yaml` not consumed by export; `HyperFramesRenderer` now reads the pin.
- **Acceptance:** each documented limit either matches code or is removed from the docs.

---

## P2 — creative capabilities and reusable skills

### P2-1 — `talking-head-editor`
- **Status:** OPEN / planned.
- **Scope:** transcribe, detect shots, cut filler, reframe to 9:16 with optional face tracking, place B-roll.
- **Dependencies:** `video-understanding` (exists, word timing only), `cv.face_detect` (not installed),
  `contentos/videojob.py` state change from `planned` to `exists` only with a smoke test.
- **Acceptance:** a supplied recording becomes a checked 9:16 edit; the selector stops reporting `planned`.

### P2-2 — `lyric-video-engine`
- **Status:** OPEN / planned.
- **Scope:** align lyrics to sung audio, beat detection, line-level animation. The vendored `lyric-video`
  recipe is a creative brief, not this engine.
- **Dependencies:** forced alignment (`torchaudio` MMS not installed) or an honest line-level fallback; beat
  detection not installed.
- **Acceptance:** a song + lyrics produces a lyric video with timing granularity reported truthfully.

### P2-3 — Decide Lottie and p5
- **Status:** OPEN.
- **Problem:** both are catalogued, neither is integrated; p5.brush 2.2.3 (MIT) was evaluated but no module
  exists.
- **Acceptance:** either one is integrated behind the HyperFrames determinism rules, or the catalogue marks
  them unavailable and the docs stop implying support.

### P2-4 — Thumbnails and packaging variants
- **Status:** OPEN.
- **Scope:** thumbnail image, title/description/tags per platform, Shorts/Reels/X variants, a packaging
  preview in Studio. Publishing stays gated.
- **Files:** `contentos/pipeline.py` package/export, `contentos/export.py`, new packaging module.

### P2-5 — Reference analysis -> style card -> storyboard
- **Status:** OPEN (extends P1-3).
- **Scope:** extract palette/type/motion signatures, write a `look/1` or style card, reconstruct a shot list,
  and hand it to `video-director`. Rights and "technique not expression" stay enforced.

### P2-6 — Format workflows as configuration
- **Status:** OPEN.
- **Scope:** podcast, documentary/long-form, character storytelling, finance/education explainers. Each is a
  `videojob` intent + look + editorial brief, not a new engine. Add only when a real request needs it.

### P2-7 — Skill ecosystem hygiene
- **Status:** OPEN (owner decision).
- **Problem:** the 79 recipes exist both in the vendored library and in the global 633-skill pack; the
  router's rationale says they are deliberately not in `.claude/skills`.
- **Acceptance:** decide whether the global pack is intentional; if not, remove the duplicate auto-load and
  keep the library as the single source. `.agents/` stays a generated mirror.

---

## P3 — advanced and publishing

### P3-1 — Publishing adapters behind the gates
- **Status:** OPEN / owner.
- **Scope:** one platform first (YouTube OAuth), `PUBLISH_APPROVED`, dry-run default, upload adapter, failure
  handling. `config/youtube.yaml` stays `publish.enabled: false` until the owner enables it.
- **Acceptance:** a real upload cannot happen without the gate and an explicit config change; a failed upload
  never marks a job published.

### P3-2 — Analytics ingestion and learning loops
- **Status:** OPEN.
- **Scope:** ingest platform metrics into the existing read-only learning reports (`learn providers|cost|
  calibration|platforms|packaging`), so `recommend` stops saying `insufficient_data`.

### P3-3 — Multi-platform packaging and variants
- **Status:** OPEN.
- **Scope:** per-platform aspect/length/caption variants, platform limits from `config/platforms.json`.

### P3-4 — Niche discovery
- **Status:** OPEN.
- **Scope:** topic/opportunity research beyond the current Reddit/HN dossier, with sources and rights.

### P3-5 — ContentForge exchange hardening
- **Status:** OPEN.
- **Scope:** keep the exchange data-only, untrusted, symlink-safe, and independent of this repo; add contract
  tests for language, style and failure states.

---

## Definition of done (every ticket)

- The behaviour is covered by a test that fails without the change, or the ticket states why a test is not
  possible and what was measured instead.
- `~/.contentos/venv/bin/python -m pytest tests -q` passes; Node tests pass when UI/worker files change.
- No publish, no paid provider, no gate/config/HyperFrames-pin change without the owner.
- Generated media stays in `$VIDEO_FACTORY_WORKSPACE`; no media or model weights are committed.
- The docs that describe the changed surface are updated in the same commit (README, HOW_IT_WORKS,
  CURRENT_STATE, RENDERERS, MULTILINGUAL or SKILLS_INVENTORY).
- The commit message says what was verified and what was not.
