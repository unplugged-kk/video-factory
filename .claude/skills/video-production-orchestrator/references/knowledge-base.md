# Knowledge base: what lives where

| Kind | Location | Written by |
|---|---|---|
| Stable registries (capabilities, providers, platforms, quality) | `config/*.json|yaml` (Git) | owner decisions only |
| Seed knowledge (motion catalogue, shipped visual looks) | `config/motion-catalogue.json`, `config/visual-languages.seed.json` (Git) | reviewed commits |
| Run evidence (visual ledger, catalogue evidence, experiments, decision records) | `<workspace>/intelligence/` (outside Git) | tools below, under a lock |
| Known failures and design | `docs/video-intelligence/` (Git) | commits |

Retrieval: ask for exactly what the phase needs. Techniques: `catalogue query`. Looks: `visual check`. Known failures: read `docs/video-intelligence/02-known-failures.md` for the tool or stage you are about to use. Do not load the whole archive into context.
Never store secrets, API keys or absolute personal paths in any of these.
