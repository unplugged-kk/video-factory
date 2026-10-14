# 05 — Creative decision framework (Deliverable E)

Goal: each video gets a **deliberate** visual language, storyboard, motion grammar and sound strategy — chosen from the content, compared against recent videos, and recorded — without sacrificing clarity or consistency. Proposal only; nothing built.

## 1. Vocabulary (taken from product-launch-motion and animate, adapted)

- **Dials** (continuous): energy, density, formality, warmth, pace.
- **Structural axes** (discrete, must differ between videos to count as "materially different"): layout system (grid / full-bleed / split / stacked cards), motion grammar (eased glide / snap-cut / draw-on / parallax / type-driven), scene rhythm (even / accelerating / punctuated), depth model (flat / layered / pseudo-3D), illustration mode (diagrammatic / iconographic / photographic / typographic), transition family.
- **Palette and typeface are not axes.** Changing only them is a "palette variant".
- **Two-film test:** if two videos' frames could be swapped without the viewer noticing, they fail.

## 2. Decision tree

```
1. HARD CONSTRAINTS (non-negotiable; filter first)
   - factual fidelity / accessibility / captions legible & in safe zone
   - licences clean; R1–R6; existing gates
   - platform + length (Short vs long-form)
   → candidates that break any are removed, not scored.

2. CLASSIFY THE CONTENT
   - What is the viewer's job? understand a system / feel a story / evaluate a claim / learn a procedure / see a thing
   - Factual density: low / medium / high
   - Emotional register: neutral / curious / urgent / reflective
   - Visual referents available? (diagram-able, historical imagery, product UI, abstract)

3. SET DIALS from the classification (rule-based defaults, human-overridable)

4. PICK STRUCTURAL AXES
   - Start from what the content wants (e.g. system → diagrammatic + layered).
   - Then apply the NOVELTY BUDGET: compare to last N videos (N≈5). Require ≥2 axes to differ
     from the most recent video and no axis combination repeated within N.
   - If content strongly demands a repeat axis, record why (consistency is allowed; accidental sameness is not).

5. GENERATE 3 MATERIALLY DIFFERENT DIRECTIONS
   - Differ on ≥2 structural axes each, not just palette.

6. SCORE each on: fit to content · clarity · feasibility in HyperFrames today · novelty vs history · cost/time · licence risk
   - Anything needing an unvalidated capability is labelled experimental and cannot be auto-picked.

7. PICK ONE; WRITE REJECTION REASONS for the other two.

8. SOUND STRATEGY
   - narration-led (default): sparse cues on key reveals, ducked under voice
   - music-led: only if beat analysis exists (currently absent → not selectable)
   - silent-cue: none
   - Cue budget: a cap per minute so effects do not become noise.

9. STYLE-FRAME CHECKPOINT → human approve / redirect.
```

## 3. How variety and consistency coexist

- **Consistency lives inside a video and across a series**: one style card per video; series identity (logo, caption treatment, safe zones, lower-third) stays fixed.
- **Variety lives between videos** in structural axes, enforced by the novelty budget and measured by the variety report.
- Clarity wins ties: a high-novelty direction that lowers legibility is rejected at step 1/6.

## 4. Sample decisions (illustrative; none rendered, no winner claimed)

| Video | Classification | Chosen direction | Two rejected | Sound |
|---|---|---|---|---|
| **Architecture lesson** (how a system's parts talk) | Understand a system; high density; neutral | Diagrammatic, layered, draw-on lines, even rhythm | Photographic montage (no referents); type-driven kinetic (too dense) | Sparse soft cues on connections |
| **Surprising AI workflow** | Evaluate a claim; medium density; curious | Split-screen "before/after", snap-cut rhythm, punctuated | Full-bleed UI recreation (feasibility); iconographic cards (too similar to last video) | Short tick on each reveal |
| **Historical explainer** | Feel a story; low-medium density; reflective | Textured flat illustration with slow parallax, accelerating rhythm toward the turning point | Diagram timeline (cold); typographic only (no emotion) | Ambient bed, near-no SFX |
| **Product launch** | See a thing; low density; urgent | Product-hero, word-locked reveals, snap-cut | Isometric diagram (hides product); documentary collage | Measured accent cues on hero reveals |
| **Science concept** | Understand a system; medium density; curious | Procedural/canvas simulation-like visual (experimental, P2-3) *or* layered diagrammatic fallback | Pure text cards; stock footage | Quiet cues |

The science-concept row shows the rule: an experimental capability is listed but the validated fallback is what ships unless the experiment passes.

## 5. Variety report (metrics)

Per video, recorded and compared with the last N:
1. Structural axes chosen, and how many differ from the previous video.
2. Axis-combination repeats within N.
3. Transition families used.
4. Distinct ease inventory (reuse of `motion_audit`).
5. Backdrop variety (reuse Rule A/B).
6. Palette distance (reported but explicitly *not* counted toward novelty).
7. Human two-film test result (yes/no).

## 6. What the framework does not do

It does not claim the chosen style looks better. That is a subjective judgement that only the bake-off (doc 06) can inform.
