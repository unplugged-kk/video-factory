# Master gap register

Ordered by severity. Every row was reproduced or read, not inferred from documentation. `VERIFIED` means I
ran the reproduction myself; `READ` means I read the code path and the cited line says so.

Status key: **FIXED** (landed, tested), **OPEN**, **BLOCKED** (needs an owner decision or an install).

## Current status - authoritative (reconciled 2026-11-20 01:15 IST)

This table is the single source of truth for status. Every other file under `docs/audit/` is history: where it
disagrees with this table, this table wins, and the older text is kept, marked superseded, never deleted. Severity
P0/P1/P2 for G rows; Critical/High/Medium/Low/Info for the PF rows of `POTATO_FINAL_SECURITY_REVIEW.md` (its
section 8.4 is the reviewer's own table). Implementation: IMPLEMENTED / NOT STARTED / N/A. Verification: TESTED
(implementer's tests pass) / VERIFIED (an independent reviewer executed the attack and saw it refused) / NONE.

### Export trust chain (P0)

| ID | Sev | Root cause | Implementation | Verification | Tests | Remaining risk / next action |
|---|---|---|---|---|---|---|
| G-01 | P0 | Export checked gates only for `track == "B"` | IMPLEMENTED (now `export.approval_refusal`, every route) | VERIFIED (PF-18) | `test_export_security.py::test_every_export_route_refuses_the_same_attack` | none known |
| G-02 | P0 | Export used `ledger.approved()` (existence) not `check_gate` (digest) | IMPLEMENTED | VERIFIED (PF-15) | `::test_an_unbound_grant_does_not_satisfy_export`, `::test_replaying_an_approval_from_a_previous_version_is_refused` | PF-07 below |
| G-03 | P0 | No approval bound to `video.mp4` | IMPLEMENTED (ledger `renders` attestation; Option D's manifest sha superseded) | VERIFIED (PF-14, PF-17) | `::test_a_replaced_video_is_refused_even_when_the_manifest_vouches_for_it`, `::test_a_video_swapped_during_export_is_refused` | PF-05 below |
| G-21 | P0 | (P0-1b) export trusted editable `manifest.json` fields (`source_spec`, `final_video_sha256`) | IMPLEMENTED | VERIFIED (PF-12, PF-13) | `::test_attack_a_*`, `::test_attack_b_*`, `::test_the_manifest_is_not_consulted_at_all` | none known |
| PF-01, PF-21, PF-27, PF-28 | High/Med/Low | production digest covered only `index.html` + takes | IMPLEMENTED (whole project tree, links followed, FIFO unbindable) | VERIFIED | `::test_pf01_*`, `::test_pf21_*`, `::test_pf27_*`, `::test_pf28_*` | none known |
| PF-02 | High | default `approve` binds whatever `source_spec` / disk holds, without confirmation | PARTIAL: `--show` + `--expect` | VERIFIED (the options); core OPEN | `::test_pf02_*`, `::test_pf26_*`, `::test_pf29_*` | **Owner decision:** make `--expect` mandatory for the two gates (changes the documented workflow) |
| PF-03 | Medium | sidecar title/description/tags come from the manifest, unapproved | NOT STARTED | NONE | - | bind sidecar metadata into SCRIPT digest before any uploader exists (blocks PUBLISH_APPROVED design) |
| PF-05 | Medium | gate checked before a minutes-long render | PARTIAL (post-render recheck; suspect render dropped) | VERIFIED for unrestored swap | `::test_pf05_*`, `::test_pf25_*` | swap-and-restore during render, output swap before hashing: render from a snapshot copy |
| PF-07 | Low | old approvals stay valid | NOT STARTED | NONE | - | a new grant should supersede earlier ones for that gate |
| PF-22 | Medium | assets outside the composition root, non-`.wav` audio, remote URLs not bound | NOT STARTED | NONE | - | refuse out-of-root / remote references at approve and render |
| PF-23 | Medium | MPT local materials not bound | NOT STARTED | NONE | - | add `material <path> <sha>` parts for the mpt lane |
| PF-04, PF-06, PF-10, PF-11, PF-20, PF-25 | Med/Low/Info | see review | IMPLEMENTED | VERIFIED | `::test_pf04_*`, `::test_pf06_*`, `::test_pf10_*`, `::test_pf11_*`, `::test_pf20_*`, `::test_pf25_*` | none known |
| PF-08, PF-09, PF-24 | Med/Info | `--approve-private`, unauthenticated ledger, Remotion toolchain link | N/A | ACCEPTED RISK | `::test_pf24_*` | assumption: single-user machine, operator acts for the owner, shared toolchain trusted |
| G-04 | P0 | export does not re-run Lane F gates | NOT STARTED | NONE | - | open |

### Everything else

| ID | Sev | Status | Next action |
|---|---|---|---|
| G-05 | P1 | OPEN | Lane F gates can never FAIL; enforce or delete |
| G-06 | P1 | OPEN | `lang doctor` must probe the TTS backend |
| G-07 | P1 | OPEN | scrub stage logs and env; blocks any ElevenLabs adapter |
| G-08 | P1 | OPEN | `RESEARCH_APPROVED` is never read |
| G-09 | P1 | OPEN, partly addressed | P1-1 M1 (`scenekit/lookmap.py`) compiles 17 of 30 looks; nothing consumes `look:` yet (M2) |
| G-10, G-11 | P1 | BLOCKED | credentials / `brew install yt-dlp` |
| G-12 .. G-20 | P2 | OPEN as written below | unchanged this pass |

Not done by anyone so far: creative/visual review of a real output, Studio UX review, Hindi listening test, a
Remotion or MPT render, CI (the branch has no upstream).

## P0 — publication correctness

| ID | Finding | Evidence | Status |
|---|---|---|---|
| G-01 | Track A reached `ready/` with **no approval gate at all**. `export_job` checked the ledger only when `manifest["track"]=="B"`; a pipeline job has no track key, so `contentos storage export <id>` and `pipeline run --only export` skipped the gates entirely. | VERIFIED: `VIDEO_FACTORY_PUBLISH_DIR=/tmp/x ./contentos.sh storage export sample-kafka-events-kinetic` exited 0 and wrote a `.mp4` + `.publish.json` into `ready/`. Code: `export.py:117` (old). | **FIXED** (mechanism superseded 2026-11-19 by `export.approval_refusal`) — gates now enforced in `export.gate_refusal()` for both tracks; regression test `tests/test_export.py::test_export_requires_both_gates_on_every_path` |
| G-02 | That gate check used `ledger.approved()` — an existence test that ignores `subject_sha256`. Approving content A and shipping content B passed, through the routes that skip the voice stage. | READ: `ledger.py:82` vs `ledger.py:68-78`; `check_gate` is only called from `pipeline.py:450` | **FIXED** — export now uses `check_gate` against the live digest via `pipeline.gate_digest`; `mismatch` is a refusal. Test `test_export_refuses_an_approval_granted_for_edited_content` |
| G-03 | **No approval binds to `video.mp4`.** `production_digest` hashes the composition HTML plus `audio/*.wav`; the video's sha is first written *at* export, after review. Hand-replacing `video.mp4` leaves every approval intact. | READ: `pipeline.py:435-443`; `export.py` writes the sha at export time | **OPEN** (2026-11-18, superseded: see Current status, G-03) — needs a design decision: record the reviewed render's sha into the production approval, then compare at export |
| G-04 | Export does **not** run the spec's Lane F gates. `qa_extra_hook` is called only by `s_qa`; `finalcheck.validate_video` re-runs the base nine checks only. | READ: `pipeline.py:334` vs `finalcheck.py:37-39` | **OPEN** |

Correction to the handover: export is **not** unvalidated. `finalcheck.validate_video` re-runs `qa.run_qa`
inline, so resolution, fps, loudness, clipping, black and frozen frames are enforced on every export. The
`qa.json` *artifact* is decorative. That is a narrower defect than "exports without QA", and the fix is G-02
plus G-03, not a new QA gate.

## P1 — quality and honesty

| ID | Finding | Evidence | Status |
|---|---|---|---|
| G-05 | Lane F gates can never FAIL. All three return `PASS`/`WARN`; `s_qa` aborts only on `FAIL`. `check_end_hold` returns `PASS` unconditionally while `END_HOLD_WARN_SEC = 3.50` sits defined and unused. | READ: `features/extra_gates.py:20,34,47,61`; `pipeline.py:337` | **OPEN** — either enforce the documented thresholds or delete the layer |
| G-06 | `hi`/`hi-en` report `READY` in `contentos.lang doctor` while `chatterbox_mlx` is NOT_INSTALLED. | VERIFIED: `python -m contentos.lang doctor` vs `./contentos.sh doctor` | **OPEN** — language doctor must probe the backend |
| G-07 | Stage logs and ledger error columns are unscrubbed. `pipeline.py:25` hands the full `os.environ` to every stage and the command line plus stdout/stderr go to `<job>/logs/<stage>.log`. | READ: `pipeline.py:25,76-87,660-673` | **OPEN** — latent today, live the moment an ElevenLabs key is in the environment |
| G-08 | `RESEARCH_APPROVED` is granted by `--approve-private` and never read as a gate. Sole occurrence in code is the grant. | VERIFIED: `grep -rn RESEARCH_APPROVED contentos/` returns one line, `pipeline.py:615` | **OPEN** |
| G-09 | The **`look/1`** catalogue (30 looks + 27 effects in `config/presets/`) has no render-path consumer: `spec["look"]` is read by nothing (only `scenekit/lookmap.py:200`, which writes it). **But the system is NOT stuck on one template** - a second, working style system exists: `spec['visual_style']` → `scenekit` (`pipeline.py:239`), with **6 styles x 3 grounds = 18 variants** in `scenekit/styles.py:25`. Same Kafka script rendered through it produced four genuinely distinct visual languages (see EVIDENCE below). So the defect is **two parallel vocabularies, one alive and one dead**, not an absence of styling. | VERIFIED BY FRAME INSPECTION, 2026-11-18 | **OPEN** — this is the core creative gap, see `ARCHITECTURE_FINDINGS.md` |
| G-10 | No ElevenLabs adapter exists, though `cli.py:13` advertises one. `grep -rin elevenlabs contentos/` finds no implementation. | READ | **BLOCKED** on credentials for a real test; the adapter itself is pure work |
| G-11 | `yt-dlp` is unusable (x86_64), so reference-video URL download cannot work. | VERIFIED: `Bad CPU type in executable` | **BLOCKED** on `brew install yt-dlp` |

## P2

| ID | Finding | Evidence |
|---|---|---|
| G-18 | HyperFrames is pinned at **0.8.114** while upstream `latest` is **0.9.66** — a minor-version gap, not a patch. `npm view hyperframes dist-tags` (run by me, 2026-11-18) returns `latest: 0.9.66`; `node_modules/hyperframes/package.json` reads `0.8.114`. A 0.8→0.9 bump may carry breaking changes to the composition contract. **Do not upgrade on this evidence alone** - the changelog between the two was not read. Needs a deliberate compatibility test against one real spec before the pin moves. | VERIFIED by me (dist-tags), upgrade impact unverified |
| G-19 | No beat/onset detection anywhere in the repo (`grep -rn librosa` finds nothing), which is why the lyric-video path has no beat analysis and cut timing is hand-guessed. `librosa` (ISC licence) is the direct fix and is the cheapest creative win identified in `OPEN_SOURCE_RESEARCH.md`. | READ — research doc + absence of any audio-analysis dependency |
| G-12 | Two divergent secret redactors: `storage.py:351` (threshold ≥12) and `ui_security.py:11` (≥8). A secret one redacts the other does not. | READ |
| G-13 | Track B can only register 9:16 videos (`storage.py:492` hardcodes `aspect_ratio="9:16"` then validates), so a hand-built 16:9 can never export. | READ |
| G-14 | Queue recovery wedges on PID reuse (`queue.py:43` `os.kill(pid,0)`); a dead job stays `running` after a reboot. | READ |
| G-15 | One YAML edit to `local-first-policy.yaml` enables paid providers globally, losing the per-job opt-in audit trail (`providers.py:48`). | READ |
| G-16 | `exceptions:` in `local-first-policy.yaml:15` is read by nothing. It looks like a control and is not one. | READ |
| G-17 | Track B scene plans are validated and never consumed by the builder. | READ — confirmed in the branch's own `docs/P1-1_LOOK_PROPOSAL.md` |
| G-20 | The QA tool named "Ayase" in the brief does not appear to exist - no video-QA project by that name on GitHub. `vidqa` exists but is a one-star single-author CLI whose OCR/frame-comparison ideas overlap the nine export-time checks already present. Action: get the real URL before scheduling any work against either. | VERIFIED by the research agent against the GitHub API; the name is the problem, not the audit |

## EVIDENCE: the working style system, inspected as frames

Contact sheets: `~/Desktop/VideoFactory-Workspace/audit/style-compare-20261118/<style>/contact-sheet.png`
(5 frames each at 2s/8s/15s/22s/30s, generated with `contentos preview --sheet`).

One script (`How Kafka Moves Events`), 7 specs differing **only** in `visual_style.id`
(`~/Desktop/VideoFactory-Workspace/experiments/style-evolution/specs/`):

| `visual_style.id` | What the frames actually show |
|---|---|
| `cinematic-documentary` | dark purple/teal gradient grounds, white display headline, inline gold caption text, no caption plate |
| `clean-explainer` | cream and pale-blue flat grounds, black bold headline, white-on-black rounded caption pill with yellow highlighted words |
| `kinetic-type` | near-black grounds, yellow/white tag chips, huge condensed uppercase headline, magenta panel outlines |
| `blueprint-architecture` | blue-teal gradient, mono/letter-spaced caps, thin-line diagram cards |

These are four different visual languages from one script. **The styling capability is real.** What is dead is the
57-file `look/1` catalogue that nobody wired up, and the `sceneplan/1` direction block that duplicates the same idea.

## Gaps that remain after this correction

- `look/1` (30 looks + 27 effects) is dead data. Either wire it into `visual_style` resolution or delete it - two
  vocabularies for one concept is how a team ends up maintaining the wrong one.
- Scenekit is opt-in only: a spec without `visual_style` falls to the hardcoded template at `pipeline.py:303-308`,
  so the *default* path is the one bland template. That is the real quality problem, not a missing style system.
- `visual_layer.py:49` still indexes backdrops by scene number, so the default template's backdrop cannot vary by look.


## Documentation that is now wrong

| Claim | Reality |
|---|---|
| "1,084 Python tests passing" | 1,169 today (`README`, handover) |
| `contentos.sh` puts arm64 ffmpeg/timeout first | `/opt/homebrew/bin` has neither; `timeout` is still the dead x86_64 one |
| labelled contact sheets cannot work here (no freetype) | **falsified**: 7 labelled sheets generated successfully on 2026-11-18 with `contentos preview --sheet`; the ffmpeg in use has `drawtext` |
| Track A export is gate-free by design | changed in this audit; `tests/test_job_register.py` now pins the new contract |

## What I did not touch

Publishing stays disabled. No paid provider was called. No approval gate was weakened. Nothing was
committed. `config/*.yaml`, `vendor/`, the pinned HyperFrames version and `.state/claims/` are untouched.
