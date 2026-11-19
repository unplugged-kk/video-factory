# Implementation plan — phase 2

One plan, ordered by dependency. Nothing here is a creative integration; rule 6 puts P0 correctness first, and the
creative work is gated behind it on purpose.

**Rung vocabulary (rule 4).** Every acceptance criterion names the rung it reaches. Nothing is called done at
READY or IMPLEMENTED.

---

## Dependency graph

```
P0-1 (G-03: bind approval to the render)  <-- needs an OWNER DECISION first
   |
   +--> gates the claim "export is production-ready"

P0-2 (G-01/G-02: export gating)  [DONE, uncommitted, TESTED]

P1-1 (G-07: scrub logs + env allowlist)
   |
   +--> BLOCKS P1-7 (ElevenLabs adapter)      a key in argv would land in logs/*.log

P1-2 (G-05: Lane F gates)   -- independent
P1-3 (G-06: lang doctor probes backend)  -- independent, unblocks honest Hindi status
P1-4 (G-09: resolve the two style vocabularies)  -- independent of P1-1..P1-3
P1-5 (default path picks a style)  -- depends on P1-4
P1-6 (G-04: run spec Gates at export)  -- depends on P0-2

P2-*  -- only after P0/P1 above are closed and verified
```

---

## P0

### P0-2 — export gating (G-01, G-02)

| Field | Value |
|---|---|
| Change | `contentos/export.py`: single `gate_refusal()` for both tracks; `check_gate` on the live digest instead of `approved()` |
| Rung | **TESTED** |
| Evidence | `docs/audit/P0_VERIFICATION.md` P0-A/P0-B; failing-test-before-fix measured in a detached worktree at HEAD |
| Acceptance | the two P0 tests pass; those same tests fail at HEAD; 1,169 suite tests pass; no published artifact appears for an ungated job |
| Rollback | `git checkout -- contentos/export.py tests/` — the change is one function plus a call site; no data migration, no schema change, nothing written to existing jobs |
| Outstanding | **not committed.** Do not let this sit in the working tree — it is the only thing protecting `ready/` right now |

### P0-1 — bind an approval to the published bytes (G-03)

| Field | Value |
|---|---|
| Change | render-sha integrity record + refusal at export (Option D). See `P0_VERIFICATION.md` §Resolution |
| Rung | **TESTED** for the render file; **OPEN** for the two manifest-level bypasses below |

### P0-1b — close the remaining manifest bypasses

> **Status 2026-11-19: IMPLEMENTED and TESTED, both bypasses independently VERIFIED closed**
> (`POTATO_FINAL_SECURITY_REVIEW.md` PF-12, PF-13). The change listed below was *not* the one built: it would
> have been another check against the same editable manifest. Built instead: a `renders` table in the ledger,
> written only by the render stages and `job register`, and an export check (`export.approval_refusal`) that
> reads the ledger and content hashed at export time, never `manifest.json`. Dossier: `P0_VERIFICATION.md`
> section P0-1b. Authoritative status: `MASTER_GAP_REGISTER.md` G-21.

- Removing `source_spec` from a manifest, or repointing it at a pristine copy, still degrades the gate to the
  existence check. Both need a hand-edited manifest, but "needs a hand-edit" is not a security property.
- Change: refuse when a job that has `artifacts.render` recorded also has no `source_spec`, and bind the spec's
  content rather than its path.
- Rung target: **TESTED**, with both scenarios as tests that fail before the change.
| Decision needed | **RESOLVED — Option D was adopted** (adversary §D killed Option C: export never re-renders, so determinism is irrelevant). `pipeline._note_stage` now records `final_video_sha256`; `export.render_integrity_refusal` refuses a swapped file. Implemented + TESTED. |
| Why it blocks | until this closes, a reviewed approval does not guarantee the published bytes are the reviewed ones. That is the definition of not production-ready |
| Acceptance | a hand-replaced `video.mp4` is refused at export, reproducibly; test asserts refusal on state, not message |
| Rollback | n/a (additive digest only; if Option A, existing grants stay valid via the `unbound` path) |

**First task of phase 2:** measure whether HyperFrames re-renders are byte-stable. If they are, Option C is
correct and cheap. If not, Option A is mandatory and the operator workflow changes.

---

## P1 — before any integration

### P1-1 — secret scrubbing and a stage env allowlist (G-07)

- Change: `pipeline.py:25` `ENV = {**os.environ}` → an allowlist; wrap `pipeline.py:76,87` log writes and the
  ledger `error` columns in `storage.scrub`.
- Rung target: **TESTED**.
- Acceptance: a stage that echoes `ELEVENLABS_API_KEY=...` leaves no plaintext in `logs/<stage>.log`, `qa.json`,
  the sidecar or `ledger.db`. Assert by grepping the artifacts for a sentinel value.
- Blocks P1-7. Doing the adapter first would write keys to disk.
- Rollback: revert two functions; no stored data changes.
- **This is the highest-value P1 because it is a precondition, not an improvement.**

### P1-2 — Lane F gates enforce or go (G-05)

- Change: `features/extra_gates.py` returns `FAIL` at its documented thresholds (`END_HOLD_WARN_SEC` is already
  defined and unused), or the layer is deleted from `s_qa`.
- Rung target: **TESTED**.
- Acceptance: a fixture video that holds the end card beyond the threshold FAILs; one under it passes. If deleted,
  `s_qa` no longer reports checks it does not perform.
- Rollback: revert one file.

### P1-3 — `lang doctor` probes the backend (G-06)

- Change: `contentos/lang/doctor` must resolve the configured TTS backend and report NOT READY when it is absent.
- Rung target: **TESTED**.
- Acceptance: with `~/.voice-clone-venv` absent, `hi` reports NOT READY naming `chatterbox_v3`, matching
  `contentos.sh doctor`. Test asserts the reported state, not the string.
- Rollback: revert one module.

### P1-4 — one style vocabulary (G-09)

- Change: `look/1` (30 looks + 27 effects, no consumer) either feeds `visual_style` resolution or is deleted.
  Recommendation: a compile step `look/1` → `scenekit-style/1`, using the existing (uncommitted) translator in
  `contentos/scenekit/lookmap.py`.
- Rung target: **RENDER-VERIFIED** (the only rung that counts for creative work).
- Acceptance: two `look` ids, one script, two visibly different contact sheets, judged by a human. Not a test.
- Rollback: presets are Git data; delete the compile step and the original files are untouched.

### P1-5 — the default path picks a style (depends on P1-4)

- Change: a spec without `visual_style` currently falls to the hardcoded template (`pipeline.py:303-308`). Make
  `auto` selection the default so the normal flow stops producing the bland template.
- Rung target: **RENDER-VERIFIED**.
- Acceptance: the stock `examples/youtube-short.yaml`, unmodified, produces a styled render and the style chosen is
  recorded in the manifest.
- Rollback: the fallback template is still there; revert the default.

### P1-6 — spec Gates run at export (G-04)

- Change: `finalcheck.validate_video` also runs the spec's `features.extra_gates`, so a route skipping `s_qa`
  cannot skip them.
- Depends on P1-2 (a gate that cannot FAIL is not worth running twice).
- Acceptance: a video tripping a Lane F gate is refused by `storage export`.

### P1-7 — ElevenLabs adapter (G-10) — BLOCKED on P1-1

- Adapter under the existing provider abstraction; explicit provider selection only; honest error when the key is
  absent; never a default; never for local jobs.
- Rung target: **IMPLEMENTED + mocked TESTED**. The real API call stays **unverified** until the owner supplies
  credentials, and must be reported as such.
- Rollback: the adapter is additive and unreachable unless named; deleting the module leaves routing unchanged.

---

## P2 — correctness debt, then creative

| ID | Item | Rung target | Rollback |
|---|---|---|---|
| G-12 | two divergent secret redactors (`storage.py:351` ≥12 vs `ui_security.py:11` ≥8) → one | TESTED | revert |
| G-13 | Track B hardcodes `aspect_ratio="9:16"` (`storage.py:492`), so a hand-built 16:9 can never export → probe the real ratio | TESTED | revert |
| G-14 | queue recovery wedges on PID reuse (`queue.py:43`) → heartbeat timestamp | TESTED | additive column |
| G-15 | one YAML edit enables paid providers globally (`providers.py:48`) → require policy **and** flag | TESTED | revert |
| G-16 | `exceptions:` in `local-first-policy.yaml:15` read by nothing → implement or delete | READY→TESTED | revert |
| G-18 | HyperFrames 0.8.114 vs upstream 0.9.66 → read the changelog, then one compatibility render before moving the pin | RENDER-VERIFIED | pin restored |
| G-19 | no beat detection anywhere → `librosa` for lyric/music-driven cutting | RENDER-VERIFIED | new dep, reversible |
| G-20 | "Ayase" does not exist → get the real URL before scheduling work | n/a | n/a |
| G-11 | `yt-dlp` broken (x86_64) → `brew install yt-dlp`, which unblocks reference-video work | EXECUTABLE | uninstall |

**Not in this plan:** Manim, Motion Canvas, Revideo, Lottie, Three.js, p5.js. The research verdict is that only
Manim adds a capability, and none should be adopted until P0/P1 close. Adding a renderer before fixing the gate
would repeat the exact mistake this audit found — a control that exists and does nothing.

---

## Phase 2 exit criteria

1. P0-1 decided and implemented; a hand-replaced render is refused with a state-asserting test.
2. G-01/G-02 committed, not merely present in a working tree.
3. P1-1 done and proven by grepping artifacts for a sentinel secret.
4. No capability marked PRODUCTION-READY that lacks RENDER-VERIFIED evidence.
5. Every fix has: reproduction, failing test before, root cause, change, regression test, independent check.
6. One independent adversary has tried and failed to break each P0.

## What must not happen

No new creative integration lands in phase 2. No gate is weakened to make a test pass. No publishing is enabled.
No user data, generated video, model weight or uncommitted work is deleted. No git history is rewritten.
