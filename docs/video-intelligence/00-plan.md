# Video Intelligence: plan (revision 2)

Revision of the plan drafted by Command Code (orchestrator skill + intelligence layer). Changes were agreed after a review; this file is the plan of record. Status per item is in section 5.

## 1. Goal
A skill that runs a video end to end, and an evidence layer around it so videos get faster (parallel where truly independent), visually distinct (two background rules) and measurably better (experiments, an evolution loop), without inventing data.

## 2. Facts that shape the design (verified in the repo)
- No orchestrator skill existed. `video-director` plans scenes; the new skill sits beside it and calls it.
- `config/capabilities.json` already lists 93 capabilities (48 rules, 22 blueprints). `production/direction.py` rejects unknown fields, so new intelligence data lives in separate files.
- Ep3 and Pilot 001 share one look (measured, see 02-known-failures.md). Pilot 001 has one distinct backdrop across 7 scenes.
- After the external-storage change, `npx --no-install hyperframes` could not resolve the pinned binary from a job folder outside the repo (fixed first, KF-001).

## 3. Decisions (and what changed from the first draft)
1. **Skill orchestrates, `video-director` plans.** Unchanged.
2. **Stable data in `config/`, mutable data outside Git.** Changed: the visual ledger, catalogue evidence and experiment records are written to `<workspace>/intelligence/`; Git holds only seeds. A `claim` must not dirty the repo.
3. **Catalogue seeded without invented numbers.** Changed: every entry is `unverified`, `evidence_count 0`, `reviewed false`; ranking uses visible components (purpose, content type, aspect, complexity, confidence), not an opaque score.
4. **Background rules measured, not regex-only.** Changed:
   - Signatures use hue families (30 degree buckets, neighbours equal), so a slightly different blue cannot pass as a new look.
   - Rule B compares against the last 5 shipped videos, not all history, and lets a series share accents (never the backdrop).
   - Rule A is verified from rendered frames (scene margins) as well as from declared backdrop ids before compose; an intentional single canvas needs a stated motif and is a warning.
   - Rule A covers backdrop only. Layout/motion rhythm stays with the critic.
5. **Parallelism is optional and gate-safe.** Changed: voice moved after `SCRIPT_APPROVED` (the pipeline blocks it otherwise); motion audit moved after render; the P2 fan-out is optional; serial execution is always valid; thumbnails are not built, so that branch is a manual brief.
6. **Experiment C-001 is a harness smoke test, not evidence.** Changed: it cannot establish comprehension, reviewers are only partly blind, so the most it can claim is `experimental`/`investigate`. Deferred to slice 3 with a better-chosen first experiment (re-skin ep3 backdrops, then re-run the critic).

## 4. Slices
- **Slice 0 (done):** `contentos/hf.py`, pipeline/preview/motion_compare call the pinned binary by absolute path.
- **Slice 1 (done):** orchestrator skill + references/templates; `contentos/intelligence/{catalogue,visual}.py`; `config/motion-catalogue.json`, `config/visual-languages.seed.json`; tests; this plan, design, known failures.
- **Slice 2 (when real runs have produced data):** `decide.py` (calls `platforms.py` for length limits, emits the pipeline spec fields and links the record to the job manifest), `evidence.py` (integration smoke-test evidence), `experiment.py`.
- **Slice 3:** first real experiment; evidence overlay writer; promote techniques only on recorded evidence.

## 5. Acceptance (slice 1)
Registry still validates (`direction registry`); catalogue validates and ranks with reasons; Rule B reports ep3 as a duplicate of Pilot 001 using the shipped seed; Rule A fails Pilot 001's render on measured data; mutable ledgers never written inside the repo; full test suite green apart from the one existing unrelated failure.
