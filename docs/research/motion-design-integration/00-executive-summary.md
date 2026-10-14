# 00 — Executive summary and final decision report

Audit date 2026-10-12 · Research only · Nothing installed, executed, rendered, published, staged or committed.

Files: 01 repository audit · 02 capability gap analysis · 03 integration architecture · 04 roadmap and decision matrix · 05 creative decision framework · 06 bake-off specification · 07 implementation prompts.

## Executive summary

The factory already has a strong render-and-verify spine: a pinned renderer, R1–R6 motion rules, a motion audit, a visual gate, a critic, contact sheets, and three approval gates. What it lacks is not another renderer or animation library. It lacks **a recorded, content-aware creative decision made before composition** and **a human checkpoint on style frames before assets are built**. Today "style" is mostly palette, typography and backdrop, so videos risk looking alike.

Of the 15 repositories, none justifies a new renderer or wholesale adoption. The value is in **small documented techniques**: animate's style contract and approvals, product-launch-motion's direction dials, structural axes and word-locked sync, and student-kit's review-gated candidates and negative-control validation. The most useful discovery is that the **already-pinned HyperFrames tag (v0.8.114) contains official skills that are not in the factory's lock file** (for example audio). They can be added through the existing hash-lock mechanism at no version change, after review.

Recommendation: **proceed conditionally.** Research and design are done. All production implementation is **blocked** until the ContentForge prerequisite is confirmed and the owner settles the uncommitted WIP.

## The ten answers

1. **Top three sources and what to extract.**
   (a) `animate`: STYLE.md contract plus frame checklist; three approvals; measured structural checks. (b) `product-launch-motion`: direction dials, structural axes, two-film test, word-locked sync, measured cue audibility. (c) `heygen-com/hyperframes` at the existing pin: official skills already in the tag (audio first), plus student-kit's review-gated candidates and negative-control calibration as a close fourth. Honest caveat: the ranking is my judgement; `charlie947` and `mdas` were reviewed shallowly.
2. **Heaviest overlap with existing capability.** `claude-motion-design`, `LottieFiles/motion-design-skill`, `gsap-skills`, `remotion-dev/skills`, and `motiondivision/motion` overlap R1–R6, the motion catalogue and the GSAP/CSS/WAAPI adapters HyperFrames already has.
3. **Creativity gains without touching render infrastructure.** Style cards; creative-decision record with a novelty budget; style-frame checkpoint; additive timeline cues; official pinned skills; seeded-fault gate harness.
4. **Is the timeline sufficient?** Not yet. `timeline/1` is shadow and carries timing, but not audio cues, beat markers, transition windows or review markers, and composition does not read it as the source of truth. Gaps are additive; no schema break is needed. Beat analysis is entirely absent (only matters for music-led styles).
5. **Materially different styles.** They need different *structural axes* (layout system, motion grammar, scene rhythm, depth model, illustration mode, transition family), enforced by style cards and a novelty budget against recent videos, plus real-render validation. Today 0 of 76 library entries are Mac-validated.
6. **Is an alternate renderer justified?** **No.** I found no unresolved use case that HyperFrames cannot meet. The only evidence that would change this is a reproducible, frame-level failure of a named visual capability in a controlled experiment (Prompt 10 then 11). Remotion also carries licence tiers.
7. **Not worth integrating.** `haidrrrry/claude-remotion-skill`, `mdas`, `kie.mjs` (paid path), object separation, remake mode, `@remotion/transitions` (UNLICENSED), vendoring any no-LICENSE repo, and gratuitous camera movement or SFX.
8. **Smallest high-value slice (after prerequisites).** Style cards + creative-decision record + advisory style-frame checkpoint (Prompts 2–4), with no renderer, gate or threshold change.
9. **How we will know.** Objectively: existing gates and critic unchanged or better (≥3 critic runs for spread), variety report showing ≥2 structural axes differing from the prior video, cost in human minutes. Subjectively: blinded pairwise preference and the reviewer checklist in doc 06. Not yet measured; no winner is claimed.
10. **Defer until after the bake-off.** Variant B (procedural/canvas), cue-audibility as a gate, SFX source adoption, any blocking storyboard gate, transcript-timed B-roll, HyperFrames upgrade, any Remotion work.

## Overall recommendation

**Proceed conditionally.** Conditions: (1) ContentForge prerequisite confirmed; (2) owner decision on the uncommitted WIP in `visual_gate.py`, `pipeline.py`, `export.py`, `supplied_audio.py`; (3) approval of each narrow prompt individually.

## Dependency-aware task sequence

0. Precondition gate (ContentForge, WIP) → 1. Pinned-skill review → 2. Style cards → 3. Decision record + variety report → 4. Advisory checkpoint → 5. Timeline cues (shadow) → 6. Seeded-fault harness → 7. Cue audibility (off) → 8. SFX listening comparison → 9. Bake-off → 10. Conditional procedural style → 11. Conditional renderer comparison. Details in docs 04 and 07.

## Evidence still missing

- **ContentForge prerequisite status** (not visible from this repo).
- Upstream repository metadata (stars, releases, issues, archive/rename state): GitHub API access returned 403.
- Any rendered output from any upstream project; no upstream code was run, no video watched.
- Licence text of `gsap-skills`, Barty's SFX individually, and `media-use` (HeyGen sign-in) not fully verified.
- Real-render validation for the design library (0/76).
- Critic variance across runs; loudness behaviour of the export path.
- Behaviour of the uncommitted WIP (read, not run).
- Shallow reviews: `charlie947`, `mdas`, part of Barty.

## Working-tree state and confirmation

At audit start: HEAD `ec4eb77`, tree dirty with pre-existing uncommitted changes (the handoff doc described a clean tree at `bd20722`; the live state is recorded here instead). A snapshot (HEAD, `git status --porcelain`, diff hashes, untracked-file hashes) was taken before any write. The only addition is this untracked folder `docs/research/motion-design-integration/`. See the integrity-check line appended below once verified.

**Confirmation:** no code, dependencies, production configuration, or Git history was modified; nothing was staged, committed, stashed, reset, installed, rendered or published. Upstream repositories were shallow-cloned read-only into a cloud scratch folder outside the checkout.

**Integrity check (2026-10-12, after delivery):** HEAD unchanged at `ec4eb774`; `git diff` hash, staged-diff hash (empty), and the three untracked-file hashes all match the pre-audit snapshot; stash list empty. The only difference is this new untracked folder.
