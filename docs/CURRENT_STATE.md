# Current state and handover

Measured 2026-11-11 on `main` at `/Users/kishore/git/video-factory` (MacBook Pro M5 Pro, 24 GB, arm64,
macOS 27). This is the authoritative handover. It distinguishes what was **read**, what was **measured**, and
what is **inferred or still unverified**. Historical plans stay in `docs/factory-v2/`,
`docs/video-intelligence/`, `docs/research/` and `docs/ui-discovery/`; they are evidence, not the current
contract. The rules every agent follows remain `AGENTS.md`.

## 1. What Video Factory is

A local-first, agent-native video factory. A topic or a script goes in; a captioned, QA-checked MP4 comes out.
It is a Python CLI (`contentos`, entry point `./contentos.sh`) plus a local Creator Studio, a SQLite ledger,
approval gates, a queue/worker, and a set of agent skills. Nothing publishes and nothing spends money by
default.

**Two tracks**

- **Track A — template pipeline.** A spec YAML goes through `brief > script > voice > compose > render > qa >
  package > export > publish`. One scene per script line, word-highlight captions. This is what the queue,
  worker and ContentForge exchange run.
- **Track B — director-led explainer.** An agent plans with `video-director`, validates a `sceneplan/1`,
  voices and aligns it, then hand-authors a HyperFrames composition. The builder does not consume scene plans
  yet, so composition is agent work. Track B jobs register with `job register --track B`.

## 2. Original product vision

A generic, domain-agnostic creative production system — not a collection of technology-explainer scripts. It
should support faceless videos, education, finance/business, emotional storytelling, Shorts/Reels, long-form,
documentary, animated explainers, podcast-style, lyric videos, character content, reference-driven
recreation, and multiple languages, without rebuilding the rendering engine for each category.

Intended lifecycle:

`reference / idea / research -> creative direction -> script -> storyboard -> assets -> scene composition ->
motion design -> voice/audio -> render -> QA -> packaging -> human approval -> publishing`.

The implementation is closest to that vision in the generic layer added in October 2026: one universal
`create-video` entry, a `videojob/1` selector, and `look/1` style data (`config/presets/`, 30 looks and 27
effects). The largest gap is that a chosen look is **not read by the builder yet**, so naming a style changes
no frame.

## 3. Repository and Git state

- Remote: `https://github.com/unplugged-kk/video-factory.git` (`origin`), branch `main`.
- Worktrees that exist on this machine: the main checkout; `../video-factory-generic` (branch
  `feat/generic-video-system`, now merged and pushed); `/private/tmp/ceh-vf-consumer` and
  `~/.codex/worktrees/ceh-catalog-consumer/video-factory` (the read-only CEH capability branch
  `codex/ceh-catalog-consumer`, unrelated to this mission).
- Recovered in this mission: the uncommitted multilingual setup work (commit `9e23654`) and the local-only
  generic video branch (merge `7068148`). The thin `lyric-video` shortcut was renamed `make-lyric-video` so it
  does not shadow the vendored `lyric-video` recipe.
- `.agents/` is a generated per-agent mirror of `.claude/skills` and `.cursor/commands`; it is gitignored and
  is not a source of truth. `.claude/skills` stays canonical.

## 4. Architecture map

| Component | Where | State |
|---|---|---|
| CLI, pipeline, ledger, gates | `contentos/cli.py`, `contentos/pipeline.py`, `contentos/ledger.py` | working; 9 stages, digest-bound gates |
| Queue and worker | `contentos/queue.py`, `contentos/production/core.py` | working; retries voice/compose/render twice, never retries QA or blocked gates |
| Storage and export | `contentos/storage.py`, `contentos/export.py`, `contentos/handoff.py` | working; refuses an in-repo workspace; finals go to `$VIDEO_FACTORY_PUBLISH_DIR/ready/` |
| Render lanes | `contentos/renderers/` | `hyperframes` (default), `remotion`, `mpt`; OpenMontage is a manual handoff |
| Scenekit | `contentos/scenekit/` | drives frames when a spec sets `visual_style`; six different styles from the style cards |
| Style cards | `config/styles/`, `config/styles/catalog/` | chosen and recorded, but only a border/background string reaches the legacy HTML |
| Look presets | `config/presets/`, `contentos/intelligence/looks.py` | 30 looks + 27 effects, schema-validated, all `unvalidated`; **not read by the builder** |
| Workflow selector | `contentos/videojob.py` | `videojob/1`; reports each capability as `exists` or `planned` |
| Asset library | `contentos/production/assets.py` | ffprobe index, sampled frames, human/agent notes, plain-English search; never invents a description |
| Language routing | `contentos/lang/` | English, Hindi, Hinglish ready on Apple Silicon; Odia blocked |
| Multilingual setup | `contentos/lang/setup.py`, `scripts/bootstrap-*.sh`, `docs/AGENT_SETUP.md` | working; installs only the languages the host can run |
| Creator Studio | `contentos/ui/`, `contentos/dashboard.py`, `contentos/ui_api.py` | vanilla ES modules, loopback + token/origin writes, no publish/paid path |
| QA and visual checks | `contentos/qa.py`, `contentos/production/{visual_gate,preview,critic,motion_audit}.py` | technical QA in the pipeline; visual gates and critic standalone |
| Research / competitor | `contentos/research.py`, `contentos/competitor.py` | research depends on `~/.agents/skills/last30days`; competitor is metadata + hook text only |
| Reference analysis | `contentos/skills/analyze.py` | local file only: probe, cut detection, pacing, loudness, coarse palette, contact sheet |

## 5. Canonical pipeline and gates

Stages and sentinels (`contentos/pipeline.py`):

| Stage | Artifact | Gate enforced in code |
|---|---|---|
| `brief` | `content.json` | none |
| `script` | `script.md`, `script-lint.json` | `SCRIPT_APPROVED` is checked before `voice` |
| `voice` | `audio/NN.wav`, `audio/voice-languages.json` for non-English | `SCRIPT_APPROVED` |
| `compose` | `project/index.html` (or `project/mpt-request.json`, `project_remotion/src/Video.tsx`) | none |
| `render` | `video.mp4` | `PRODUCTION_APPROVED` |
| `qa` | `qa.json`; a `FAIL` raises | none |
| `package` | `metadata.yaml` | none |
| `export` | `export-result.json`, sidecar in `ready/` | Track B only: both approvals must exist (not digest-bound) |
| `publish` | `publish-result.json` | `PUBLISH_APPROVED`, and `config/youtube.yaml` has `publish.enabled: false`; no uploader exists |

Approvals bind to a digest of the artifact they cover. `SCRIPT_APPROVED` covers the title and every spoken
line; `PRODUCTION_APPROVED` covers the composed project plus every audio take. A forced rerun deletes later
sentinels and revokes the approvals it invalidates. `RESEARCH_APPROVED` is written by `--approve-private` but
**nothing reads it**; treat it as reserved, not enforced.

`--approve-private` grants research, script and production (never publish). Use it only after owner approval
or for an explicit unattended sample.

## 6. Rendering

- **HyperFrames 0.8.114** is pinned in `package.json` and the lockfile, and the installed tree matches. The
  pipeline invokes `node_modules/.bin/hyperframes`, never a bare `npx`. `renderers.hyperframes.version` now
  reads the pin instead of a hand-maintained string.
- **HyperFrames lane** writes one paused, seek-safe GSAP timeline with word captions from whisper timings.
  Safe zones are 460 px bottom and 190 px right in the composer; the standalone `visual_gate` default is looser
  (350 px bottom, 180 px right), so a gate pass is not proof of the composer's own padding.
- **Scenekit** (`visual_style` in the spec) is the only path where a style materially changes layout, motion,
  grounds and type. It uses its own six styles, not `config/styles/catalog/`.
- **Remotion lane** is real but gated on `~/.contentos/remotion`; it now uses `npx --no-install`, a 1800 s
  timeout, and passes the language to ASR for non-English jobs.
- **MPT lane** needs Docker and a stock source; `mpt.source: local` is the tested path. Its `preflight` is
  still a no-op.
- **Motion technologies actually integrated:** GSAP, CSS, SVG (scenekit), Remotion. **Not integrated:** Lottie,
  p5.js/p5.brush, Three.js. They exist as catalogued candidates or skill prose only.
- **Style cards vs looks:** the catalog card affects only a border/radius/background string in
  `features/visual_layer.py`; the card's axes, motion and dials do not reach frames. The `look/1` presets are
  not consumed by any builder. This is the next P1 feature.

## 7. Audio, voice and languages

| Language | TTS | ASR | Status | What that means |
|---|---|---|---|---|
| `en` (or absent) | Kokoro through `hyperframes tts`, `af_heart` | `ggml-small.en.bin` | production-ready | the original English path is unchanged |
| `hi` | Chatterbox v3 on MLX, `hindi-default` (synthetic Kokoro reference) | `ggml-large-v3-turbo-q5_0.bin` | experimental | generation and renders exist; **no fluent listener has approved the audio** |
| `hi-en` | same Chatterbox voice | same multilingual model, `-l hi` | experimental | Devanagari script with Latin terms; only a 23-term lexicon is transliterated |
| `or` | blocked (Indic Parler is gated) | missing (`ggml-vaani-odia.bin`) | blocked | rejected with `language_blocked`; no silent fallback |

Commands:

```bash
~/.contentos/venv/bin/python -m contentos.lang doctor --require en,hi,hi-en   # Ubuntu: --require en
~/.contentos/venv/bin/python -m contentos.lang matrix --check
~/.contentos/venv/bin/python -m contentos.lang verify-models
```

`setup` installs only the languages the host can run; on Linux it downloads only the English ASR model. A
partial Chatterbox download is no longer mistaken for a complete cache (`.incomplete` blobs or an empty
`snapshots/` make readiness fail), and a `.wav` left without its `.tts.json` is regenerated instead of being
dropped. The capability snapshot is machine-specific by design; `matrix --check` is meaningful on the host
that wrote it, not in CI.

## 8. Creator Studio

`./contentos.sh dashboard` serves the UI and `/api/v1` on `127.0.0.1:4310`. It is loopback-only, rejects a
non-local `Host` with 421, and requires the per-session token plus a same-origin `Origin` for writes. The
frontend is vanilla ES modules with no build step; the CLI is still the source of truth and each action calls
the same backend function.

Working: jobs list, job workspace, script approval, production approval, run/resume, one-stage rerun preview,
QA rerun, preview frames, stage logs with secrets redacted, artifact list, validated export, New Job validation,
Track B intake/voice/align/render/QA/register, queue add/list/requeue, health, help, SSE progress with polling
fallback.

Missing by design: publish, `PUBLISH_APPROVED`, `--allow-paid`, `--approve-private`, cancel, worker start/stop,
storage `--apply`, research, competitor, ContentForge.

The jobs list tolerates legacy project folders (they are skipped; migrate with `storage adopt`). Known Studio
issues: requeue preserves a row's earlier `--approve-private` flag without showing it; the SSE
and `/health?refresh=1` read endpoints are unauthenticated (local work amplification only, no data
exfiltration); the Review tab enables approval when a video **or** frames exist, which is weaker than the
screen spec. The log-stage, duration and storage-label field mismatches and the stale polling watcher were
fixed in this mission.

## 9. Skills

Canonical inventory: [`SKILLS_INVENTORY.md`](SKILLS_INVENTORY.md). Short version:

- Factory-owned in `.claude/skills/`: `video-production-orchestrator`, `video-director`,
  `explainer-motion-craft`, `explainer-visual-qa`, `creative-skill-router`, `create-video`,
  `edit-video`, `make-lyric-video`, `repurpose-video`, `video-assets`.
- Pinned upstream, gitignored, hash-verified: `hyperframes-core`, `hyperframes-animation`,
  `hyperframes-keyframes`. Restore with `python scripts/upstream_skills.py sync`, verify with `verify`.
- Vendored creative library: 79 recipes + 7 core workflow skills in `contentos/skills/library/`, indexed by
  `config/creative-skills.json`; route with `python -m contentos.skills route|show|deps|compat|plan|verify`.
- Global engineering skills worth using: `wayfinder` (needs a tracker), `writing-plans`, `executing-plans`,
  `brainstorming`, `grilling`, `systematic-debugging`, `test-driven-development`,
  `verification-before-completion`, `subagent-driven-development`, `reference-video-analyzer`,
  `video-qa-critic`, `script-to-storyboard`, `style-architect`, `publishing-packager`.
- Not found anywhere: `mad-poke`, `potato-agent`. The "poteto" family exists but is a different thing.

Wayfinder is installed but has no configured issue tracker, so it was not used to create a second planning
system. The roadmap lives in [`ROADMAP.md`](ROADMAP.md).

## 10. Reference-video workflow — what exists

Implemented: local-file structural analysis with
`~/.contentos/venv/bin/python -m contentos.skills analyze-reference REF.mp4 --out DIR` (probe, cut detection,
cuts/minute and shot lengths, LUFS/true peak, coarse palette, contact sheet). `./contentos.sh competitor URL`
gets metadata, captions without timings, the first 35 words and a hook score. `./contentos.sh research
"topic"` writes a keyless Reddit/Hacker News dossier.

**Not implemented:** download from a URL (yt-dlp is broken on this machine), shot-scale/typography/OCR/face
analysis, storyboard reconstruction, automatic style-card extraction, and any consumer that turns an analysis
into a spec or composition. Rights protection is real for supplied **audio** only; there is no footage, music
or script-reuse rights record. Do not describe this as a complete reference-recreation pipeline.

## 11. Tests and verification

Measured in this mission (exact counts are repeated in the final report):

```bash
~/.contentos/venv/bin/python -m pytest tests -q          # repo suite; do not use a bare pytest
node --test contentos/ui/*.test.mjs contentos/adapters/v1/*.test.mjs
npx playwright install && npx playwright test            # browser binaries are not installed by default
```

The Python suite is hermetic; skips name their precondition (pinned HyperFrames skills, Remotion, ffmpeg,
gitignored fixtures). Baseline before the recovery: 1023 passed, 8 skipped; after the fixes: 1084 passed, 8 skipped. The Node suite
has 91 tests (25 UI + the ContentForge worker). Playwright has 6 journeys against fixture data.

**Rendered sample (2026-11-11).** `recovery-smoke-20261111`, a two-line English 9:16 short, ran all nine
stages on this Mac (`pipeline run --approve-private`, sample id only): brief 0.0 s, script 0.1 s, voice 4.2 s,
compose 2.1 s, render 11.9 s, qa 0.4 s, package 0.1 s, export 0.5 s, publish 0.0 s. Job:
`~/Desktop/VideoFactory-Workspace/jobs/2026/11/11/recovery-smoke-20261111/`.

QA: 8 PASS and one expected WARN — `render_integrity 7.3 s`, `resolution 1080x1920`, `frame_rate 30`, `audio
aac`, `loudness -13.7 LUFS`, `clipping -1.5 dBFS`, `black_frames 0`, `frozen_frames 1 segment >3 s` (the
documented text-slide WARN). Export:
`ready/recovery/2026/11/recovery-smoke-test__recovery-smoke-20261111.mp4` plus its `.publish.json`; publish
returned `DRY_RUN` with `publish.enabled=false`.

Frame inspected at 5.0 s: 1080x1920, dark gradient, `2 / 2` tag, white "Local only" headline, and the spoken
caption with the word "render" highlighted in amber. Legible at phone size; no clipping or black frame.

Two visual-gate calibration findings, not render failures: `visual_gate safezone --times 2,5` returns
`ok:false` because the legacy template's default bottom padding is 307 px (16% of 1920) while the gate's
default bottom zone is 350 px; the documented 460 px applies only when `captions_hook` is enabled.
`visual_gate transitions --at 3.7:0.4` also returns `ok:false` for the legacy crossfade; only a `blend`
verdict is `ok`, and a slow fade needs the real cut window and the skill's `--at start:duration[:kind]`
form. Read the verdict and frames, not just the boolean.

**Hindi sample (2026-11-11).** `contentos.lang speak --lang hi` produced 3.44 s, 24 kHz mono PCM through
`mlx-community/chatterbox-multilingual-v3`, 3.23 s generation, 4.64 GB peak, synthetic reference (no real
person's voice). `contentos.lang transcribe --lang hi` returned in 0.84 s but the text was
"कुबैनिट्स में पॉट सबसे छुटी ही काई है।" — real ASR spelling errors. The pipeline keeps the script's spelling
and uses ASR only for timing, but this is why Hindi/Hinglish stay `experimental` until a fluent listener
reviews them.

**Full Hindi render (2026-11-11).** `recovery-hi-smoke-20261111`, two Devanagari lines, ran all nine stages:
brief 0.0 s, script 0.1 s, voice 10.5 s, compose 1.8 s, render 10.9 s, qa 0.4 s, package 0.0 s, export 0.5 s.
QA: 8 PASS and the expected `frozen_frames` WARN; `loudness -11.9 LUFS`, `clipping -1.5 dBFS`. The frame at
4.0 s shows the Devanagari headline "कंटेनर" and the spoken caption with "पॉड" highlighted; conjuncts and
matras render correctly and nothing clips. `audio/voice-languages.json` records `hi: experimental` and the
synthetic reference provenance. Export:
`ready/recovery/2026/11/recovery-hi-smoke-20261111__recovery-hi-smoke-20261111.mp4`. This proves the language
path, not narration quality: no fluent listener has approved the audio.

## 12. Known bugs and debt (not fixed here)

1. **A named look does not change a frame.** `config/presets/` is not read by the builder; style cards reach
   only `features/visual_layer.py`'s border string. Wire one path, then render.
2. **Track A export has no approval gate.** `--only export` can export a video that never passed `qa`; the
   export's own `finalcheck` still runs. Track B export checks both approvals but does not bind them to the
   current video digest.
3. **`RESEARCH_APPROVED` is inert.** Written by `--approve-private`, read by nothing. Documented as reserved.
4. **`pipeline run` does not scrub a killed run by default.** `production run` does (`recover=True`); the CLI
   trusts any existing sentinel.
5. **Track B does not consume `sceneplan/1`.** Composition is agent-authored.
6. **MPT `preflight` is a no-op**; a missing container is discovered mid-render.
7. **`qa_extra` / `extra_gates`:** the alias does not enable the hook through `pipeline.run`; `check_end_hold`
   always returns PASS, so extra gates can warn but never fail a job.
8. **Language snapshot is host-specific** (`config/language-capabilities.json` embeds absolute paths). A cloud
   reader on another host should treat it as a hint and re-check readiness.
9. **`yt-dlp` is still the x86 `/usr/local/bin` binary on this Mac** ("Bad CPU type"), so URL download and the
   reference-video URL path do not work. `brew install yt-dlp` is the fix; do not substitute a paid API.
10. **Odia needs owner approval** for a gated Hugging Face model and an isolated PyTorch venv. Do not claim it
    works because the selector lists it.
11. **Hindi/Hinglish audio has not been reviewed by a fluent listener.** They are `experimental`, not
    production-ready.
12. **Labelled contact sheets need an ffmpeg with `drawtext`.** This Mac's Homebrew build has no freetype; the
    labelled path fails closed. Use `preview --sheet`, not `--allow-unlabelled`.
13. **Creator Studio's read endpoints are unauthenticated** and `/health?refresh=1` probes tools. Local only.
14. **No uploader, thumbnails, analytics, niche discovery, or multi-platform packaging.**
15. **`metadata.yaml` is produced but not consumed by export**; the sidecar takes title/description/tags from
    the manifest.
16. **Legacy project folders are skipped by the Studio jobs list.** `/api/v1/jobs` used to crash with an empty
    reply on the old `pilot-001-agent-tool-use` manifest; it now skips any folder whose manifest is not
    `jobmanifest/1`. Run `contentos storage adopt` to migrate one deliberately.
17. **Visual-gate calibration.** `safezone` defaults to a 350 px bottom zone while the legacy template uses
    307 px; the 460 px figure is feature-gated. `transitions` marks only `blend` as `ok`, so a slow crossfade
    can read `ok:false`. These are heuristic signals, not render failures; inspect the frame and the verdict.

## 13. Roadmap and next task

The authoritative, ticket-shaped roadmap is [`ROADMAP.md`](ROADMAP.md). Priorities: P0 safety and
correctness; P1 the production pipeline and the look/scene-plan integration; P2 creative capabilities and the
reusable skill ecosystem; P3 advanced publishing and analytics.

**Next recommended task (P1):** make one chosen `look/1` preset change real frames. Extend
`features/style_card.py` to load a preset by id and pass its palette/type/texture/motion into
`features/visual_layer.py` (or route it through scenekit), add a test that compares composed HTML for two
different looks, then render a short and inspect frames. Do not add a new renderer or a new skill for this.

## 14. Exact commands to get started

```bash
cd ~/git/video-factory
./scripts/bootstrap-mac.sh                      # idempotent; Apple Silicon: en, hi, hi-en
./contentos.sh doctor --require tts,stt,render  # optional providers stay informational
~/.contentos/venv/bin/python -m contentos.lang doctor --require en,hi,hi-en
./contentos.sh storage paths --check
~/.contentos/venv/bin/python -m pytest tests -q
node --test contentos/ui/*.test.mjs contentos/adapters/v1/*.test.mjs
./contentos.sh looks validate
./contentos.sh videojob select --intent create --input topic:"your topic"
./contentos.sh pipeline run SPEC.yaml            # stops at the gates
```

New-agent onboarding sequence:

1. Read `AGENTS.md`, then this file, then `docs/HOW_IT_WORKS.md` and `docs/AGENT_BRIEF.md`.
2. Read `docs/SKILLS_INVENTORY.md` before choosing a skill; do not copy global skills into the repo.
3. Run the verification block above and confirm the counts.
4. Pick a ticket from `docs/ROADMAP.md`; claim it in your own notes, not in a new planning system.
5. Never publish, never spend money, never edit `config/*.yaml`, the gates or the HyperFrames pin without the
   owner asking. Generated media goes to `$VIDEO_FACTORY_WORKSPACE`, never the repo.
6. Report the absolute `video.mp4` path, the QA table, what you measured, and what you could not check.
