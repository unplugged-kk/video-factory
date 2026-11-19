# Architecture findings

Branch `feat/p1-1-lookmap`, HEAD `86eeaa2`. Scope: why a system with 57 preset files, six style families
and a validated sceneplan format still renders near-identical videos.

> **Substitution note.** The specialist assigned this document (an `architect` agent on a rate-limited model) was
> attempted twice and produced nothing — two HTTP 429s, zero output. A third attempt under a different type
> (`code-reviewer`) writes `ARCHITECTURE_FINDINGS_2.md`, which exists to confirm or contradict this file. What
> follows is my own reading of the code, verified line by line. It is narrower than the original brief - it does
> not exhaustively enumerate every style registry - and until the second document lands it is not independently
> reviewed.

## 1. What actually decides the pixels

> **Corrected by `ARCHITECTURE_FINDINGS_2.md`.** My first version of this section had two mechanics wrong. Both
> corrections are verified below. Do not rely on the original wording.

`contentos/pipeline.py:233` `s_compose` dispatches four ways: `render == "remotion"` (`:234`), `render == "mpt"`
(`:237`), `spec['visual_style']` → scenekit (`:239-243`), else the **hardcoded template** (`:246`). A normal
spec takes branch four.

In that branch the palette, typography and layout are a **single hardcoded f-string written at
`pipeline.py:303-308`**: `background:#090a0f`, a `#root` radial gradient `#1a1e36,#08090e`, `.tag` `#a5b4fc`,
`h1 {U*0.085}px`, `.cap` `#fff`, and a caption highlight `#fbbf24` set at `pipeline.py:270`. None of that is
read from a preset, a style card, or a look.

Two hooks do run on this path - `style_card` at `pipeline.py:246` and `visual_layer` at `pipeline.py:283` -
so my earlier claim that they were Remotion-only was **wrong**. But both are off unless
`spec['features'][<name>]` is truthy (`features/registry.py:56-57` returns a pass-through), and neither owns the
values above. `visual_layer` rewrites the scene's opening `<div>` and prepends one decoration; it never touches
the root background, headline size, caption colour or grid.

**The mechanical proof of the whole gap:** `visual_layer.py:49` is
`bg_style = BACKDROPS[(scene_idx - 1) % len(BACKDROPS)]`. The backdrop is indexed by **scene number**, never by
look. Two different look ids therefore cannot produce different frames even with the feature enabled.

## 2. Where "style" is represented, and who reads it

| Location | Files | Read by | Effect on a frame |
|---|---|---|---|
| `config/presets/looks/` + `effects/` | 57 JSON | `contentos/intelligence/looks.py` only | **none** |
| `config/design-library.json` | 1 | `intelligence/designs.py` (recommendation output) | none |
| `config/motion-catalogue.json` | 1 | catalogue queries | none |
| `config/visual-languages.seed.json` | 1 | export stage writes a shipped-look record | none (it is an output ledger) |
| `config/styles/` | — | not read by any composer path I found | none |
| `contentos/scenekit/styles.py` | 1 | scenekit preview | partial |
| creative skill library (`contentos/skills/library/`) | 79 recipes | `creative-skill-router` skill | none automatically |

The decisive evidence is in the repo's own words: `contentos/videojob.py:38` —
*"looks and effects are data in config/presets/; the builder does not read them yet"*.

`contentos/intelligence/looks.py:99` is the only code that even opens a preset, and it exists to say
`"cannot load presets: ..."`.

**`spec["look"]` is read by nothing.** Grepping every form of the key across `contentos/` returns one hit,
`scenekit/lookmap.py:200`, and that one *writes* the key. No composer consumes it. A spec carrying a `look:`
id falls to the hardcoded branch and emits identical bytes.

**Conclusion:** the preset catalogue is data with no consumer in the render path. That is one line of truth
that no amount of catalogue size changes.

## 3. Two style systems describing one idea

`config/presets/*.json` (`look/1`) and the `sceneplan/1` direction block describe the same intent - palette,
typography, motion, treatment - in two schemas that nothing reconciles. `AGENTS.md` §10 already warns that
the tag `look/1` names two different things (a preset, and the export stage's shipped-look record), and that
confusion is a symptom of the same duplication.

Recommendation: keep `look/1` as the only style vocabulary, because it is already validated
(`contentos.sh looks validate`), versioned in Git, and referenced by the migration map. Retire the
`sceneplan/1` direction block's style fields into a reference to a look id.

## 4. The smallest change that makes a look change frames

Not a new engine. Three edits, revised after the second pass:

1. **Add the dispatch branch.** `contentos/pipeline.py:233` `s_compose` must resolve `spec['look']` and route it
to scenekit (or a look-driven template), instead of falling through to the hardcoded f-string at `:303-308`.
2. **Make the backdrop look-indexed.** `features/visual_layer.py:49` must read the resolved look's backdrop
   rather than `BACKDROPS[(scene_idx-1) % len(BACKDROPS)]`.
3. **Make the palette and type look-driven.** The colours and sizes at `pipeline.py:303-308` and the caption
   highlight at `:270` have to come from the look, or the first two edits just move a hardcode.

Then the acceptance test the brief asks for becomes provable: two look ids, same spec, two visibly
different frames. Until those three land, "30 looks" is a catalogue, not a capability.

The uncommitted `contentos/scenekit/lookmap.py` is the **right half, with no caller** - its own docstring says
so: *"P1-1 M1, compile only, nothing in the pipeline calls it yet"*. `to_style` and `compile_all` are a real
`look/1` → scenekit translator with contrast maths, but they emit into a scenekit state dict for a path gated
on `visual_style`, which nothing sets. One dispatch branch turns it into a capability; that is why edit 1
comes first.

## 5. Dead ends worth naming

- `features/extra_gates.py` registers three gates that cannot FAIL (see `MASTER_GAP_REGISTER.md` G-05).
- `local-first-policy.yaml:15` `exceptions:` is read by nothing (G-16).
- `contentos/export.py:117` used `ledger.approved()` for one of the two tracks and not the other - the
  asymmetry was the whole bug class (G-01).
- `provide_.py:48` lets a YAML edit enable paid providers globally (G-15).

The pattern across all four: a control that looks enforced and is only recorded. When auditing this codebase,
the useful question is never "does a registry/flags/gate exist" but "which call site reads it, and what
happens when it says no". Most of the real defects found today were of that shape.
