# T9 — Bake-off runbook: Baseline vs Variant A (human-in-the-loop)

**Goal:** measure whether adding style card + decision record + style-frame checkpoint (Variant A) improves finished videos versus today's pipeline (Baseline), using the **same** renderer and gates. Spec: `06-bakeoff-specification.md`. **Haiku does not decide who wins.** No winner may be claimed without actual renders and the owner's blinded review.
**Prereq:** T0 CLEARED, T2, T3a, T4 DONE (T5–T8 optional). Owner approval to proceed and to spend local compute time (free; no paid services).
**Roles (strict):** *Builder session* builds a video. *Critic session* (a **different** session/agent that did not build it) scores it. *Owner* approves gates and does blinded review. The same session must never build and critique the same video.

## 0. What Haiku may and may not do here
- May: create folders, scripts under `docs/research/motion-design-integration/bakeoff/`, run the existing documented commands exactly as `AGENTS.md` §3 describes, collect measurements, produce tables.
- May not: change any code/config, skip a gate, use `--approve-private` unless the owner explicitly says "run unattended", publish, run paid sources, or grade its own build.

## 1. Preparation
1. Snapshot `before-T9.txt`.
2. Owner picks **3 scripts** of different content types (e.g. architecture lesson, historical explainer, product/launch). Each approved at `SCRIPT_APPROVED` once, then **voice generated once per script and reused** across arms (copy the audio into both arms' job folders so narration is byte-identical).
3. Create `bakeoff/` in the docs folder with: `plan.md` (the three scripts, content types, the job ids below), `results.md` (empty table), `reviewer-sheet.md` (copy of the checklist from `06-bakeoff-specification.md` §5), `key-do-not-open.txt`.
4. Job ids: `bo-<script>-base` and `bo-<script>-a` (e.g. `bo-dns-base`, `bo-dns-a`), six jobs total, all matching `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`.
5. Confirm free local capability: `./contentos.sh doctor`; `./contentos.sh storage paths --check`. Anything `NOT_INSTALLED` → report, stop.

## 2. Baseline arm (per script)
Follow `.claude/skills/video-production-orchestrator/SKILL.md` exactly as today: `video-director` plan → `direction validate` → `director check` → compose → **GATE 2 (owner)** → render → `qa` → `preview --sheet` → export is **not** required for the bake-off (stop before export; no publish).

## 3. Variant A arm (per script) — the only differences
1. Write the brief JSON; run `python -m contentos.intelligence.creative propose --brief …`.
2. Owner picks/overrides; run `creative record … --out <workspace>/bakeoff/<job>.decision.json` (outside the repo; record rejections).
3. Plan with the chosen **style card** as an extra input to the director step (paste the card's axes, motion forbids, frame checklist into the director's brief). The plan must still pass `direction validate` and `director check` unchanged.
4. Make 3–5 style frames (existing tools: `./contentos.sh preview …` or a single composed scene); `checkpoint request …`; **owner** runs `checkpoint decide … --human`. If `redirect` → revise and re-request; count the loops (a cost metric).
5. Then identical to Baseline from compose onward (same renderer, gates, R1–R6).

## 4. Measurements (fill `results.md`; one row per job)
Automatic: `qa` table; `motion_audit` numbers (ease inventory, `pop_count`, `still_fraction`) via its documented CLI/functions; Rule A/B result (`visual check`); `visual_gate` results; critic report JSON checked by `python -m contentos.production.critic report.json`.
**Critic variance:** the critic session scores each video **3 separate times** (fresh sessions); record all three; report mean and spread (max−min) per dimension. A baseline-vs-A difference smaller than the spread is "no measurable difference".
Cost: wall-clock minutes, agent turns (approx), human minutes at gates, revision loops, retries.
Variety: `creative report --history <dir of the 3 Variant-A decision records>`; for Baseline, record by hand the six axes of each video (owner confirms) so both arms are compared on the same variety measure.

## 5. Blinded human review
Copy each rendered MP4 to `bakeoff/review/` under neutral names (`V1.mp4`…`V6.mp4`, random order, key saved separately). Owner fills `reviewer-sheet.md` per video and does pairwise "which would you rather publish" per script (base vs A). Owner may open the key only after finishing.
(MP4s are media: they stay in `$VIDEO_FACTORY_WORKSPACE`; the repo folder holds only sheets and tables. Provide the workspace path to the owner.)

## 6. Decision (owner, using spec §6)
Fill the six go/no-go criteria in `results.md` with the measured values. Haiku writes "criterion met / not met / not measurable" and the numbers; the **owner** writes the final ADOPT / DO NOT ADOPT line.

## 7. Verify
`snapshot` after → only `docs/…/bakeoff/` untracked additions; no media in repo; `pytest tests -q` unchanged; ledger/workspace changes are expected **only** under `$VIDEO_FACTORY_WORKSPACE` and the publishing library's `ready/` is **not** touched (we stop before export).

## 8. Acceptance
All 6 jobs rendered or a documented reason; 3 critic scorings per video; results table complete; blinded sheet returned by owner; owner's decision line present. If anything cannot be run (e.g. ffmpeg `drawtext` missing for labelled sheets) → say so, use the documented alternative (`preview --sheet`), never fake it.

## 9. Rollback / Do not
`rm -r docs/research/motion-design-integration/bakeoff`; renders live in the workspace and can stay or be deleted by the owner (Haiku never deletes workspace files). Do not claim Variant A "won" from your own impression; do not modify styles or thresholds after seeing results; do not start the conditional procedural-style or renderer experiments.
