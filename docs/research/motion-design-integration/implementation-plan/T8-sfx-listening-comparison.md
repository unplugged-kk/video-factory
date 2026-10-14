# T8 — SFX source comparison (licence table + blind listening sheet; human-in-the-loop)

**Goal:** decide *whether and from where* to source sound effects, using licences first and a blind listening test second. Output is a **recommendation memo**, not an integration. Haiku prepares the paperwork; **the owner listens and decides.**
**Prereq:** T0 CLEARED; T5 DONE helpful but not required. Owner approval to download anything (see Step 3).
**You create:** files under `docs/research/motion-design-integration/sfx-comparison/` only, and scratch audio under `$HOME/audit-scratch/t8/`. **You modify:** nothing.

## Candidates
1. **Synth** — the idea from `whaleyxbt/claude-motion` (generate simple SFX with code). *Reference only; write your own tiny generator using Python stdlib `wave`+`math`, original code, no copied code.*
2. **Barty** SFX library (`Barty`, commit `d6e5d95…`) — claimed CC0; **verify per file**.
3. **HyperFrames bundled** audio assets inside the pinned tag (see T1 note) — verify licence.

## Steps
1. Snapshot `before-T8.txt`.
2. **Licence table first** (`sfx-comparison/01-licences.md`): for each candidate source: repo LICENSE text (quote the first lines), per-asset licence/attribution statements, whether attribution is required, whether commercial use/monetised YouTube is allowed, whether redistribution inside our repo is allowed (we will **not** vendor; note it anyway), and URLs/file paths as evidence. If any licence is unclear for the assets you'd use → mark **EXCLUDE** and stop work on that candidate.
3. **Owner checkpoint:** ask the owner "May I download the specific permissively-licensed files listed in 01-licences.md into `$HOME/audit-scratch/t8/`?" Do not download before a yes. Downloads: `git clone --depth 1` of the repo into scratch only (no execution of anything in it). No paid sources.
4. Pick **one** fixed narration clip (≈20 s) already in the workspace (a previous job's `voice` audio — copy to scratch; do not edit the original). Pick **6 moments** in it (word times from that job's `captions/word-timings.json` or `audio/timing.json`).
5. Build three versions of the same clip with identical cue timing: same 6 cue times, same `max_cues_per_minute`-style budget, each version using one source (choose the closest-sounding SFX per moment from that source). Mix with the same fixed gain relation: cues at −18 dBFS RMS target under the voice (write the gain math down). Use ffmpeg `amix`/`adelay` in scratch; **no change to repo code**. Also write voice-only and cues-only stems for each version (needed by T7).
6. Blind the files: copy to `A.wav`, `B.wav`, `C.wav` with a random assignment; keep the key in a separate file `sfx-comparison/KEY-do-not-open.txt` (owner opens it after listening). Create a fourth `D.wav` = no SFX (control).
7. Create `sfx-comparison/02-listening-sheet.md`: for each of A, B, C, D the owner rates 1–5 on: *helps me notice the reveal*, *distracting*, *sounds cheap*, *competes with voice*; plus "would you publish this?" yes/no; free text.
8. If T7 exists, run `cue_audibility` on each version's stems and put the table in `sfx-comparison/03-measured.md` labelled "provisional proxy".
9. **STOP.** Report to the owner: "Please listen and fill 02-listening-sheet.md." The recommendation memo (`04-recommendation.md`) is written **after** the owner returns the sheet, by a new session: it states the winner **only** if the sheet supports it, otherwise "no clear winner" or "no SFX".
10. Verify: snapshot diff identical (only docs untracked); no audio files in the repo (`git status --porcelain | grep -E '\.(wav|mp3|mp4)'` prints nothing; `find docs -name '*.wav'` prints nothing).

## Acceptance
Licence table complete with quoted evidence; blinded files + key + sheet created; nothing audio in repo; recommendation memo deferred until owner input.

## Rollback / Do not
`rm -r docs/research/motion-design-integration/sfx-comparison $HOME/audit-scratch/t8`. Do not vendor audio into the repo; do not pull assets with unclear licence; do not choose a winner yourself; do not add SFX to any production pipeline or template.
