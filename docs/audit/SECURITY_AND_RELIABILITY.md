# Security and Reliability Audit

Scope: every path that can put a file into `$VIDEO_FACTORY_PUBLISH_DIR/ready/`, every approval gate,
secret handling, path handling, and queue/worker recovery.
Method: read the code, then reproduce. No claim below is based on a docstring or a test name.

**State of the tree at audit time.** Branch `feat/p1-1-lookmap`, uncommitted work in
`contentos/export.py`, `contentos/scenekit/styles.py`, `contentos/scenekit/lookmap.py`.
`export.py` changed *while this audit was running*: another agent added a Track-A approval check at
`contentos/export.py:116-122` during the session. Findings are written against the tree as of that edit;
where a finding is about the *just-added* code it says so. Re-check line numbers before acting.

**Baseline test state (executed, not quoted):**

```
$ ~/.contentos/venv/bin/python -m pytest tests -q
1 failed, 1166 passed, 8 skipped in 178.54s
  FAILED tests/test_lang.py::test_real_hindi_audio_transcribes_with_valid_timestamps_and_mostly_right_text
    contentos/lang/asr.py:28 LangError [asr_binary_missing] whisper-cli not found

$ node --test contentos/adapters/v1/*.test.mjs
tests 66 / pass 66 / fail 0
```

The single Python failure is an environment gap (no `whisper-cli`), not a code defect — but it means
**word-level caption timing has no ASR on this machine**, which is a reliability problem, not just a test colour.

---

## 1. Paths that can reach `ready/`

There is exactly **one** function that writes a `.publish.json` sidecar or a video into `ready/`:
`contentos/export.py:132 _export_locked`. Everything funnels through `contentos/export.py:107 export_job`.
Good design — one choke point to defend. Four callers:

| # | Caller | Extra preconditions beyond `export_job` |
|---|---|---|
| 1 | `pipeline.py:387 s_export` | stage ordering only (voice→SCRIPT_APPROVED, render→PRODUCTION_APPROVED) |
| 2 | `storage_cli.py:57` — `contentos storage export` | **none**; skips all stages |
| 3 | `ui_api.py:257 _export` — Studio | rejects `allowPaid`/`publish`/`destination`/`path` (`:251-253`), needs `confirm: true` |
| 4 | `ui_api.py:191` rerun → `SUPERVISOR.start(..., force=True)` | none at export |

`handoff.py` never writes into `ready/` — `discover()` (`:70`) is read-only, claims/transitions live under
`.state/claims/`.

**What `export_job` did NOT enforce before this session's edit:** anything. Approvals were checked only
for `manifest["track"] == "B"`. All 37 workspace manifests are Track A (no `track` key), so they got no
approval check at all — and routes 2 and 3 never touch the pipeline stages, which were the only place the
gates lived. **That gap is now closed** by `export.py:116-122`.

## 2. What export still does not enforce

### 2.1 QA is re-computed, never consumed — and the Lane F gates never run on this path

`export.py:164` calls `finalcheck.validate_video`, which calls `qa.run_qa` (`finalcheck.py:37`). So export
does run real technical QA (resolution, fps, duration cap, audio track present, EBU R128 loudness,
clipping, black frames, frozen frames). Good — a video that fails those is refused at `export.py:165-169`.

But two things follow:

- **`qa.json` is decorative.** Nothing in `export_job` reads it, and nothing compares its age against
  `video.mp4`. So "the QA stage passed" and "export validated" are two independent computations that can
  disagree. A job with a stale or absent `qa.json` exports fine — reproduced below.
- **The extra gates are only wired into the pipeline stage**, not export:
  `features/extra_gates.py:79 qa_extra_hook` is invoked solely from `pipeline.py:334 s_qa`. A video that
  trips a Lane F gate can be exported through routes 2 and 3, which never call `s_qa`.

Reproduction (isolated `VIDEO_FACTORY_PUBLISH_DIR`, real job, nothing mutated):

```
$ TMPPUB=$(mktemp -d); VIDEO_FACTORY_PUBLISH_DIR=$TMPPUB \
    ./contentos.sh storage export sample-kafka-events-kinetic
exported: ready/unassigned/2026/11/how-kafka-moves-events__sample-kafka-events-kinetic.mp4
  sidecar: . . . .publish.json
  (exit 0)
```

That job has **no `qa.json` at all** (`jobs/2026/11/03/sample-kafka-events-kinetic/`). The export succeeded
because technical QA was recomputed inline. **Correction to the brief:** this is not "export skips QA
entirely" — `run_qa` does run. The real defect is narrower and more useful: *the QA stage artifact is not
an input to export, and the extra-gate layer is not reachable from any export route that skips `s_qa`.*

### 2.2 The approval check is existence-only, so digest binding is lost at the door

`export.py:119` uses `ledger.approved(job_id, g)`, which is `ledger.py:82`:

```python
def approved(content_id, gate):
    return db().execute("SELECT 1 FROM approvals WHERE content_id=? AND gate=?", ...) is not None
```

A pure existence check. It ignores `subject_sha256` completely. The digest-binding machinery
(`ledger.check_gate`, `pipeline._check_gate` at `pipeline.py:450`) is enforced **only** at the voice and
render stages. Consequence: approve a script, edit the script, hand-replace or re-render `video.mp4`
outside the pipeline, then `contentos storage export <id>` — the approval row still exists, so the gate
passes and the *unreviewed* artifact reaches `ready/`. `ledger.check_gate` already returns `"mismatch"`
for exactly this case; export just does not ask it.

### 2.3 The approval digest does not cover the shipped artifact

`pipeline.py:435 production_digest` hashes the composed project file plus `audio/*.wav`:

```python
parts = [f"composition {artifact('compose', spec)} {...}"]
parts += [f"audio {w.name} {...}" for w in sorted((d / "audio").glob("*.wav"))]
```

`video.mp4` is **not** in that digest, and no digest anywhere covers it. So `PRODUCTION_APPROVED` means
"the composition and the audio were reviewed", never "this MP4 was reviewed". Combined with 2.2 this is the
complete chain gap: the thing that gets published is the one artifact no approval binds to.

### 2.4 `RESEARCH_APPROVED` is written and never read

`grep -rn RESEARCH_APPROVED --include=*.py contentos/` returns one line: `pipeline.py:615`, inside the
`--approve-private` grant loop. No gate in `GATE_OF` (`pipeline.py:418`) references it, and nothing calls
`ledger.approved(..., "RESEARCH_APPROVED")`. It is a ledger decoration. Either wire it to the `brief`
stage or stop granting it.

### 2.5 The Lane F gate layer cannot fail

`features/extra_gates.py` — every return path, read in full:

| function | line | worst status it can return |
|---|---|---|
| `check_silence_gaps` | 34, 35 | `WARN` |
| `check_end_hold` | 47 | `PASS` only — the function probes duration and unconditionally returns PASS |
| `check_blank_field_run` | 61, 62 | `WARN` |

`s_qa` (`pipeline.py:337`) aborts only on `s == "FAIL"`. So `features.extra_gates` can never fail a job.
It is a reporting layer wearing a gate's clothes. `check_end_hold` in particular measures nothing it
claims to measure despite `END_HOLD_WARN_SEC = 3.50` being defined at `extra_gates.py:20` and never used.

## 3. Path handling and untrusted input

This area is genuinely well built; I tried to break it and could not.

- `storage.py:200 valid_job_id` — anchored regex plus explicit `".." not in job_id`, called by
  `check_job_id` (`:204`), which is called by both `find_job_dir` (`:314`) and `job_dir` (`:321`).
- `storage.slugify` (`:210`) rebuilds names from `[a-z0-9-]`, so ids cannot introduce separators.
- `ui_api.py:111-121,209` reject symlinks and require `resolve().relative_to(directory)`;
  `ui_state.py:462-468` does the same for artifact reads; `specs.py:178-182,205` for spec paths.
- `handoff.py:79-80` rejects a `video_filename` containing `/` or `\`.

Residual, minor: `queue.add` (`queue.py:20-31`) resolves the spec path but does not require it under a specs
dir, and reads `content_id` from the YAML without `valid_job_id`. Bounded, because `job_dir` re-validates.
`ui_api.py:298 _queue_add` does validate first, so only the CLI is loose.

## 4. Secret handling

### 4.1 Stage logs are written unscrubbed, and every stage inherits the full parent environment

`pipeline.py:25`:

```python
ENV = {**os.environ, "HYPERFRAMES_PYTHON": str(providers.VENV_PY)}
```

Every stage subprocess (`pipeline.py:77 subprocess.Popen(cmd, ..., env=ENV)`) receives
`ELEVENLABS_API_KEY`, `ANTHROPIC_API_KEY`, `AI_API_KEY`, `YOUTUBE_API_KEY` and everything else in the
parent environment. Nothing strips the ones a stage does not need.

`pipeline.py:76, 83, 85` then write, to `<job>/logs/<stage>.log`, with no scrubbing:

```python
_append_log(log_path, f"$ {shlex.join(map(str, cmd))}\n")      # full command line
_append_log(log_path, f"[stdout]\n{out}[stderr]\n{err}[exit {p.returncode}]\n")   # full streams
```

And `pipeline.py:87` embeds the first 120 chars of the command line into the raised `RuntimeError`, which
the stage loop stores verbatim in the ledger: `pipeline.py:660, 667, 673` all call
`ledger.record(..., error=str(e))` with no `storage.scrub`.

`storage.scrub` exists (`storage.py:351`) and is correctly applied to the manifest failure reason
(`pipeline.py:560`) and to `export._fail` (`export.py:129`) — it just is not applied to the stage log or
the ledger error column.

Whether a live key is exposed today depends on argv: `s_voice` passes text and a voice id to
`hf.command("tts", ...)`, not a key, so the current CLI path is clean. It becomes a live leak the moment
the ElevenLabs adapter passes anything credential-shaped, or any tool dumps its environment on error.
The dashboard does redact on *read* (`ui_api.py:414 redact_text`, `ui_runner.py:103`), which means the
browser is safe while the file on disk is not.

### 4.2 Two overlapping redactors

`storage.scrub` (`storage.py:351`) and `ui_security.redact_text` (`ui_security.py:11`) implement
near-identical rules with different thresholds (`len >= 12` vs `len >= 8`) and different pattern sets.
Two redactors with different answers is how a leak survives a "we redact secrets" review.

## 5. Paid providers and opt-in

Correct, and worth preserving:

- `config/local-first-policy.yaml:14 allow_paid: false`.
- `providers.py:53` blocks `paid_api`/`low_cost_api` unless `allow_paid`.
- When a paid/unsupported provider *is* selected, `pipeline.py:161` refuses honestly:
  `raise Blocked(f"TTS provider {prim['id']} selected but has no adapter yet")`. No silent substitution.
- Publishing needs `PUBLISH_APPROVED` (`pipeline.py:403`) and `config/youtube.yaml` has publishing disabled.

Two soft spots:

- `providers.py:48`: `allow_paid = allow_paid or pol.get("allow_paid", False)`. Editing one YAML file
  promotes paid providers to default for **every** job on the machine, with no CLI opt-in and no audit
  trail. The `--allow-paid` flag currently reads as the gate it is not.
- `config/local-first-policy.yaml:15 exceptions: []` is consumed by nothing
  (`grep -rn exceptions --include=*.py contentos/` → no hits). Dead config that looks like policy.
- `cli.py:13` advertises `elevenlabs` and `doctor` probes `ELEVENLABS_API_KEY`, but no adapter exists.
  The doctor line is honest (OPTIONAL, env-gated); the CLI help implies more than is built.

## 6. Queue and worker reliability

- `queue.py:48 claim()` uses `BEGIN IMMEDIATE` + one `SELECT ... LIMIT 1` + `UPDATE` in a single
  transaction. Correct under multiple workers.
- `queue.py:35 recover()` decides liveness with `os.kill(pid, 0)` (`:43`). **PID reuse** makes a dead job look
  alive forever: after a reboot the recycled PID belongs to an unrelated process, so the row stays `running`
  and the queue wedges. The `pid == 0` case is guarded (`:39`); this one is not.
- `queue.py:20 add()` de-duplicates on `content_id` + status, so the same content under a different spec is
  silently skipped (`:27`). Not unsafe, but surprising.
- `_production_result` parses the child's human-readable stdout to decide success. A wording change in a
  stage's print statement silently changes job semantics.
- `storage.py:245 file_lock` / `:266 lock_is_held` are honest `fcntl.flock` locks, used on the job run, the
  manifest read-modify-write, the per-job export and the claims dir. `export.recover` (`export.py:236`)
  refuses to touch a job whose lock is held.
- Export atomicity (`export.py:188-205`) is correct in the important way: the sidecar is promoted **last**, so
  a crash leaves an orphan video with no sidecar, which `discover()` reports and `recover()` quarantines.

## 7. Findings

| ID | Sev | Title | Location | Evidence | Impact | Smallest fix |
|---|---|---|---|---|---|---|
| S-01 | **P0** | Export approves on existence, not on content | `export.py:119`, `ledger.py:82` | `ledger.approved()` ignores `subject_sha256`; `check_gate()` is only called at `pipeline.py:450` | An approval for content A ships content B via `contentos storage export` / Studio export | Replace with `check_gate(cid, gate, gate_digest(gate, d, spec))` and treat `mismatch`/`none` as refusals |
| S-02 | **P0** | No *approval* binds to `video.mp4` | `pipeline.py:435-443` | `production_digest` hashes composition + `audio/*.wav` only; the video sha is first recorded at export (`export.py:196`), i.e. after review | The artifact that gets published is the one artifact no approval covers; a hand-replaced render ships under an approval for the old one | Bind the reviewed `video.mp4` sha into the recorded approval and compare it at export |
| S-03 | P1 | Lane F extra gates can never FAIL | `features/extra_gates.py:34,47,61` | all returns are `PASS`/`WARN`; `s_qa` aborts only on `FAIL` (`pipeline.py:337`) | The gate set is decorative; `check_end_hold` measures nothing though `END_HOLD_WARN_SEC` is defined at `:20` | Either return `FAIL` at the documented thresholds or delete the layer from `s_qa` |
| S-04 | P1 | Extra gates unreachable from export routes | `pipeline.py:334` vs `export.py:164` | `qa_extra_hook` is called only by `s_qa` | A video tripping a Lane F gate exports via `storage export` / Studio | Call the same gate list from `finalcheck.validate_video` |
| S-05 | P1 | `qa.json` is not an input to export | `export.py:164` | QA recomputed; no freshness or presence check | "QA stage passed" and "export validated" can disagree silently | Require `qa.json` newer than `video.mp4` with no `FAIL` rows |
| S-06 | P1 | Stage logs and ledger errors are unscrubbed | `pipeline.py:76,83,85,87`; `pipeline.py:660,667,673` | `scrub` applied at `:560` and `export.py:129` only | Any credential in argv or in a tool's stderr lands in `logs/*.log` and `ledger.db` | Wrap both write sites in `storage.scrub` |
| S-07 | P1 | Every stage inherits the full parent env | `pipeline.py:25` | `ENV = {**os.environ, ...}` passed at `:77` | Any stage or tool can read `ELEVENLABS_API_KEY`, `ANTHROPIC_API_KEY`, … | Pass an allowlist; inject only the provider's own key |
| S-08 | P2 | `RESEARCH_APPROVED` granted, never enforced | `pipeline.py:615` | sole occurrence in the codebase; absent from `GATE_OF` `:418` | False impression of a research gate; `--approve-private` fabricates it | Enforce it at `brief`, or stop granting it |
| S-09 | P2 | Legacy unbound approvals only warn | `ledger.py:74`, `pipeline.py:459` | `state == "unbound"` prints to stderr and continues | An edit made since an unbound approval cannot be detected, and ships anyway | Treat `unbound` as `mismatch` for jobs created after a cutoff |
| S-10 | P2 | Queue recovery wedges on PID reuse | `queue.py:43` | `os.kill(pid, 0)` on a recycled PID | A dead job stays `running` forever after a reboot; queue stalls | Store a heartbeat timestamp on the row and expire it |
| S-11 | P2 | Track B can only register 9:16 videos | `storage.py:492` | `register()` writes `aspect_ratio="9:16"` and then validates immediately (`:496`) | A hand-built 16:9 video fails the `resolution` check at registration *and* at every export attempt — it can never be published | Probe the real ratio instead of hardcoding it |
| S-12 | P2 | Two divergent secret redactors | `storage.py:351`, `ui_security.py:11` | thresholds `>=12` vs `>=8`, different pattern sets | A secret one redacts and the other does not | Delete one; have both call it |
| S-13 | P3 | One YAML edit enables paid globally | `providers.py:48` | `allow_paid = allow_paid or pol.get(...)` | Loses the per-job opt-in and its audit trail | Require both the policy and the flag |
| S-14 | P3 | `exceptions:` in the policy is dead config | `local-first-policy.yaml:15` | no reads anywhere under `contentos/` | Looks like a control; is not one | Implement it or remove it |
| S-15 | P3 | `queue.add` does not validate `content_id` | `queue.py:26` | reads YAML value directly; `ui_api:298` does validate | CLI-only looseness; bounded by `job_dir`'s re-check | Call `storage.valid_job_id` before the INSERT |
| S-16 | P3 | Studio reaches into export internals | `ui_api.py:257` → `export._existing` | private function used across a module boundary | Refactor hazard, no current defect | Expose a public preview helper |
| S-17 | P3 | CLI advertises an ElevenLabs adapter that does not exist | `cli.py:13` | `grep -rin elevenlabs contentos/` finds no adapter | Users expect `--provider elevenlabs` to work; it Blocks at `pipeline.py:161` | Land the adapter or change the help text |

---

## 8. Positive observations

These are load-bearing; do not refactor them away.

1. **One choke point for publication.** Every route to `ready/` goes through `export.export_job`. The fix
   landed during this audit proves the design pays off: one precondition protects all four callers.
2. **The sidecar is the "ready" marker, promoted last** (`export.py:190-199`). A crash between video and
   sidecar leaves an orphan that `discover()` reports and `recover()` quarantines (`export.py:243-251`)
   instead of publishing. Correct ordering, and tested.
3. **Honest failure over silent substitution.** `pipeline.py:161` refuses rather than routing a paid or
   unimplemented provider to Kokoro. `words_for` (`pipeline.py:190-196`) refuses to fabricate Hindi word
   timings and records `"UNVERIFIED word timing"` when it falls back to even spacing.
4. **Path validation is real** — anchored regex, explicit `..` rejection, `resolve()` + `relative_to()` +
   symlink rejection on every artifact read and every Studio-supplied path (§3).
5. **The Studio is bound to loopback** (`dashboard.py:288 127.0.0.1`) with a per-process
   `secrets.token_urlsafe(32)` (`:289`); `write_authorized` (`ui_api.py:41`) demands same-origin, a matching
   `Host`, and the token, so writes are not reachable cross-origin.
6. **Publishing is defence-in-depth:** `PUBLISH_APPROVED` (`pipeline.py:403`) **and** `youtube.yaml`
   disabled **and** `supplied_audio.publish_blockers` checked at both `export.py:137` and `pipeline.py:400`.
7. **Locking is honest:** `fcntl.flock`, non-blocking mode raises instead of waiting, one run per job
   (`pipeline.py:590`), `recover()` refuses a held lock.
8. **The manifest failure reason is scrubbed** (`pipeline.py:560`) — the one place a raw exception most often
   escapes, and it is handled.

## 9. Recommended order of work

1. **S-01 + S-02 together** — the same hole from two ends; fixing one alone leaves the chain open. Add
   `video.mp4` to the approval digest and make export ask `check_gate`, not `approved`.
2. **S-06 + S-07 together** — one env allowlist, two `scrub()` calls. Cheap, and it stops the leak before the
   ElevenLabs adapter puts a real key into argv.
3. **S-03 + S-04 + S-05 together** — decide whether Lane F is a gate or a report; either way make `s_qa` and
   `export_job` agree, and make `qa.json` load-bearing.
4. **S-08, S-09** — close the two approval gates that only pretend to work.
5. **S-10, S-11** — reliability only, but they cause stuck queues and unexportable jobs.
6. P3 items whenever those files are next touched.

## 10. Unverified

- Whether any *live* credential has already reached `<job>/logs/*.log` on this machine. I did not read those
  logs — reading them would itself be the exposure. If any run used a paid provider, assume the key is in a
  log and rotate it.
- Whether `ELEVENLABS_API_KEY` is currently set. Not inspected, per the brief.
- Playwright/Studio browser journeys — not run.
