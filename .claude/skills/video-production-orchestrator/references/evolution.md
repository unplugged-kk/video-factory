# Evolution: how the system learns without fooling itself

Ladder for any technique, tool or recipe: `unverified` -> `experimental` -> `validated` -> `preferred` -> `deprecated`.
- `experimental`: one controlled run or one shipped, QA-passed use.
- `validated`: repeated evidence (at least two independent runs or videos) and a reviewed purpose mapping.
- `preferred`: validated *and* beats the alternatives on a stated measure.
- `deprecated`: a recorded failure or regression; hidden from default queries, never deleted.
Observing the same thing twice updates `evidence_count`; it never creates a second rule.

Triggers to record something: a QA or critic finding, a tool failure, a rule that did not behave as documented, a background-rule failure, a measured time or cost surprise, an experiment result, a new tool smoke-tested.
Update loop: (1) write the observation with its evidence path, (2) check it is not a duplicate of a known failure, (3) decide the smallest change that addresses it, (4) change only the evolving data (workspace evidence overlay) unless the owner approves a code or registry change, (5) re-run the affected check, (6) record before/after, (7) keep the old value so the change can be rolled back, (8) update `docs/video-intelligence/02-known-failures.md` for anything a future agent could trip on.
Stable rules (`config/capabilities.json`, gates, `hyperframes-core`) change only by owner decision. Evidence overlays can be deleted to return to the seed.
