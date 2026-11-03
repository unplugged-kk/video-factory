# Operating Model: One Factory, Many Content Types

## Request lifecycle

1. **Intake** — user provides a topic, script, audio, clip, or reference.
2. **Analyze** — classify content, audience, duration, language, platform, factual risks, and rights.
3. **Recommend** — select a primary style and alternatives from the live skill/style catalog.
4. **Plan** — produce scene plan and identify which skills and capabilities are needed.
5. **Approve** — ask for creative/script approval where required by the factory.
6. **Produce** — invoke skills through the existing orchestrator and renderer.
7. **Inspect** — create preview/contact sheet and run technical, visual, audio, and content QA.
8. **Revise** — make targeted fixes, preserve reproducibility, rerun relevant gates.
9. **Package** — video, metadata, source ledger, manifest, QA report.
10. **Publish** — only through the approved publishing boundary.

## Required user experience

The user can say:
- "Create video number 12 about Kubernetes scheduling."
- "Here is a script; recommend the best format before rendering."
- "Make this a cinematic documentary, not a normal explainer."
- "Analyze this reference video and adapt the pacing and scene grammar."
- "Use the skills you have; tell me what's missing before you start."

The agent must translate this into the same factory lifecycle. The user should not need to know which renderer, animation library, or helper script is involved.

## Default assumptions

When the request is clear, infer reasonable defaults and state them briefly. Ask only for a missing essential detail. Use a preview-first workflow. Do not publish or overwrite without approval.
