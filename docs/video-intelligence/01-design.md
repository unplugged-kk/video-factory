# Video Intelligence: design (as built in slice 1)

```
.claude/skills/video-production-orchestrator/   SKILL.md + references + templates   (what an agent reads)
contentos/intelligence/catalogue.py             config/motion-catalogue.json  x  config/capabilities.json   (read-only)
contentos/intelligence/visual.py                Rule A / Rule B                                             (ledger in workspace)
config/motion-catalogue.json                    70 techniques -> purposes (heuristic seed, unverified)
config/visual-languages.seed.json               looks of videos already shipped (ep2, pilot-001)
<workspace>/intelligence/                       visual-languages.json, catalogue-evidence.json   (written at run time)
```

**Catalogue.** Joins the seed to the capability registry by id; the registry stays the authority for status, paid and fallback. `validate` fails on unknown ids, uncatalogued rules/blueprints, unknown fields, out-of-vocabulary values, confidence without evidence, and a heuristic seed promoted past `experimental` without review. `query` excludes anything not `installed`, paid (unless allowed) or deprecated, and prints each score component. Evidence overlay can only change `confidence`, `evidence_count`, `examples` of ids that exist.

**Visual signature** = structure (radial/linear/flat/mesh/paper), temperature, texture (grid/noise/paper/none), base (hue family + brightness tier), accents (two most used hue families, design tokens first). Extracted from the composition's CSS (linked stylesheets included); verified against frames with ffmpeg when a video exists. Hue families are 30 degrees wide and neighbours count as equal.

**Rule B**: differ on at least 2 of 5 fields from each of the last 5 ledger entries (seed + workspace). `claim` is locked, atomic, idempotent per content id, and never records a duplicate. **Rule A**: distinct backdrops >= ceil(scenes/2) and never all equal; frame margins only (top/sides, not captions or centre), so foreground at an edge can add false variety (errs toward passing).

Exit codes everywhere: 0 ok, 1 finding, 2 unreadable input. Nothing here edits a project, a registry, or the pipeline.

Known limits: purposes are a first draft; CSS extraction cannot see styles set by script at runtime (the frame check backs it up); no audience analytics exist, so nothing here claims audience impact.
