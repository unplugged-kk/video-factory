# T10 — Final regression and close-out

**Goal:** prove that after everything the old system behaves exactly as before and that every new piece is present, tested, optional and removable; update the docs so the next person knows the state.
**Prereq:** whichever of T2–T9 the owner chose to run are DONE. Run by a **different session** than the one that implemented (verifier role).
**You create:** `docs/research/motion-design-integration/implementation-plan/99-final-verification.md`. **You modify:** nothing else (the owner decides about `AGENTS.md`/README edits; propose text, don't apply).

## Steps
1. Read `90-run-log.md` to see which tasks ran and their reports. Do not trust reports blindly; re-check.
2. Fresh snapshot `final.txt` and compare with `before-T0.txt`:
   - `--- owner-wip files`, `--- protected`, `--- staged`, `--- stash` blocks **identical to T0**.
   - `--- tracked tests` identical to T0 (no existing test edited).
   - Tracked-file changes (from `git diff --stat`) are **only** `contentos/production/timeline.py` (T5) and, if T3b ran, `contentos/production/critic.py`. Anything else → FAIL.
3. Removed-lines audit on the two modified files: `git diff contentos/production/timeline.py contentos/production/critic.py | grep '^-[^-]'` → only the single permitted changed line in `critic.py` (the `for extra in …` loop); nothing for `timeline.py`.
4. Full suite: `~/.contentos/venv/bin/python -m pytest tests -q`; compare to the T0 baseline (same failures, if any; new passes added; strict xfails listed). Also `node --test contentos/adapters/v1/*.test.mjs` if T0 ran it.
5. Existing CLIs still behave: run each with `--help` or its safe read-only subcommand and confirm exit 0: `./contentos.sh doctor`, `./contentos.sh storage paths --check`, `python -m contentos.production.direction validate tests/fixtures/pilot-001-scene-plan.json`, `python -m contentos.intelligence.designs list`, `python -m contentos.intelligence.catalogue --help`, `python scripts/upstream_skills.py verify`.
6. **Regression of an existing artifact (no render):** if an existing project exists in the workspace, run `python -m contentos.production.timeline <project>` and confirm its output is unchanged from a pre-T5 baseline (if you have none, say "no pre-T5 baseline captured"). Do **not** render.
7. Presence/removability matrix — for each new file confirm: exists, has tests, not imported by any pre-existing module:
   ```bash
   grep -rnE "intelligence\.(styles|creative)|production\.(checkpoint|cue_audibility)|from \. import styles" contentos scripts --include=*.py | grep -vE "^contentos/(intelligence/(styles|creative)|production/(checkpoint|cue_audibility))\.py"
   ```
   must print nothing (nothing in the old system depends on the new modules → deleting them cannot break production).
8. Security/licence sweep: `git status --porcelain` shows no media files; no new dependency (`git diff package.json`/lock empty; no `requirements` change); no URLs fetched except those T1/T8 allowed (check run log).
9. Write `99-final-verification.md`: table of checks with the actual command output excerpt and PASS/FAIL; the list of new/modified files; the list of **not verified** items (no production render performed; style cards unvalidated; cue thresholds provisional; bake-off outcome pending/complete; ContentForge integration untouched and untested here).
10. Propose (as text in the doc, not applied) one short paragraph for `AGENTS.md` §10 / §6 describing: style cards (`config/styles/`), `creative` CLI, `checkpoint` CLI, optional timeline fields, `cue_audibility`, all **advisory/shadow**.
11. Report in the §5.4 format. If any check FAILS, status FAILED and list exact differences; do not repair.

## Acceptance
All checks PASS or are explicitly listed as not verified with reasons; the owner receives the doc.

## Rollback
The whole programme is undone by deleting the new files listed in the Master Plan §8 and the owner restoring `timeline.py` (and `critic.py` if T3b ran) from their own review of `git diff`.
