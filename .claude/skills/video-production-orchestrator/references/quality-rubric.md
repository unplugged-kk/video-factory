# Quality rubric

Internal review scores (1-10) judge the *video as made*. They are not audience data: never report them as retention, engagement or "performs better". Only analytics from a platform are audience evidence, and the factory has none yet.

Dimensions and anchors (6 = acceptable, 8 = ship-worthy; write the evidence for every score):
1. **Clarity of takeaway** - 6: a viewer could state it after a rewatch; 8: after one viewing.
2. **Script and pacing** - 6: no dead air, a few filler lines; 8: every line earns its seconds.
3. **Composition** - 6: readable, but scenes share one rhythm or layout; 8: layout and motion change with purpose.
4. **Motion** - 6: nothing pops or jars; 8: motion carries meaning and each cue lands on its word.
5. **Typography and legibility** - 6: safe zones respected, small text only where unavoidable; 8: legible on a phone at arm's length.
6. **Audio** - 6: intelligible, loudness near target; 8: balanced, no clipping, music never competes.
7. **Visual identity** - 6: consistent; 8: consistent *and* distinct from recent videos (background rules A and B pass).
8. **Technical integrity** - 6: QA passes; 8: QA passes with no warnings you cannot explain.

Critical failures block shipping whatever the scores: failed QA/export validation, unreadable text, clipping, missing audio when required, a failing background rule without a declared motif, unverified factual claims, unlicensed assets. Use the independent critic (`contentos/production/critic.py`) and `explainer-visual-qa`; the author does not grade their own work.
