# Test inventory (Phase 4, 2026-10-20)

Verified on the owner's Mac, `main` at eab249a. Commands run from the repo root with `/opt/homebrew/bin` first on PATH and a scratch `VIDEO_FACTORY_WORKSPACE` / `VIDEO_FACTORY_PUBLISH_DIR` (as CI does). Nothing in the repo changed.

## Actual results

| Suite | Command | Result |
|---|---|---|
| Node adapter | `node --test contentos/adapters/v1/*.test.mjs` | 44 pass, 0 fail, 0 skip (5.0 s) |
| Python, whole `tests/` | `~/.contentos/venv/bin/python -m pytest tests -q -rs` | COLLECTION ERROR in `tests/test_sheet.py`; run aborts before executing anything |
| Python, minus `test_sheet.py` | same plus `--ignore=tests/test_sheet.py` | 591 passed, 48 failed, 177 errors, 6 skipped (15 s) |

Cause of the red (measured, not assumed): `/opt/homebrew/bin/ffmpeg` and `/opt/homebrew/bin/whisper-cli` do not exist on this Mac right now. The only `ffmpeg` on PATH is the dead x86 `/usr/local/bin/ffmpeg`. 223 of the 225 failing/erroring tests show `OSError: [Errno 86] Bad CPU type in executable: 'ffmpeg'` (218) or `'ffprobe'` (5). The other two (`test_finalcheck_missing_empty_and_garbage_files_fail` KeyError `render_integrity`; `test_invalid_audio_with_audio_extension` regex mismatch) sit in the same ffprobe-dependent files and were not isolated; treat them as unexplained until ffmpeg is installed and they are re-run. `./contentos.sh doctor` agrees: `[stt] NONE`, `ffmpeg NOT_INSTALLED`, `[llm]`, `[youtube_read]`, `[publish_youtube]`, `[decision]` NONE. Selected and healthy: `tts: kokoro_local`, `render: hyperframes` (and `mpt` answers on 127.0.0.1:8081).

So the green count is a lower bound on health, not proof, and the pipeline cannot currently render on this machine. A job rendered here on 2026-10-19 (`m3-sample-01-hf-sketch`, ledger rows all OK), so ffmpeg disappeared since. Owner action: `brew install ffmpeg whisper-cpp` (not done by this mission).

Two defects found while running (both in test infrastructure, in scope under the "fix flakiness and failures" rule, but not fixed because this is a discovery mission; listed in the roadmap as M0):
1. `tests/test_sheet.py:88` evaluates `drawing_ok()` at import time; with a non-executable ffmpeg this raises instead of skipping, so the whole `pytest tests` command dies at collection. A bare-minimum fix is catching `OSError` in `sheet._drawtext_available` (`contentos/production/sheet.py:87`) and returning False.
2. CI (`.github/workflows/ci.yml`) installs ffmpeg with `brew install ffmpeg` and so cannot see problem 1; it also never installs whisper-cpp, Chrome-dependent E2E is opt-in, so CI does not cover a real render.

## CI

`.github/workflows/ci.yml`: on pull_request and push to main; `macos-latest`; Python 3.12 with only `pytest pyyaml numpy`; Node 22; `brew install ffmpeg`; `npm ci`; `pytest tests -q -rs`; `node --test contentos/adapters/v1/*.test.mjs`; fails if the tree is dirty. Pinned upstream skills are not synced (those tests skip). Last CI result was not read here (no network request made); `gh-axi` reported 0 open PRs. No browser, accessibility or visual-regression job exists.

## Per-file profile (counts from `def test_` greps; "mocks" = uses monkeypatch/mock/patch; "ffmpeg" = shells out to ffmpeg/ffprobe)

Deterministic unless stated. Names are not coverage claims; the "Verifies" column comes from each file's docstring or first lines.

| File | Tests | Mocks | ffmpeg | Verifies | UI journeys |
|---|---|---|---|---|---|
| test_approval_binding | 23 | yes | no | approvals bound to script/production digests, authorising identity | J12 |
| test_core | 5 | yes | no | production core retry/failure class with injected run/sleep/clock | J5, J9 |
| test_production_core_smoke | 13 | yes | no | failure meaning, retry, what a hard kill leaves behind | J5, J9 |
| test_storage / test_storage_admin / test_job_day_folders / test_legacy_manifest | 20 / 9 / 2 / 8 | yes | no | path safety, no in-repo workspace, manifests, migration, cleanup (temp copies) | J1, J13 |
| test_export / test_export_divergence / test_pipeline_export | 22 / 9 / 19 | yes | yes (fixture clips) | export lifecycle, atomic promotion, divergence reporting | J14 |
| test_handoff | 12 | yes | yes (fixtures) | scheduler boundary, claiming, duplicates | J6 |
| test_job_register | 15 | yes | yes | Track B registration | J2 |
| test_hf / test_renderers / test_mpt / test_remotion_render | 5 / 8 / 6 / 1 | partly | no | HyperFrames CLI path, renderer registry, MPT adapter, Remotion (the last is labelled E2E, see gaps) | J3, J5 |
| test_pipeline_hooks / test_pipeline_captions / test_caption_* / test_align_sceneplan | 6 / 6 / 6+7 / 6 | some | no | golden compose output with features off, caption timing on a recorded ASR take | J5 |
| test_feature_* (7 files) + test_feature_regressions | 3-6 each | no | audio_bed and extra_gates call ffmpeg | M2 feature hooks | J3 |
| test_e2e_features | 1 (6 fixtures) | few | yes | REAL pipeline run, real render, six fixtures; opt-in `CONTENTOS_E2E=1`, about 5 min, needs Chrome, ffmpeg, Kokoro | J5, J10 |
| test_visual_gate / test_safe_zone / test_gate_calibration / test_gate_negative_controls / test_visual_language / test_visual_dominant_backdrop / test_visual_scene_backdrops / test_motion_audit / test_layout | 23 / 22 / 58 / 17 / 23 / 21 / 11 / 8 / 1 | rarely | many on synthetic clips | gates fail on deliberately bad clips and pass on good ones; Rule A/B | J11 |
| test_critic / test_cue_audibility / test_checkpoint / test_platforms / test_direction / test_director / test_creative / test_designs / test_styles / test_motion_catalogue / test_timeline_* / test_sheet | various | no | sheet only | schemas and validators for plans, critics, catalogues, timeline (shadow), contact sheets | J4, J10, J11 |
| test_supplied_audio | 34 | yes | yes | supplied voiceover rights record and publication block | J14 |
| test_loops, test_measure_job, test_upstream_skills | 5 / 14 / 6 | yes | no | learning loops, process-tree sampler, skill pin verification | none |
| `contentos/adapters/v1/*.test.mjs` (7 files) | 44 | local | no | contract v1 validation, exchange folders, worker lifecycle, process-group kill | parked ContentForge lane |

## What is NOT tested at all (grep-verified)

- `dashboard.py` / `dashboard.html`: no test file references `dashboard` (see gaps).
- `queue.py` (`add`, `claim`, `work`, `requeue`): the word "queue" appears only in `test_production_core_smoke.py` and `test_storage_admin.py`; no test starts a worker.
- `cli.py` as a whole: only `test_approval_binding.py` and `test_job_register.py` import it (approve and job register paths); `cmd_doctor` output and argument parsing are untested.
- `providers.py` health probes (tests reference `providers` only in `test_core`, `test_supplied_audio` and the pinned-skills helper).
- Any browser, accessibility or visual-regression check of a UI.

## What could break if the UI or backend changes

Anything the UI adds writes to the ledger (`approvals`, `jobs`) and the job manifest. The tests that guard those: `test_approval_binding`, `test_storage*`, `test_core`, `test_production_core_smoke`, `test_export*`. A UI that calls `pipeline.run` / `core.run_until_blocked_or_done` in-process, instead of re-implementing them, stays under those tests.
