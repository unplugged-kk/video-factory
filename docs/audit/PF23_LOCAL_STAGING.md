# PF-23: staged MPT adapter inputs

**Status: tested at the adapter boundary; PF-23 remains open.** The old request passed arbitrary existing job-root material paths to a shared container mount. The production digest covered the request strings, not the referenced footage; remote sources could pick clips after review. `tests/test_mpt.py` reproduced the missing staging and late stock paths before the fix.

## Operational behavior

- Use `mpt.source: local` and set `mpt.materials` to files under workspace `jobs/`. Out-of-root files, symlink components and non-regular files are refused. For legacy jobs re-run compose before reviewing; legacy requests produce no digest. The existing stock example is not runnable through this route until reviewed stock staging is built.
- Compose copies the ordered inputs into `project/mpt-assets/` and records SHA-256, jobs-relative origin and the user-supplied/rights-unverified label in `project/mpt-request.json`. There is no verified license input for the existing local path-list format. Joined narration is also staged and hashed. Same bytes can share a staged path when extensions match; each selection retains its provenance and order.
- `production_digest` refuses a missing, malformed, substituted or spec-mismatched request. The existing digest hashes the manifest and the staged project tree. `render` derives Docker arguments from validated staged paths, not from editable container path fields. It checks the container mount's hashes before its CLI call. The rights receipt summarizes the reviewed list, not a claim about every clip actually used by the vendor.
- Render-time Pexels, Pixabay and Coverr selection is blocked. To use footage obtained separately, import it as local clips after checking rights. This is not an automated stock acquisition path and does not verify the provider's license.

## Reproduction and evidence

ARM64, Python 3.12.16, pre-change HEAD `cce972d` plus the stated working diffs; logs in `/Users/kishore/.contentos/checkpoints/video-factory-pf23.89gf1FNw/`. Local clocks IST.

| Run | Start/end | Command | Result |
|---|---|---|---|
| Red | 14:15:25-14:15:26 | `~/.contentos/venv/bin/python -m pytest tests/test_mpt.py -q` | 10 failed, 5 passed, exit 1, `mpt-red.log` |
| Focused | 14:18:28-14:18:49 | `~/.contentos/venv/bin/python -m pytest tests/test_mpt.py tests/test_export_security.py tests/test_ui_api.py tests/test_lang.py -q -rs` | 160 passed, exit 0, `targeted-final.log` |
| Node | 14:18:28-14:18:35 | `node --test contentos/adapters/v1/*.test.mjs` (Node 24.22.1) | 66 passed, exit 0, `node.log` |
| Full local Python | 14:18:17-14:21:27 | `~/.contentos/venv/bin/python -m pytest tests -q -rs` with isolated storage roots; final code diff before commit | 1,224 passed, 17 skipped, exit 0, `full-python.log` |
| Real HyperFrames regression | 14:21:46-14:22:42 | `CONTENTOS_E2E=1 ~/.contentos/venv/bin/python -m pytest tests/test_e2e_features.py -q -rs -k hf-sketch --basetemp <evidence>/hf-regression` at `46f8e78`, offline model settings | 1 passed, 5 deselected, exit 0, `hf-regression.log`; 12 technical QA passes |

The HyperFrames regression used the existing mutable lane, not the PF-05 prototype. Primary frame inspection found the familiar text-card layout and a dim transition sample at 10 seconds; no creative or independent acceptance. Actual MP4 and contact sheet are under `hf-regression/`.

## Limits

No MPT image was present on the local Docker daemon; no install or network requests were made. Tests validate the manifest and Docker argument contract with fixtures, not real clip selection. The mount hash check and vendor reads are separate operations; a same-user host writer could still change and restore staged data between them. PF-05 must remove live job mounts. Content-addressed clips are retained across compose runs; do not prune them automatically until retention and approved snapshot references are defined. Independent review remains pending.
