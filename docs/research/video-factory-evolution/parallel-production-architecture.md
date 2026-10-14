# D — Parallel production architecture

**Design only. Nothing in this document is implemented, and no measurement was taken in this session.** Where a number is
required and has not been measured, it says so and names the measurement that would settle it. The single most important
sentence in this document: **on a 24 GB machine, HyperFrames itself already parallelises internally and its own upstream
documentation records a heap OOM on exactly 24 GB — so concurrency must be added around the renderer, not by multiplying
`hyperframes render` processes.**

Machine under design: Apple M5 Pro, 15 logical cores (5P + 10E), **24 GB** unified memory, macOS 27.0.1, FFmpeg 9.0.2,
HyperFrames 0.8.114, 642 GB free.

---

## 1. Phase A — Where the bottleneck actually is

### 1.1 Stage-by-stage profile (from source reading, not measurement)

| Stage | Dominant resource | Blocks other jobs? | Safe to run concurrently across jobs? | Evidence |
|---|---|---|---|---|
| `brief` | agent/LLM time, no local compute | No | Yes — but needs an LLM, so it is out of scope for a deterministic local worker | `pipeline.py` stage list |
| `script` | LLM time | No | Yes, same caveat | `pipeline.py` |
| `voice` | **CPU-bound** (Kokoro ONNX inference per line) | No | Yes, with a per-stage cap | `pipeline.py:97-99`; `TRANSIENT_STAGES` includes `voice` |
| `compose` | Light CPU; writes `project/` (HTML + `gsap.min.js`) | No | Yes — **but shares a global frame cache at render time**, not here | `pipeline.py:148-191` |
| `render` | **Heavy**: N Chrome processes + FFmpeg encode; intra-render parallelism already automatic | No lock, but resource-exclusive in practice | **Yes, with a low cap** — this is the constrained stage | doc A §HyperFrames findings |
| `qa` | **CPU-bound FFmpeg decode** (blackdetect, freezedetect, ebur128 ×2 passes) | No | Yes, with a cap; **no timeout today** | `qa.py:9-14`, `:18-51` |
| `package` | CPU-light | No | Yes | `pipeline.py` |
| `export` | **I/O-bound**: sha256 + fsync + `os.replace` of a large file | Holds a per-job lock only | Yes, but cap at 1–2 to avoid disk thrash | `export.py:125-193` |
| `publish` | Dry run only | No | n/a — disabled | `config/youtube.yaml` |

### 1.2 Where serialization **actually** occurs

It is a common error to call the pipeline "globally serial because one command does one job". The real serialization
points, established from code, are:

1. **The ContentForge v1 Node worker is single-lane by explicit design.** `tick()` returns immediately when anything is
   in `work/` — the one-job-in-`work/` rule — and claims are directory **moves**. One worker per workspace is enforced by
   a heartbeat-file lock; a second live worker is refused. **[read: `factory_worker.mjs:599-615`, `:501-514`, `:681-685`;
   `lifecycle.mjs:58-70`]** This is the hard constraint on the ContentForge path, and it is intentional.
2. **One SQLite ledger for the whole workspace.** Every stage of every job writes `runs` rows to the same
   `<workspace>/ledger.db`, and `queue.claim()` uses `BEGIN IMMEDIATE`. **No `busy_timeout` is set anywhere**, so the
   sqlite3 default (~5 s) applies, and concurrent writers can raise `database is locked`. **[read: `storage.py:157-158`,
   `ledger.py:21-27`, `queue.py:46`]**
3. **One MPT container.** `CONTAINER = "moneyprinterturbo-api"` with a shared `config.toml` and the workspace mounted at
   `/workspace/projects`. Two concurrent MPT jobs share one task store. **[read: `mpt.py:16-21`, `:97-101`]**
4. **The Python worker pool size** is whatever `--concurrency` says (default 2) and cannot exceed it.
5. **A hung job permanently consumes a pool slot.** `queue._run`'s `subprocess.run` has **no timeout and no signal
   handling** **[read: `queue.py:54-64`]**, so effective concurrency silently degrades below the configured value.
6. **The renderer's own internals** (see §1.3) — this is the one that constrains how far you can scale.

### 1.3 The renderer is already parallel — and already has a documented ceiling on this machine's RAM

From the upstream HyperFrames source and CLI help **[read]**:

- `hyperframes render` has `--workers/-w`, **default `auto`**. Each worker is a **separate Chrome process at ~256 MB RAM**.
  Auto-sizing is bounded by four ceilings — CPU, system RAM, **the V8 heap**, and frame count — and records which one
  bound it.
- A capture-cost multiplier *reduces* worker count for heavy work (shader transitions +2, `requestAnimationFrame` +1,
  `iframe` +0.5) to avoid compositor starvation.
- **Documented field failure, and it is on a 24 GB machine:** upstream's own heap-advisory text records *"field OOM,
  0.7.66 on 24GB: auto-picked 6 workers blew Node's default ~4GB heap."* Auto-sizing is now capped at the heap budget and
  the suggested remedy is `NODE_OPTIONS=--max-old-space-size=8192` or an explicit `--workers N`.
- The producer server exposes `--max-concurrent-renders` (**range 1–10, default 2**) and `--batch --batch-concurrency`
  (**default 1**, documented as such "because each render already parallelizes across workers").
- `drawElementImage`/`htmlInCanvas` capture **forces 1 worker**: upstream states Chrome's `CanvasDrawElement` is
  non-deterministic across concurrent browser instances due to paint-cache races and SwiftShader contention.
- Low-memory mode auto-engages at **total RAM ≤ 8 GB** and pins 1 worker.

**Consequence for the design.** One `hyperframes render` is *already* a multi-process parallel pipeline. Adding N
simultaneous `hyperframes render` processes multiplies Chrome count and Node heap pressure against one 24 GB budget, and
one of them may be silently pinned to 1 worker by the determinism guard. The correct scaling axis is therefore a **small
number of render processes, each explicitly sized**, not "N× auto".

- **Per-render total RSS and per-frame CPU time: NOT DOCUMENTED — must be measured.** Only the ~256 MB/worker figure is
  documented.
- **Whether composing two HyperFrames renders in one workspace is byte-for-byte deterministic: NOT VERIFIED.**

### 1.4 Shared state that is not per-job isolated (the collision surface)

| Shared object | Path / constant | Risk if two jobs run | Evidence |
|---|---|---|---|
| Workspace ledger | `<workspace>/ledger.db` | Writer contention / `database is locked`; both jobs' rows interleave | `storage.py:157`, `ledger.py:21` |
| ContentForge exchange manifest | `manifest.json` beside `state/` | **Fixed filename**; only safe because exactly one worker may run | `factory_worker.mjs:236` |
| Worker lock/heartbeat | `WORKSPACE/.factory_worker.heartbeat` | One fixed file for the whole workspace | `factory_worker.mjs:93` |
| HyperFrames global frame cache | `<tmpdir>/hyperframes-extract-cache-<uid>` | Content-addressed and shared on purpose; bounded by disk, **not** by render — a disk-growth surface | upstream CLI |
| HyperFrames config | `~/.hyperframes/config.json` | Telemetry + DE parallel-router circuit-breaker. Upstream code notes **there is no file locking** and tolerates lost writes | upstream source |
| DE parallel router | process-wide env + module-level flags | Upstream states it is only safe for **sequential** renders; deliberately left unset at `--batch-concurrency ≥ 2` | upstream source |
| Visual-languages ledger | `<workspace>/intelligence/visual-languages.json` (+`.lock`) | Locked on write — OK, but read-modify-write across a worker boundary needs care | `intelligence/visual.py:419-420, 455` |
| Catalogue / design evidence overlays | `<workspace>/intelligence/catalogue-evidence.json`, `design-evidence.json` | **Unlocked** shared overlays | `catalogue.py:47-48`, `designs.py:55` |
| **Same-`content_id` job artifacts** | `audio/%02d.wav`, `project/`, `work-*`, `video.mp4`, `qa.json`, `metadata.yaml`, `export-result.json` | **No job-level mutex exists.** Only `.manifest.lock` and the export/claim locks | `storage.py:407, 424`; `export.py:117` |
| MPT container | `moneyprinterturbo-api` + shared `config.toml` | Two MPT jobs contend for one task store | `mpt.py:21, 97-101` |
| Research / migration outputs | `<workspace>/research/<slug>/dossier.json`; `<workspace>/recovery/migrations/<UTCts>.json` | The migration name is **second-resolution** — two migrations in one second collide | `research.py:20`, `storage_admin.py:248-249` |

`VIDEO_FACTORY_CACHE_DIR` / `<workspace>/shared-cache` is declared and printed but **no code path writes to it**
**[read: `storage.py:123-130`, `storage_cli.py:20`]**. Whether it was reserved for concurrent use is **unverified**.

---

## 2. Phase B — Job orchestration model

### 2.1 Options considered, and the honest verdict on each

| Option | Verdict | Why |
|---|---|---|
| **Bounded pool of isolated worker processes + filesystem job manifests** (extend what exists) | **RECOMMENDED** | The code already spawns one process per job (`queue._run` → `contentos.sh pipeline run`) and already has a manifest, a ledger, per-job dirs and a lock primitive. The smallest correct change is to add admission control, per-stage limits, timeouts and leases — not a new system. |
| Persistent queue with durability guarantees | **Already satisfied** | The SQLite `jobs` table **is** a durable queue, and `claim()` already does an atomic `BEGIN IMMEDIATE` lease with a pid stamp. No broker needed. **What is missing is not durability but timeout, cancellation, and resource awareness.** |
| Temporal / workflow engine | **REJECT** | No existing integration path, a server dependency for a single-machine pipeline, and the registry already marks `contentos` as the execution plane. Adding it would violate the project's "no second orchestration framework" rule. |
| Separate queues for heavy vs light stages | **ADAPT, minimally** | Implement as **per-stage concurrency limits on one queue**, not as two queues. Two queues would double the state machine and the recovery logic for no gain on a single machine. |
| Detached background processes with no durable status | **REJECT** | Explicitly excluded by the brief. |

### 2.2 Job lifecycle and states

Today's statuses are `queued → running → done | blocked | failed` (plus `recover()` rewriting dead `running` → `queued`)
**[read: `queue.py:33-96`]**. Proposed superset, keeping the existing names so nothing downstream breaks:

```
queued ──admit──▶ leased ──▶ running ──▶ done
  ▲                 │           │
  │                 │           ├─▶ blocked   (a gate is unmet; resumable, NOT a failure)
  │                 │           ├─▶ failed    (terminal for this attempt)
  │                 │           └─▶ cancelled
  └──reclaim────────┴───────────────┘   (lease expired: pid dead / heartbeat stale)
```

Rules that make it safe:

- **`leased` ≠ `running`.** `leased` means "ownership claimed, resources not yet granted". Admission control can hold a
  job in `leased` while it waits for a render slot, which is exactly the backpressure knob the system lacks.
- **`blocked` is a first-class resumable state, not an error.** The pipeline already distinguishes it; it must not be
  retried on a backoff schedule (a gate will not un-gate itself).
- **Leases carry an owner and an expiry.** Reuse the existing pid stamp; add a heartbeat timestamp written by the
  executing worker. `recover()` becomes "reclaim jobs whose lease expired", preserving today's behaviour but making the
  criterion explicit.
- **Terminal states never silently mutate.** A second run that finds a `done` job must not re-enter it; that already
  holds for `exported` **[read: `pipeline.py:293-294`]**.

### 2.3 Per-job isolation boundary

**The boundary is the job directory** `<workspace>/jobs/YYYY/MM/DD/<job-id>/`. Everything a stage writes for a job must be
inside it. Enforce these four rules before any concurrency work lands:

1. **One job = one `content_id` = one directory, and a job directory is owned by exactly one running lease.** Add a
   `<job>/.run.lock` (the same `fcntl.flock` primitive already in `storage.file_lock`) taken for the duration of a run,
   in addition to today's short-lived `.manifest.lock`. Two `pipeline run` calls for the same `content_id` must make the
   second one refuse loudly rather than interleave writes into `audio/`, `project/` and `video.mp4`.
2. **Immutable inputs.** The spec and any supplied audio are read-only for the whole run (`supplied_audio` already copies
   byte-for-byte read-only — extend that discipline to the spec).
3. **No stage writes outside its job dir.** The three current offenders are the shared ledger, the `intelligence/`
   overlays, and (for the MPT lane) the shared container. The ledger is fine if writes are made short and busy-timeout is
   set; the overlays must take the existing lock; the MPT lane needs its own concurrency limit of 1.
4. **Cancellation is scoped to the job's process group.** Node already does this correctly (`killProcessGroup`
   SIGTERM→SIGKILL); the Python queue must adopt it. Cancelling job A must never touch job B's files or the shared tools.

**A failure in job A must not corrupt job B.** Under rules 1–4 the only remaining cross-job coupling is resource exhaustion,
which §3 handles with admission control rather than with locking.

### 2.4 Retry, cancellation and idempotency semantics

| Concern | Today | Proposed |
|---|---|---|
| Retry | `TRANSIENT_STAGES=("voice","compose","render")`, backoff `(15,45)`, `WALL_CLOCK_CAP=360` | Keep. Add the rule that a retry re-runs **only** the failed stage and after, because resume is artifact-sentinel based |
| Resumability | Sentinel file existence; the sentinel is deleted on failure so a retry cannot trust a half-built artifact | Keep — this is already the correct instinct. Add that the **sentinel must be written last** inside each stage, and prefer a per-stage `.done` marker over keying off a substantive artifact |
| Idempotency | Stages that overwrite their own outputs are idempotent; `export` already short-circuits on an identical sha256 and refuses a claimed-but-different video | Keep. Extend the short-circuit to `compose` and `render` |
| Cancellation | Node: clean. Python queue: **absent** | Add a timeout and process-group kill to `queue._run`; make `cancelled` a terminal state |
| Partial artifacts | `scrub_interrupted()` deletes artifacts from stages the ledger did not record `OK` | Keep; make it run at the start of every run, as `queue.work` already does via `recover()` |
| Leases | pid stamp only; a pid can be recycled | Add heartbeat mtime, as the Node worker already does |

---

## 3. Phase C — Resource-aware concurrency

### 3.1 The budget, and why the numbers are small

Measured hardware: **24 GB** unified memory, 15 logical cores (5P + 10E), 642 GB free disk. Apple Silicon shares one memory
pool between CPU and GPU, so "RAM available to renderers" is the whole machine's memory minus the OS, minus whatever the
owner is doing interactively.

Reserve for the OS and interactive work. A defensible starting envelope, to be confirmed by measurement, is:

- **Memory ceiling for factory work: ~14 GB** (leaving ~10 GB for macOS, the browser the owner is using, and the agent
  itself).
- **CPU ceiling: ~10 of 15 logical cores**, leaving the efficiency cores and headroom so the machine stays usable.

Against that envelope, the renderer's documented behaviour matters more than any invented formula:

- Each Chrome worker ≈ **256 MB** (documented). One auto render on a 24 GB box has already been recorded upstream as
  picking 6 workers and **exhausting Node's default ~4 GB heap**. So a single auto render can plausibly want several GB.
- Therefore: **cap simultaneous render processes at 2** (which is also HyperFrames' own `--max-concurrent-renders`
  default), and give each an explicit `--workers` value rather than `auto`, so two renders cannot each independently
  decide to spawn six Chrome processes.
- Set `NODE_OPTIONS=--max-old-space-size=8192` for render processes so the heap is not the binding ceiling at 4 GB.

### 3.2 Proposed policy (configurable, conservative defaults)

```yaml
# proposed: config/concurrency.yaml  (does not exist yet)
max_active_jobs: 2 # top-level admission: how many jobs may be in `running`
per_stage:
  voice: 2 # CPU-bound, cheap to over-commit slightly
  compose: 3 # light; mostly HTML generation
  render: 2 # the real ceiling — see the renderer note above
  qa: 2 # FFmpeg decode; no timeout today
  export: 1 # I/O; one large atomic promote at a time
  mpt: 1 # one shared container; hard limit
budget:
  memory_gb: 14
  cpu_cores: 10
  min_free_disk_gb: 50 # refuse to start a render below this
  headroom_pct: 25 # keep this much of the ceiling unused
overrides:
  node_options: "--max-old-space-size=8192"
  hyperframes_workers: 2 # explicit, never `auto`, once concurrency > 1
pause_on:
  memory_pressure: true
  thermal: true # macOS will throttle; do not fight it
```

- **Admission control.** A job entering `render` waits in `leased` until both `per_stage.render` and the memory/CPU
  budget allow it. Note the honest trade-off: with `max_active_jobs: 2` and `per_stage.render: 2`, the queue is only
  slightly better than serial for render-heavy work — **that is the correct starting point on 24 GB, and the benchmark in
  §6 is what would justify raising it.**
- **Backpressure, not unbounded growth.** `queue add` is already cheap and durable. Keep accepting submissions; the
  ceiling is on *running*, never on *queued*. Add a watermark that warns when `queued` exceeds a configured depth.
- **Automatic reduction.** If memory pressure or thermal throttling is observed, stop admitting new render slots and let
  running jobs finish; never kill a running render to make room (that would waste the most expensive work in the system).
- **Fair scheduling.** Priority first (the queue already orders `priority DESC, id`), then **age**, so one long job cannot
  starve the queue. Cap a single job's share of render slots at 1 when more than one job is waiting.
- **Operator override.** `--concurrency`, `--max-renders`, `--no-admission` with the effective policy printed by
  `doctor`, so an override is never silent.

### 3.3 What cannot be decided until measured

1. **The safe first concurrency target.** Everything above is a *conservative floor* derived from documented behaviour.
   The actual saturating point needs §6.
2. **Per-render peak RSS and CPU.** Not documented anywhere. Without it, `memory_gb: 14` is an estimate.
3. **Whether two simultaneous HyperFrames renders are byte-reproducible.** The determinism guard already forces 1 worker
   in one capture mode; whether two *processes* interfere through the shared frame cache or `~/.hyperframes/config.json` is
   unverified.
4. **Whether `qa` (FFmpeg decode, no timeout) or `voice` (ONNX) binds before `render` does.** If `voice` binds first, the
   render cap is not the right knob.
5. **Disk growth rate of the global frame-extract cache** over repeated runs — a slow disk-full failure mode.
6. **Thermal behaviour on sustained load** — a machine that is fine for two renders for ten minutes may throttle at forty.

---

## 4. Phase D — Protecting running work (race catalogue)

| # | Race | Concrete failure | Required guard |
|---|---|---|---|
| 1 | Two runs, same `content_id` | Interleaved writes to `audio/`, `project/`, `video.mp4`; a resume trusts the other run's artifact | Per-run `<job>/.run.lock`; refuse the second run |
| 2 | Two runs, different `content_id`, same input filename | Both derive the same intermediate name | Names must be derived from `content_id` and a run id, never from the input filename |
| 3 | Concurrent ledger writes | `database is locked` after ~5 s | Set `busy_timeout`; keep write transactions short; retry once on lock |
| 4 | Simultaneous `export` | Two atomic promotes contend on the same staging dir | `per_stage.export: 1`; the export lock is already per-job, keep it |
| 5 | Cancelling job A | Kills the shared worker, or deletes shared caches | Cancel the job's **process group** only; never touch caches or shared tools |
| 6 | A worker crash | Leaves `running` rows that block the queue forever | Heartbeat-based lease reclaim (extend today's pid check) |
| 7 | `recover()` / `scrub_interrupted()` | Deletes another live job's artifacts | Scope recovery to expired leases only; never scan the whole workspace for cleanup while jobs run |
| 8 | `visual claim` / evidence overlays | Read-modify-write lost update across workers | Take `storage.file_lock` around every write, not just `visual claim` |
| 9 | Two MPT jobs | Both drive one container | `per_stage.mpt: 1` |
| 10 | Two migrations in one second | Collide on `<workspace>/recovery/migrations/<UTCts>.json` | Add the job id or a uuid to that filename |
| 11 | Global frame cache | Unbounded disk growth under repeated concurrent renders | Include it in `storage inventory`; cap it; do not delete it while a render is live |
| 12 | `~/.hyperframes/config.json` | Lost writes (upstream notes **no locking**) | Do not run a render configuration that depends on it while `max-concurrent-renders ≥ 2`; treat it as read-mostly |
| 13 | DE parallel router | Non-determinism / wrong frames when two renders are in flight | Keep `HF_DE_PARALLEL_ROUTER` unset for any run at concurrency ≥ 2 |
| 14 | Pointer-like renames of deterministically-named outputs | One job overwrites another's caption/cue file | Derive every output name from `content_id` + run id (same rule as #2) |

**Shared and read-only is fine.** Immutable tools (`node_modules/.bin/hyperframes`), templates
(`contentos/templates/gsap.min.js`), registries in `config/`, and the pinned skill set can be shared by every job because
nothing writes to them. The isolation rule is about **writable** state only.

---

## 5. Phase E — Quality and correctness under concurrency

### 5.1 Test matrix

| # | Test | Type | Asserts |
|---|---|---|---|
| 1 | Enqueue N independent jobs, distinct `content_id` | integration | All reach `done`; one directory per job; no shared file written |
| 2 | `content_id` collision | negative | Second run refuses; first job's artifacts unchanged (hash before/after) |
| 3 | Two jobs, same input filename | unit | Derived intermediate names differ |
| 4 | Resource-cap enforcement | unit | A stubbed budget admits exactly `max_active_jobs`; the rest stay `leased`, never `running` |
| 5 | Cancel while `queued` | integration | Leaves `cancelled`; no process spawned; no artifact written |
| 6 | Cancel while `running` | integration | Process group dies; other jobs' pids untouched; job is resumable |
| 7 | Worker crash mid-render | integration (fault injection) | Lease expires; job reclaimed; no other job's artifact removed |
| 8 | Partial artifact detection | unit | A truncated `video.mp4` fails `finalcheck`; export refuses |
| 9 | Interrupted `voice` then resume | integration | Stages ≤ `voice` skip; `voice` re-runs; no duplicate audio files |
| 10 | Retry without duplication | integration | Ledger shows one `OK` row per stage; artifact count stable across attempts |
| 11 | Stale manifest vs live run | negative | A second run does not consume the first's manifest |
| 12 | Disk-full condition | unit (simulated) | Admission refuses below `min_free_disk_gb`; exit is `blocked`/`failed`, never a half-exported final |
| 13 | Memory pressure | unit (simulated) | New render slots withheld; running jobs not killed |
| 14 | FFmpeg / browser process failure | integration (fault injection) | Classified retryable; backoff applied once; third failure is terminal with a reason |
| 15 | Per-job logs and error attribution | integration | Each job's failure names its own job id; no cross-job log interleaving |
| 16 | Final render integrity under load | integration | Two concurrent renders both pass all 9 QA checks and `finalcheck` |

### 5.2 Acceptance criteria

- **Data isolation:** for every test above, a hash taken over job B's directory tree is identical before and after any
  operation on job A (including cancellation, crash, retry and cleanup).
- **No cross-job artifact reuse:** a resume never reads a file that a different `content_id` produced. Assert by
  provenance, not by filename.
- **Reproducible resume:** interrupted-then-resumed produces the same artifact set as an uninterrupted run.
- **Failure containment:** injecting a failure into one job leaves every other job's state machine unchanged and its
  artifacts intact.
- **Bounded resources:** at no point does the number of `running` jobs exceed `max_active_jobs`, nor the number of
  concurrent renders exceed `per_stage.render`.
- **Output quality unchanged:** every exported final still passes `finalcheck` + the 9 QA checks, and the critic result
  distribution does not shift (compare over ≥3 runs — critic scores vary run to run, so report the spread, never an
  average that hides it).

---

## 6. Phase F — Capacity experiment (designed, NOT executed)

**Nothing below has been run.** Do not claim any concurrency figure before this produces data.

1. **Baseline.** One representative job end to end. Record per stage: wall time, peak RSS, CPU time, disk written,
   temporary storage, and the render's own `boundBy` reason and chosen worker count.
2. **Sweep.** Repeat at 1, 2, 3 and 4 simultaneous renders, with a **mix** of light (short, few scenes, no shaders) and
   heavy (long, many scenes, shader transitions) jobs. For each run set an explicit `--workers`, not `auto`, and record
   both settings.
3. **Measure:** throughput (completed jobs/hour), per-job latency (median and p95), error rate, peak RSS, peak CPU,
   sustained-load thermal behaviour, and interactive responsiveness (a simple repeated UI action).
4. **Control for cache warming** — run each configuration at least twice and discard the first.
5. **Find the saturation point** where throughput stops improving or latency degrades super-linearly, then **reserve 25 %
   headroom** below it. That, not a target number, is the policy default.
6. **Define the adaptive fallback:** the observed signal (memory pressure, thermal state, or rising p95 latency) that
   triggers automatic reduction to fewer workers.

**Report capacity as measured jobs/hour with the stage-level bottleneck named.** The brief asks for 5–10 concurrent
videos; on 24 GB with a renderer that already parallelises internally, **the honest expectation is that the safe ceiling is
well below 10 simultaneous renders, and that a 5-job throughput target is met by pipelining stages (some jobs rendering
while others are in voice/qa/export) rather than by 5 concurrent renders.** This hypothesis is exactly what §6.2 tests.

---

## 7. What to build, in order (detail and acceptance criteria in doc F)

| Step | Change | Why it is first |
|---|---|---|
| 1 | Per-run `<job>/.run.lock` + heartbeat lease | Without it, concurrency corrupts work. It is also useful at concurrency 1. |
| 2 | `busy_timeout` + short write transactions on the ledger | Removes the most likely spurious failure |
| 3 | Timeout + process-group kill in `queue._run` | A hung job currently consumes a slot forever; this restores the configured concurrency |
| 4 | Explicit per-stage concurrency limits (config file) | The knob, with conservative defaults, before any tuning |
| 5 | Admission control + `leased` state + backpressure warning | Converts "unbounded submission" into "bounded running" |
| 6 | Per-job structured log + stage metrics | Nothing can be tuned or diagnosed without this |
| 7 | The §6 benchmark, then set the policy from data | Never set a concurrency number before measuring |
| 8 | Fix the shared-writer races: overlays under lock, migration filename, MPT cap | Low risk, removes cross-job coupling |
| 9 | **Only then** consider raising limits | Expansion is a data decision |

**Do not** build a workflow engine, a message broker, a second queue, or detached unowned background workers. The durable
SQLite queue, the per-job process model, the manifest and the flock primitive already exist and are sufficient.
