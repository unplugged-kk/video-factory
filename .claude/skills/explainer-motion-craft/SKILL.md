---
name: explainer-motion-craft
description: Use when authoring or revising the HyperFrames animation of a Video Factory explainer (easing, camera, reveal timing, captions, safe zones) so it avoids slideshow-style motion. Not for TTS, scene planning, rendering or QA.
---

# Explainer motion craft

House motion rules for HyperFrames explainers built from a `sceneplan/1` scene plan and aligned word timings. They are
distilled from an audit of upstream skills (`docs/factory-v2/07-motion-graphics-skills-audit.md`) and checked on a
controlled A/B of Pilot 001. Where a rule is only guidance, it says so.

## Load order
1. `hyperframes-core` (installed, pinned) for the composition contract: one paused GSAP timeline at `window.__timelines["main"]`, `data-*` timing, no randomness or wall-clock, no render-time network.
2. `hyperframes-animation/rules-index.md`: pick 2-4 atomic rules and compose them. Read a blueprint (`blueprints-index.md`) only when a scene matches one (`agent-progress-theater`, `camera-journey` and `typewriter-reveal` fit explainers about agents and tools).
3. `hyperframes-keyframes` for camera moves, punch-ins and `hyperframes keyframes` diagnostics.
4. Use the project's local `gsap.min.js`. Upstream examples load GSAP and fonts from a CDN; never copy that, renders must not touch the network.

## Rules (R1-R6)
- **R1 Smooth settle.** Default entrance ease is `power3.out`. No `back`, `elastic` or `bounce` unless the brief asks for playful. (Upstream motion doctrine; Pilot 001 had 5 `back.out` pops, variant B has 0.)
- **R2 Reveal on the spoken cue.** An element appears when its word is spoken, using `cue(phrase, scene)` from the aligned word timings, not at scene start. Do not dump a scene's content in its first quarter.
- **R3 One world, one camera.** Move the `#stage` wrapper once per scene (about 0.6-0.9 s, `power2.inOut`), then HOLD. Start each move from where the previous one ended: use `tl.to`, never `fromTo` with a reset start (Pilot 001 snapped at four scene cuts; about 22 px measured at the one frame pair inspected). No scene-long drift. Captions and the kicker stay outside the stage.
- **R4 Stillness beats fake life.** No scale "breathing", no `repeat:-1`, no decorative loops. A held frame is fine. (Upstream says this; one upstream skill says the opposite, "idle elements breathe", and was rejected for explainers.)
- **R5 Safe zones.** Captions and key content inside the title-safe box (80%, 10% inset per edge); everything visible inside action-safe (90%). 9:16 platform UI overlap zones are NOT verified, treat the portrait layout as unconfirmed until checked on a phone.
- **R6 Short statements.** One idea per shot; split a claim of more than about 6 words or turn it into a visual. Narration pace: upstream and a second skill both budget 2.3-2.5 words/s (about 140-150 wpm). Pilot 001 runs 3.0 words/s; if a new script is that dense, trim words or lengthen scenes before speeding the voice. (Guidance, not a tested threshold.)

## Local checks (run after every build)
```
npx --no-install hyperframes lint && npx --no-install hyperframes check
python scripts/motion_compare.py ...            # A/B on a COPY when you change a rule
node .claude/skills/hyperframes-animation/scripts/animation-map.mjs <composition-dir> --out <tmp> --width W --height H --fps 30
```
`animation-map.mjs` is only needed occasionally and installs nothing unless you opt in:
set `HYPERFRAMES_SKILL_PKG_VERSION=0.8.114` (the pinned renderer) and, after reading `scripts/package-loader.mjs`, `HYPERFRAMES_SKILL_BOOTSTRAP_DEPS=1`.
Read its flags with care: `paced-slow` on a `#stage` tween means a drift (R3); `dead zones` are holds with nothing developing, check them against the narration before reacting; `collision` counts overlapping boxes and is usually by design (36 on Pilot 001, unreviewed), so do not gate on it.

## Hand off
When the render exists, switch to `explainer-visual-qa`. Never edit a finished pilot in place: change a copy.
