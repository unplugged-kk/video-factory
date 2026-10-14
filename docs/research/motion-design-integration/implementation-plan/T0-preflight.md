# T0 — Preflight (no code changes)

**Goal:** prove the starting state is healthy, create the snapshot tool, and get the two owner answers that unblock everything.
**You create:** files **outside the repo** only (`$HOME/audit-scratch/…`) plus one repo doc: `docs/research/motion-design-integration/implementation-plan/90-run-log.md`.
**You modify:** nothing in the repo.

## 1. Steps

1. Read `00-MASTER-PLAN.md` fully, then `AGENTS.md` sections 1, 2, 4.
2. Confirm tools:
   ```bash
   test -x ~/.contentos/venv/bin/python && echo VENV_OK || echo VENV_MISSING     # MISSING → BLOCKED, stop
   cd $HOME/mnt/video-factory 2>/dev/null || cd /Users/kishore/git/video-factory
   git rev-parse HEAD ; git status --porcelain ; git stash list | wc -l
   ```
3. Write `$HOME/audit-scratch/snapshot.sh` exactly as in Master Plan §5.1. `chmod +x` it. Run it: `bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/before-T0.txt`. Do **not** overwrite `$HOME/audit-scratch/pre-state.txt` (audit evidence).
4. Baseline tests (read-only; writes only `__pycache__`, which is gitignored):
   ```bash
   ~/.contentos/venv/bin/python -m pytest tests -q -p no:cacheprovider 2>&1 | tail -15
   ```
   Record: passed / failed / skipped counts, and the **names** of any failing tests. If anything fails, that is a pre-existing failure: record it, do not fix it, and tell the owner.
5. Also run `node --test contentos/adapters/v1/*.test.mjs 2>&1 | tail -5` and record the result (read-only). If `node` is missing, record "not run".
6. Run `bash $HOME/audit-scratch/snapshot.sh $HOME/audit-scratch/after-T0.txt` and `diff` it with `before-T0.txt`. Must be identical.
7. Check ground-truth facts the plan relies on; write each as `OK` / `DIFFERENT: <what>`:
   - `ls contentos/production/{timeline,critic,direction,motion_audit,sheet,visual_gate}.py contentos/intelligence/{designs,visual,catalogue}.py scripts/upstream_skills.py config/capabilities.json config/upstream-skills.lock.json`
   - `grep -n "^def load_registry" contentos/production/direction.py`
   - `grep -n "^SCHEMA\|^def validate\|^def build_timeline" contentos/production/timeline.py`
   - `grep -n "^DIMENSIONS\|^MIN_EACH" contentos/production/critic.py`
   - `ls config/styles 2>&1` (expected: no such directory — we create it in T2)
   - `ls contentos/intelligence/styles.py contentos/intelligence/creative.py contentos/production/checkpoint.py contentos/production/cue_audibility.py 2>&1` (expected: none exist; if any exist, **stop**: someone started this work).
8. Create `docs/research/motion-design-integration/implementation-plan/90-run-log.md` and append the T0 report (Master Plan §5.4) plus the baseline numbers and ground-truth results.

## 2. Questions to put to the owner (verbatim) — T0 is not DONE until answered

> **Q1 — ContentForge prerequisite.** Is the ContentForge-side prerequisite for new Video Factory work complete? (yes / no / partly — say what remains.) The audit could not see this from the factory repo.
>
> **Q2 — Uncommitted work.** `export.py`, `pipeline.py`, `visual_gate.py`, `supplied_audio.py`, `test_safe_zone.py`, `test_supplied_audio.py` have uncommitted changes. Is it OK to work alongside them (I will not touch those files), or do you want them committed/parked first by you?
>
> **Q3 — critic.py edit.** T3b adds an *optional* `style_fidelity` score to `critic.py` without changing thresholds or existing results. Approve, or skip T3b?

Record the exact answers in `90-run-log.md`.

## 3. Status rules
- Q1 = "no"/"partly" → status **BLOCKED**; stop. Nothing else in the plan may start. (T1 is read-only research and may proceed only if the owner explicitly says so.)
- Q2 = "wait" → BLOCKED until the owner says go.
- Q1 = yes and Q2 = ok → status **CLEARED**. Write `CLEARED` in the run log with date.

## 4. Verification
- `before-T0.txt` and `after-T0.txt` identical.
- `git status --porcelain` shows only the pre-existing WIP lines plus `?? docs/research/motion-design-integration/` (already present).
- Baseline numbers recorded.

## 5. Rollback
Delete `90-run-log.md` and `$HOME/audit-scratch/snapshot.sh`. Nothing else was changed.

## 6. Do not
Run a render, edit anything in `contentos/`, `config/`, or `tests/`, or run `git` commands other than `rev-parse`, `status`, `stash list`, `diff`, `diff --cached`, `ls-files`.
