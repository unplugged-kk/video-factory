# AGENT_HANDOVER

Resume from Git plus this file. Read AGENTS.md first, then docs/CURRENT_STATE.md and docs/ROADMAP.md. Updated 2026-11-13.

## Product mandate

Video Factory is an independent, complete, local-first video platform. CEH (Creative Ecosystem Hub) is an OPTIONAL extension.
Two modes, one engine: Standalone (native only) and CEH-enhanced (native plus approved CEH capabilities). Must work with CEH absent,
disabled, empty or incompatible. Never silently substitute an unapproved resource. Keep core engine, native registry, CEH adapter,
provider adapters, render/export and QA gates separate. No `ceh_*` imports in core.

## State (verified 2026-11-11)

- VF: `main` at `a0f60cd`, equal to origin/main, working tree was clean at session start. Repo `unplugged-kk/video-factory`, 0 open PRs/issues.
- Branches on origin: `codex/ceh-catalog-consumer` (b1befad, unmerged, disabled), `feat/generic-video-system`.
- HyperFrames pin 0.8.114 (not touched). Publishing disabled. No paid spend.
- CEH: `~/git/creative-engineering-hub`, main `ad1e133`, origin `github.com/unplugged-kk/creative-engineering-hub` (private), pushed and equal to local.
  Latest HANDOVER there: 2026-11-11. 48 registry resources, 104 tests per its report (not rerun by me).
- CEH real catalog `integrations/video-factory/catalog-v2.json`: entries empty, digest `11ef940259fddbb642ed9545579c4be1592cd34155b81709651be7aaed9cc9da`.
- CEH-0018 registry status CANDIDATE. Approved skill entries: NONE.

## CEH integration status

| Item | Status |
|---|---|
| Catalog metadata consumer (b1befad) | built, tested by CEH side (71 tests), NOT merged, disabled by default |
| Skill artifact consumption | NOT BUILT. Consumer never opens or verifies the skill bundle. Metadata discovery only. |
| Production activation | none |
| Decision A (approve/publish kinetic-type-planning 0.1.0) | APPROVED by owner 2026-11-11, narrow scope, DOCUMENTED ONLY (CEH decision-a-approval-record.md). Registry cannot express it while CEH-0018 stays CANDIDATE; no catalog entry exists. Needs A2. [was: PENDING] |
| Decision B (merge + opt-in) | DOSSIER READY, AWAITING OWNER. docs/integrations/CEH_DECISION_B_DOSSIER.md (B1 metadata merge, B2 verify_artifact). Nothing implemented. |

Candidate bundle fingerprints: current `942d06fc...c679` (recomputed), prospective `addfcc1b...b0` (from CEH report, unrecomputed).
Final entry/catalog fingerprints do not exist yet.

## Doc inconsistency fixed

CEH HANDOVER.md and remaining-risks.md said "CEH has no Git remote". Wrong after 2026-11-11 repo creation. Annotated as superseded in CEH
working tree (UNCOMMITTED, owner did not ask for a CEH commit). Historical text preserved. `/tmp/ceh-vf-consumer` cited by CEH docs no longer exists.

## Work in this session left uncommitted

VF: AGENT_HANDOVER.md, SESSION_LOG.md, docs/integrations/CEH_DECISION_A_DOSSIER.md, docs/integrations/CEH_DECISION_B_PROPOSAL.md.
CEH: 2-line annotations in HANDOVER.md and reports/acceptance/2026-11-11/remaining-risks.md.
AGENTS.md forbids commits unless asked, so none were made.

## Standalone roadmap (NOT abandoned)

The general Video Factory milestone work (TTS provider abstraction, Hindi/Hinglish, motion library, reference analysis, Studio) is paused only
for this decision gate. Not yet audited this session: HyperFrames status, TTS matrix, Studio, skill inventory refresh. See docs/ROADMAP.md.

## Next action

Owner answers Decision A (approve/reject/defer + usage scope + parent bookkeeping option + media reviewed). Then prepare Decision B with
final fingerprints. After A is answered, resume the standalone roadmap in parallel; standalone work never waits on CEH.

## Resume commands

```
cd ~/git/video-factory && git fetch origin && git status -sb
cd ~/git/creative-engineering-hub && git fetch origin && git status -sb && cat HANDOVER.md | head -60
uv run ceh validate --json            # in CEH
~/.contentos/venv/bin/python -m pytest tests -q   # in VF
```

## Update 2026-11-11 (Decision A recorded, B prepared)

- Both repos re-verified: VF main a0f60cd = origin; CEH main ad1e133 = origin (ls-remote). CEH remote annotations confirmed correct.
- CEH uncommitted: HANDOVER.md (remote note + Decision A section), remaining-risks.md (remote note + A row), NEW reports/acceptance/2026-11-11/decision-a-approval-record.md.
- VF uncommitted (untracked): AGENT_HANDOVER.md, SESSION_LOG.md, docs/integrations/{CEH_DECISION_A_DOSSIER,CEH_DECISION_B_PROPOSAL,CEH_DECISION_B_DOSSIER}.md.
- Verified: bundle 942d06fc recomputed; prospective addfcc1b recomputed; catalog empty; CEH 104 pass, validate ok; b1befad 5 add-only files, 71 tests pass in scratch; merge-tree clean.
- Found: proposed-skill-metadata.yaml assigns a LicenseRef, conflicting with owner "licence unassigned". Approved bytes assumed = current bundle (Q1).
- Open: Q1-Q7 in CEH_DECISION_B_DOSSIER.md, A2 authorization.
- Next action: wait for owner's Decision B answer and A2 decision. Do not commit, push, merge, branch, install or activate before that.
- Also present untracked in VF: examples/finance/ (NOT created by this session; appeared since earlier status; left untouched).

## Update 2026-11-11 (standalone workstream, branch feat/standalone-acceptance)

- Branch `feat/standalone-acceptance` created from main a0f60cd. Nothing committed. CEH consumer branch NOT touched; no `ceh_*` import anywhere.
- Done: standalone Hindi finance sample `sample-fin-sip-hi-001` rendered end to end (QA 8 PASS + expected frozen-frames WARN). Read
  `docs/STANDALONE_ASSESSMENT.md` for the audit, matrix, defects and next milestones. MP4 in `~/Desktop/VideoFactory-Workspace/experiments/standalone-samples/`.
- Code fixed: chart value wrapping, optional `note:` footnote override, larger chart text (scenekit). Test added in `tests/test_scenekit.py`.
- Owner granted gates 1 and 2 for `sample-fin-sip-hi-001` only (this session). Hindi audio still unreviewed by a human: keep `experimental`.
- Uncommitted VF files: scenekit/compose.py, scenekit/primitives.py, tests/test_scenekit.py, examples/finance/, docs/STANDALONE_ASSESSMENT.md, this file, SESSION_LOG.md.
- Next executable task: ROADMAP P1-1 (look changes frames) and drop the English "scene N of M" ornament for non-English jobs. CEH decisions run in the separate workstream.

## Update 2026-11-11 (owner decisions: A2 authorized, B1 approved, B2 deferred, B3 not approved)

- B1 DONE locally: VF main fast-forwarded a0f60cd -> 016b5a526afb29cbcd6e659e7c99d7160f8a1547 (--no-ff merge of b1befad73b4285ce461eb48861e5559c069d2776). NOT pushed. Disabled by default, not activated.
  Isolated worktree ~/git/vf-b1 (branch merge/ceh-metadata-consumer). Suite on worktree: baseline 1 failed/1069 passed/22 skipped; merged 1 failed/1140 passed/22 skipped.
  The 1 failure (tests/test_lang.py::test_english_words_for_keeps_the_legacy_hyperframes_path...) is identical before and after; passes in the user checkout (env difference: worktree has no node_modules/ignored files). Node 66 pass.
  Rollback proven: `git revert -m 1 016b5a5` tree == a0f60cd tree (93641d117bc9ee19155741f4d1fc6a4754e1edbc).
- User checkout has tracked WIP (contentos/scenekit/*, tests/test_scenekit.py) and untracked docs/examples; untouched. ff-merge needed no stash.
- A2 DONE on CEH branch feat/skill-level-approval at ~/git/ceh-a2, commit c58a41592e090e0997fd377e0aad69d2294eb7d5. NOT merged, NOT pushed. No skill approved; real catalog export still 0 entries.
- B2 still deferred. Findings reported: real LicenseRef validates in contract; bundle has 1 non-ASCII char, in references/provenance.md (hashed as bytes, no ensure_ascii path); VF has no pyproject, PyYAML only in ~/.contentos/venv; ff-merge into a dirty checkout worked; full suite run above.

## Update 2026-11-11 (standalone close-out and P1-1 proposal)

- Branch `feat/standalone-acceptance` at `016b5a5` (includes the B1 merge, so `contentos/ceh_*.py` exist, opt-in, unimported by pipeline). Still nothing committed.
- Verified: full suite after the last code edit = 1085 passed, 8 skipped, 148.64 s (log /tmp/vf-pytest2.log). Sample MP4 is only in
  `~/Desktop/VideoFactory-Workspace/experiments/standalone-samples/`; nothing named `*sample-fin-sip*` under `Video-Publishing/ready`.
- Open acceptance gaps: no human Hindi listening, no independent visual critic, remaining visual defects (English "scene N of M" in `split`, empty bands in text-only scenes, no imagery).
  Not run: Hinglish, Remotion, MPT, Playwright, Node suite.
- NEW `docs/P1-1_LOOK_PROPOSAL.md`: root cause (look/1 is read by nothing; scenekit styles do change frames; legacy style_card barely does; look fonts are not installed), architecture
  (compile a look into a scenekit style via `scenekit/lookmap.py`, new `look:` spec key), milestones M1-M5, decisions D1-D3. Nothing implemented.
- Next: owner decides D1-D3, then M1 (lookmap compile-only) and M2 (wire plus golden no-regression test).

## Update 2026-11-13 (everything committed and pushed to main)

- All pending work is now in Git. main = origin/main after push. Commits: scenekit chart fix, standalone docs and CEH dossiers, finance sample spec.
- The B1 merge (016b5a5, CEH catalog consumer) is now on origin/main. Still disabled by default, unimported by the pipeline, no CEH entry exists.
- `feat/standalone-acceptance` is fully merged into main. Branches `merge/ceh-metadata-consumer`, `codex/ceh-catalog-consumer`, `feat/generic-video-system` still exist.
- Suite at last code edit: 1085 passed, 8 skipped. Scenekit tests re-run before commit.
- Still open from earlier: human Hindi listening, independent visual critic, English "scene N of M" ornament, empty bands in text-only scenes, CEH decisions B2/B3 (deferred / not approved).

### Next plan (docs/ROADMAP.md is the tracker)

1. Owner decides D1-D3 in `docs/P1-1_LOOK_PROPOSAL.md` (compile looks into scenekit styles only; system fonts vs bundled; include figure/ticks empty-scene fix or defer).
2. P1-1 M1: `scenekit/lookmap.py`, compile-only, no pipeline change. M2: `look:` spec key plus golden no-regression test.
3. Quick win: drop the English "scene N of M" ornament for non-English jobs (compose.py split branch).
4. P1-5 (owner): listen to the Hindi sample, run an independent critic, then decide promotion from `experimental`.
5. Then P1-2 (consume `sceneplan/1`), P1-6 (one style system, not three).
