# T4 — Advisory style-frame / storyboard checkpoint

**Goal:** before building a whole video, a human sees 3–5 still frames plus a one-line-per-scene shot list and records **approved / redirect / rejected**. This task builds only the *record and its checks*. It does **not** generate frames, does **not** block any pipeline stage, and does **not** replace `SCRIPT_APPROVED`/`PRODUCTION_APPROVED`.
**Prereq:** T0 CLEARED, T2 DONE, T3a DONE.
**You create:** `contentos/production/checkpoint.py`, `tests/test_checkpoint.py`. **You modify:** nothing.

## 1. Read first
`contentos/production/sheet.py` (how sheets are made; note it fails closed without `drawtext`), `contentos/production/preview.py` (`video_frames`, `contact_sheet`), `AGENTS.md` §2 (gates) and §10. Understand: frames come from existing tools or the owner; this module only records the review.

## 2. Snapshot
`bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/before-T4.txt`

## 3. Contract `style-checkpoint/1`
```json
{"schema": "style-checkpoint/1", "job": "ep4-example", "style": "blueprint-diagram",
 "mode": "full",                      // "full" (3-8 frames) or "lite" (exactly 1 frame; for 15-second Shorts)
 "frames": [{"path": "/abs/or/rel/frame1.png", "sha256": "…"}],
 "shot_list": ["s1 hook: …", "s2 mechanism: …"],
 "status": "pending",                 // pending | approved | redirect | rejected | stale
 "decision": null,
 "advisory": true}
```
After a human decision `decision` becomes `{"by": "Kishore", "at": "2026-10-12", "note": "…"}`.

Rules (each needs a test):
- `request(...)`: frames must exist, be `.png/.jpg/.jpeg`, be regular files, count 3–8 (`full`) or exactly 1 (`lite`); `shot_list` ≥ 1 non-empty string (`full`: ≥ 3); `style` must be a valid card id from `styles.load_all()`; `job` matches the job-id regex; refuses to overwrite an existing `--out`.
- `decide(...)`: only from `pending`; `decision` ∈ `approved|redirect|rejected`; `by` is a non-empty string and the flag `--human` must be passed (a deliberate speed-bump so an agent cannot silently approve); `redirect`/`rejected` require a note ≥ 8 chars.
- **Stale detection:** `verify(path)` recomputes each frame's sha256; if any frame is missing or changed since the request, status becomes reported as `stale` (returned, and written only by `decide`'s refusal message — never silently edit the file in `verify`).
- `advisory` is always `true` in this version. There is no function that reads a checkpoint to allow/deny a pipeline stage.

## 4. Tests first (`tests/test_checkpoint.py`)
Use `tmp_path`; make tiny PNGs by writing a valid 1×1 PNG bytes constant (`b"\x89PNG\r\n\x1a\n" + …` — or simply write any bytes to a `.png` file: the module checks extension and existence, not image decoding; say so in a comment).
1. request ok (full) / request ok (lite) → file written with `status == "pending"`, `advisory is True`, correct hashes.
2. request refuses: missing frame, wrong extension, 2 frames in full, 2 frames in lite, empty shot list, unknown style id, bad job id, existing out.
3. decide approve with `human=True` → status `approved`, decision has `by`, `at`.
4. decide refuses without `human=True`; with empty `by`; from non-pending; redirect with short note.
5. verify detects a changed frame (modify bytes) and a deleted frame → `{"stale": True, "changed": [...]}`.
6. decide on a stale checkpoint is refused with a message telling the human to re-request.
7. `test_module_has_no_gate_or_pipeline_imports` — `inspect.getsource(checkpoint)` contains neither `pipeline` nor `approve(` nor `SCRIPT_APPROVED`/`PRODUCTION_APPROVED`/`PUBLISH_APPROVED`.
8. CLI exit codes: ok 0, refusal 1, unreadable 2.

## 5. Implementation guide (write it yourself in the style of `styles.py`; keep under ~180 lines)
Functions: `request(job, style, frames, shot_list, out, mode="full") -> dict`, `verify(path) -> dict`, `decide(path, decision, by, human, note="", at=None) -> dict`, `main(argv)`.
CLI:
```
python -m contentos.production.checkpoint request --job J --style S --frame F1 --frame F2 --frame F3 --shot "…" --shot "…" --shot "…" --out FILE [--lite]
python -m contentos.production.checkpoint verify FILE
python -m contentos.production.checkpoint decide FILE --decision approved --by NAME --human [--note TEXT]
```
Use `hashlib.sha256` in 64 KiB chunks, `json.dumps(indent=1)`, `datetime.date.today().isoformat()` only in the CLI layer (pass `at` into `decide`). Imports allowed: stdlib, `contentos.intelligence.styles`. No ffmpeg, no pipeline.

## 6. Verify
```bash
~/.contentos/venv/bin/python -m pytest tests/test_checkpoint.py -q
~/.contentos/venv/bin/python -m pytest tests -q
bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/after-T4.txt && diff $HOME/audit-scratch/before-T4.txt $HOME/audit-scratch/after-T4.txt
```
Manual smoke (in `$HOME/audit-scratch/t4/`, **not** in the repo): create three dummy `.png` files, run `request`, `verify`, then `decide … --human`; paste outputs.

## 7. Acceptance
Tests pass; no existing test changed; only two new repo files; smoke outputs pasted; test 7 proves no gate coupling.

## 8. Rollback / Do not
`rm contentos/production/checkpoint.py tests/test_checkpoint.py`. Do not call `./contentos.sh approve`, import `pipeline`, or make any stage read checkpoints. Do not generate frames here (render/preview happens in T9 under the owner's eye).
