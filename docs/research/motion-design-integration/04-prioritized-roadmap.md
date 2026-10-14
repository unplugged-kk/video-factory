# 04 — Prioritized roadmap and decision matrix (Deliverable D)

**Gate on everything below:** ContentForge prerequisite unconfirmed → all production implementation is **BLOCKED**. Research and design prompts may proceed. The repo also carries uncommitted WIP (G3/G6-type work in `visual_gate.py`, `pipeline.py`, `export.py`, `supplied_audio.py`) whose owner decision is needed before anything touches those files.

## 1. Decision matrix (15 repositories)

| Repository | Decision | One-line reason |
|---|---|---|
| AbubakrChan/product-launch-motion | **ADAPT** | Direction dials, structural axes, two-film test, word-locked sync, cue audibility — techniques, not code |
| charlie947/motion-graphics-skills | **REFERENCE** | Shallow review; ideas overlap R1–R6 |
| howseen-ai/claude-motion-design | **ADAPT** (small) | A few catalogue entries; mostly overlap |
| heygen-com/hyperframes-student-kit | **ADAPT** | Review-gated cut candidates, EDL, quality-gates table, negative-control calibration |
| Barty (SFX library) | **ADAPT** | Candidate CC0 SFX source, subject to licence check and listening test |
| animate | **ADAPT** | STYLE.md + frame-checklist contract, three approvals, formats formula |
| whaleyxbt/claude-motion | **ADAPT** | Timeline/review discipline, synth SFX idea, sound engine concept |
| haidrrrry/claude-remotion-skill | **REJECT** | Remotion-bound, not reusable here |
| motiondivision/motion | **REFERENCE** | Web animation library; HyperFrames already has GSAP/CSS/WAAPI/animejs adapters |
| mdas | **REJECT** | Shallow; no verified reusable method or clean licence story |
| heygen-com/hyperframes (tag v0.8.114) | **ADOPT selectively** | Official skills at the existing pin, via the existing hash lock |
| remotion-dev/remotion | **DEFER** | No unresolved use case HyperFrames cannot meet; licence tiers apply |
| remotion-dev/skills | **REFERENCE** | Renderer-specific |
| gsap-skills | **REFERENCE** | Already covered; verify licence before any reuse |
| LottieFiles/motion-design-skill | **REFERENCE** | Overlap; Lottie runtime adapter already exists upstream |

## 2. Roadmap

Each item lists: dependencies · files · tests · acceptance · rollback · unchanged.

### P0 — safety or correctness blockers
**None proven by this audit.** One process item to flag, not a code bug: the live tree is dirty and differs from the handoff (HEAD `ec4eb77` vs documented `bd20722`). Ownership of that WIP must be settled before parallel work. [read]

### P1 — small, high-value, same renderer

**P1-1 Extend pinned official skills at the same tag (review first).**
Dependencies: ContentForge confirmation; owner decision on WIP. Files: `config/upstream-skills.lock.json` (via `scripts/upstream_skills.py` only), optionally a short review note. Tests: existing lock-verification tests; hash match. Acceptance: reviewed list of which official skills (e.g. `hyperframes-audio`) to add; `faceless-explainer` excluded until `media-use`/HeyGen sign-in is reviewed. Rollback: revert the lock entry. Unchanged: renderer version, `.claude/skills/hyperframes-*` existing content.

**P1-2 Style cards (`style/1`) + optional `style_fidelity` critic dimension.**
Dependencies: P1-1 not required; design-library validation policy. Files: new `config/styles/` or library entries (**not** `config/*.yaml` gates), critic prompt extension gated on presence of a card. Tests: schema validation; card with missing motion grammar rejected; critic unchanged when no card. Acceptance: ≥3 cards that differ in motion grammar and ≥2 structural axes; none claimed validated until a real render. Rollback: delete cards; flag off. Unchanged: thresholds 7/8.0, E2/E3b.

**P1-3 Creative-decision record + variety report.**
Files: new small module under `contentos/production/`, report script. Tests: deterministic output for fixed input; novelty metric against recent history. Acceptance: record written per video; report shows axes used in last N videos. Rollback: stop writing record. Unchanged: gates.

**P1-4 Advisory style-frame / storyboard checkpoint.**
Dependencies: P1-2, P1-3. Files: step reusing `sheet.py`; approval JSON. Tests: sheet labelled; approval record schema. Acceptance: human can approve or redirect in <2 min; non-blocking. Rollback: skip step. Unchanged: three existing gates.

**P1-5 Additive timeline cues (shadow).**
Dependencies: owner decision on `supplied_audio` WIP. Files: `timeline.py` additive keys. Tests: old timelines still validate; round-trip. Acceptance: cues/markers representable with no composition change. Rollback: ignore keys. Unchanged: `timeline/1` remains shadow.

**P1-6 Seeded-fault harness for gates (student-kit negative controls).**
Files: test fixtures only. Acceptance: each of `motion_audit`, `visual_gate`, new cue check demonstrably fails a known-bad fixture. Rollback: remove tests. Unchanged: thresholds.

### P2 — distinct capabilities needing controlled experiments

**P2-1 Cue-audibility gate** (off by default; needs P1-5, P1-6).
**P2-2 SFX source listening comparison**: claude-motion synth vs Barty CC0 vs HyperFrames bundled; licence check first; blind listening, same mix. Output: a recommendation, not an integration.
**P2-3 Procedural/canvas style experiment inside HyperFrames** (one style card, one fixed script); measured by the bake-off.
**P2-4 Transcript-timed B-roll** using student-kit's review-gated candidates; only if explainer videos need cutaways.

### P3 — expensive, redundant or blocked
- Remotion renderer comparison — only if a measured limitation in P2-3 is attributed to HyperFrames.
- Footage/talking-head editing flows (student-kit's main use) — out of scope for explainers.
- Upgrading HyperFrames 0.8.114 → 0.8.150 — separate, risk-assessed change; not bundled with creative work.
- Object separation, remake mode.

### Never integrate
| Item | Reason |
|---|---|
| `haidrrrry/claude-remotion-skill` | Renderer-locked, unverified |
| `mdas` | No verified method, unclear licence |
| `kie.mjs` (paid/remote generation path) | Paid service; violates no-paid-services |
| Object separation, remake mode | Cost, provenance and fidelity risk |
| `@remotion/transitions` | UNLICENSED |
| Any no-LICENSE repo vendored | Cannot be redistributed |
| Constant camera movement, SFX on every cut, random style rotation | Violates principle 12 |

## 3. Now / after prerequisite / experiment / never / manual

| Bucket | Items |
|---|---|
| **Now (research only)** | This audit; owner decision on WIP; ContentForge status check |
| **After prerequisite** | P1-1 … P1-6 |
| **Experiment only** | P2-1 … P2-4 and the bake-off |
| **Never** | List above |
| **Manual / human** | Style-frame approval; SFX listening; final taste judgement; any gate threshold change |
