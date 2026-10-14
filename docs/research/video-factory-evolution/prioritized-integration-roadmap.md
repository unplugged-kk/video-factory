# F — Prioritized integration roadmap

**The prime directive for everything below: the current system works. Do not break it.**
Every task is additive; every task is removable by deleting the files it creates; nothing changes a render, a gate, a
threshold, a `config/*.yaml` file or a passing test. Rollback is stated per task.

### Verified starting point (measured this session)

| Fact | Value | How |
|---|---|---|
| HEAD | `ec4eb774ef66710533e0068dd6b1b7d9b094a2fc` | `git rev-parse HEAD` **[ran]** |
| Branch | `feature/labelled-contact-sheets`, 19 `git status` lines (18 pre-existing owner WIP + this audit's docs dir) | **[ran]** |
| **Test suite** | **548 passed, 1 skipped, 0 failed** (44 s) | `~/.contentos/venv/bin/python -m pytest tests -p no:cacheprovider -q` with `PYTHONDONTWRITEBYTECODE=1` **[ran]** |
| Prior baseline docs claim | "363 passed / 1 failed / 2 skipped", and later "495 passed, 1 skipped" | **[doc]** — **both superseded.** There is **no known failing test** on this tree |
| Stash | empty | **[ran]** |

**A safety-protocol discrepancy to settle in the next T0.** The Master Plan (§4) records the reference tracked-diff hash as
`f6f02110ad3792eb9fa8bda1da6dc85a245192b6e31930e094f0122200f390a7`. Measured today it is
`7655d5734ec1555c192baf3786fd5baee3f6317a971b9f3e913c8bba07d23742`. HEAD is unchanged (`ec4eb77`), so **the working-tree
WIP itself has evolved since that plan was written** — and **that change is not from this audit**: this session edited no
code and created only the new `docs/research/video-factory-evolution/` folder (verified: 0 unexpected tracked-file
changes, 0 changes under `config/` or to `package.json`). Any task that compares against the documented reference must
**re-derive the baseline with the snapshot script** rather than trusting the recorded constant.

This matters for the safety protocol: because the suite is **green**, any new failure is caused by the change under test.
Do not carry forward the old "1 known failure" allowance — it no longer exists.

### Working conventions to reuse (already established in this repo — do not re-invent)

`docs/research/motion-design-integration/implementation-plan/` already defines a **master plan with a safety protocol**: a
snapshot script, an owner-WIP hash block, a protected-file hash block, a per-task stop-condition list, a report format, and
**an independent verifier session for every task** ("the implementer never grades its own work"). **Continue that
convention.** Do not run two tasks in one session.

### Status of the existing plan (do not re-do these)

| Task | Status | Evidence |
|---|---|---|
| T0 preflight | **DONE, verified PASS** | run log; gate **CLEARED** |
| T1 pinned-skill review | **DONE** | `T1-pinned-skill-review.md`; recommendation: add nothing, owner-decide `hyperframes-audio` |
| T2 style cards | **DONE, verified PASS** | 3 cards, all `unvalidated`, all 6 axes pairwise distinct, 32 tests |
| T3a creative decision + variety | **DONE** (verifier pending in the log) | `creative.py`; 19 tests |
| T3b critic `style_fidelity` | **SKIPPED** by owner | do not build unless asked |
| T4–T10 | **NOT STARTED** | T4 checkpoint, T5 timeline fields, T6 negative controls, T7 cue audibility, T8 SFX listening, T9 bake-off, T10 close-out |

**The ContentForge prerequisite is resolved.** The run log records the owner's ruling: ContentForge is a separate repo and is
**not** a prerequisite for these Video Factory changes; **gate CLEARED**. Independently, ContentForge is a live system
(CURRENT_ARCHITECTURE 2026-10-02, decision layer built and deployed, currently on `feat/auth0-migration`) that **owns**
decisions, research and publication. **Nothing in this roadmap requires a ContentForge change, and no new direct
factory→ContentForge call may be introduced.**

**Correction to two prior documents:** `04-prioritized-roadmap.md:3` and `00-executive-summary.md:13` still say
"BLOCKED on the ContentForge prerequisite". Both are stale — the gate was cleared on 2026-10-12.

---

## Tier 0 — Protect and correct (all safe now; do these first)

| ID | Task | Depends on | Benefit | Scope / modules | Risks | Tests | Measurable acceptance | Effort | Rollback | Blocked by |
|---|---|---|---|---|---|---|---|---|---|---|
| **R-1** | **Owner decision on the uncommitted WIP** (9 modified, 10 untracked). Decide: commit the safe-zone + supplied-audio + day-folder work as its own change, split it, or park it. | nothing | Removes the largest source of "do not touch" friction; the suite is already green **with** this WIP, so committing it locks in a verified state | none (a decision, then a commit by the owner) | If it is parked, every later task keeps a six-file no-go zone | suite must still be 548/0 after the decision | Owner states the disposition; HEAD moves to a commit that includes the WIP, or the WIP is explicitly frozen | **S** (owner time) | n/a | owner only |
| **R-2** | **Correct the stale documents.** Three verified contradictions: (a) `04-visual-reliability-gate.md:351` lists G3 and G6 as "not built" — both exist; (b) `06-…-target-architecture.md:275` calls safe-zone "partial" without noting it has **no production caller**; (c) the two "BLOCKED on ContentForge" lines. Also G1 ("Track A uses the proportional index") is already fixed — `pipeline.py:130-138` calls `align_words`. | nothing | Stops future agents acting on false premises. This is the highest ratio of value to risk in the whole roadmap | `docs/` only | none — docs only | none needed | Each corrected line cites the code path that contradicts it | **S** | revert the doc edit | nothing |
| **R-3** | **Decide the disposition of the new audit docs** (`docs/research/video-factory-evolution/`). They are untracked; the owner commits or deletes. | nothing | Keeps the docs out of the "unknown untracked" pile | docs only | none | none | Owner has explicitly committed or discarded them | **S** | delete the folder | owner only |
| **R-4** | **Record the entry-point naming convention.** A safe-zone check exists as `visual_gate check_safe_zones` and a `safezone` subparser, but **nothing calls it**, and `contentos.sh` has no `safezone` command. Decide whether it becomes a QA step (a behaviour change) or stays a manual tool and is documented as such. | R-1 | Removes an ambiguity that will otherwise be rediscovered | decision + possibly `docs/` | If it is wired into `s_qa`, that **changes pipeline behaviour** and needs its own render test | if wired: a seeded fault must fail the check | Either "wired and proven on a seeded fault" or "documented as manual-only, not part of QA" | **S–M** | unwire the call | R-1 (do not touch `visual_gate.py` while it is owner WIP) |

---

## Tier 1 — Cheap creative wins (already specified; **reference the existing task files, do not re-write them**)

These are the next tasks in the existing plan and remain the best value per unit of risk. **Full instructions already exist;
this roadmap only records their place in the order.**

| ID | Task | Existing task file | Depends on | Blocked by |
|---|---|---|---|---|
| T4 | Advisory style-frame checkpoint (labelled `sheet/1` of 3–5 style frames + an approval record; **advisory, not a new blocking gate**, with a lite path for Shorts) | `T4-style-frame-checkpoint.md` | T2, T3a | **Real dependency: `sheet.py` fails closed on this Mac** (FFmpeg 9.0.2 has no `drawtext`). Either use `./contentos.sh preview … --sheet`, or accept an unlabelled JSON manifest. **Do not** use `--allow-unlabelled` as a substitute for the labelled artifact |
| T5 | Additive `timeline/1` fields (cues, beats, transition windows, review markers, `timing_trust`) — shadow only, old timelines must still validate | `T5-timeline-additive-fields.md` | T3a | nothing |
| T6 | Gate negative-control tests (prove the gates can fail) | `T6-gate-negative-controls.md` | T5 | nothing |
| T7 | Cue-audibility measurement, **off by default** | `T7-cue-audibility.md` | T6 | nothing |
| T9 | Bake-off baseline vs one variant, blinded review | `T9-bakeoff-runbook.md` | T2+T3+T4 (T5–T7 optional) | **Needs owner listening/judging and is the only task allowed to render.** Runs must go to `$VIDEO_FACTORY_WORKSPACE`, never the repo |

**Adopted principle from the audit (add to T6).** The single best idea found in the 19-repo audit belongs here, and it is a
sentence, not code: *"Calibrate new validators with negative controls. A caption shifted by 0.3 seconds, a one-frame scene
gap, and an omitted spoken word should fail the relevant checks."* T6 should adopt exactly that shape — **and must not "fix"
a threshold when a negative control fails to fail; it must report it.**

---

## Tier 2 — Visual quality (the answer to "what most improves the videos")

| ID | Task | Depends on | Benefit | Scope / modules | Risks | Tests | Measurable acceptance | Effort | Rollback | Blocked by |
|---|---|---|---|---|---|---|---|---|---|---|
| **V-1** | **Validate the renderer upgrade on a copy, not in place.** The pin is 0.8.114; the renderer's own release notes contain fixes for **black last-8-pixel columns at widths like 1080** (this project's 9:16 width) and a **VFR sample-by-timestamp fix for FFmpeg 8** (this machine runs FFmpeg **9.0.2**), plus a fix for per-frame memory growth. The upgrade is **breaking** (artifacts move into `.hyperframes/artifacts/`). | R-1 | The only change in this entire audit with a plausible direct effect on *correctness of the shipped pixels* | `package.json` (pin), `hf.py`, any code reading render artifacts, `scripts/upstream_skills.py` lock (skills are pinned to the old tag) | **High if done casually.** A renderer bump can change every output. Must be run **in a scratch clone or worktree**, never in this working tree | full suite **plus at least one real render diffed against a known-good 0.8.114 render**, frame-by-frame on a vertical 1080-wide output | A named defect is reproduced on 0.8.114 and absent on the candidate, **or** the upgrade is rejected with the evidence recorded. Either outcome is a success | **M–L** (assumes a known-good baseline render exists or can be made) | restore the pin; `npm ci` returns to 0.8.114; lock file unchanged | R-1; **needs a measured render experiment**; owner approval (a renderer change is explicitly out of scope of the existing plan) |
| **V-2** | **Knowledge-contract cards through real renders.** 0 of 76 design-library entries and 0 of 3 style cards are validated on this machine. Add render evidence to **one** card. | T9 | Converts the creative layer from aspirational to evidenced; makes `status: validated` mean something | `config/design-library.json` or `config/styles/*.json`, plus a render record | Claiming validation without a render is exactly the failure the schema forbids | the card's `evidence[]` must cite paths to real render records | One card reaches `validated` with `evidence[]` naming a real render on `mac-hf0.8.114`, and `styles validate` still exits 0 | **S–M** | remove the evidence entry | T9; needs a render |
| **V-3** | **Two small verified additions from the audit, re-implemented in-house:** (a) an **audio cut-sync check** (share of cuts within ±80 ms of an onset) and (b) a **DOM-level "page-chrome" lint** family (corner labels, tracked caps, counters, footer bars, kicker-over-headline, progress bar). | T7 for (a) | These are the only two deterministic measurements found across 19 repos that this project's frame-based audit **cannot** see. Both are cheap | new modules + tests; **do not** vendor either repo (one bundles a non-open GSAP; one is a commercial funnel that claims precedence over this renderer's house style) | New checks can produce false positives; keep them **report-only** first | seeded faults must trip them; known-good renders must not | Each check trips on a seeded fault and stays silent on a known-good render | **M** | delete the new module | (a) T7; (b) nothing |

**Not recommended, with reasons:** a second renderer (no demonstrated limitation of the current one; the alternative's
licence bills per render above three employees — a direct conflict with "never spend money"); generative image/video; voice
cloning; a prompt-to-code sandbox; and any repo that ships no licence file.

---

## Tier 3 — Concurrency foundations (design in doc D; the safety rule is that **nothing here runs a render**)

Order matters: **isolation before speed.** Tasks C-1 to C-4 add no parallelism at all — they make the existing serial path
safer — which is why they are safe to do before any benchmark.

| ID | Task | Depends on | Benefit | Scope | Risks | Tests | Measurable acceptance | Effort | Rollback | Blocked by |
|---|---|---|---|---|---|---|---|---|---|---|
| **C-1** | Per-run `<job>/.run.lock` + heartbeat lease. Two `pipeline run` calls for the same `content_id` must make the second one refuse loudly. | R-1 | **This is the isolation boundary.** Without it, any concurrency corrupts work — and it is useful at concurrency 1 too | `storage.py` (`file_lock` already exists), `pipeline.run`, `queue.py` | A stale lock could wedge a job → hence the heartbeat, not just a pid | two concurrent runs, same `content_id`: second refuses; job B's tree hash unchanged before/after | Second run exits non-zero with a message naming the holder; job A's artifacts are byte-identical | **M** | remove the lock acquisition | R-1 (touches `pipeline.py`/`storage.py`, which are owner WIP) |
| **C-2** | `busy_timeout` on the ledger + short write transactions. | nothing | Removes the most likely spurious failure in a shared-workspace design (`database is locked` after ~5 s) | `ledger.py:21-27` | None meaningful; it is a timeout, not a behaviour change | concurrent-writer test; existing ledger tests unchanged | 20 concurrent stage writes all succeed; no test changes | **S** | revert the connect kwargs | nothing |
| **C-3** | Timeout + process-group kill in `queue._run`. Today a `subprocess.run` with **no timeout and no signal handling** means a hung job consumes a pool slot **forever**, silently lowering effective concurrency below the configured value. | nothing | Restores the configured concurrency. This is likely the real reason "one video at a time" is observed | `queue.py:54-64` | A too-short timeout kills legitimate renders — derive it from the existing `RENDER_TIMEOUT` (1800 s) plus margin, never a new invented number | a deliberately hung job is killed at the limit; a normal job is unaffected | A hung job reaches `failed` with a timeout reason instead of hanging indefinitely | **S–M** | revert the timeout | nothing |
| **C-4** | Explicit per-stage concurrency limits in a config file, with conservative defaults (`render: 2`, `voice: 2`, `compose: 3`, `qa: 2`, `export: 1`, `mpt: 1`), plus a documented honest note that on a 24 GB machine two concurrent renders is close to serial for render-heavy work. | C-3 | Gives one knob and one place to document why it is low | new `config/concurrency.yaml` (or similar) + `queue.py` | A config file next to the "do not edit `config/*.yaml`" rule — so **add a new file**, do not edit an existing one | admission test with a stubbed budget | No more than `render: 2` renders run at once; the rest stay `leased` | **M** | delete the config file and the limiter | C-3 |
| **C-5** | Admission control + a `leased` state + a queue-depth backpressure warning. Unbounded **submission**, bounded **running**. | C-4 | The explicit requirement from the brief | `queue.py` state machine | More states = more recovery paths; keep `queued/running/done/blocked/failed` working unchanged | state-machine tests incl. reclaim of an expired lease | Submitting 50 jobs never produces more than `max_active_jobs` running | **M** | revert the state machine | C-4 |
| **C-6** | Per-job structured log + stage metrics (wall time, peak RSS, CPU, disk written, renderer worker count and `boundBy`). | C-3 | **Nothing can be tuned or diagnosed without this.** It is also how the V-1 and C-9 numbers get collected | new logging module; `pipeline.py` calls | Bounded output required — never let logs grow without limit | log-line assertions; log size cap | Each job has one log with its own job id; no cross-job interleaving | **M** | delete the module | C-3 |
| **C-7** | Fix the remaining shared-writer races: `intelligence/` evidence overlays written without a lock; the second-resolution migration filename (`<UTCts>.json`) that collides when two run in the same second; and `per_stage.mpt: 1` (one shared Docker container). | C-2 | Removes every remaining cross-job coupling that C-1 does not cover | `catalogue.py:47`, `designs.py:55`, `storage_admin.py:248`, `mpt.py` | Low — all three are small, local changes | concurrent-write tests | No lost update on an overlay; two migrations in one second get distinct names | **S–M** | revert each independently | C-2 |
| **C-8** | Keep the parallel-router flag unset at concurrency ≥ 2 and stop depending on `~/.hyperframes/config.json`. Upstream documents the router as safe only for **sequential** renders and notes that config file has **no locking**. | V-1 | Prevents a subtle, hard-to-debug determinism bug when two renders overlap | render invocation env | A wrong setting could itself cause nondeterminism — hence an explicit test | two identical renders produce identical frame hashes | Two concurrent renders of the same composition are byte-identical | **S** | revert the env handling | C-4 |

---

## Tier 4 — Measured capacity (the only place a concurrency number may be set)

| ID | Task | Depends on | Benefit | Acceptance | Effort | Blocked by |
|---|---|---|---|---|---|---|
| **C-9** | **Run the benchmark designed in doc D §6** (documented, **not executed**, in this audit): baseline single job; sweeps at 1/2/3/4 concurrent renders with light+heavy mix; explicit `--workers`, never `auto`; measure throughput, median/p95 latency, error rate, peak RSS/CPU, thermal behaviour, interactive responsiveness; control for cache warming; reserve 25 % headroom below saturation; define the automatic reduction signal. | C-1…C-8, C-6 (metrics), V-1 decided | Replaces every estimate in doc D with a measurement | **Measured jobs/hour**, the named stage bottleneck, and a policy default derived from the data. If the data says two, the answer is two — **do not degrade quality or destabilise the machine to hit a numeric target like 5 or 10** | **L** (many renders; this is the expensive item) | **Owner approval, because this is the only tier that runs many renders.** Needs production-scale benchmark evidence |

**Explicitly not to be built:** a workflow engine (Temporal or similar), a message broker, a second queue, or detached
background workers without durable ownership. The SQLite queue, the per-job process model, the manifest and `flock` already
exist and are sufficient.

---

## Tier 5 — Platform and niche expansion (last, and mostly research)

| ID | Task | Depends on | Benefit | Acceptance | Effort | Blocked by |
|---|---|---|---|---|---|---|
| **X-1** | Move safe-zone geometry out of code into config, marked `unverified`, with a dated source. Today the numbers are hard-coded heuristics explicitly labelled "NOT published platform specs". | R-1 | The one platform-adjacent change that is safe now — a data move that deletes a hard-coded assumption | `config/` gains the zones, `visual_gate.py` reads them, existing tests pass with the same defaults | **S** | R-1 |
| **X-2** | Add the **niche contract** (`niche/1`) and one niche, **as data**, reusing the existing `content_type` vocabulary so no new code path is created. | T2 done | Makes the multi-niche framework real without touching the pipeline | One niche file validates; no pipeline code changes | **M** | nothing |
| **X-3** | **Research only** (no code): the eight platform questions in doc E §6, each needing a **first-party** source with a date — in particular automation permission, monetisation eligibility, AI-disclosure obligations, and the two rows currently resting on third-party evidence (LinkedIn, TikTok). | nothing | Every later adapter depends on it | A dated table of first-party citations; **no adapter built** | **M** (research) | **Needs a licensing/policy decision**; publishing stays disabled regardless |

**Publishing remains disabled and no format, API or monetisation rule may be assumed common across platforms** — the
research already shows first-party and third-party sources disagreeing on at least two.

---

## Sequencing summary

```
Tier 0  R-1 owner decision ─► R-2 doc corrections ─► R-4 safe-zone disposition
                                                      │
Tier 1  T4 ─► T5 ─► T6 ─► T7 ─► T9 bake-off  (existing plan; one task per session, each verified)
                                                      │
Tier 2  V-1 renderer upgrade (scratch clone) ─► V-2 card validation ─► V-3 two new checks
                                                      │
Tier 3  C-2 ─► C-1 ─► C-3 ─► C-4 ─► C-5 ─► C-7 ─► C-6 ─► C-8   (no renders)
                                                      │
Tier 4  C-9 benchmark  ──► set the policy number from data (owner approval to run renders)
                                                      │
Tier 5  X-1 ─► X-2 ─► X-3 research only
```

## The four rules that keep this from breaking a working system

1. **Add, don't change.** If an existing function's behaviour would change for existing inputs, the task is wrong. Every
   task in Tiers 0–3 is a new file or an optional, backward-compatible addition.
2. **The suite is green (548/0).** Any red is caused by the change under test. Never edit an existing test to make it pass;
   never lower a critic threshold (7 each / 8.0 average); never edit `config/*.yaml`, the approval gates, or the pinned
   renderer version except in the V-1 task that exists to change it deliberately.
3. **Only two tasks may render:** T9 (the bake-off) and V-1/V-2/C-9, each with explicit owner approval and each writing to
   `$VIDEO_FACTORY_WORKSPACE`, never into the repo.
4. **One task per session, with an independent verifier.** The implementer never grades its own work — the same principle as
   "a builder never grades its own video".
