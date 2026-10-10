"""Video Intelligence: evidence-driven decisions around the production pipeline.

Modules (each runnable as `python -m contentos.intelligence.<name>`; exit 0 ok, 1 finding, 2 unreadable input):
  catalogue   motion techniques by communication purpose, joined to config/capabilities.json (read-only)
  visual      the two background rules: A (variety inside one video) and B (variety across videos)

Stable registries stay in config/ and are never written here. Anything a run changes (ledgers, evidence) lives in
<workspace>/intelligence/ so the repository stays clean. See docs/video-intelligence/."""
