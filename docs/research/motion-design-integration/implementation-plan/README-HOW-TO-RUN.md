# How to run this plan (owner's page)

Run **one task per fresh Haiku session**, in order. Paste the prompt below, changing only `T#`. After each task, start a **different** session as verifier with the verifier prompt.

## Order
T0 → (you answer Q1–Q3) → T1 (optional, read-only) → T2 → T3 → T4 → T5 → T6 → T7 → T8 (you listen) → T9 (you review) → T10.
T2–T4 and T5–T7 are two independent chains. If T0 says BLOCKED, stop.

## Implementer prompt (paste per session)
> You are implementing one task of the Motion Design Integration plan in the Video Factory repo.
> 1. Read `docs/research/motion-design-integration/implementation-plan/00-MASTER-PLAN.md` completely, then `AGENTS.md` sections 1–4.
> 2. Read `docs/research/motion-design-integration/implementation-plan/T#-….md` and do exactly that task, in order, test-first.
> 3. Use only `~/.contentos/venv/bin/python`. Never git add/commit/stash/reset/checkout. Never edit config/*.yaml, vendor/, .claude/skills/hyperframes-*, or the owner-WIP files named in the plan. Never edit an existing test.
> 4. If any stop condition in the Master Plan §6 occurs, stop and report BLOCKED. Do not improvise or work around.
> 5. Finish with the report in Master Plan §5.4 and append it to `90-run-log.md`. Do not start another task.

## Verifier prompt (different session)
> You are the independent verifier for task T#. Do not implement. Read the Master Plan and `T#-….md`. Re-run its Verify section and the snapshot comparison yourself. Read the diff of every file the task created or modified. Check each Acceptance line against evidence, not against the implementer's report. Report PASS/FAIL per line with command output. If anything is protected-and-changed, report FAIL and stop.

## Your decisions the plan waits for
Q1 ContentForge prerequisite · Q2 uncommitted WIP · Q3 critic `style_fidelity` (T3b) · approval before each task · downloads in T8 · listening in T8 · gate approvals and blinded review in T9.
