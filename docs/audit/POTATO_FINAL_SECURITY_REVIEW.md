# Potato - final security review of the approval-to-export trust chain

Reviewer: Potato (independent, adversarial). Date: Thu Nov 19 21:57 IST 2026 (from `date`).
Subject: branch `feat/p1-1-lookmap`, uncommitted working tree (git status: export.py, ledger.py, pipeline.py, track_b.py,
cli.py, ui_state.py modified; tests/test_export_security.py new).

## 1. Scope and method

Read (code, not comments, treated as the truth): `contentos/export.py` (export_job, approval_refusal, _current_spec,
_export_locked, build_sidecar, names/locations), `contentos/ledger.py` (approve, check_gate, attest_render,
render_record, db), `contentos/pipeline.py` (script_digest, production_digest, render_subjects, approval_subjects,
_check_gate, run, _stages, _note_spec, s_compose, s_render, s_export), `contentos/track_b.py` (intake, register, render,
voice, attest_registration, script_spec, _composition), `contentos/cli.py` (cmd_approve, _subject_digest,
cmd_job_register), `contentos/ui_api.py` (_approve, _export), `contentos/ui_state.py` (job_state, _spec_for),
`contentos/storage_cli.py` (cmd_export), `contentos/storage.py` (find_job_dir, read_manifest, adopt_external),
`contentos/features/audio_bed.py`, `contentos/adapters/v1/factory_worker.mjs` (runCore), `contentos/queue.py`,
the full `git diff`, and the tests named in the brief.

Ran:
- The four test files: `~/.contentos/venv/bin/python -m pytest tests/test_export_security.py tests/test_export.py
  tests/test_job_register.py tests/test_pipeline_export.py -q -p no:cacheprovider` -> `86 passed`.
- 13 attack scripts under `/tmp/potato/` against fresh `VIDEO_FACTORY_WORKSPACE` / `VIDEO_FACTORY_PUBLISH_DIR`
  directories under `/tmp/potato/potato-*`. Real code paths: `cli.cmd_approve`, `cli.cmd_job_register`,
  `pipeline.run(...)` (so the real `_stages` gate check and render attestation run), `track_b.intake/register/render`,
  `export.export_job`, `storage_cli.cmd_export`, `ui_api._export`, `ui_api._approve`. The only stand-in is the
  renderer: `pipeline.FN["render"]` / `pipeline.s_render` is replaced by an ffmpeg call so no Chrome/HyperFrames run is
  needed. Where it matters, the stand-in reads the same inputs HyperFrames reads (see PF-01).
- A mutation pass: a pytest plugin (`/tmp/potato/mutplug.py`, loaded with `-p mutplug`) that removes one protection at
  a time in-process, to check the tests would fail without it (section 5).
- For every refusal claimed as VERIFIED, the same tampered state was re-exported with `export.approval_refusal`
  monkeypatched to `lambda *a, **k: None`; it then exported. So the refusal comes from approval_refusal and not from
  something unrelated like validation.

Nothing in the repo was modified except this file. No git writes, no network.

Harness (`/tmp/potato/h.py`, abridged): `fresh()` makes new ws/pub dirs and calls `storage.preflight()`.
`track_a(root)` writes a spec outside the job, opens the job, sets `source_spec`, and lays out `project/` the way
`s_compose` does (`project/index.html` that loads `./gsap.min.js` and `./assets/voice/01.wav`, plus the copy of
`audio/01.wav` at `project/assets/voice/01.wav`). `approve()` calls the real `cli.cmd_approve`. `render(j)` calls
`pipeline.run(spec, only="render", force=True)` with `fake_render`, which writes `video.mp4` whose audio track is
`project/assets/voice/01.wav`, the file `index.html` plays.

## 2. Trust model (reconstructed)

Actors: the owner (human approver), coding agents and tools that edit the workspace, the ContentForge worker, and the
Studio HTTP API (local).

| Asset | Where | Who can change it | Trusted by export? |
|---|---|---|---|
| `manifest.json` | job dir | any tool, agent, `update_manifest` | Declared untrusted for approval. **Still trusted for job_id, destination path and every sidecar metadata field** (PF-03, PF-04) |
| spec YAML (Track A) | anywhere (`spec_path` recorded at render) | anyone | Content-compared: script_digest only (title + say/tts/language) |
| `project/index.html`, `audio/*.wav` | job dir | anyone | Content-compared: production_digest |
| other `project/` files (`assets/voice/*.wav`, `gsap.min.js`, `hyperframes.json`, Track B assets) | job dir | anyone | **Not covered by anything** (PF-01) |
| `video.mp4` | job dir | anyone | Hashed at export and matched to a `renders` row |
| `ledger.db` (`approvals`, `renders`) | `<workspace>/ledger.db` | anything that runs `contentos approve`, `job register`, the render stages, or plain sqlite | Trusted root (PF-09) |
| Owner identity | none | n/a | The approve CLI is unauthenticated: running it IS the approval (PF-09) |

Routes into `ready/`: all go through `export.export_job` -> `approval_refusal` -> `_export_locked`:
1. `contentos storage export` (`storage_cli.cmd_export`).
2. The pipeline `export` stage (`s_export`), which also runs at the end of `pipeline run` / `production run` / the
   queue / the ContentForge worker (`factory_worker.mjs` always passes `--approve-private`, PF-08).
3. Studio `POST .../export` (`ui_api._export`).
No other writer of `ready/` was found (`grep` for `ready`, `export_job`: `handoff.py` and `export.recover` only move or
read existing files). Writes outside `ready/` are possible through PF-04.

Records that create a render attestation (`ledger.attest_render`): `pipeline._stages` (source `pipeline`, after the
PRODUCTION gate), `track_b.render` (source `track-b`, PRODUCTION gate only), `track_b.attest_registration` via
`contentos job register` and `track_b.register` (source `register`, no gate, PRODUCTION then binds to the video bytes).

STRIDE summary of the boundaries: Tampering with job files after approval is now mostly detected (section 3, VERIFIED
rows). The open problems are tampering with files outside the digest (PF-01), within the render window (PF-05) and with
the manifest fields export still trusts (PF-03, PF-04). Spoofing the approver is possible because what gets bound is
chosen by untrusted state and never shown (PF-02). Repudiation: the sidecar does not record how the gates were granted
(PF-08).

## 3. Findings

Status column = current status after Round 2 (section 7). Round-1 status kept in brackets where it changed;
round-1 statuses marked "R1" are superseded.

| ID | Severity | Status | Title |
|---|---|---|---|
| PF-01 | High | VERIFIED (R1: OPEN, superseded) | PRODUCTION_APPROVED does not cover the files the renderer actually consumes |
| PF-02 | High | OPEN (mitigated: display only, after binding) | `contentos approve` binds to content chosen by untrusted state and never shows it |
| PF-03 | Medium | OPEN | Sidecar title/description/tags/targets/project come from the editable manifest, bound to nothing |
| PF-04 | Medium | VERIFIED (R1: OPEN, superseded) | Manifest `job_id` decides the destination: hijack another job's ready/ slot, path traversal out of ready/ |
| PF-05 | Medium | OPEN (partly fixed: an unrestored mid-render swap is now VERIFIED refused) | Render-window TOCTOU: swap composition during render, or video.mp4 before it is hashed |
| PF-06 | Medium | VERIFIED (R1: OPEN, superseded) | Regression: `features.audio_bed` makes every honest render unexportable |
| PF-07 | Low | OPEN | Old approvals never expire: a superseded v1 can be restored and re-exported over v2 |
| PF-08 | Medium | ACCEPTED RISK | `--approve-private` (always used by the ContentForge worker) self-grants all gates; ready/ cannot tell |
| PF-09 | Info | ACCEPTED RISK | Ledger and approve CLI are unauthenticated local state |
| PF-10 | Low | VERIFIED (R1: OPEN, superseded) | `track_b.render` checks only PRODUCTION; a script edited after voice is rendered and later approved |
| PF-11 | Info | VERIFIED (R1: OPEN, superseded) | `job register` on a Track B intake without video.mp4 crashes with an uncaught FileNotFoundError |
| PF-12 | - | VERIFIED | Original bypass A (delete `source_spec`) closed |
| PF-13 | - | VERIFIED | Original bypass B (repoint `source_spec` at a pristine copy) closed |
| PF-14 | - | VERIFIED | Render replacement before/after export, forged or replaced manifest, video symlink, swap + re-register |
| PF-15 | - | VERIFIED | Unbound legacy grants, grants for another content_id, missing attestation, lost ledger refused |
| PF-16 | - | VERIFIED | Spec deleted / truncated / replaced by a dir symlink / replaced by another valid spec; audio edited |
| PF-17 | - | VERIFIED | Video swapped between the approval check and the copy is refused inside the lock |
| PF-18 | - | VERIFIED | All three export routes refuse the same attack |
| PF-19 | - | VERIFIED | Studio approve refuses when content changed after it was shown (seenDigest) |
| PF-20 | Low | OPEN | (R2) A forged `.state/exports/<job>.json` in the publish dir makes `export --force` delete an arbitrary file |
| PF-21 | High | OPEN | (R2) A symlinked directory under the project binds only its link text; content behind it changes freely |
| PF-22 | Medium | OPEN | (R2) Assets the composition loads from outside the project (`../x`, `audio/ambient_bed.wav`, non-.wav files in audio/, remote URLs) are not bound |
| PF-23 | Medium | OPEN | (R2) MPT `mpt.source: local` materials are not bound |
| PF-24 | Info | ACCEPTED RISK | (R2) Remotion `node_modules` (shared toolchain behind a symlink) is not bound |
| PF-25 | Low | OPEN | (R2) A Track B render blocked mid-render leaves video.mp4 in place, ready for `job register` |

### PF-01 [High, R1: OPEN -> R2: VERIFIED, see 7.2] PRODUCTION_APPROVED does not cover the files the renderer actually consumes

- Location: `contentos/pipeline.py` production_digest (digests `project/index.html` + `audio/*.wav` only);
  `s_compose` (pipeline.py ~248-306) writes `project/gsap.min.js`, `project/assets/voice/NN.wav` (copies of the takes)
  and `project/hyperframes.json`, and index.html loads `./gsap.min.js` and plays `./assets/voice/NN.wav`; `s_render`
  runs HyperFrames with `cwd=project`. Track B: `track_b.render` uses the same digest; hand-built compositions load
  arbitrary `project/` assets. Remotion lane digests only `project_remotion/src/Video.tsx`; mpt only `mpt-request.json`.
- Description: after the owner approves PRODUCTION and before render, anyone can replace the audio the composition
  plays, the JavaScript it executes, its duration file, or any image. The digest does not move, the render gate passes,
  the render is attested with the approved digests, and export ships it.
- Impact: the shipped video has unreviewed audio and visuals while every gate reads "approved". This breaks the core
  claimed property.
- Reproduction (`/tmp/potato/a_assets.py`):
  ```python
  root = fresh(); j = track_a(root)
  approve(j.id, "SCRIPT_APPROVED"); approve(j.id, "PRODUCTION_APPROVED")
  before = pipeline.production_digest(j.d, spec)
  wav(j.d / "project/assets/voice/01.wav", 1500)            # unreviewed audio
  (j.d / "project/gsap.min.js").write_text("document.body.innerHTML='<h1>UNREVIEWED</h1>'")
  (j.d / "project/hyperframes.json").write_text('{"duration": 999}')
  print(before == pipeline.production_digest(j.d, spec)); print(render(j)); print(try_export(j.id))
  ```
  Observed: `production digest unchanged by swap: True` / `render: [('render', 'OK', ...)]` / `export: EXPORTED exported`
  / `published audio == approved take? False`.
  Track B (`/tmp/potato/a_tb.py` T3, intake with `project/assets/scene1.png` and `project/scene.js`, both swapped after
  approval): `T3 track_b.render -> OK | export -> EXPORTED exported`.
- Recommendation: digest the whole render input tree, not a sentinel file. In `production_digest`, hash every regular
  file under the compose root (`project/`, `project_remotion/`), sorted by relative path, and refuse symlinks, e.g.
  `parts += [f"file {p.relative_to(d)} {sha256_file(p)}" for p in sorted(root.rglob("*")) if p.is_file()]`. Generated
  files the render itself writes must live outside that tree. Add an attack test that swaps `project/assets/voice/01.wav`.

### PF-02 [High, R1: OPEN -> R2: OPEN, mitigated, see 7.2] `contentos approve` binds to content chosen by untrusted state and never shows it

- Location: `contentos/cli.py` `_subject_digest` / `cmd_approve`; `pipeline._note_spec`; `pipeline.approval_subjects`.
- Description: `contentos approve <id> SCRIPT_APPROVED` with no `--spec` digests the spec at `manifest.source_spec`.
  That field is (a) freely editable and (b) silently rewritten by `pipeline run` to whatever spec was last run with that
  content_id. PRODUCTION binds to whatever composition, or for a registered job whatever `video.mp4`, is on disk at that
  moment. The CLI prints only a 64-hex digest. An owner who reviewed text S and types the documented command can bind
  text E that they never saw. The code itself declares the manifest untrusted, yet uses it to pick what the human
  approves.
- Impact: an agent or tool can get unreviewed content approved by a real human, and then everything downstream is
  legitimately "approved".
- Reproduction:
  - `/tmp/potato/a_bind.py`: manifest repointed to `evil.yaml`, owner runs approve. Observed: `approved SCRIPT_APPROVED
    for a1 (bound to 533d35...)`, `digest of the reviewed spec: fe90bf...`, `digest of evil spec: 533d35...`,
    `voice gate for evil spec: PASSES`, `voice gate for reviewed spec: BLOCKED`, then render of evil spec OK and
    `export: EXPORTED exported`.
  - `/tmp/potato/a_tb.py` T1, no manifest edit at all: the agent runs `pipeline.run(evil.yaml)` (same content_id). It
    stops at a gate but `source_spec` now points at evil. Observed: `T1 manifest.source_spec now: True`, after the owner's
    approve `T1 bound digest == evil digest: ok`.
  - `/tmp/potato/a_tb.py` T2: a Track A job's video swapped for an attacker video, manifest deleted, `contentos job
    register` run. The CLI then prints "Export needs both gates: contentos approve ...". The owner runs them. Observed:
    `T2 export -> EXPORTED exported | published == attacker video: True`.
- Recommendation: make the CLI show what it binds and require consent, the way the Studio's `seenDigest` does. Print
  title and script lines (SCRIPT), the composition file list and video sha (PRODUCTION), and require either `--yes` after
  display or `--digest <hex>` that must equal the current digest. Do not default to `manifest.source_spec`: require
  `--spec` for Track A, or take the spec path from the latest ledger row for the job.

### PF-03 [Medium, OPEN (R1 and R2)] Sidecar publishing metadata is bound to nothing

- Location: `contentos/export.py` build_sidecar (all fields from `m`, the manifest), names/locations (project_id),
  `_export_locked` (`require_audio`, `aspect_ratio` for validation from the manifest); `ui_state.job_state`
  (`"title": manifest.get("title")`).
- Description: the scheduler that publishes from `ready/` reads title, description, tags, platform_targets and project
  from the sidecar. Those are copied from `manifest.json` at export time. SCRIPT_APPROVED covers the spec title only, so
  none of these is approved. The Studio also shows the manifest title, so the reviewer sees a title that is not what is
  bound.
- Impact: an approved video is published under an unreviewed title, description or links, to a different
  channel/project folder, or to more platforms.
- Reproduction (`/tmp/potato/a_meta.py`): after approval and render,
  `storage.update_manifest(j.d, title="Miracle cure doctors hate", description="Buy now at scam.example", tags=["scam"],
  platform_targets=["youtube","tiktok"], project_id="someone-elses-channel", require_audio=False)`. Observed:
  `export: EXPORTED exported`,
  `sidecar path: pub/ready/someone-elses-channel/2026/11/approved-title__a1.publish.json`,
  `{'title': 'Miracle cure doctors hate', 'description': 'Buy now at scam.example', 'tags': ['scam'],
  'platform_targets': ['youtube', 'tiktok'], 'project_id': 'someone-elses-channel', ...}`.
  `/tmp/potato/a_studio.py`: `after manifest edit studio title: Forged display title`.
- Recommendation: build the sidecar's publishable fields from the approved source (the spec at the attested
  `spec_path`, or the Track B script), and add description/tags/targets to `script_digest`, so a change re-opens
  SCRIPT_APPROVED. At minimum, record the approved title in the `renders` row and refuse export when the manifest
  title differs. Take `require_audio`/`aspect_ratio` from config/spec, not the manifest.

### PF-04 [Medium, R1: OPEN -> R2: VERIFIED, see 7.2] Manifest `job_id` decides where export writes

- Location: `contentos/export.py` `_export_locked` (`job = m["job_id"]`), names/locations/_state/_existing, staging
  path. `storage.read_manifest` does not check `m["job_id"]` against the directory name or `valid_job_id`.
- Description: approval_refusal runs for the job_id argument, then `_export_locked` uses the manifest's job_id for the
  file stem, the sidecar's `job_id`, the prior-export lookup, the `.state/exports/<job>.json` record and the staging
  folder.
- Impact: (1) Slot hijack: approved job A overwrites job V's ready/ entry, and the sidecar says it is V. (2) Path
  traversal: a job_id with `/..` writes the video, the sidecar and the export record outside `ready/` (the target dir
  must exist; one `mkdir` is enough).
- Reproduction (`/tmp/potato/a_jobid.py`, `/tmp/potato/a_trav.py`):
  - Hijack: a1's manifest `job_id="v1"` plus v1's content_id/created_at, then `export_job("a1", force=True)`. Observed:
    `EXPORTED exported`, `pub/ready/demo/2026/11/victim-title__v1.mp4 8c301a401e98` (a1's sha; v1's is dbb91660b042),
    sidecar `job_id` `v1`.
  - Traversal: `m["job_id"] = "x/../../../escaped/owned"`, `mkdir pub/ready/approved-title__x`, `export_job("a1",
    mode="flat")`. Observed: `EXPORTED exported`, `written: escaped/owned.mp4`, `written: escaped/owned.publish.json`,
    `written: pub/escaped/owned.json`.
- Recommendation: in `_export_locked`, use the job_id argument (already `check_job_id`-validated) and refuse when
  `m.get("job_id") != job_id`. Assert `dest.resolve().is_relative_to((pub / "ready").resolve())` before promotion.

### PF-05 [Medium, R1: OPEN -> R2: OPEN, partly fixed, see 7.2] Render-window TOCTOU

- Location: `pipeline._stages` (`subjects` taken before `FN[st](ctx)`, `sha256_file(d / "video.mp4")` after it);
  `track_b.render` (same shape).
- Description: the digests are taken before a render that runs for minutes and reads the composition during that time.
  The video is hashed in place after the external renderer exits. (a) Swap index.html after the gate, restore it before
  the render returns: the video is of the swapped composition, the record and later checks see the original.
  (b) Replace video.mp4 between render exit and the hash: the attacker's bytes are attested.
- Reproduction (`/tmp/potato/a_race.py`; the attacker's timing is simulated inside the stand-in renderer): (a)
  `render: [('render', 'OK', ...)]`, `export: EXPORTED exported` (the published video is the red "EVIL" render);
  (b) `export: EXPORTED exported | published == attacker file: True`.
- Recommendation: render from a private snapshot: copy the compose tree to a temp dir, digest the copy, render the copy
  into a temp output, hash that output, attest it, then `os.replace` it to `video.mp4`.

### PF-06 [Medium, R1: OPEN -> R2: VERIFIED, see 7.2] Regression: `features.audio_bed` makes honest renders unexportable

- Location: `features/audio_bed.py` writes `audio/ambient_bed.wav` after render; `production_digest` globs
  `audio/*.wav`; `approval_refusal` step 3 recomputes it.
- Description: the post-render hook changes an input of the PRODUCTION digest, so the job's own render looks "changed
  after this render". The error tells the operator to re-approve and re-render. That trains blind re-approval, and the
  second round binds the generated bed file.
- Reproduction (`/tmp/potato/a_bed.py`, spec with `features: {audio_bed: true}`, stand-in render followed by the real
  hook as `s_render` calls it): `render: OK`, `audio/ now: ['01.wav', 'ambient_bed.wav']`, `export of an honest,
  approved render: REFUSED: ... the content behind PRODUCTION_APPROVED changed after this render`.
- Recommendation: write render byproducts outside `audio/` (e.g. `work/`), or digest only `audio/NN.wav` takes by
  name. Add a test with the hook enabled.

### PF-07 [Low, OPEN (R1 and R2)] Approvals are never superseded

- Location: `ledger.check_gate` ("ok" if the digest is in any bound grant ever recorded); no CLI or Studio revoke
  (`ledger.revoke` exists but nothing exposes it).
- Description: once v2 is approved because v1 had a problem, v1's grants stay valid forever. Restoring v1's files from
  a backup brings v1 back, and it exports with force over v2.
- Reproduction (`/tmp/potato/a_replay.py`): `export v2: EXPORTED exported`, then v1 files restored,
  `export v1 again (force): EXPORTED exported`, `ready/ now holds v1 bytes: True`.
- Recommendation: treat the latest bound grant per gate as authoritative (or record supersession when a new digest is
  approved), and add `contentos approve --revoke`.

### PF-08 [Medium, ACCEPTED RISK] `--approve-private` self-grants every gate; ready/ cannot tell

- Location: `pipeline._stages` (grants SCRIPT bound to the running spec, PRODUCTION bound at render time to whatever
  composition exists); `factory_worker.mjs` runCore always passes `--approve-private`. `CONTENTOS_FACTORY_AUTHORIZED_BY`
  is a static label (default `factory-mode:production-job`), not a verified identity.
- Assumption that makes it acceptable: whoever can run the CLI with that flag or drop a spec into the exchange inbox is
  acting for the owner (AGENTS.md section 2). Under that assumption the claimed property ("a human approved") does not
  hold for this route by design.
- Reproduction (`/tmp/potato/a_ap.py`): one `pipeline.run(spec, approve_private=True)` gives `('export', 'OK')`,
  `ready: [... .mp4, ... .publish.json]`, approvals `by='cli --approve-private authorized-by=factory-mode:production-job'`,
  `sidecar mentions approval provenance? False`.
- Recommendation: record the approvers (`by` of the bound grants) in the `renders` row and in the sidecar
  (`approval: {"script_by": ..., "production_by": ...}`), so a scheduler can refuse self-approved videos for public
  release.

### PF-09 [Info, ACCEPTED RISK] Ledger and approver identity are unauthenticated

- `ledger.db` sits in the workspace, writable by the same principals as the manifest; `contentos approve` has no
  authentication. Any local process can insert a bound grant or a `renders` row. Assumption: single-user machine,
  attackers are buggy or overreaching tools that go through normal workflows, not code that writes sqlite directly.
  Reproduction: `/tmp/potato/a_verify.py` writes `approvals` directly (V3/V4), and those writes take effect.
  Recommendation (only if the model changes): sign rows with a key outside the workspace (`~/.contentos/secrets`) or
  require an interactive TTY confirmation in `cmd_approve`.

### PF-10 [Low, R1: OPEN -> R2: VERIFIED, see 7.2] `track_b.render` does not check SCRIPT_APPROVED

- Export catches it (the record's script digest is not approved): `/tmp/potato/a_tb4.py` -> `track_b.render with
  unapproved script -> OK`, `render record script digest is approved? mismatch`, `export -> REFUSED: tb2:
  SCRIPT_APPROVED was granted for different content`. The residual risk: when the owner later approves the edited
  script, the already-rendered video exports with audio voiced from the earlier script (audio is under PRODUCTION, so
  this was approved too, but as a pair the two were never reviewed together). Recommendation: call
  `_require_gate(job_id, "SCRIPT_APPROVED", script_digest(spec))` in `track_b.render`.

### PF-11 [Info, R1: OPEN -> R2: VERIFIED, see 7.2] `job register` crash path

- `/tmp/potato/a_reg.py`: a Track B intake with no video.mp4, then `cli.cmd_job_register(...)` -> `uncaught:
  FileNotFoundError .../tb9/video.mp4`. `adopt_external` returns the existing Track B manifest without checking for
  the video, then `attest_registration` hashes a missing file. No security impact (nothing is attested). Recommendation:
  check `video.is_file()` in `attest_registration` and raise StorageError.

### PF-12 / PF-13 [VERIFIED] Original bypasses A and B

`/tmp/potato/a_ab.py` (real CLI approvals, real `pipeline.run` render attestation):
```
baseline: EXPORTED exported ['approved-title__a1.mp4', 'approved-title__a1.publish.json']
attack A: REFUSED: a1: not exported, the content behind SCRIPT_APPROVED changed after this render; ... ready files: 0
attack A with approval_refusal disabled: EXPORTED exported
attack B: REFUSED: a1: not exported, the content behind SCRIPT_APPROVED changed after this render; ... ready files: 0
attack B with approval_refusal disabled: EXPORTED exported
```
Cause: `_current_spec` reads the spec from the ledger's `spec_path` and never from the manifest. Deleting or repointing
`source_spec` has no effect on the check (mutations M2/M3 in section 5 bring both bypasses back and the tests catch
it).

### PF-14 .. PF-18 [VERIFIED] (`/tmp/potato/a_verify.py`)

Every row below was refused with ready/ empty, and the same state exported once `approval_refusal` was disabled:

| Row | Attack | Observed refusal |
|---|---|---|
| V1 | video.mp4 swapped after render | `not a render the factory recorded` |
| V2 | manifest replaced (track B, forged sha, fake approvals) + swapped video | `not a render the factory recorded` |
| V3 | only unbound legacy grants | `an unbound grant does not count` |
| V4 | grants moved to another content_id | `not exported until SCRIPT_APPROVED and PRODUCTION_APPROVED` |
| V5 | renders rows deleted | `not a render the factory recorded` |
| V6/V7/V8 | spec deleted / truncated / replaced by a symlink to a directory | `can no longer be read` |
| V9 | spec replaced by another valid spec | `content behind SCRIPT_APPROVED changed` |
| V10 | video.mp4 -> symlink to an unattested file | `not a render the factory recorded` |
| V11 | audio take edited after render | `content behind PRODUCTION_APPROVED changed` |
| V13 | Track A: swap video, delete manifest, `job register` | `granted for different content` (then PF-02 T2 shows the owner can be talked into binding it) |
| V14 | video swapped between approval check and copy | `video.mp4 changed while it was being exported` (only `sha != checked` in `_export_locked` raises this) |
| V15 | same swap via `storage export`, Studio `_export`, `pipeline run --only export` | `1`, `409 EXPORT_REFUSED`, `FAIL: ... not a render the factory recorded`; ready 0 |

V12 (composition replaced by a symlink to identical bytes) exported, as expected: the check is content-based, so this is
not a bypass.

### PF-19 [VERIFIED] Studio approve binds what it showed

`/tmp/potato/a_studio.py`: the spec changed after `job_state` was read, so the stale `seenDigest` gives `409
DIGEST_MISMATCH` and `grants recorded: 0`. A fresh digest gives `200` and the bound digest equals `script_digest` of the
displayed spec. Caveat: the displayed title is the manifest's (PF-03).

## 4. Positive observations

- Export trust moved from the manifest to a ledger attestation keyed by video sha. Bypasses A and B are closed by
  construction, not by a special case.
- One function (`render_subjects`) computes digests for render, register, approve and export, so they cannot drift.
- Unbound grants no longer satisfy export. Mismatch beats unbound in `check_gate`.
- The bytes are pinned from check to copy (`checked` -> `sha != checked` -> staged copy verified -> promoted copy
  verified).
- Registered (hand-built) renders bind PRODUCTION to the exact bytes, so re-registering needs a fresh approval.
- The Studio approve uses a `seenDigest` handshake, which is the right design. The CLI should copy it (PF-02).
- The security tests assert on state (`tree(ready)` unchanged), not only on messages.

## 5. Test quality

Mutation pass (`MUT=Mx PYTHONPATH=/tmp/potato ... -m pytest <4 files> -p mutplug`), with one protection removed each
time:

| Mutation | Effect on the suite |
|---|---|
| M1 approval_refusal always None | 23 failed (all attack tests) |
| M2 `_current_spec` reads `manifest.source_spec` (old bypass B) | 37 failed, including attack A/B tests |
| M3 skip the content check when `source_spec` is absent (old bypass A) | 18 failed, including attack A/B |
| M4 drop step 3 (current content vs record) | 7 failed |
| M5 treat unbound grants as ok | 1 failed (`test_an_unbound_grant_does_not_satisfy_export`) |
| M6 remove the `sha != checked` pin | 1 failed (`test_a_video_swapped_during_export_is_refused`) |
| M7 registration binds PRODUCTION to the composition instead of the bytes | 6 failed |

So every protection that was added has at least one test that fails without it. Gaps and weaknesses:

1. No test covers PF-01, PF-02, PF-03, PF-04, PF-05, PF-06 or PF-07. All of them are exploitable while the suite is
   green.
2. `test_the_manifest_is_not_consulted_at_all` overclaims: export still takes job_id, destination and all sidecar
   metadata from the manifest (PF-03/PF-04). The `approval_refusal` docstring says the same thing and is true only
   for that function.
3. The `track_a` fixture in test_export_security.py and `storage_helpers.approve` call `ledger.approve` and
   `ledger.attest_render` directly. Only `test_the_render_stage_attests_what_it_rendered` and
   `test_the_render_stage_does_not_render_unapproved_content` exercise the real `_stages` attestation.
   `storage_helpers.approve()` will attest whatever `video.mp4` is in place, so tests in test_export.py that swap a
   video and call `approve()` again silently bless arbitrary bytes. That is fine as a fixture, but it means those tests
   say nothing about the trust chain.
4. The fixtures' `project/` has only `index.html`, so the suite cannot see PF-01. Copy the real `s_compose` layout.
5. The CLI approve is tested only for "binds to the current content", never for "binds to what the owner reviewed".

## 6. Verdict (Round 1, superseded by 7.6)

- Bypass A (deleting `source_spec`): **closed** - VERIFIED (PF-12).
- Bypass B (repointing `source_spec` at a pristine copy): **closed** - VERIFIED (PF-13).
- The broader property ("nothing reaches ready/ unless it is bytes rendered from content a human approved, unchanged
  since") does **not** hold yet. The PRODUCTION digest omits rendered inputs (PF-01). The approver can be made to bind
  unreviewed content (PF-02). Publishing metadata and the destination are still manifest-controlled (PF-03, PF-04).
  Fix PF-01 and PF-02 before relying on this chain. PF-06 is a regression that will block honest jobs that use
  `audio_bed`.

## 7. Round 2

Date: Thu Nov 19 22:17 IST 2026 (from `date`). Subject: the same uncommitted working tree, now including the
implementer's response. I read the new `production_digest` / `_tree_parts` / `GENERATED_AUDIO`, the `_stages` and
`track_b.render` post-render rechecks, the `export_job` job_id check, `attest_registration`, `cli._subject_digest` /
`cmd_approve`, and the new tests at the end of `tests/test_export_security.py`. I also read the parts of the
HyperFrames compiler (`node_modules/hyperframes/dist/chunk-P3FGUSFK.js`, `collectExternalAssets`), `mpt.py` and
`renderers/remotion.py` that decide what a render reads.

Suite: `tests/test_export_security.py tests/test_export.py tests/test_job_register.py tests/test_pipeline_export.py
tests/test_track_b.py` -> `108 passed, 1 skipped`.

Method as in round 1. The round-1 scripts were re-run unchanged against fresh `/tmp/potato/potato-*` dirs. New scripts:
`/tmp/potato/r2.py` (R1-R7), `/tmp/potato/r2_tb.py`, `/tmp/potato/r2_state.py`. The mutation plugin is
`/tmp/potato/mut2.py`: it rewrites one guard line in the loaded function source and re-execs it, in-process only.
The repo was not modified except this file. HyperFrames was **not** run for real: its CLI sends anonymous render
telemetry, and network is out of bounds. Renderer behaviour therefore comes from reading its compiler source plus
the ffmpeg stand-in.

### 7.1 Re-run of round-1 attacks

| Script | Round 1 | Round 2 observed |
|---|---|---|
| a_ab (bypass A/B) | refused | refused, same message; exports with approval_refusal disabled |
| a_assets (PF-01) | `EXPORTED`, published audio != approved take | `production digest unchanged by swap: False`; `render: BLOCKED: gate PRODUCTION_APPROVED was approved for different content`; `export: REFUSED: a1: final video is missing` |
| a_tb T3 (PF-01, Track B assets) | `EXPORTED` | `TrackBError: PRODUCTION_APPROVED is required for the current digest` |
| a_bed (PF-06) | `REFUSED ... PRODUCTION_APPROVED changed` | `render: OK`, `audio/ now: ['01.wav', 'ambient_bed.wav']`, `export of an honest, approved render: EXPORTED exported` |
| a_jobid (PF-04 hijack) | `EXPORTED` into victim's slot | `REFUSED: a1: not exported, manifest.json names a different job ('v1')`; ready/ holds only v1's own bytes (dbb91660b042) |
| a_trav (PF-04 traversal) | files written to `escaped/` | `REFUSED: ... names a different job ('x/../../../escaped/owned')` |
| a_race (a) swap + restore index.html during render | `EXPORTED` | `render: OK`, `export: EXPORTED exported` - **still open** |
| a_race (b) replace video.mp4 after render, before hash | `EXPORTED`, attacker file | `export: EXPORTED exported | published == attacker file: True` - **still open** |
| a_tb4 (PF-10) | render OK | `TrackBError: SCRIPT_APPROVED is required for the current digest` (PRODUCTION inputs untouched, so only the new SCRIPT check can raise it) |
| a_reg (PF-11) | `uncaught: FileNotFoundError` | `already registered tb9 (Track B). Export needs both gates: ...`, returns `0` |
| a_bind (PF-02) | binds evil.yaml, exports | still binds evil.yaml and exports. New output, printed **after** the grant is recorded: `this approval covers: spec: .../elsewhere/evil.yaml / title: Approved title / | Words the owner never saw.` |
| a_tb T1 / T2 (PF-02) | bound / exported attacker video | unchanged: `T1 bound digest == evil digest: ok`, `T2 export -> EXPORTED exported | published == attacker video: True` (the CLI shows `the hand-built video ... (sha256 6f27...)`, which says nothing about what the video contains) |
| a_meta (PF-03) | forged sidecar | unchanged: sidecar title `Miracle cure doctors hate`, project `someone-elses-channel` |
| a_replay (PF-07) | v1 re-exported over v2 | unchanged: `export v1 again (force): EXPORTED exported`, `ready/ now holds v1 bytes: True` |
| a_verify V1-V15 (PF-14..18) | refused | all refused with the same messages; every one exports with approval_refusal disabled; V12 still allowed (by design) |
| a_studio (PF-19) | 409 / 200 | `409 DIGEST_MISMATCH`, `grants recorded: 0`, then `200 True` |

### 7.2 Status of each claimed fix

- **PF-01 -> VERIFIED** for the round-1 finding: files inside the composition root. Causality (`r2.py` R1): the same
  `project/assets/voice/01.wav` swap with `pipeline._tree_parts` patched to `lambda *a: []` gives `render: ('render',
  'OK') export: EXPORTED exported`. So the tree hash is what stops it. The neighbouring gaps are new findings
  PF-21, PF-22 and PF-23 below; they are why the PRODUCTION property as a whole still does not hold.
- **PF-02 -> OPEN (mitigated).** The display is printed after `ledger.approve` has already run, so it is a receipt,
  not a consent step. Nothing asks the owner to confirm, and the binding source is still `manifest.source_spec` /
  the video on disk. Observed above. For PRODUCTION on a composed job it prints only `the composed project and audio
  takes in <dir>`, which does not show the content.
- **PF-04 -> VERIFIED.** Both attacks are refused. The message `names a different job` is produced only by the new
  check in `export_job`. Mutation N3 (check removed) makes `test_pf04_...` fail. Residual: other manifest fields
  (title, project_id, created_at) still choose the slug and folder. They are slugified, so no traversal, but they
  remain PF-03.
- **PF-05 -> OPEN, partly fixed.** VERIFIED part: an unrestored composition swap during render. `r2.py` R6 gives
  `render: BLOCKED: the approved content changed while it was rendering; this render is not attested`, `attested:
  None`, and video.mp4 removed (`export: REFUSED: a1: final video is missing`). The Track B equivalent (`r2_tb.py`)
  gives `track_b.render: the approved content changed while it was rendering`, `attested: None`, export refused.
  Open part: (a) swap and **restore** before the renderer exits still exports, because the recheck compares state
  before and after, not what the renderer read. (b) The output-swap window is unchanged: `_stages` and
  `track_b.render` hash `video.mp4` in place after the recheck, so a file put there between renderer exit and the hash
  is attested (`a_race` b: `published == attacker file: True`). The recommendation stands: render from a snapshot
  into a private temp output, hash that, then `os.replace` it into place.
- **PF-06 -> VERIFIED.** `a_bed`: an honest render with `audio_bed` exports. Causality (`r2.py` R7, `GENERATED_AUDIO`
  emptied): `render: BLOCKED: the approved content changed while it was rendering`. Mutation N2 fails
  `test_pf06_...`. Side effect: the exclusion opens a hole (PF-22, `../audio/ambient_bed.wav`).
- **PF-10 -> VERIFIED** (a_tb4 above; mutation N6 fails `test_pf10_...`).
- **PF-11 -> VERIFIED** (a_reg above; mutation N7 fails `test_pf11_...`).
- **PF-03, PF-07 -> OPEN** (re-run, unchanged). **PF-08, PF-09 -> ACCEPTED RISK** (unchanged).

### 7.3 New findings (Round 2)

#### PF-21 [High, OPEN] A symlinked directory under the project binds only its link text

- Location: `pipeline._tree_parts`. For a symlinked directory it appends `link <rel> <readlink>` and does not
  descend. `os.walk` does not follow links.
- Description: if any directory in the composition root is a symlink when PRODUCTION is approved, every file behind
  it can be changed afterwards without moving the digest. The CLI shows only "the composed project ... in <dir>", so
  the owner cannot see that `project/assets` is a link. The exemption exists for Remotion's shared `node_modules`
  but applies to every directory.
- Reproduction (`/tmp/potato/r2.py` R2): before approval, `project/assets` is moved to `<root>/outside/assets` and
  replaced by a symlink to it (same bytes). Approve both gates, then `wav(<root>/outside/assets/voice/01.wav, 1500)`.
  Observed: `digest unchanged: True`, `render: ('render', 'OK') | export: EXPORTED exported`, `published audio ==
  approved take: False`.
- Recommendation: descend into symlinked directories and hash their content, as for files, except for one explicit
  allowlisted toolchain link per lane (`project_remotion/node_modules` -> the configured `REMOTION_DIR`). Refuse
  approval and render if any other directory symlink exists. Change `test_pf01_a_symlinked_directory_is_bound_by_its_target`
  to modify a file **behind** the link; today it only checks that adding a link changes the digest.

#### PF-22 [Medium, OPEN] Assets loaded from outside the composition root are not bound

- Location: `production_digest` hashes the composition root plus `audio/*.wav` minus `GENERATED_AUDIO`. The HyperFrames
  compiler `collectExternalAssets` (dist/chunk-P3FGUSFK.js) resolves every `src`/`href`/CSS `url()` against the
  project dir. A path outside it that exists is copied into the render ("asset(s) outside project directory - will
  copy to render output"). `http(s)` media and CDN scripts are downloaded at render time (`REMOTE_MEDIA_TAG_RE`,
  "Inlined CDN script").
- Description: a composition approved with `<audio src="../extras/bg.wav">`, `../audio/ambient_bed.wav` (excluded by
  the PF-06 fix), `../audio/music.mp3` (only `*.wav` is globbed) or a remote URL renders whatever those resolve to
  at render time. The composition text is bound; the bytes are not. Pipeline-composed jobs do not emit such
  references; Track B hand-built compositions and agent-edited pages can.
- Reproduction (`/tmp/potato/r2.py` R3): each of the three references above, file swapped after approval:
  `digest unchanged after swap: True` for all three. End to end for `../extras/bg.wav`, with a stand-in that plays the
  external file as HyperFrames copies it in: `render: ('render', 'OK') | export: EXPORTED exported`.
- Recommendation: refuse to approve or render a composition that references anything outside its root or any non-local
  URL. Parse the same attributes HyperFrames does, or run `hyperframes lint` with that rule if it has one. Otherwise,
  hash every resolved external file into the digest. Also hash all of `audio/` except the generated file, and make sure
  a composition cannot reference the generated file.

#### PF-23 [Medium, OPEN] MPT lane: local b-roll materials are not bound

- Location: `mpt.request` takes `mpt.materials` paths anywhere under the workspace jobs root (including other jobs).
  The MPT sentinel `project/mpt-request.json` records only container paths.
- Reproduction (`/tmp/potato/r2.py` R4): material `<jobs>/broll/clip.mp4`, request written, digest taken, material
  replaced. Observed: `material swapped, digest unchanged: True | request names it: ['/workspace/projects/broll/clip.mp4']`.
  Docker/MPT was not run; this proves only the digest gap. Stock-source b-roll (pexels) fetched at render is inherently
  unbound.
- Recommendation: add `material <path> <sha256>` parts for each local material to `production_digest` when
  `render == "mpt"`. Document that stock b-roll fetched at render is outside the approval.

#### PF-24 [Info, ACCEPTED RISK] Remotion `node_modules` content is not bound

- `r2.py` R5: changing a file behind `project_remotion/node_modules` -> `digest unchanged: True`. Assumption: the
  shared Remotion install (`~/.contentos/remotion`) is toolchain, trusted like the hyperframes binary and ffmpeg.
  PF-21's fix should make this the only exempt link.

#### PF-25 [Low, OPEN] Track B leaves a rejected render on disk

- `r2_tb.py`: after the recheck blocks, `video.mp4 left in place: True` (the pipeline path removes it; the test
  asserts that for the pipeline only). Export refuses it, but `contentos job register` will attest it as a hand-built
  render, and the CLI then tells the owner to approve PRODUCTION for "the hand-built video" (PF-02 path, like T2).
  Recommendation: unlink `video.mp4` in `track_b.render` on the recheck failure, as `_stages` does. Add the Track B case
  to `test_pf05_...`.

#### PF-20 [Low, OPEN] Forged publish-dir export state deletes an arbitrary file

- Location: `export._existing` trusts `.state/exports/<job>.json` (`Path(pub) / rec["video"]`, no containment check).
  `_export_locked` with force unlinks `prior[0]` when it differs from the destination.
- Reproduction (`/tmp/potato/r2_state.py`): an honest approved job. `pub/.state/exports/a1.json` = `{"video":
  "../precious.txt", "sidecar": "fake.publish.json"}` plus a sidecar naming job a1. Observed: `export --force: EXPORTED
  exported`, `victim still exists: False`.
- Impact is limited to whoever can write the publish library (scheduler, sync tools). That principal can usually
  delete files itself, so Low. It was there before this branch.
- Recommendation: in `_existing`, resolve both paths and require them to be inside `pub / "ready"`; ignore the record
  otherwise.

### 7.4 Test quality (Round 2)

Mutation pass (`MUT=Nx PYTHONPATH=/tmp/potato ... -m pytest <5 files> -p mut2`), with one new guard removed each time:

| Mutation | Result |
|---|---|
| N1 `_tree_parts` returns [] | 5 failed: 3x `test_pf01_every_file...`, `test_pf01_a_symlinked...`, plus `test_export.py::test_two_processes_one_copy`. The last one is an artifact of my in-process mutation: its subprocesses import the unmutated module and compute a different digest. Unmutated it passed 3/3. |
| N2 `GENERATED_AUDIO` ignored | 1 failed (`test_pf06_...`) |
| N3 job_id check removed | 1 failed (`test_pf04_...`) |
| N4 `_stages` recheck removed | 1 failed (`test_pf05_...`) |
| N5 `track_b.render` recheck removed | **0 failed** - no test covers the Track B mid-render recheck |
| N6 Track B SCRIPT gate removed | 1 failed (`test_pf10_...`) |
| N7 `attest_registration` no-video guard removed | 1 failed (`test_pf11_...`) |
| N8 approve display removed | 1 failed (`test_pf02_...`) |
| N9 symlinked-dir `link` part removed | 1 failed (`test_pf01_a_symlinked...`) |

Gaps:
1. The Track B recheck (N5) is untested, and so is the PF-25 leftover video.
2. `test_pf01_a_symlinked_directory_is_bound_by_its_target` overclaims. It adds a link and checks the digest moves;
   it never changes content behind the link, which is the PF-21 bypass.
3. `test_pf05_...` covers only the unrestored swap. Neither the restore variant nor the output-swap window is tested,
   and both are still exploitable.
4. `test_pf02_...` asserts that the display text exists, not that the owner saw it before binding. It would pass with
   the current print-after-bind order, which is the weakness.
5. Nothing tests out-of-root references (PF-22), MPT materials (PF-23) or the PF-06 exclusion being abused.
6. Each new guard has exactly one test that fails without it, and those tests assert on state (`render_record is
   None`, `tree(env.pub) == before`, video removed), not only messages. Good.

### 7.5 Not verified

- No real HyperFrames / Remotion / MPT render (telemetry/network and Docker). Two consequences: PF-22 rests on the
  compiler source plus the stand-in, and I could not check whether a real HyperFrames or Remotion render writes
  anything inside the composition root. If it does (a cache, a `renders/` dir), the new post-render recheck would
  block every honest render, the same way PF-06 did. Worth one real render before merging.

### 7.6 Verdict (Round 2)

- Bypass A (delete `source_spec`): **closed - VERIFIED** (re-run, same refusal, causality re-checked).
- Bypass B (repoint `source_spec` at a pristine copy): **closed - VERIFIED**.
- The round-1 fixes for PF-01 (in-root files), PF-04, PF-06, PF-10 and PF-11 are VERIFIED.
- The full property still does not hold. Content behind a symlinked directory (PF-21, High), outside the root
  (PF-22) or in MPT materials (PF-23) can change after approval and ship. The approver can still be steered to bind
  unreviewed content (PF-02, High). The render-window swaps remain (PF-05). Metadata and stale-approval issues
  (PF-03, PF-07) are untouched. Fix PF-21 and PF-02 before relying on the chain; PF-21 is a small change.

## 8. Round 3

Date: Fri Nov 20 01:11 IST 2026 (from `date`). Subject: the same uncommitted working tree with the implementer's
round-3 changes: `_tree_parts` follows symlinked dirs, exempts only `project_remotion/node_modules`, returns None on
FIFO/device; `track_b.render` unlinks a rejected video; `export._existing` containment check; `cmd_approve` prints
before recording, plus `--show`, `--expect` (`is not None`) and `spoken as: <tts>`.

Suite: 5 files (`test_export_security`, `test_export`, `test_job_register`, `test_pipeline_export`, `test_track_b`)
-> `117 passed, 1 skipped`.

ID mapping: the implementer's PF-26..PF-29 are new IDs for issues I raised in my round-3 transcript before this file
was updated. PF-26 = `--show` printed only `say` while the voice speaks `tts`. PF-27 = the node_modules exemption
applied to any symlinked `node_modules` (HyperFrames page loading `./node_modules/voice.wav`: digest unchanged,
render OK, **exported** on the pre-fix code). PF-28 = FIFO/device files hashed as a constant. PF-29 = `--expect ""`
silently granted.

Scripts: `/tmp/potato/r3.py`, `/tmp/potato/r3b.py` (fresh `/tmp` workspaces, real `cli.cmd_approve`,
`pipeline.run`, `track_b.render`, `export_job`; ffmpeg stand-in renderer). Mutations: `/tmp/potato/mut3.py`,
`/tmp/potato/mut4.py` (same technique as round 2).

### 8.1 Attack re-runs (observed)

| Finding | Attack | Observed |
|---|---|---|
| PF-21 | content behind a symlinked `project/assets` changed after approval | `digest unchanged: False`, `render: BLOCKED: gate PRODUCTION_APPROVED was approved for different content`, `export: REFUSED: final video is missing` (in round 2 the same script exported) |
| PF-27 | symlinked `project/node_modules` and `project/assets/node_modules`, file behind swapped | both `digest unchanged: False`, render BLOCKED, export REFUSED |
| PF-28 | FIFO in project at approval / after approval / after render | approve: `recorded unbound ... export refuses unbound`; render: `BLOCKED ... different content`; export: `REFUSED ... PRODUCTION_APPROVED changed after this render` |
| PF-25 | Track B composition swapped mid-render | `blocked: the approved content changed while it was rendering`, `video.mp4 left: False` |
| PF-20 | forged record `{"video": "../precious.txt"}`; and a record aimed at `ready/old.mp4`, a symlink to an outside file | both `export --force: EXPORTED`, `victim exists: True` (the symlink variant is covered by `resolve()`) |
| PF-26 | line with `tts` != `say` | `--show mentions tts: True`; when tts == say there is no extra line (correct) |
| PF-29 | `--expect ""` | `rc 1`, grants 0 |
| PF-02 | `--show` then content swapped then `--expect <shown digest>` | `rc 1`, grants 0. `--show` alone: rc 0, grants 0. Unreadable `source_spec` with `--expect`: rc 1. Track B video swapped and re-registered, `--expect` old digest: rc 1, export refused |
| PF-02 | default path: manifest `source_spec` repointed, plain `contentos approve` | `rc 0`, `bound evil: ok` - unchanged, still OPEN |

### 8.2 Mutation check (each guard removed, `tests/test_export_security.py`)

| Guard removed | Failing test |
|---|---|
| `followlinks=True` -> False | test_pf21_files_behind_a_symlinked_directory_are_bound, test_pf27_... |
| node_modules exemption no longer scoped to `project_remotion` | test_pf27_only_remotions_top_level_node_modules_is_exempt |
| FIFO `return None` -> `continue`; or production_digest ignores None tree | test_pf28_a_fifo_in_the_project_cannot_be_approved (both) |
| `spoken as` line removed | test_pf26_show_prints_what_the_voice_will_speak |
| `expect is not None` -> truthy | test_pf29_an_empty_expect_is_an_expectation |
| Track B mid-render recheck removed (the round-2 gap, N5) | test_pf25_a_track_b_render_blocked_mid_render_leaves_no_video - **gap closed** |
| Track B unlink removed | test_pf25_... |
| `_existing` containment removed | test_pf20_a_forged_export_record_cannot_aim_force_at_another_file |
| `--show` early return removed | test_pf02_approve_shows_what_it_binds_before_recording |

Remaining test gap: with the `real in seen` loop guard removed, `test_pf21_a_symlink_loop_terminates` still passed
(os.walk stops at the OS symlink-depth limit), so the guard is untested. Low impact: the guard prevents slowness and
duplicate parts, not a bypass.

### 8.3 Residual notes (no new IDs, Info)

- `tts: ""` (empty) is bound by the digest but `--show` prints no `spoken as` line (truthy check), while the voice stage
  speaks `""`. The effect is a silent line, which PRODUCTION review of the audio would catch.
- A FIFO named `audio/*.wav` makes `sha256_file` block (approve/render hang). Denial of service only.
- `--show` for PRODUCTION on a composed job still prints only `the composed project and audio takes in <dir>`, with no
  file list. `--expect` pins exactly what was there at `--show` time, but the owner is not shown what that is.
- The implementer reports a real HyperFrames render (22:17) that rendered, attested and exported, which addresses the
  7.5 concern. I did not reproduce it (network/telemetry rule). Remotion and MPT were still not run.

### 8.4 Final status table (all IDs, supersedes the table in section 3 and statuses in 7.2/7.3)

| ID | Severity | Final status | Title / evidence |
|---|---|---|---|
| PF-01 | High | VERIFIED | Files inside the composition root are bound (R2; causality by `_tree_parts` removal) |
| PF-02 | High | OPEN (mitigated) | `--show` / `--expect` work and are VERIFIED (8.1). Default `contentos approve` still binds from `manifest.source_spec` / the disk without consent; making `--expect` mandatory is an owner decision |
| PF-03 | Medium | OPEN | Sidecar title/description/tags/targets/project come from the manifest, not approved |
| PF-04 | Medium | VERIFIED | Manifest job_id != requested job refused (R2) |
| PF-05 | Medium | OPEN (partly fixed) | Unrestored mid-render swap refused (VERIFIED, both tracks). Swap-and-restore during render and the video.mp4 output-swap window before hashing remain |
| PF-06 | Medium | VERIFIED | audio_bed honest render exports (R2) |
| PF-07 | Low | OPEN | Superseded approvals stay valid; v1 re-exported over v2 |
| PF-08 | Medium | ACCEPTED RISK | `--approve-private` self-grants; assumption: the operator of that flag acts for the owner |
| PF-09 | Info | ACCEPTED RISK | Ledger/approve CLI unauthenticated; assumption: single-user machine, no direct sqlite writes |
| PF-10 | Low | VERIFIED | Track B render requires SCRIPT_APPROVED (R2) |
| PF-11 | Info | VERIFIED | `job register` without video no longer crashes (R2) |
| PF-12 | - | VERIFIED | Original bypass A (delete `source_spec`) closed |
| PF-13 | - | VERIFIED | Original bypass B (repoint `source_spec` at a pristine copy) closed |
| PF-14 | - | VERIFIED | Render replacement, forged manifest, video symlink, swap + re-register refused |
| PF-15 | - | VERIFIED | Unbound / foreign / missing approvals and attestations refused |
| PF-16 | - | VERIFIED | Spec deleted / truncated / dir symlink / substituted; audio edited - refused |
| PF-17 | - | VERIFIED | Video swapped between check and copy refused |
| PF-18 | - | VERIFIED | All three export routes refuse |
| PF-19 | - | VERIFIED | Studio approve seenDigest handshake |
| PF-20 | Low | VERIFIED | Forged export record cannot aim `--force` outside ready/ (also via symlink inside ready/) |
| PF-21 | High | VERIFIED | Content behind symlinked directories is bound |
| PF-22 | Medium | OPEN | Assets referenced from outside the composition root (`../x`, `audio/ambient_bed.wav`, non-.wav in audio/, remote URLs) not bound |
| PF-23 | Medium | OPEN | MPT local materials not bound |
| PF-24 | Info | ACCEPTED RISK | `project_remotion/node_modules` bound by link only; assumption: the shared Remotion install is trusted toolchain |
| PF-25 | Low | VERIFIED | Rejected Track B render deleted |
| PF-26 | Medium | VERIFIED | `--show` prints `spoken as: <tts>` |
| PF-27 | Medium | VERIFIED | node_modules exemption limited to `project_remotion/node_modules` |
| PF-28 | Low | VERIFIED | FIFO/device makes the digest None: approval unbound, render/export refused |
| PF-29 | Low | VERIFIED | `--expect ""` refuses |

### 8.5 Verdict (Round 3)

Original bypasses A and B: **closed, VERIFIED**. The chain now holds against every in-root, symlink, manifest,
attestation and replay-of-files attack I ran. The claimed property still does **not** fully hold, because of PF-02
(default approve binds unreviewed content chosen by editable state), PF-22/PF-23 (render inputs outside the digest),
PF-05 (render-window swaps), PF-03 (unapproved publishing metadata) and PF-07 (stale approvals). PF-02 is High. If the
owner makes `--expect` (or the Studio flow) the only way to approve, PF-02 closes with no new code.
