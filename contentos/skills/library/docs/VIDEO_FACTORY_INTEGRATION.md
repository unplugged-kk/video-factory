# Video Factory Integration Guide

## Goal

Make this skill pack a portable creative layer for the existing Video Factory. The factory remains responsible for job orchestration, authoritative timeline, rendering, QA, artifacts, and approvals.

## Recommended integration pattern

### Option A — Keep the bundle as a separate GitHub repository
- Version the bundle independently.
- Pin a release or commit in the Video Factory repository.
- Copy selected skills into the local skill directory or reference this repository from your agent instructions.
- Update the catalog when adding/removing skills.

### Option B — Vendor the bundle into the factory
- Place skills under the factory's established skill path.
- Merge, rather than replace, existing `AGENTS.md` or root instructions.
- Reconcile the starter `config/style-registry.yaml` with the existing `config/design-library.json`; do not create two competing registries.
- Map skill outputs to the existing episode manifest/timeline.
- Map checks to existing QA gates rather than duplicating them.

## Integration steps

1. Record current branch, HEAD, working-tree changes, and tests.
2. Inspect the live factory architecture and current instructions.
3. Compare every skill against existing `.claude/skills/` and the capability registry.
4. Identify duplicate, conflicting, unsupported, and high-value skills.
5. Select a small pilot set: one code-first explainer, one kinetic-typography style, one illustrated/story style, and one reference-video analysis workflow.
6. Map each selected skill to the existing renderer, timeline, asset registry, and QA.
7. Add a stable skill ID and capability requirements to the catalog.
8. Render the same approved script in at least three genuinely different styles.
9. Inspect contact sheets and run the existing QA suite.
10. Measure visual differences, failures, render time, and manual corrections.
11. Only then expand to the remaining styles.

## Architecture boundary

- **Creative layer:** style cards, skill recipes, storyboard rules, scene composition choices.
- **Execution layer:** Video Factory orchestration, authoritative timeline, renderer adapters, audio, asset handling, QA.
- **Control/approval layer:** ContentForge or existing approval boundary. Do not bypass it or add direct calls that conflict with current project architecture.
- **Publishing:** package metadata can be generated, but publishing remains separately approved.

## Compatibility cautions

- A source prompt's Remotion/Canvas/Playwright instruction is not a reason to add another renderer automatically.
- The source prompts mention various ASR, forced-alignment, audio-separation, font, and model dependencies. Check whether each is actually installed and appropriately licensed.
- Do not treat a prompt as tested code. Each skill must be validated in the target environment.
- If a style needs a missing primitive, first determine whether it can be added to HyperFrames cleanly. Propose a new backend only with evidence and explicit approval.
