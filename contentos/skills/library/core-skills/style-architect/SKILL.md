---
name: style-architect
description: "Selects and evolves distinct video styles using versioned style cards and checkable visual signatures."
metadata:
  bundle: video-factory-skills
  kind: core-workflow
  version: "1.0.0"
---

# Style Architect

## Purpose
Make different styles genuinely different in visual grammar, not merely in color or font.

## Style card requirements
Every style should define:
- ID, version, intended content, and audience fit.
- Composition and layout rules.
- Typography hierarchy and caption treatment.
- Color, texture, shape language, and asset approach.
- Camera language, movement personality, easing, and transition families.
- Scene families and examples.
- Audio/sound design guidance when relevant.
- Readability, safe-zone, and accessibility constraints.
- Forbidden/reduced patterns to prevent visual monotony.
- A review rubric and at least one validated sample.

## Selection
Choose styles based on script intent, not arbitrary variety. A code tutorial should remain readable; an architecture explanation should preserve correct relationships; a story should maintain character continuity. Offer a primary recommendation and alternatives where useful.

## Validation
Compare actual rendered frames and contact sheets. Reject superficial variants that change only palette/background. Record style ID/version in the episode manifest. Keep animation deterministic and reproducible. Reconcile this registry with the factory's existing design library instead of creating competing registries.
