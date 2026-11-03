---
name: factory-skill-integrator
description: "Integrates a new skill into the existing Video Factory without duplicating renderers, timelines, or QA."
metadata:
  bundle: video-factory-skills
  kind: core-workflow
  version: "1.0.0"
---

# Factory Skill Integrator

1. Inspect current branch, working tree, root instructions, capability registry, design library, skill conventions, timeline, renderer adapters, and QA.
2. Search for existing equivalent behavior before adding code.
3. Define skill inputs, outputs, configuration, dependencies, error handling, and tests.
4. Reuse the authoritative episode manifest/timeline and renderer adapter.
5. Keep creative instructions in the skill; keep orchestration, rendering, and QA in the factory.
6. Do not add a second renderer unless the current one cannot meet a verified requirement.
7. Verify dependency and asset licenses; never install without approval.
8. Add examples and tests, run authorized validation, update registries, and document rollback.
9. Report exactly what changed and which tests/renders were actually run.
