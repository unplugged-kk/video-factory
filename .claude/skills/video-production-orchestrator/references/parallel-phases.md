# Parallel phases

The dependency graph below says what *may* overlap. Executing it serially is always correct; the pipeline itself is serial. Many agents cannot spawn sub-agents, so never make a result depend on parallelism.

```
P0 inventory (doctor, storage paths, catalogue validate)            serial
P1 classify + objective                                             serial   gates everything
P2 analyse: audience | formats | technique shortlist | tool feasibility   optional fan-out (short reasoning: often one pass is cheaper)
P3 decide -> decision record                                        serial
P4 plan: video-director -> scene-plan.json; director check          serial
   GATE 1  SCRIPT_APPROVED                                          human   (the pipeline blocks voice without it)
P5 voice (Kokoro) | thumbnail brief (manual: thumbnails are not built)    parallel
P6 align words -> sceneplan.resolve                                 serial
P7 visual: Rule B check + Rule A plan check | compose               parallel (visual may veto compose)
P8 hyperframes lint + check, until 0 errors                         serial
   GATE 2  PRODUCTION_APPROVED                                      human   (the pipeline blocks render without it)
P9 render                                                           serial
P10 technical QA | independent critic | visual compliance (Rule A on video, motion_audit)     parallel, read-only on the render
P11 package, export, record evidence                                serial
```
Real time savings come from P5, P7 and P10 (voice with thumbnail, compose with the visual checks, three read-only QA instruments). Do not parallelise: compose (one artifact), gates, or any step where two agents would write the same file.

## Agent-brief contract (give a sub-agent exactly this)
Question to answer; evidence you give it (paths, not summaries); output schema; the one output path it may write (unique per agent); time and cost boundary; files it must not touch; "report findings, do not fix". Results are merged by the orchestrator; two agents never share an output file. Independent agents (critic, QA) are not told what you expect.
