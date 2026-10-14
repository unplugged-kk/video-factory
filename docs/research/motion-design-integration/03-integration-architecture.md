# 03 — Integration architecture (Deliverable C)

Status: **proposal only.** Nothing here is implemented. Every new element is additive, optional, and removable by deleting one file or flag. All implementation is **BLOCKED** until the ContentForge prerequisite is confirmed (see doc 00).

## 1. Design principle

Add one thing the factory lacks: a **content-aware creative decision** that is recorded, reviewable, and checked afterwards. Reuse the existing renderer (HyperFrames 0.8.114), `sceneplan/1`, `timeline/1`, `sheet/1`, `motion_audit`, `visual_gate`, the critic, and the three approval gates. No new renderer, no new registry (style cards are *entries in the existing design library / `capabilities.json` mechanism*, not a parallel one).

## 2. Data flow

```
brief + script (SCRIPT_APPROVED)
        │
        ▼
 [1] creative-decision record  (creative-decision/1)   ← new, small JSON
        │   inputs: content type, audience, length, platform, recent-video history, hard constraints
        │   outputs: chosen style card id, motion grammar, sound strategy, 3 candidate directions + rejection reasons
        ▼
 [2] style card (style/1)  ← new contract file per style, referenced by id
        │
        ▼
 [3] sceneplan/1 .direction  ← EXISTING block, gains `style_ref` + `decision_ref` (optional fields)
        │
        ▼
 [4] style-frame / storyboard checkpoint  ← new ADVISORY step, then explicit approval record
        │   contact sheet (sheet/1) of 3–5 stills + one-line shot list
        ▼
 [5] timeline/1 (extended, shadow)  ← EXISTING schema + additive: audio cues, beat markers, transition windows, review markers
        │
        ▼
 [6] compose (HyperFrames HTML)  ← UNCHANGED renderer, R1–R6 preserved
        │
        ▼
 [7] render  ← UNCHANGED
        │
        ▼
 [8] gates: motion_audit, visual_gate, align_words, Rule A/B  ← UNCHANGED thresholds
        │      + optional cue-audibility gate (new, off by default)
        ▼
 [9] critic  ← EXISTING 8 dimensions; optional 9th `style_fidelity` only when a style card is present
        │
        ▼
[10] PRODUCTION_APPROVED → export → package → PUBLISH_APPROVED (dry-run)  ← UNCHANGED
```

## 3. Interfaces and ownership

| Element | Owner | Format | New or existing | Notes |
|---|---|---|---|---|
| Creative-decision record | Video Factory (execution plane) | `creative-decision/1` JSON next to the sceneplan | **New** | Advisory; written by the director agent, human-approvable. Contains no secrets. |
| Style card | Video Factory | `style/1`: STYLE contract (motion grammar, layout vocabulary, forbidden moves, frame checklist, sound strategy, required capabilities, licence notes) | **New** (small) | Lives with the design library; **not** a second registry. Validation status field mirrors the library (`validated: false` until a real render passes). |
| `sceneplan/1.direction` | Video Factory | existing | Existing, +2 optional fields | Backward compatible: absent fields mean today's behaviour. |
| Storyboard / style-frame checkpoint | Video Factory generates; **human** approves | `sheet/1` + approval JSON | New step, reuses sheet | Starts advisory (no blocking). Becoming a blocking gate needs a separate decision. |
| Timeline cues | Video Factory | `timeline/1` additive keys | Existing schema extended | Stays **shadow** until a later task promotes it. |
| Cue-audibility measure | Video Factory | check producing a number per cue | New, off by default | Calibrated with seeded faults first. |
| Approvals / publish | **ContentForge** (control plane) | existing | Existing | Factory does not call ContentForge directly. Exchange stays filesystem (`~/.contentos/exchange`) / `factory-worker`. |
| Renderer | HyperFrames (pinned) | existing | Existing | Unchanged. |

**Boundary rule.** The factory *writes* a decision record and a checkpoint artefact; ContentForge may *read* them via the existing exchange if it wants to surface them. No new factory→ContentForge call is introduced.

## 4. The twelve-step workflow

| Step | What happens | Automatic? | Alternatives offered | Approval | Blocking? |
|---|---|---|---|---|---|
| 1 | Brief and script | Existing | — | SCRIPT_APPROVED | Yes (existing) |
| 2 | Classify content (type, tone, length, platform, audience, factual density) | Automatic | Override | — | No |
| 3 | Fetch recent-video history (styles/grammars used in last N) | Automatic | — | — | No |
| 4 | Generate 3 materially different directions (different structural axes, not palettes) | Automatic | 3 | — | No |
| 5 | Score and pick one; record rejections | Automatic recommendation | Human may pick another | **Explicit** if the human wants a different one; otherwise recorded as accepted by default | No (advisory) |
| 6 | Style frames (3–5 stills) + shot list as a labelled sheet | Automatic | — | **Explicit** approval record | Advisory first; blocking only after owner decision |
| 7 | Build extended timeline (cues, markers) | Automatic | — | — | No |
| 8 | Compose in HyperFrames | Existing | — | — | — |
| 9 | Render | Existing | — | — | — |
| 10 | Technical gates | Existing (+ optional audibility) | — | — | Yes (existing) |
| 11 | Critic by a **different** agent from the builder | Existing | — | — | Yes (existing thresholds untouched) |
| 12 | PRODUCTION_APPROVED, export, package, PUBLISH_APPROVED dry-run | Existing | — | Existing gates | Yes (existing) |

**Lite path (15-second Short).** Steps 2–5 collapse into one recorded choice among two directions; step 6 is a single still; step 7 skips beat markers; the cue-audibility gate is off. Total added human time target: under two minutes. A heavy ceremony on a Short would be a regression.

## 5. Capability validation and licensing metadata

- Style card has `requires: [capability ids]`. Each id must exist in `capabilities.json`. A card that requires an unvalidated capability is labelled `experimental` and cannot be auto-recommended.
- Software provenance continues through `upstream-skills.lock.json` (tag + commit + hash). Any new pinned skill goes through `scripts/upstream_skills.py`, never copied by hand.
- Media provenance (SFX, fonts, stock) gains a minimal record: source, licence id, URL, checksum. Not built now; specified in the SFX experiment prompt.
- No-LICENSE repos are reference-only; nothing is vendored from them.

## 6. What stays unchanged

Renderer and version; R1–R6; critic thresholds (7 each / 8.0 avg); `config/*.yaml` and the three gates; `vendor/`; `.claude/skills/hyperframes-*`; E2/E3b styles unpromoted; dry-run publish; builder never grades own video.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Style cards turn into palette presets again | Card must declare a motion grammar and at least two structural axes that differ from the prior N videos; reviewer checks this in the variety report |
| Ceremony slows production | Lite path; checkpoint advisory first |
| Cue gate passes vacuously | Seeded-fault harness must show it fails known-bad inputs before it is trusted |
| `style_fidelity` critic dimension inflates scores | Conditional only; thresholds not changed; spread measured over ≥3 critic runs |
| Prompt-injection through upstream text | Upstream content is reference only; skills enter via hash-lock review |
