# Master capability matrix

Status ladder: EXISTS → INSTALLED → CONFIGURED → EXECUTABLE → TESTED → RENDER-VERIFIED →
VISUALLY VERIFIED → QUALITY-APPROVED → PRODUCTION-READY. A row stops at the first rung it cannot prove.

**Revised 2026-11-18 after an adversarial review (`POTATO_CHALLENGE.md` §E) found this table inflated.** Five rows
were marked PRODUCTION-READY on the strength of passing tests plus existing video files. Passing tests prove
TESTED, not PRODUCTION-READY; a video existing proves RENDER-VERIFIED, not QUALITY-APPROVED. The honest count of
PRODUCTION-READY capabilities is **0**, because no capability here has a documented independent quality approval
and the export gate still has open bypasses (see `P0_VERIFICATION.md`).

| # | Capability | Rung (revised) | Was | Evidence |
|---|---|---|---|---|
| 1 | HyperFrames render lane | **RENDER-VERIFIED** | ~~PRODUCTION-READY~~ | `doctor` PASS; 9 `ready/` videos produced through it |
| 2 | English TTS (Kokoro) | **RENDER-VERIFIED** | ~~PRODUCTION-READY~~ | `doctor` PASS; audio in shipped jobs. No listener approval |
| 3 | Track A pipeline (brief→export) | **RENDER-VERIFIED** | ~~PRODUCTION-READY~~ | full suite green; 9 videos. No quality approval |
| 4 | Export into `ready/` + sidecar | **TESTED** | ~~PRODUCTION-READY~~ | 3 state-asserting P0 tests + failing-at-HEAD proof. Open bypasses remain |
| 5 | Technical QA (9 checks) | **TESTED** | ~~PRODUCTION-READY~~ | re-run at export via `finalcheck`; no negative-control video |
| 6 | Approval gates (script, production) | **TESTED** | TESTED | digest binding enforced at export; `test_approval_binding.py` |
| 7 | Render integrity (video sha) | **TESTED** | (new) | `test_export_refuses_a_swapped_render`; fails at HEAD |
| 8 | Publishing | **CONFIGURED** (disabled) | same | `publish.enabled: false`; dry-run record |
| 9 | `look/1` presets (30 + 27 effects) | **EXISTS** | same | validated by `contentos.sh looks validate`; **no render-path consumer** |
| 10 | `visual_style` → scenekit (6 styles, 18 grounds) | **VISUALLY VERIFIED** | (new row) | 7 contact sheets inspected; 4 styles visibly distinct |
| 11 | Default path picks a style | **EXISTS (absent)** | same | no `visual_style` → hardcoded template `pipeline.py:303-308` |
| 12 | `sceneplan/1` validation | **TESTED** | same | `test_director.py`, `test_direction.py` |
| 13 | Track B hand-built composition | **TESTED** | ~~VISUALLY VERIFIED~~ | register/export path tested. **No manifest on disk has `"track": "B"`** - the visual claim was unsupported |
| 14 | ASR / word alignment | **EXECUTABLE** | same | whisper.cpp 1.9.5 + 3 models; `test_lang.py` 63 pass |
| 15 | Hindi TTS | **EXISTS** | same | `chatterbox_v3` route configured; **backend not installed** |
| 16 | Hindi / Hinglish production | **RENDER-VERIFIED** | same | 5 Hindi sample renders exist. No listener test |
| 17 | Odia | **NOT READY** | same | missing model + HF terms |
| 18 | ElevenLabs TTS | **EXISTS (help text only)** | same | no adapter; `cli.py:13` advertises one |
| 19 | Remotion lane | **INSTALLED** | same | not exercised |
| 20 | MPT lane | **NOT_INSTALLED** | same | docker refused |
| 21 | Job queue + worker | **TESTED** | TESTED | queue tests; PID-reuse wedge open (G-14) |
| 22 | Batch / concurrent jobs | **TESTED (unit only)** | ~~TESTED~~ | locks tested in isolation; **no real multi-job batch run** |
| 23 | ContentForge worker | **TESTED** | same | 66 Node tests incl. Hindi/Odia paths |
| 24 | Creator Studio | **EXISTS** | same | `ui_api.py`; **no Studio journey run**; export-over-HTTP unverified |
| 25 | yt-dlp research / reference video | **NOT_INSTALLED** | same | `Bad CPU type in executable` |
| 26 | Creative skill library (79) | **EXISTS** | same | hash-verified; readiness per recipe unaudited |
| 27 | Thumbnails | **EXISTS (incomplete)** | same | — |
| 28 | Niche discovery / analytics | **EXISTS (foundations)** | same | `learn.py`; no real metrics ingested |

## Counts (corrected)

- Rows: **28** (the previous table said "30 inventoried" against 27 listed rows - both were sloppy)
- PRODUCTION-READY: **0**
- QUALITY-APPROVED: **0**
- VISUALLY VERIFIED: **1** (scenekit styles - the only claim backed by frames I actually looked at)
- RENDER-VERIFIED: **4**
- TESTED: **8**
- EXISTS or lower: **15**

## What this table says about the audit itself

The system is further along than "a pile of dead config": 6 working visual styles, 1,172 passing tests, 9 shipped
videos, a real gate mechanism. It is also further from production than my first table implied, because nothing
here has been quality-approved by anyone other than the agent that built it.

The corrected number to act on is **0**, and the answer to "is this production-ready" is: not yet, and
`P0_VERIFICATION.md` lists exactly what is missing.
