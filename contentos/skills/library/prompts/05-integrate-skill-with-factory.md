# Prompt: Integrate a skill into Video Factory

Audit the live repository before making changes.

1. Read `AGENTS.md`, `config/capabilities.json`, `config/design-library.json`, existing `.claude/skills/`, orchestration stages, renderer adapter, timeline schema, and QA gates.
2. Determine whether the requested skill already exists in whole or in part.
3. Define a minimal interface: inputs, outputs, configuration, dependencies, errors, and tests.
4. Make the skill a creative recipe that calls existing components. Do not duplicate renderer, timeline, asset registry, or QA logic.
5. Use the current renderer unless a documented requirement cannot be satisfied.
6. Verify every dependency and license. Do not install without permission.
7. Add examples and tests; validate a small sample if authorized.
8. Update the capability registry and skill map if the repository uses them.
9. Keep the change isolated, reversible, and documented.
10. Report changed files, tests actually run, visual evidence, limitations, and rollback instructions.
