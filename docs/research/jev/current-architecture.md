# Jev evaluation - current architecture (Phase 1)

Date: 2026-10-11. Scope: read-only discovery. Nothing was installed, configured, committed or modified except this
folder (`docs/research/jev/`, new and untracked). No secret file was opened; no Jev call was made.

Evidence labels: **[read]** I read the file; **[ran]** I ran the command and saw the output; **[doc]** stated by a doc, not
re-checked; **[not verified]** I could not check it.

## 1. Which repositories and where [ran]

| Name | Path on the Mac | Git state when inspected |
|---|---|---|
| Video Factory (`contentos`) | `~/git/video-factory` | branch `video-intelligence`, HEAD `c7cf7d3`, working tree clean (`git status --short` empty before and after the test run) |
| ContentForge | `~/git/ContentForge` | branch `feat/auth0-migration`, HEAD `c7fc4c0`; about 40 untracked entries (agent config folders such as `.agents/ .audit/ .gemini/ .kiro/`, plus loose files like `art.txt`, `lj.json`, `Claude outputs/`, `architecture/`). A first look at this status was cut off by `head -5`; the full listing was seen later. I wrote nothing in this repo (only `rg`, `git status`, `git log`), so none of it is from this session |
| MoneyPrinterTurbo, OpenMontage | `~/git/video-factory/vendor/` (git-ignored) | not inspected beyond the registry entries |
| Agent OS (AESP), Hermes | not found as sibling repos under `~/git` | **[not verified]**; `~/.hermes` exists as a home dot-folder; out of scope for this phase |

They are separate repositories. The ContentForge exchange folder (`~/.contentos/exchange`) is the only runtime link
between the first two, plus one HTTP adapter (section 4).

**Project notes are out of date.** The Project summaries describe `main`/`cfc0ea3`, 17 uncommitted entries and 66 tests.
Reality today: branch `video-intelligence`, clean tree, **289 tests** [ran]. Docs 11-14 (Motion Director M1/M2, platform
limits, external storage) and the `video-intelligence` work are committed since those notes.

## 2. Baseline [ran, 2026-10-11]

`~/.contentos/venv/bin/python -m pytest tests -q -p no:cacheprovider` (with `PYTHONDONTWRITEBYTECODE=1`):
**289 passed in 21.9 s**; tree still clean afterwards. This is the regression baseline for any later change.
ContentForge's TypeScript tests (`server/decision/*.test.ts`) were **not run** (different repo, branch with unrelated
auth work); treat the engine's test status as **[not verified]**.

## 3. The two tracks, as implemented

**Track A - template production (end to end, works).** `contentos/pipeline.py`:
`STAGES = brief > script > voice > compose > render > qa > package > export > publish` [read]. The spec's `render:` field
picks the lane (`hyperframes` default, `mpt`; `RENDER_LANES` check at `pipeline.py:272`). `s_compose` [read] copies the local
`contentos/templates/gsap.min.js` into the project and builds one headline-and-caption scene per `script:` line, with caption
timing from whisper.cpp word timings (script words shown, ASR used for timing only).
Gates: `SCRIPT_APPROVED` before voice, `PRODUCTION_APPROVED` before render. Failures: `production/core.py` wraps the
pipeline with `classify(stage, status)` -> `blocked | transient | output`; only voice/compose/render are retried
(backoff 15 s, 45 s; 360 s cap).

**Track B - director-led explainers (plan + validate shipped; build is not unified).**
- `contentos/production/sceneplan.py` resolves narration-anchored scenes to times (`resolve`, `storyboard_md`).
- `contentos/production/direction.py` is a read-only validator of the optional `direction` block and `brief`
  against `config/capabilities.json` (statuses `installed | available | candidate | unavailable`).
- `contentos/production/director.py` holds `select_capability()` (substitution + recorded fallback), `coherence_issues()`,
  `anchor_issues()`, estimated timeline, `check`, `report` CLI.
- `contentos/production/platforms.py` answers length/aspect limits per platform (`budget`, `check`, `plan`).
- Skills (`.claude/skills/`, 8 entries [ran: ls]): `video-director`, `video-production-orchestrator`, `explainer-motion-craft`,
  `explainer-visual-qa`, `hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes` (pinned upstream, vendored,
  git-ignored) and an `_upstream` working folder.
- **The distinction you described is confirmed**: outside `production/` only `cli.py` imports it (`core`, `preview`);
  `sceneplan.resolve()` is called by `director.py` and tests only [ran: rg]. No code turns a `direction` plan into
  HyperFrames HTML; Track B compositions are agent-authored per project. `pipeline.compose` does not read `direction`.

## 4. Component map (who calls whom) [read]

```
operator / agent (Claude Code, Codex, ...)
  |  reads docs/AGENT_BRIEF.md, .claude/skills/*   (LLM planning: audience, arc, scenes)      <- Track B creative work
  v
./contentos.sh  -> contentos/cli.py
  |-- doctor/route -> providers.py (select by tier -> health -> quality; paid blocked)         <- deterministic router
  |-- pipeline run -> pipeline.py -> hf.py (pinned hyperframes 0.8.114), kokoro, whisper.cpp, ffmpeg, mpt.py (Docker)
  |        \-> qa.py / finalcheck.py (ffprobe gates) -> export.py/storage.py -> ready/ + .publish.json
  |-- production run -> production/core.py (retries, failure classes) -> pipeline.run
  |-- preview/qa    -> production/preview.py, critic.py, motion_audit.py
  |-- jev status|triage -> contentos/jev.py --HTTP, session cookie--> ContentForge :3000 /api/decision/*   <- ONLY Jev touchpoint
  |-- learn/recommend -> learn.py (reads ledger; may call jev.triage; records decisions)
  |-- queue/worker/factory-worker -> queue.py, adapters/v1/*.mjs  <-- ContentForge exchange folder (filesystem, untrusted input)
  `-- dashboard -> dashboard.py :4310 (read-only; shows jev.status())
SQLite ledger (ledger.py): runs, decisions (id,type,subject,decision,confidence,source,reasons,predicted,actual,ts)
ContentForge (separate repo): server/decision/{jev.ts, engine, registry.ts, policies.ts, ledger*, shadow.ts, decisions/*.ts}
   --HTTPS POST https://api.typesafe.ai/v1/systemone (Bearer TYPESAFE_API_KEY) or `cmd -m typesafe/jev` CLI--> TypeSafe Jev
```

## 5. What already exists for Jev (the central finding) [read]

1. **ContentForge already integrates TypeSafe Jev in production code**: `server/decision/jev.ts` (transport: `api` or
   `cli`, typed questions `noul|choice|score`, response validation, 3 attempts with backoff on 429/529, 30 s timeout,
   key redaction), a registry of **ten** decision types, versioned policies, declared fallback classes
   (`fail_open_keep`, `deterministic`, `fail_closed_hold`), a ledger with `input_state_hash`, a shadow harness and per-type
   feature flags (`JEV_DECISION_MAP.md`, "as-built status"). Its own doc marks eight types "VERIFIED LIVE" (research triage, opportunity score, content strategy, quality gate,
   format select, and the three shadow-only legacy ones; dated 2026-10-02) and states that production runs only research triage and framing (`JEV_DECISION_ENGINE_ENABLED=1`, `JEV_RESEARCH_GATE=1`,
   `JEV_FRAMING=1`); this is **[doc]**, not re-verified by me.
2. **Video Factory has a thin adapter** (`contentos/jev.py`, 69 lines): `status()` and `triage()` over HTTP with
   `CONTENTFORGE_COOKIE`; every call is written to the local `decisions` table; if Jev is unreachable it returns `watch`
   with `source=local_fallback` (never silently `pursue`). `config/providers.yaml` declares `decision: jev_contentforge`
   ("adapter only, never reimplemented here").
3. **Live status today [ran]**: `./contentos.sh jev status` -> `reachable: true, authed: false`
   ("401: set CONTENTFORGE_COOKIE from a logged-in session"). So the adapter works end to end only against a stub
   (`tests/test_loops.py`), as the README says. I cannot get live Jev answers from this side without a credential.
4. **No decision type in ContentForge's registry covers production-side choices.** The ten types are research triage and
   depth, opportunity score, content strategy, quality gate, publish gate, format select (which *channel formats* to
   generate, e.g. `x_thread` vs `video`), and three shadow-only legacy ones (viral score, discover rank, agent route).
   Nothing selects video format, renderer, scene treatment, skill, or failure recovery.
5. ContentForge's `agent_route` is the closest analogue of Candidate A/C: a closed list of eight tools, Jev picks one,
   answers outside the list are discarded, shadow only. It is a pattern to reuse, not the same decision.

## 6. Decision points found in Video Factory code (summary; full inventory is Phase 3)

| Area | Where | Today |
|---|---|---|
| Provider/tool routing | `providers.py:select`, `config/local-first-policy.yaml`, `providers.yaml` | deterministic: tier rank -> health probe -> quality; paid blocked unless `allow_paid` |
| Render lane | `pipeline.py` (`render:` in spec) | operator/agent writes it in the spec; no automatic choice |
| Capability substitution | `production/director.py:select_capability` | deterministic: status/fallback chain ending at `hf.native:html-svg-css` |
| Plan validity / coherence | `direction.py`, `director.py` | deterministic validators with enumerated vocabularies |
| Platform/aspect limits | `production/platforms.py`, `config/platforms.json` | deterministic table lookup |
| Retry/fallback | `production/core.py:classify` | deterministic: stage-based failure class, 2 retries |
| Editorial quality | `production/critic.py` (rubric verdict computed from scores), `qa.py`, `motion_audit.py` | scores are produced by an LLM critic agent, verdict by code |
| Publish recommendation | `learn.py:recommend` | local rules; optional `jev.triage` |
| Format/strategy, scene treatment, story structure, skill choice | `video-director` / orchestrator skills | **LLM agent judgment** (no code) |
| Topic triage | `jev.triage` -> ContentForge | Jev (when authed), else `watch` |

## 7. Integration boundaries

- Exchange folder with ContentForge is **hostile input** (job id from folder names, symlinks ignored, derived spec written
  outside the root; worker refuses a root inside the repo) [doc: README].
- Jev boundary: HTTP to `CONTENTFORGE_URL` (default `localhost:3000`), session cookie only; ContentForge's auth is cookie +
  CSRF, no service tokens [doc: CHATGPT_BRIEF]. Containers cannot reach host services via `host.docker.internal` (tested by
  the owner) [doc].
- Nothing in contentos calls `api.typesafe.ai` directly, and no TypeSafe key is in contentos' configuration
  (`env | grep TYPESAFE|JEV` on the Mac returned nothing [ran]). ContentForge's `.env` was not opened.

## 8. Existing safeguards (all must survive any change)

Approval gates (`SCRIPT_APPROVED`, `PRODUCTION_APPROVED`, `PUBLISH_APPROVED`); publish is DRY_RUN and
`config/youtube.yaml publish.enabled: false`; paid providers blocked by policy; 9 ffprobe/ffmpeg QA checks; a failed stage
deletes its own artifact; `export` never ships unvalidated video; one worker per workspace with heartbeat; storage rules
(no media in Git, no fallback into the repo); `production/*` validators are read-only and network-free; hyperframes pinned
at 0.8.114; Jev adapter fails open to `watch`, and ContentForge's engine declares fail-closed HOLD for any publish-class
decision.

## 9. Known limitations relevant to this evaluation

1. No unified Track B builder (section 3), so there is no automatic consumer for a scene-treatment decision yet.
2. No labelled ground truth for video-production decisions; ContentForge's own cut-over gate is also blocked on a golden set.
3. No telemetry of production decisions exists beyond `runs` and the `decisions` table (few rows; `learn` reports
   `insufficient_data`).
4. Live Jev unreachable from contentos without `CONTENTFORGE_COOKIE` (or a TypeSafe key); no latency/cost data exists.
5. Pi, the host of the candidate extension, is not the runtime for these agents (see `repository-assessment.md`).
