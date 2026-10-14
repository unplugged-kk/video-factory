# 06 — Bake-off specification (Deliverable F)

**Not executed.** This document specifies a future controlled comparison. No renders were made for this audit, so **no winner is claimed**. It may run only after the ContentForge prerequisite is confirmed and P1-2/P1-3/P1-4 exist.

## 1. Question

Does adding a content-aware creative decision (style card + decision record + storyboard checkpoint) improve the finished video relative to today's pipeline, using the same renderer?

## 2. Arms

| Arm | Description |
|---|---|
| **Baseline** | Current pipeline exactly as it stands (director skill, R1–R6, existing gates). |
| **Variant A** | Baseline + style card + creative-decision record + advisory style-frame checkpoint. Same HyperFrames version, same gates. |
| **Variant B (conditional)** | Variant A + one procedural/canvas style (P2-3). Run only if A passes and a specific creative limitation is hypothesised. |

No renderer arm. An alternate renderer is considered only if Variant B fails and the failure is attributed to HyperFrames with evidence (frame-level, reproducible).

## 3. Controls

- **Same script, same narration audio file, same duration** across arms (voice generated once, reused).
- Same machine, same pinned renderer 0.8.114, same fonts/assets, same output spec.
- Three scripts of different types (e.g. architecture lesson, historical explainer, launch/product) so one content type does not decide.
- **Builder ≠ grader.** The agent that built a video never scores it. Critic runs by a separate agent.
- Order of review randomised; arms blinded (neutral filenames, no style-card metadata shown).

## 4. Measurements

**Objective (automatic)**
- Existing gates pass/fail: `motion_audit`, `visual_gate`, `align_words`, Rule A/B.
- Critic scores on 8 dimensions (thresholds untouched), **≥3 critic runs per video** to report spread; a difference smaller than the spread is "no difference".
- Variety report (doc 05 §5) across the three videos per arm.
- Production cost: wall-clock, agent turns, human minutes, retries.
- Failure count and gate false-positives/negatives (using seeded-fault harness from P1-6).
- Cue audibility numbers (only if the cue gate exists).

**Subjective (human)**
- Blinded pairwise preference, per video: A vs baseline.
- Reviewer checklist (§5), 1–5 per item, with free-text notes.
- Two-film test across videos in one arm.

## 5. Reviewer checklist (sample)

1. In the first 3 seconds, do I know what this video is about?
2. Does the visual language feel chosen for this content?
3. Is any frame hard to read (caption, safe zone, contrast)?
4. Do reveals land on the words they illustrate?
5. Is any motion gratuitous (movement without meaning)?
6. Are sound effects noticed, and are they helpful rather than distracting?
7. Does it look like a different film from the previous one in the same arm?
8. Would I publish it as-is? (yes / yes with fixes / no)

## 6. Go / no-go criteria (adopt Variant A)

All must hold:
1. Variant A passes every existing gate at least as often as baseline.
2. Critic scores are not lower than baseline beyond the measured spread.
3. Blinded human preference favours A in a majority of pairs, or ties with A materially cheaper in human minutes.
4. Variety report shows ≥2 structural axes differing between consecutive videos in A and not in baseline.
5. Added human time per video ≤ the budget set in the owner's approval (suggested ≤ 5 min full path, ≤ 2 min lite path).
6. No regression in licence/provenance records.

Any one failing → do not adopt; record why; keep cards as reference only.

**Variant B** adopts only if it meets 1–6 *and* demonstrably achieves something A cannot (named visual capability), without a determinism or runtime regression.

## 7. Threats to validity

- Three videos is a small sample; results are indicative, not statistical proof.
- Critic is an LLM and its thresholds are provisional; hence spread measurement.
- One reviewer (the owner) is subjective; if possible add a second blinded reviewer.
- Novelty effect: a first-time style may feel fresher simply for being new.

## 8. Outputs of a future run

A results table, the three × three renders, the variety report, critic logs, reviewer sheets, and a one-page decision memo. No production configuration changes during the run.
