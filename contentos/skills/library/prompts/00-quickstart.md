# Quickstart: Use this skill bundle with any coding agent

Read `AGENTS.md`, `SKILL-MAP.md`, `config/skill-catalog.json`, and `docs/VIDEO_FACTORY_INTEGRATION.md`.

First inspect the target Video Factory repository and report:
- current renderer and version;
- existing style/design registry;
- available skills and QA gates;
- expected job/episode manifest;
- approval boundaries;
- any conflicting or duplicate capability.

Do not install anything or modify production code yet.

Then demonstrate one request end-to-end in planning mode: resolve the requested skill, inspect the inputs, recommend a style, produce a scene plan, and identify which existing factory components will execute it. Only render when the user authorizes it and the current pipeline's approval gates permit it.
