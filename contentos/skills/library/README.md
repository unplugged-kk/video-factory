# Video Factory Skills Bundle

A portable, agent-friendly skill library for a single extensible Video Factory.

**Included:** 79 normalized creative skills derived from the supplied skill prompts, 7 core workflow skills, routing maps, reusable prompts, a style registry starter, and integration guidance.

## Design principles

- One factory, many formats: skills specify creative intent; the factory owns orchestration and rendering.
- Reuse before adding: inspect the current capability registry and design library before adopting a dependency or renderer.
- Agent-portable: use `AGENTS.md` as the common operating contract. Claude Code users can use each skill folder's `SKILL.md` as a skill recipe; other agents can read the same Markdown.
- Preview before full render; QA before delivery; human approval before publishing.
- Preserve license, asset provenance, and cost awareness.
- Keep outputs reproducible and avoid duplicate pipelines.

## Repository layout

```text
.
├── AGENTS.md
├── README.md
├── SKILL-MAP.md
├── VIDEO_FACTORY_SKILLS.org
├── config/
│   ├── skill-catalog.json
│   └── style-registry.yaml
├── docs/
│   ├── VIDEO_FACTORY_INTEGRATION.md
│   └── OPERATING_MODEL.md
├── prompts/
│   ├── 00-quickstart.md
│   ├── 01-wispr-flow-command.md
│   ├── 02-script-intake-and-style-selector.md
│   ├── 03-create-video.md
│   ├── 04-reference-video-analysis.md
│   ├── 05-integrate-skill-with-factory.md
│   ├── 06-research-upstream-project.md
│   ├── 07-review-and-qa.md
│   └── 08-publish-package.md
└── skills/
    └── <skill-name>/SKILL.md  (79 skills)
```

## Quick start

1. Copy or clone this bundle into your Video Factory repository, or add it as a Git submodule/subtree.
2. Read `AGENTS.md` and `docs/VIDEO_FACTORY_INTEGRATION.md`.
3. Verify that the target factory's skills convention and renderer adapter match the assumptions.
4. Select a skill using `SKILL-MAP.md` or `config/skill-catalog.json`.
5. Ask the agent to analyze the script first and recommend a format/style before rendering.
6. Preview and run QA; publish only after approval.

## Core workflow skills

The `core-skills/` directory contains the reusable director, script-to-storyboard, style architect, reference analyzer, skill integrator, QA critic, and publishing packager. These are separate from the numbered creative catalog, so adding a workflow does not silently renumber the user's existing creative shortcuts.

## Numbered requests

Numbers are stable catalog IDs in `config/skill-catalog.json`, starting at 1 in catalog order. Use `/numbered-video` or the Wispr Flow template in `prompts/01-wispr-flow-command.md`. Do not use a number without the catalog mapping.

## Important compatibility note

The source collection contains prompts that sometimes hard-code a specific renderer or dependency. The normalized skills preserve the creative brief and steps but instruct agents to verify compatibility and prefer the existing Video Factory backend. This prevents 79 skills from becoming 79 independent rendering stacks.

## Source and transformation

The bundle was generated from the supplied text collection containing 79 skill prompts. Each skill preserves the source's creative intent and workflow instructions, with a common integration contract, safety rules, preview-first workflow, quality checklist, and failure handling. The prompts have not all been executed against a live Video Factory repository; implementation and render quality must be validated in that repository.

## License

This bundle's generated integration instructions are provided for reuse. Individual upstream code, assets, fonts, models, and external references remain subject to their own licenses. Review source provenance before redistributing third-party material.
