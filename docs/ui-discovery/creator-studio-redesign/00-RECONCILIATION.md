# 00 / Reconciliation

**Research date:** 2026-11-24. **Scope:** `main` at `8709b0b`, Studio and its production dependencies. Evidence: `node --test contentos/ui/*.test.mjs` (25 passed); `~/.contentos/venv/bin/python -m pytest tests/test_ui_api.py tests/test_videojob.py -q` (53 passed). No production job or browser run performed. “Verified” is limited to the test scope noted below.

| Capability | Classification | Evidence and boundary |
|---|---|---|
| Local Studio shell, job list/detail, spec validation/create | IMPLEMENTED AND VERIFIED | `contentos/ui/{main,api}.js`, `contentos/ui_api.py:dispatch`; `test_spec_validate_create_collision_and_draft_read_model`. YAML/JSON spec authoring is not topic-to-script generation. |
| Health, capability registry, logs, bounded media, event refresh | IMPLEMENTED AND VERIFIED | `tests/test_ui_api.py`: health readiness, canonical registry, range, log scrub, event invalidation. Events are a reread hint, not authoritative progress. |
| Track A orchestration | IMPLEMENTED AND VERIFIED | `contentos/pipeline.py`, `test_run_route_uses_saved_workspace_spec_without_approval_shortcuts`; earlier real HF fixtures in `docs/audit/CREATIVE_QUALITY_RESULTS.md`. Fixtures are not all-platform proof. |
| Script/production review | PARTIALLY IMPLEMENTED | `ui_api.py:_approve` requires `seenDigest`; `test_approval_is_digest_bound_and_publish_gate_is_not_exposed`. `_approve` records the channel label `creator-studio` after comparing a read-model digest; it does not authenticate a human or compare and grant atomically. Legacy unbound-only grants can pass pipeline stage gates with a warning, but `export.py:approval_refusal` already rejects them. CLI mandatory confirmation, atomic sealed subjects and supersession are not active (`docs/audit/APPROVAL_POLICY.md`). |
| Track B | MANUAL HANDOFF | `contentos/track_b.py`, `ui_api.py:_track_b`, `tests/browser/studio.spec.js`. Plan validation and staged operations exist; agent builds composition; not an automatic scene-plan renderer. |
| QA, export preview and per-job export | IMPLEMENTED AND VERIFIED | `ui_api.py:_export_preview/_export`, `tests/test_export_security.py` (inspected), prior run receipts in `docs/project-intelligence/VERIFICATION_EVIDENCE.md`. A WARN differs from not run; export is not upload. |
| Queue, single job retry, worker | IMPLEMENTED AND VERIFIED | `contentos/queue.py:claim/recover/work/requeue`; write-contract and held-lock tests. Studio does not start/stop a worker. No independent batch object or UI concurrency control. |
| HyperFrames | IMPLEMENTED AND VERIFIED | Prior fixture evidence `docs/audit/CREATIVE_QUALITY_RESULTS.md`; does not establish sealed rendering or creative acceptance. |
| Remotion | IMPLEMENTED BUT NOT VERIFIED OPERATIONALLY | `contentos/renderers/`; executable path and project compatibility are different, see `docs/audit/PHASE_2_RUNTIME_READINESS.md`. |
| MPT | BLOCKED (real runtime here) | `contentos/mpt.py`, `tests/test_mpt.py` staged-local contract; render-time stock rejected, real container consumption not verified, live-mount race remains. |
| OpenMontage | MANUAL HANDOFF | `docs/CAPABILITIES.md`, `contentos/videojob.py`; no native render lane. |
| Looks, effects, creative recipes | PARTIALLY IMPLEMENTED | `config/presets/`, `contentos/skills/library/`, `contentos/scenekit/lookmap.py`; 17/30 compiled in prior checkpoint, not a builder style guarantee. Recipe discoverability is not installed runtime support. |
| English/Hindi/Hinglish voice | PARTIALLY IMPLEMENTED | `contentos/lang/`, `tests/test_lang.py`, prior English Kokoro and Hindi Chatterbox offline WAVs. Hindi/Hinglish quality and toolchain portability not accepted. Odia BLOCKED. |
| Assets / uploads | PARTIALLY IMPLEMENTED | `contentos/production/assets.py` indexes local media; not a Studio upload manager. MPT staged clips are a lane-specific exception, not general asset import. |
| Reference analysis | EXPERIMENTAL | `docs/CURRENT_STATE.md` §10, `docs/ROADMAP.md` P1-3; local frame/metadata review is not rights clearance, semantic reconstruction, or an end-to-end recreation pipeline. |
| Podcast/talking head, lyric engine | PLANNED | `contentos/videojob.py` explicitly marks the two engines planned. Manual edit is not an automated route. |
| Independent batch, campaign inheritance, fleet/agents, publishing | NOT IMPLEMENTED | `ui_api.py:dispatch` has no grouping, membership, agent control or publish endpoint. Queue and log rows do not imply those entities. |

**Sources:** `AGENTS.md`, `README.md`, `docs/{CURRENT_STATE,CAPABILITIES,ROADMAP}.md`, prior `docs/ui-discovery/creator-studio/` (especially rollout, API contract, evidence ledger), and named source/test anchors above. Earlier “implemented” labels omitted runtime/rights distinctions; keep them scoped. Existing browser suite covers fixture keyboard, theme, mobile and Track B intake, not actual production.

**Assumptions:** local-first and one operator remain binding. **Open questions:** live worker/readiness signals, asset import contract, and preview fidelity need future verification; do not expose unverified features as runnable. Next: [requirements](01-PRODUCT-REQUIREMENTS.md).
