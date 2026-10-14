# B — Current state and verified gap analysis

Verified against the live checkout at `ec4eb77` on `feature/labelled-contact-sheets`, 2026-10-14. Read-only: no file was
modified, no test suite was executed in this session (see §8 for why), no render was run.

Purpose: separate **what is deployed** from **what is proposed**, and pin down the exact places where a concurrent design
would break. Every status is one of `implemented`, `partial`, `experimental`, `proposed`, `absent`, `unverified`.

---

## 1. The real runtime shape

### 1.1 Entry points

`contentos.sh` is a thin launcher: it `cd`s to the repo root, exports `HYPERFRAMES_PYTHON` (default
`~/.contentos/venv/bin/python` — present **[ran]**), forces `/opt/homebrew/bin` ahead of `/usr/local/bin` (the `/usr/local`
ffmpeg/`timeout` are x86_64 and die on arm64), and `exec`s `python -m contentos`. `contentos/__main__.py` calls
`cli.main`. **[read]**

`contentos/cli.py` is one argparse tree. Subcommand → module:

| Subcommand | Reaches |
|---|---|
| `doctor`, `status`, `route` | `providers` / `ledger` inline |
| `pipeline run` | `contentos.pipeline.run` |
| `production run` | `contentos.production.core.run_until_blocked_or_done` |
| `qa`, `preview` | `contentos.qa.run_qa`, `contentos.production.preview` |
| `approve` | `ledger.approve` |
| `jev`, `learn`, `recommend`, `research`, `competitor`, `dashboard` | their modules |
| `queue add\|list\|requeue` | `contentos.queue` |
| `worker` | `queue.work(concurrency, once)` — **default concurrency 2** |
| `factory-worker` | spawns `node contentos/adapters/v1/factory_worker.mjs` |
| `storage …` | `contentos.storage_cli.register(sp)` |

There is **no** `sheet` subcommand and **no** `safezone` subcommand. `cli.py` imports only `production.core` and
`production.preview`; `pipeline.py` imports only `align` and `supplied_audio`. Everything else under `contentos/production/`
is a standalone CLI invoked by hand or by a skill. **[read]**

### 1.2 Stages, gates and resume

`STAGES = ["brief","script","voice","compose","render","qa","package","export","publish"]`, run in one sequential
`for st in STAGES` loop. **[read: `contentos/pipeline.py:22`, `:302`]**

Gate enforcement is a two-entry map checked immediately before the stage runs:

```python
gate = {"voice": "SCRIPT_APPROVED", "render": "PRODUCTION_APPROVED"}.get(st)
if gate and not ledger.approved(cid, gate): raise Blocked(...)
```
**[read: `pipeline.py:309-314`]**

`PUBLISH_APPROVED` is checked only inside `s_publish` **[read: `pipeline.py:246-247`]**. `RESEARCH_APPROVED` is **written**
by `--approve-private` **[read: `pipeline.py:298`]** but is **never read anywhere** — research gating is effectively
absent. Publishing itself is disabled: `config/youtube.yaml` sets `publish.enabled: false` and no upload adapter exists.

**Resume is artifact-sentinel based, not checkpointed.** `ARTIFACT` maps each stage to one file whose existence means
"done"; the loop skips the stage if that file exists:

```python
art = d / artifact(st, spec).replace("%02d", "01")
if art.exists() and not force and st != "publish":
    report.append((st, "SKIP(resume)", 0.0)); continue
```
**[read: `pipeline.py:256-263`, `:305-307`]**

It trusts the **first** artifact of a stage and does not verify contents. `publish` is never skipped. On `Blocked` or any
exception the single sentinel is unlinked before breaking **[read: `pipeline.py:319-329`]**. There is **no** per-stage
state file, no attempt log inside the manifest, and no stage-level lock. A second `pipeline run` for the same `content_id`
can therefore interleave with the first one, and the only protection is the queue's `add()` de-duplication for
`queued`/`running` rows **[read: `contentos/queue.py:24-26`]**.

### 1.3 Render lanes

Exactly two, chosen by the spec's `render:` key (default `hyperframes`):
`RENDER_LANES = ("hyperframes", "mpt")` **[read: `pipeline.py:258`]**. The `mpt` lane talks to a **single** Docker
container `moneyprinterturbo-api` with a shared `vendor/MoneyPrinterTurbo/config.toml` **[read: `contentos/mpt.py:21`,
`:97-101`]**. HyperFrames is pinned at **0.8.114** in three places that agree: `package.json:6`, `package-lock.json`, and
`config/capabilities.json:6`; resolved by absolute path in `contentos/hf.py:15-23` (the fix for KF-001). There is **no
Python-side hash check at render time** — the pin rests on `package.json`/lock plus the resolved binary. **[read]**

### 1.4 Storage, export and the refusal to live in the repo

- Job dir: `jobs/YYYY/MM/DD/<job-id>/` (new), with `jobs/YYYY/MM/<job-id>/` still readable and an in-repo
  `workspace/projects/<id>` treated as legacy read-only. **[read: `contentos/storage.py:289-336`]**
- Manifest: `manifest.json`, schema `jobmanifest/1`, guarded by `<job>/.manifest.lock` (`fcntl.flock`). **[read:
  `storage.py:38`, `:407`, `:424`, `:244-259`]**
- Roots: `VIDEO_FACTORY_WORKSPACE` (default `~/Desktop/VideoFactory-Workspace`) and `VIDEO_FACTORY_PUBLISH_DIR` (default
  `~/Desktop/Video-Publishing`); both exist on this machine **[ran]**. `_check_outside_repo()` refuses a root inside the
  repo or containing it, and requires absolute paths. **[read: `storage.py:35-41`, `:90-130`]**
- The ledger is **one SQLite file for the whole workspace**: `<workspace>/ledger.db`, tables
  `runs, jobs, approvals, decisions, video_metrics`. **[read: `storage.py:157-158`, `contentos/ledger.py:9-27`]**
- Export holds a per-job lock `pub/.state/locks/<job_id>.lock`, is gated by `finalcheck.validate_video()` (any `FAIL` →
  `ExportRefused`, the video stays in the workspace), stages into `<publish>/.staging`, verifies size+sha256, then
  `os.replace`s the video and **writes the sidecar last** as the ready marker. **[read: `contentos/export.py:106-193`]**
- `retention` in `config/storage.yaml` removes only `temporary` and `project/work-*` after 30 days, never the final
  video; `failed_days: null` keeps failures; `staging_stale_minutes: 60`. **[read]**

### 1.5 Error handling, retries, timeouts, cancellation

| Mechanism | Where | Value |
|---|---|---|
| Transient stages | `production/core.py:13` | `("voice","compose","render")` |
| Retry backoff | `core.py:14` | `(15, 45)` → 3 attempts |
| Wall-clock cap | `core.py:15` | `WALL_CLOCK_CAP = 360` |
| `scrub_interrupted()` | `core.py:40-69` | deletes artifacts a killed run left, keeping only ledger-`OK` stages |
| Shell / render timeouts | `pipeline.py:37-38` | `SH_TIMEOUT=600`, `RENDER_TIMEOUT=1800` |
| Kill | `pipeline._kill_tree()` | SIGKILLs the `ps` child tree **[read: `pipeline.py:41-57`]** |
| Node worker job timeout | `factory_worker.mjs:67-69` | 45 min; stale work 10 min; heartbeat stale 60 s |
| MPT | `mpt.py:80-87` | `timeout=1500` |
| Python queue subprocess | `queue.py:54-64` | **no timeout, no signal handling** |

`qa.py`'s ffprobe/ffmpeg calls have **no timeout** **[read: `contentos/qa.py:9-14`]**.

---

## 2. Two execution planes, one of which is single-lane

This is the single most important structural fact for concurrency.

**(a) Python job queue (`contentos/queue.py`).** Jobs are rows in `jobs` inside the workspace `ledger.db`. `claim()` opens
`isolation_level = None`, issues `BEGIN IMMEDIATE`, selects the highest-priority `queued` row and stamps
`status='running', started, pid=os.getpid()` — the only real lease in the Python side. `work()` wraps a
`ThreadPoolExecutor(concurrency)` and keeps that many futures alive; each `_run` spawns a **separate
`contentos.sh pipeline run <spec>` process**, so a pipeline crash cannot kill the worker. `recover()` flips `running` rows
whose recorded pid is dead back to `queued`. **[read: `queue.py:33-96`]**

**(b) ContentForge v1 filesystem worker (`contentos/adapters/v1/factory_worker.mjs`).** Exchange root
`VIDEO_FACTORY_ROOT` (default `~/.contentos/exchange` — **exists** **[ran]**) with `queue/ work/ done/ failed/ output/
state/ building/`. Its `tick()` returns immediately **if anything is in `work/`** — the explicit one-job-in-`work/` rule.
Claims are atomic directory **moves** `queue/<id>` → `work/<id>`. A single heartbeat file
`WORKSPACE/.factory_worker.heartbeat` acts as an advisory single-instance lock, and a live second worker is refused. A
dead worker's orphaned pipeline is stopped on boot; jobs left in `work/` are resumed with `MAX_RECLAIMS = 3`. Job ids are
`cfvg-<n>`. **[read: `factory_worker.mjs:58-75`, `:93`, `:293-350`, `:501-546`, `:599-615`, `:681-685`;
`adapters/v1/lifecycle.mjs:58-70`, `:86-96`]**

So: **the ContentForge path is inherently serial by design, and the Python path is bounded by `--concurrency` (default
2).** Neither is a resource-aware scheduler.

---

## 3. Capability inventory

### 3.1 Spine — deployed and wired

| Capability | Status | Evidence |
|---|---|---|
| Stage pipeline with gates and artifact resume | implemented | `pipeline.py:22, 254-263, 286-330` |
| HyperFrames lane, version pinned 0.8.114, absolute-path resolution | implemented | `package.json:6`, `hf.py:15-23`, KF-001 fix |
| MPT lane behind a Docker container | implemented | `pipeline.py:141-145`, `mpt.py:21` |
| 9-check technical QA (ffprobe/ffmpeg) | implemented | `qa.py:18-51`; thresholds in `config/quality.yaml` |
| Word-highlight captions from script words aligned to whisper.cpp ASR | implemented | `production/align.py:27`; `pipeline.py:130-138, 164-166`; pinned by `tests/test_pipeline_captions.py` |
| Export gate: `finalcheck` + atomic promote + sidecar-last | implemented | `export.py:125-193`, `finalcheck.py:17-58` |
| Approval gates `SCRIPT_APPROVED` / `PRODUCTION_APPROVED` / `PUBLISH_APPROVED` | implemented | `pipeline.py:309-314`, `:246-247`, `ledger.py:43-49` |
| `RESEARCH_APPROVED` enforcement | **partial** | written at `pipeline.py:298`; never read — no enforcement |
| Durable job identity + per-job dir + manifest lock | implemented | `storage.py:315-329, 398-437` |
| Job storage outside the repo, enforced | implemented | `storage.py:90-130` |
| Ledger with per-stage `runs` rows, costs, retries | implemented | `ledger.py:9-40` |

### 3.2 Visual reliability and quality

| Capability | Status | Evidence |
|---|---|---|
| Rule A — ≥ceil(scenes/2) distinct backdrops | implemented | `intelligence/visual.py:515-536` |
| Rule B — differ from last 5 shipped on ≥2 of 5 signature fields | implemented | `FIELDS=("structure","temperature","texture","base","accents")`, `MIN_DIFFERENT=2`, `WINDOW=5`, `visual.py:48-51, 437-448` |
| `--motif` escape hatch (fails → warns, reported never hidden) | implemented | `visual.py:518-519, 572` |
| Shipped-look ledger | implemented | `config/visual-languages.seed.json` (**2 entries** [read]) + `<workspace>/intelligence/visual-languages.json` under `file_lock` |
| 9 QA checks incl. `frozen_frames` WARN | implemented | `qa.py:48-50`; expected on text slides |
| Rendered-output gate (transitions, render log, captions, caption layering) | implemented, **standalone** | `production/visual_gate.py:87-169, 347`; used only by the mac-experiment `run.sh` and the `/audit-video` command |
| Safe-zone check (G6) | **implemented but not wired** | `visual_gate.check_safe_zones` `:295-320`; only caller is `tests/test_safe_zone.py` |
| Objective motion audit (ease inventory, ydif pops) | implemented, dev tooling | `production/motion_audit.py:21-76`; driven by `scripts/motion_compare.py` |
| Critic with dimensions + hard failures + recomputed verdict | implemented, skill-invoked | `production/critic.py:12-73` |
| Behavioural KF-004/-005 shader + caption-layer gates | implemented, synthetic tests | `visual_gate.py` + `tests/test_visual_gate.py` |
| Rule B with per-scene backdrops (KF-006) | **open** | `02-known-failures.md:KF-006` — signature reads stale `#root` CSS |
| Labelled contact sheets (`sheet/1`) + `timeline/1` | **experimental (shadow)** | `production/sheet.py`, `production/timeline.py:1-6` ("Nothing reads this file yet"), not in `contentos.sh` |
| Mac-validated shader transitions | **absent** | 0 of 14 shader transitions Mac-validated |

### 3.3 Creative / intelligence layer

| Capability | Status | Evidence |
|---|---|---|
| Capability registry | implemented | `config/capabilities.json`, `capabilities/1`, **93 entries (88 installed, 2 available, 1 candidate, 2 unavailable; 48 rules, 22 blueprints)** [read: `tests/test_direction.py` invariants] |
| Technique registry | implemented, all unverified | `config/motion-catalogue.json`, `motion-catalogue/1`, **70 entries**, seeder `heuristic-v1`, every entry `confidence:"unverified"`, `evidence_count:0`, `reviewed:false` |
| Design/palette/transition library | implemented, unvalidated | `config/design-library.json`, `design-library/2`, **76 entries** (13 frame_preset, 9 palette, 8 visual_style, 14 shader_transition, 32 css_transition); **0 validated on this Mac** |
| Style cards (`style/1`, 6 structural axes, dials, frame checklist) | **partial — new, untracked** | `intelligence/styles.py`, `config/styles/{blueprint-diagram,punch-split,slow-parallax-story}.json`, **all `status:"unvalidated"`, `evidence:[]`**; module says "Shadow mode: no pipeline reads cards yet" |
| Creative decision record + variety report (`creative-decision/1`) | **partial — new, untracked** | `intelligence/creative.py`; `propose`/`record`/`report`; writes only to `--out` and refuses to overwrite |
| Deterministic scored selection (no LLM) | implemented | `catalogue.query` bonuses; `designs.score`; `creative.score_card` = `2*fit + novelty + repeat_penalty` |
| Structural plan validator + coherence checks | implemented, standalone | `production/direction.py:268`, `production/director.py:160-190` |
| Storyboard (resolved plan + estimated) | implemented, planning only | `production/sceneplan.py:39-50`, `director.py:247-251` |
| Platform length/aspect budgets | implemented, standalone | `production/platforms.py:179`; `config/platforms.json` |
| Hook **selection** (choosing among hook options) | **partial** | `PURPOSES` includes `hook` and `director` forces scene 1 to be the hook; hook *scoring* exists (`pipeline.py:91`, `competitor.py:36`, `learn.py:110`); no module proposes/ranks hook options |
| Style-frame preview / approval of a style card | **absent** | grep for `preview|approv` inside `intelligence/` finds only the unused `requires_explicit_approval` boolean |
| Novelty / diversity enforcement | implemented, advisory only | Rule A/B `visual.py`; `check_distinct` `styles.py:190`; `variety_report` `creative.py` |
| Content-aware creative brief model | **partial** | `validate_brief` accepts `job, topic, content_type, length_kind, factual_density, register` — no audience, no learning objective, no hook, no platform |
| Performance feedback loop (provider stats, calibration, opportunity ranking) | implemented, advises only | `contentos/learn.py` (`MIN_N=5`, weights `W`, hook floor 55) |

### 3.4 Absent capabilities (verified by grep/absence of callers)

- Any scheduler, admission control, or resource-aware concurrency policy.
- Per-job isolation of the ledger — one SQLite file for all jobs.
- Per-job locks beyond `.manifest.lock` and the export/claim locks.
- Structured per-job logs, metrics emission, or progress events beyond the ledger rows and the dashboard.
- Music / SFX / ducking anywhere. `mpt.py` sets `--bgm-type=none`.
- Supplied-audio **consumption** by compose (see §6).
- Odia/Hindi voices, a lip-synced animated host, thumbnail images, an uploader.
- A dead-letter / backpressure mechanism for the queue.

---

## 4. G3 and G6 — verified state (do not assume fixed)

**G3, supplied audio — `partial`.** The provenance/rights half is real and **wired**: `production/supplied_audio.py`
(schema `supplied-audio/1`, rights vocabulary `owned|licensed|unknown`) has `ingest` (:250, byte-for-byte read-only copy of
the original), `verify` (:182, re-hash) and `publish_blockers` (:200-216, fails closed on a malformed record or hash
mismatch and blocks on `rights=unknown`). Callers: `pipeline.s_voice` raises `Blocked` if a record exists (so a different
Kokoro voice is never silently substituted) **[read: `pipeline.py:97-99`]**, `pipeline.s_export`/`s_publish` **[read:
`:228-230`, `:243-245`]**, and `export.export_job` raises `ExportRefused` **[read: `export.py:25, 130-132`]**. Tested by
`tests/test_supplied_audio.py`.

The **consumption** half is **absent**: the module header says "Nothing consumes the audio yet … a job that holds a
supplied-audio record STOPS at `voice`" **[read: `supplied_audio.py:5-7`]**. So you can supply audio and be forced to
stop; you cannot yet build a video around it.

**G6, safe zone — `partial`: implemented, unwired, and the zone numbers are hard-coded heuristics.**
`visual_gate.check_safe_zones` (:295-320) defaults to top 150 px, bottom 350 px, right 180 px strip on 1080×1920, detecting
"content" as neighbour luma steps > `EDGE_JUMP=0.20` occupying more than `MAX_ZONE_EDGE_FRACTION=0.01` of a zone (pinned
by `tests/test_safe_zone.py:183`). The module labels the zones "NOT published platform specs" **[read:
`visual_gate.py:192-194`]**, it cannot distinguish a caption from decoration, and the roadmap's acceptance condition —
zones marked `unverified` **in config** — is unmet because they live in code. The check is not called by the pipeline,
`contentos.sh`, or the mac-experiment `run.sh` **[read]**.

**Two documents are stale on this point and should be corrected by whoever owns them:** `04-visual-reliability-gate.md:351`
lists G3 and G6 as "Not built", and `06-video-factory-target-architecture.md:275` calls safe-zone "partial; new, small".
The code described above already exists on this branch, uncommitted. **[read]**

---

## 5. What is committed vs proposed vs running only in tests

| Kind | Examples |
|---|---|
| Committed and reachable from `./contentos.sh` | pipeline, queue/worker, storage/export, qa, preview, approve, research, competitor, dashboard |
| Committed, reachable only as `python -m …` or via a skill | `direction`, `director`, `platforms`, `critic`, `visual_gate` (incl. `safezone`), `motion_audit`, `sheet`, `timeline`, `intelligence.{catalogue,designs,visual}` |
| Committed + tests, but **no caller at all** | `visual_gate.check_safe_zones` (G6) |
| Untracked on this branch (new work) | `intelligence/creative.py`, `intelligence/styles.py`, `config/styles/*.json`, `production/supplied_audio.py`, and the test files `test_creative.py`, `test_styles.py`, `test_safe_zone.py`, `test_supplied_audio.py`, `test_job_day_folders.py` |
| Documented as proposals, not code | `docs/video-intelligence/06-video-factory-target-architecture.md` (target design), `07-prioritized-integration-roadmap.md` (stages), `docs/research/motion-design-integration/*` |

`registry/capabilities.yaml` at the repo root is a **planning graph**, not a live registry: no `contentos/` module reads it;
only `tests/test_core.py:31` touches it, to check provider names. `config/capabilities.json` is the authoritative
machine-readable registry (`direction.load_registry()` is the only loader the pipeline uses). **[read]**

---

## 6. Working-tree state at audit start

9 modified, 10 untracked. `git diff --stat`: **195 insertions, 14 deletions** across `AGENTS.md` (2), `dashboard.py` (2),
`export.py` (4), `pipeline.py` (11), `visual_gate.py` (**149**), `storage.py` (35), `storage_admin.py` (2),
`docs/STORAGE.md` (2), `tests/test_storage.py` (2). **[ran]**

Interpretation: the large added block is the safe-zone work in `visual_gate.py`; `storage.py`+`test_job_day_folders.py` are
the `jobs/YYYY/MM/DD/` day-folder change; `pipeline.py`/`export.py` are the supplied-audio wiring.

**This work is uncommitted and owner-held. Nothing in this audit stages, stashes, resets or discards it.** Any roadmap task
that touches these files must start from an owner decision about their disposition (see doc F, task P0-3).

---

## 7. Corrections to prior documents (evidence-backed)

| Claim in a prior doc | Verified reality | Source |
|---|---|---|
| `04-visual-reliability-gate.md:351` — "Not built: … supplied-audio ingest (G3), … safe-zone check (G6)" | Both exist as code on this branch (uncommitted). G3 is wired into the publish gate; G6 is implemented and unwired. | §4 |
| `06-video-factory-target-architecture.md:275` — safe-zone "partial; new, small" | Accurate for the *code*, misleading on wiring: no production caller exists. | §3.2 |
| `07-prioritized-integration-roadmap.md` G1 — "Track A captions use the proportional index at `pipeline.py:150`" | The shipped path now calls `align_words` via `caption_words` **[read: `pipeline.py:130-138`]** and `tests/test_pipeline_captions.py` asserts the proportional map is **gone**. G1 appears already fixed. | §3.1 |
| `docs/video-intelligence/05-…` §7 — "the standalone `remotion-dev/skills` licence was not re-checked (a prior project finding says it has no licence file)" | **Confirmed:** `contents/LICENSE` returns 404 and the API reports `license: null`. Unlicensed → must not be vendored. | doc A |
| `docs/factory-v2/04-licensing-matrix.md` — HyperFrames "Apache-2.0 … no action" | Correct, but incomplete: the pin is **43 releases behind** and known bugs fixed after 0.8.114 directly affect this project's output geometry and FFmpeg version. | doc A, doc H |
| `motion-design-integration/00` — "0 of 76 library entries are Mac-validated" | Still true. Also true for the 3 new style cards (`evidence: []`). | §3.3 |
| `docs/research/motion-design-integration/01` §2.14 — GSAP licence "not reconciled here; the owner should read the current GSAP licence page" | Resolved: GSAP is now free for commercial use under Webflow's Standard "No Charge" GSAP License (effective 2025-04-30); the only prohibited use is building competing no-code animation builders. | doc A |

---

## 8. Evidence gaps in this document

- **No test suite was run in this session.** `./contentos.sh` would execute the pipeline wrapper and the tests need
  `~/.contentos/venv`; running them is a state-changing safety decision I did not take unilaterally on a dirty tree. The
  last suite state recorded anywhere is 363 passed / 1 failed / 2 skipped **[doc: `07-…:§6`]**, with the known failure
  `tests/test_core.py::test_local_beats_paid_even_when_both_healthy`. **Treat the suite state as [carried].**
- **No render was performed**, so every timing, memory and thermal figure a concurrency design needs is **unmeasured**
  (§doc D §1). This is the largest single gap in the whole audit set.
- The uncommitted WIP was **read, not executed**.
- `factory_worker.mjs`'s interaction with the Python queue when *both* run against the same workspace is **unverified**
  — I read both designs; I did not observe them together.
- `VIDEO_FACTORY_CACHE_DIR` / `<workspace>/shared-cache` is declared and printed but **no code path writes to it**
  **[read: `storage.py:123-130`, `storage_cli.py:20`]**. Its intended role is **unverified**.
- MPT's internal task-store behaviour under two simultaneous jobs is outside this repo and **unverified**.
