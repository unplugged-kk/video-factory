# Decision Log

Append-only. Supersede a decision with a new entry; mark the old one
"Superseded by DEC-NNN" (the only permitted edit to a past entry).

<!-- Entry format:

## DEC-NNN - <title>
- **Date:**
- **Status:** active | superseded by DEC-NNN
- **Context:**
- **Options considered:**
- **Selected:**
- **Reason:**
- **Trade-offs:**
- **Consequences:**
- **Recorded by:**
-->

## DEC-001 - Treat the invoked-skill-only turn as Report mode, promoted to Checkpoint (no baseline)
- **Date:** 2026-11-21
- **Status:** active
- **Context:** The turn contained the project-execution-handoff skill and repository context but no user
  question. `docs/project-intelligence/` did not exist, so any report would have had no recorded
  boundary and nothing for the next agent to build on.
- **Options considered:** (a) Report only, leaving no artifacts; (b) Checkpoint a fresh baseline now;
  (c) ask the user which they wanted.
- **Selected:** (b).
- **Reason:** the skill says init artifacts only in Checkpoint/Handoff mode, and the working state had
  genuinely moved relative to every recorded source (2 unpushed commits, dirty tree, no baseline), which is
  the stated condition for also writing a checkpoint. Asking first would have spent a turn to reach the
  same place.
- **Trade-offs:** artifacts are written without an explicit request. Everything written is under
  `docs/project-intelligence/` and is untracked, so it is cheap to delete.
- **Consequences:** the next invocation has a real boundary (`849ea6a`, ITER-2026-11-21-001) and can diff
  against it.
- **Recorded by:** pi/root

## DEC-002 - Commit nothing; the repo has 2 unpushed commits and that stays the owner's call
- **Date:** 2026-11-21
- **Status:** active
- **Context:** `feat/p1-1-lookmap` is 2 commits ahead of `main`, has no upstream, and the readiness report
  asks the owner where those commits should go.
- **Options considered:** push the branch, open a PR, or leave it for the owner.
- **Selected:** leave it; record OPEN-002 and say so in the reply.
- **Reason:** AGENTS.md forbids commit/push without being asked, and the skill's safety section forbids
  it as well. The previous session also deliberately left both commits local.
- **Trade-offs:** the work stays only on this Mac and only on this branch.
- **Consequences:** no CI runs, and `origin/main` is 2 commits behind.
- **Recorded by:** pi/root

## DEC-003 - Hold the original branch; integrate Phase 2 on an isolated local branch
- **Date:** 2026-11-24
- **Status:** active
- **Selected:** User authorised new local focused commits and worktrees, not push, merge to main, or movement of the existing branch. Keep the original checkout and its historical deliverables intact, archive and verify them outside Git, and iterate on `feat/phase2-foundation`. This does not override the historic hold in DEC-002.
- **Consequences:** New code commits are local. The Phase 2 checkpoint artifacts stay in the isolated worktree and external archive. No hosted CI inferred.
- **Recorded by:** pi/root

## DEC-004 - Do not adopt a digest-only CLI migration
- **Date:** 2026-11-24
- **Status:** approved by Kishore in the Phase 2 execution directive; implementation pending
- **Selected:** Propose mandatory confirmation on every human approval write surface, using the same reviewed script or sealed production identity. Studio's existing `seenDigest` is one component. The owner approved shared human confirmation and a separate authenticated, permission-scoped automation identity. Implement after sealed and complete subject work, in the order directed. The existing CLI behavior is unchanged for now.
- **Alternatives and trade-offs:** `docs/audit/APPROVAL_POLICY.md`.
- **Recorded by:** pi/root

## DEC-005 - Park Phase 2 on its remote branch while prototyping UI
- **Date:** 2026-11-24
- **Status:** active
- **Selected:** The owner authorised committing and pushing the checkpoint. Preserve the full ancestry on `feat/phase2-foundation` and use a draft PR for CI and review. This supersedes the no-push portion of DEC-002 and DEC-003 for this branch only. Do not merge or move `main` at this checkpoint.
- **Consequences:** UI work can start separately from `main`. Treat the approved PF-02 migration as pending; production snapshot, asset coverage and independent-review gates remain open. No publishing or deployment.
- **Recorded by:** pi/root
