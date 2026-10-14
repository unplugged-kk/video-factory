# 02 — Capability gap analysis (Deliverable B)

Audit date 2026-10-12. Research only. Statuses use the six allowed values: `implemented`, `partial`, `experimental`, `proposed`, `absent`, `unverified`.

**Reading rule.** A feature in a plan is not implemented. A passing unit test is not proof of good visual results. Where the only evidence is a unit test or a check that measures structure (not appearance), the Status says so in *Known limitations* and I did not upgrade it. Evidence labels as in doc 01: **[read]**, **[ran]**, **[claim]**, **[not verified]**, **[mine]**.

**Live-repo caveat.** The project handoff described a clean tree at HEAD `bd20722`. The live checkout was at `ec4eb77` with a dirty tree (uncommitted WIP in `visual_gate.py`, `pipeline.py`, `export.py`, and the new `supplied_audio.py`). Rows touching that WIP are `partial`/`experimental` because the code is uncommitted and I did not run it. [read]

## 1. Inventory (23 rows)

| # | Capability | Current implementation | Status | Evidence | Known limitations |
|---|---|---|---|---|---|
| 1 | Creative direction | `video-director` skill + `sceneplan/1` `direction` block; orchestrator `decision-engine.md`; `visual-languages.seed.json` | **partial** | [read] skill, decision-engine, seed JSON | Direction is a per-video narrative written by an agent. There is no structured record of *why* a visual language, motion grammar or sound strategy was chosen, no comparison against recent videos, and no rejected-alternatives log. Palette/typography are the main axes of "style". |
| 2 | Story and hook planning | Script stage + SCRIPT_APPROVED gate; director skill covers hook and beats; `align_words` links script to audio | **implemented** | [read] AGENTS.md, skills | Verified as process and artefacts, not as quality of hooks. No upstream technique is needed here. |
| 3 | Style selection and variation | Design library (76 entries, **0 Mac-validated**), `visual-languages.seed.json`, Rule A/B backdrop variety in `intelligence/visual.py` | **partial** | [read] design-library.json, visual.py; [ran] entry counts | Variation is mostly palette/typeface/backdrop. No "style card" contract that fixes a motion grammar, layout vocabulary and forbidden moves per style. 0 of 76 library entries validated on the real render path, so none can honestly be called production-ready. |
| 4 | Storyboard and style-frame approval | Three gates (SCRIPT / PRODUCTION / PUBLISH). Track B has a director review | **absent** (as a visual gate) | [read] AGENTS.md, pipeline | No gate shows the human a still style frame or a storyboard *before* composition. PRODUCTION_APPROVED comes after assets exist. Animate and student-kit supply the method. |
| 5 | Scene composition | HyperFrames HTML compositions (Track B) and templates (Track A); `explainer-motion-craft` R1–R6; `visual_gate` layer checks | **implemented** | [read] skills, visual_gate; prior shipped pilots in project docs [claim] | Quality of results is judged by the critic and a human; the gate checks layers and structure, not taste. |
| 6 | Motion choreography | `explainer-motion-craft` R1–R6; motion catalogue (70 entries); `motion_audit` (ease inventory, YDIF pops, still-fraction) | **implemented** | [read] motion_audit.py, catalogue; [claim] pilot summaries | The audit measures ease variety and pops, not whether motion serves meaning. Catalogue entries are not validated per style. |
| 7 | Camera and parallax | Possible via GSAP transforms in HyperFrames; no dedicated camera/parallax primitive found | **partial** | [read] catalogue/skills (no camera rig entry identified); [mine] | Handled ad hoc by the agent per composition. No reusable "camera move" with timing hooks. Upstream skills (product-launch-motion, claude-motion) describe camera grammars that could be documented as catalogue entries. |
| 8 | Kinetic typography | Caption system + word timing; motion catalogue text entries; R-rules on legibility | **partial** | [read] align_words, catalogue; [mine] | Captions are word-aligned. Expressive kinetic type (word-locked emphasis tied to speech) exists as technique, not as a verified, repeatable component. |
| 9 | Word-level synchronization | `align_words` caption alignment from audio; `timeline/1` carries word/segment timing | **implemented** (captions) / **partial** (visual reveals) | [read] timeline.py (214 lines), align_words | Reveals tied to specific spoken words are not enforced by any check; `timeline/1` is **shadow**, not authoritative for composition. |
| 10 | Beat and drop analysis | None found | **absent** | [read] grep of production code found no beat/onset analysis [mine: search was by reading, not exhaustive static analysis] | Needed only for music-led styles. Not needed for narration-led explainers. Claude-motion describes the idea; I did not run it. |
| 11 | Narration and audio ingest | TTS voice stage; `supplied-audio/1` for user-supplied audio is in **uncommitted WIP** | **partial** | [read] supplied_audio.py header, pipeline/export diffs | Supplied-audio path not committed, not run by me, not covered by a rendered evidence. |
| 12 | Sound effects and music mixing | Export mixes voice and (optional) music with ducking per prior docs; no SFX cue system | **partial** | [read] export.py diff, docs 05/07; [claim] | No cue list on the timeline, no SFX library with provenance, no measured cue audibility. Upstream `hyperframes-audio` skill (in the pinned v0.8.114 tag, **not** in the lock file) documents `data-fx-chain` and voiceover carve ducking [read]. |
| 13 | B-roll and visual cutaways | Asset/stock handling per pipeline docs; Track A backdrops; no transcript-timed B-roll planner | **partial** | [read] docs 05/07 | Cutaway selection is agent-judged. Student-kit's review-gated cut candidates are the closest method. Footage editing itself is out of scope for the current explainer factory. |
| 14 | Procedural illustration | SVG/CSS/canvas by hand inside compositions; no style-bound procedural illustrator | **partial** | [read] catalogue; [mine] | Each video re-invents illustration. Upstream repos (mdas, charlie947, haidrrrry) did not show a verified, licence-clean, reusable method; `mdas` and `haidrrrry` are rejected. |
| 15 | 3D and simulated visuals | HyperFrames `three` and `typegpu` runtime adapters exist upstream at the pin; none used in a validated factory capability | **unverified** | [read] upstream adapter list; [not verified] any factory use | The `capabilities.json` registry does not claim it as validated. GPU/headless determinism on Mac is unproven. |
| 16 | Timeline and retiming | `timeline/1` (214 lines) — **shadow** schema; `sceneplan/1` timings | **partial** | [read] timeline.py | Does not yet carry audio cues, beats, transition windows or review markers; composition does not read it as source of truth. |
| 17 | Preview and labelled contact sheets | `preview.py`, `sheet/1` labelled contact sheets | **implemented** | [read] preview.py, sheet.py header | Static stills only; no per-style sheet layout. |
| 18 | Frame inspection | `motion_audit` (YDIF), `visual_gate`, contact sheets, critic frame review | **implemented** | [read] motion_audit.py, visual_gate | Measures pops, stillness, layers, captions. Does not detect "looks samey to the last video". |
| 19 | Visual quality scoring | Critic rubric: 8 dimensions + hard failures; **provisional** thresholds (7 each, 8.0 avg) | **partial** | [read] critic.py, quality.yaml | Thresholds are provisional. No dimension asks "does this video follow its chosen style's contract". Scoring variance across runs not measured here (see bake-off). |
| 20 | Safe-zone and text readability | `visual_gate` captions/transition checks; WIP safe-zone addition | **partial** | [read] visual_gate WIP diff | Safe-zone code is uncommitted; I did not run it. |
| 21 | Export and mastering | `export.py`, package stage, publish is dry-run | **implemented** | [read] pipeline/export | Export diff is uncommitted WIP; loudness normalisation not independently verified. |
| 22 | Asset provenance and licensing | `capabilities.json` registry; hash-pinned upstream skills (`upstream_skills.py` + lock); AGENTS.md rules | **partial** | [read] capabilities.json, lock file | Software provenance is strong. Per-asset media licence (fonts, SFX, stock) is not a first-class record. |
| 23 | Reproducibility and resume | Pinned renderer 0.8.114, hash-verified skills, stage artefacts, resume per pipeline docs | **implemented** | [read] lock file, pipeline docs | Reproducibility of *creative* choices is not recorded (see row 1). |

### Status counts
implemented 7 (rows 2, 5, 6, 17, 18, 21, 23) · partial 12 (rows 1, 3, 7, 8, 11, 12, 13, 14, 16, 19, 20, 22) · absent 2 (rows 4, 10) · unverified 1 (row 15) · split 1 (row 9: captions implemented, visual reveals partial) · experimental 0 · proposed 0. [mine] tally of the table above.

The weaker status governs any decision on a split row.

## 2. Where upstream offers genuinely new capability

Only items that the table shows as `absent` or `partial` with a gap upstream actually fills:

| Gap | Upstream source | New capability | Net value |
|---|---|---|---|
| Storyboard / style-frame gate (row 4) | animate (three approvals), student-kit (review-gated candidates) | A review checkpoint *before* composition, with explicit approval records | **High**, small to add; no renderer change |
| Style as contract (row 3) | animate (STYLE.md + frame checklist), product-launch-motion (direction dials, structural axes, two-film test) | A style card with motion grammar, layout vocabulary, forbidden moves, and a checklist the critic can score | **High**; answers "palette variants" |
| Word-locked visual sync (rows 8, 9, 16) | product-launch-motion | Rule that reveals land on specific word timestamps, plus measured cue audibility | **Medium-high**; needs timeline cues (additive, shadow) |
| SFX cue system (row 12) | claude-motion (synth), Barty (CC0 library), `hyperframes-audio` (bundled, at current pin) | Cue list on the timeline; optional source; audibility measurement | **Medium**; needs a listening comparison before choosing a source |
| Gate calibration | student-kit (negative-control validators) | Seed known-bad fixtures to prove a gate can fail | **Medium**; protects against vacuous gates |
| Official HyperFrames skills already inside the pinned tag (rows 12, 13, 15) | hyperframes @ v0.8.114 | `hyperframes-audio`, `faceless-explainer`, etc. at the **same** version the factory already pins | **High, lowest risk**; goes through the existing hash-lock mechanism. `faceless-explainer` pulls in `media-use` (HeyGen catalogue/CLI sign-in) so it needs a service/licence review first |

## 3. Overlap (no new capability)

- `claude-motion-design` and `LottieFiles/motion-design-skill`: overlap with R1–R6 and the motion catalogue. Take at most a few catalogue entries.
- `remotion-dev/skills` and `gsap-skills`: GSAP/animation guidance already covered by pinned HyperFrames skills and `explainer-motion-craft`.
- Remotion itself and `motiondivision/motion`: different renderer / different animation library. No unresolved use case found that HyperFrames cannot do (see doc 04).

## 4. What this table does not show

- No row has been checked against a **rendered** video by me; no renders were produced.
- The `0/76` Mac-validated figure means the design library cannot yet back a "materially different styles" claim without validation work.
- ContentForge-side status is not visible from this repo; see doc 00 for the blocked-implementation statement.
