---
name: video-director
description: "Routes any topic, script, audio, clip, or reference to the right Video Factory workflow and skills."
metadata:
  bundle: video-factory-skills
  kind: core-workflow
  version: "1.0.0"
---

# Video Director

## Purpose
Be the single front door to the Video Factory. Understand what the user wants, inspect available capabilities, choose the smallest useful skill set, and route production through the existing factory.

## Workflow
1. Parse the request: topic/script/media, intended audience, purpose, platform, language, duration, aspect ratio, style preferences, deadline, and approval status.
2. If the request begins with a number, resolve it using `config/skill-catalog.json`. Never guess a mapping.
3. If a script is supplied without a style, invoke the script-to-storyboard and style-architect workflows before rendering.
4. Read the live factory capability registry and check whether selected skills, renderers, fonts, models, and effects actually exist.
5. Recommend one primary style and up to two alternatives when a choice is meaningful. Explain differences in visual grammar, pacing, readability, and effort.
6. Produce a plan that maps each scene to an available skill or primitive.
7. Follow the factory's approval gates; render previews before full output where required.
8. Deliver verified outputs and QA evidence. Never claim work that was not executed.

## Constraints
- Prefer one factory and existing components over multiple disconnected tools.
- Do not install dependencies, overwrite files, publish, or incur paid costs without authorization.
- If the requested capability is missing, report the gap and offer a minimal integration plan.
