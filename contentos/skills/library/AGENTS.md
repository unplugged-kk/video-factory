# Video Factory Skills — Agent Operating Contract

## Mission
Use this repository as a portable creative skill pack for a single, extensible Video Factory. The goal is not to create a separate toolchain per format; it is to let any compatible coding agent discover the right recipe and invoke the existing factory safely.

## Priority order
1. User's explicit brief and approval decisions.
2. The live Video Factory repository instructions and capability registry.
3. Existing approved design/style definitions and production gates.
4. The selected skill in this bundle.
5. Research-derived recommendations, only when compatible with the above.

## Agent behavior
- Inspect before changing. Never assume skills, renderers, models, fonts, APIs, or dependencies are installed.
- Discover skills by reading `SKILL-MAP.md`, `config/skill-catalog.json`, and the selected `skills/<name>/SKILL.md`.
- For scripts, first analyze the content, intended audience, length, language, platform, and likely visual approaches. Recommend a style and explain why before rendering.
- For a numbered request, resolve the number using `config/skill-catalog.json`; never guess what the number means.
- Treat style names as creative specifications, not permission to copy a living creator's exact signature or a copyrighted character. Translate references into high-level attributes and use original assets.
- Prefer local/open tools and the current factory's pinned renderer. Verify licenses, API costs, and service requirements before adopting dependencies.
- Reuse the existing timeline, renderer adapter, asset registry, QA gates, and publishing boundary. Do not introduce parallel manifests or duplicate QA systems.
- Preserve deterministic time-based animation wherever practical. Do not rely on wall-clock timers or unseeded randomness for frame rendering.
- Never fabricate transcript timing, data, citations, commands, metrics, or test results.
- Render a preview/contact sheet and run relevant QA before delivery. Follow existing approval gates.
- Do not publish, commit, push, delete, overwrite, install, or incur paid costs without authorization.
- Report what was actually inspected, tested, rendered, and left unverified.

## Required output
For each job, return:
1. Intake summary and any assumptions.
2. Recommended format/style with rationale.
3. Selected skills and existing factory capabilities.
4. Scene/storyboard plan.
5. Preview and QA results, if rendering was authorized and possible.
6. Output locations using verified paths only.
7. Limitations, licensing questions, and next recommended action.

## Stop conditions
Stop before production rendering if script approval is required but absent; stop before publishing without explicit approval; stop before installing a new dependency if permission is required; stop if asset rights or source integrity create a material unresolved risk.
