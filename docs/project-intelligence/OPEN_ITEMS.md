# Open Items

One table row per item. Close an item by setting Status to done with the
evidence id; do not delete rows.

| ID | Type | Item | Priority | Depends on | Acceptance criteria | Status | Owner |
|---|---|---|---|---|---|---|---|

<!-- Type: requirement | bug | incomplete | test-gap | security | debt | external | human-decision
     Priority: P0 (blocking) .. P3 (nice to have) -->

| ID | Type | Item | Priority | Depends on | Acceptance criteria | Status | Owner |
|---|---|---|---|---|---|---|---|
| OPEN-001 | security | PF-02: mandatory confirmed digest for human SCRIPT and PRODUCTION grants | P1 | PF-05 / PF-22 | Shared atomic CLI/API/Studio policy and authenticated, scope-limited automation | owner approved; implementation open | pi/root |
| OPEN-002 | human-decision | Where `c391db0` + `849ea6a` go: push to origin, PR, or hold | P1 | - | Owner records a disposition | done: DEC-005, included in Phase 2 branch; main merge deferred | owner |
| OPEN-003 | security | PF-22: out-of-root and remote asset references are not bound at approve or render time | P1 | - | Only staged and hashed assets can affect a confined render; prove refusal for unstaged dependencies | partial: incomplete local walks addressed (`d9c1d8e`, EV-20261124-135640) | pi/root |
| OPEN-004 | security | PF-05: content can be swapped and restored inside the render window | P2 | - | Render reads from a snapshot copy of the approved content; test drives the swap-and-restore attack | open | unassigned |
| OPEN-005 | test-gap | Real Hindi ASR test failed when `whisper-cli` was absent | P2 | - | Actual missing binary is a targeted skip, present binary is exercised, transcription errors are not hidden | done: `cce972d`, VF2-ASR-GREEN, EV-20261124-135640 | pi/root |
| OPEN-006 | debt | Keep the Phase 1 and Phase 2 checkpoints in Git | P2 | OPEN-002 | Both are committed on the Phase 2 branch, so a clone preserves the baseline | done in the parking checkpoint | pi/root |
| OPEN-007 | incomplete | P1-1 M2: `features/style_card.py` and the backdrop table do not consume a chosen look | P3 | OPEN-003 | A chosen `look/1` id changes real frames, proven by two renders that differ | open | unassigned |
| OPEN-008 | security | PF-03, PF-07, PF-23 and G-05/G-06/G-07 remain open | P2 | PF-03/PF-07 gate semantics: OPEN-001 | PF-23 local adapter slice tested at `46f8e78`; verify real MPT, immutable inputs and reviewed stock. Close each other finding with tests and evidence. | open | pi/root |
| OPEN-009 | test-gap | Fresh worktree reproducibility and CI | P2 | - | Local bootstrap succeeds with hosted-tool versions and clean tree; hosted CI independently runs when authorized | partial: local 1211/17 Python and 66/0 Node; no hosted run | pi/root |
| OPEN-010 | external | Independent security and visual review | P1 | - | Report from a fresh approved-model reviewer with evidence; not a self-review | blocked on permitted model route | unassigned |
