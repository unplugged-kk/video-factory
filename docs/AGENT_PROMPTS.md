# Agent prompts: copy, paste, go

Two workstreams, two prompts. Paste one into a fresh agent session (Claude Code, Codex, Cursor). Each prompt only points at
files; the files carry the state. Updated 2026-11-13. Keep this file current whenever the next step changes.

## Prompt 1: Video Factory (standalone workstream)

> You are working in `~/git/video-factory` (contentos). Read `AGENTS.md`, then `AGENT_HANDOVER.md` (the newest "Update" section
> is the truth), then `docs/ROADMAP.md`. Video Factory is a standalone, local-first product: CEH is optional and must never be required.
> Obey AGENTS.md sections 1 and 2: never publish, never spend money, never edit `config/*.yaml`, gates or the HyperFrames pin, never
> write media into the repo, no commit/push/merge unless I ask.
> **Current task: ROADMAP P1-1 (a chosen look must change real frames), next milestone M2.** Decisions already made: D1 = compile a
> look into a scenekit style, legacy `style_card`/`visual_layer` stay frozen; D2 = system fonts with an explicit map, no bundled fonts;
> D3 (figure/ticks empty-scene primitives) is still OPEN, do not start M3 until I answer. M1 is done: `contentos/scenekit/lookmap.py`
> plus `tests/test_lookmap.py` (17 of 30 looks compile, 13 blocked by named reasons). M2: add the `look:` spec key in
> `pipeline.s_compose` and `scenekit/planner.resolve_style`, make `compose` paint `tokens["texture"]`, write `look-input.json`
> (look id, look digest, style digest), and add golden tests proving a spec without `look:` composes byte-identical to today.
> Spec for M2 is in `docs/P1-1_LOOK_PROPOSAL.md` sections 3, 9 and 11. Verify with
> `~/.contentos/venv/bin/python -m pytest tests -q` (baseline 1085+ passed, 8 skipped) and a real compose of
> `examples/finance/sip-small-savings-hi.yaml` with two looks. Report what you ran, what you could not verify, and update
> `AGENT_HANDOVER.md` and `SESSION_LOG.md` before you stop.

Other next steps after P1-1, in order: drop the English "scene N of M" ornament for non-English jobs (M3 part), P1-5 human Hindi
listening plus an independent critic (owner), P1-2 consume `sceneplan/1`, P1-6 one style system.

## Prompt 2: Creative Engineering Hub (CEH)

The original mission prompt ("MASTER MISSION: Build Creative Engineering Hub") is not stored in either repo (CEH `HANDOVER.md` says
to read it "if you have it"). This prompt replaces it for follow-on work.

> You are working in `~/git/creative-engineering-hub` (CEH), the user's registry, R&D lab and skills library. Read `AGENTS.md`,
> then `HANDOVER.md` (newest section first), then `reports/acceptance/2026-11-11/decision-a-approval-record.md` and
> `~/git/video-factory/docs/integrations/CEH_DECISION_B_DOSSIER.md`. Run everything as `uv run ceh <command>`.
> Rules: adding is not integrating; never execute resource code; never edit Video Factory from CEH; never guess a licence, pin or
> benchmark; no commit/push/merge unless I ask. Video Factory is standalone and CEH is an optional extension.
> **State:** Decision A approved narrowly (kinetic-type-planning 0.1.0, internal commercial planning/production, no redistribution,
> licence unassigned) but documentation only: `CEH-0018` is still CANDIDATE and the real catalog `catalog-v2.json` has 0 entries.
> A2 (skill-level approval) is implemented on branch `feat/skill-level-approval` (c58a415, 123 tests), NOT merged. VF's B1 consumer
> is merged and pushed on VF `main`, disabled by default. B2 (`verify_artifact`) deferred, B3 (activation) not approved.
> **Open items, do them only when I say go:** (1) CEH working tree has uncommitted HANDOVER.md, remaining-risks.md and the
> decision-a-approval-record.md: show me the diff and ask before committing. (2) Merge A2 into CEH main. (3) Answer Q1-Q7 in the Decision B
> dossier with me, starting with the licence conflict in `proposed-skill-metadata.yaml`. (4) Only then `ceh skills approve`
> and export a catalog entry. Report evidence for every claim and update `HANDOVER.md` before you stop.
