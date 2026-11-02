# Capability inventory (Phase 1)

Status key: IMPL = code exists and is wired; PARTIAL; EXPERIMENTAL (opt-in/shadow); PARKED (owner decision); NOT IMPL. "Verified" below means read in source, not executed.

| Capability | Status | Evidence |
|---|---|---|
| Environment check (`doctor`) | IMPL | cli.py `cmd_doctor`: per capability, selected provider and PASS/OPTIONAL/NOT_INSTALLED with a fix hint |
| Provider routing (`route`) | IMPL | providers.py `select`, config/providers.yaml (tts, stt, render, llm, youtube_read, publish_youtube, decision) |
| Track A pipeline | IMPL | pipeline.py stages; `pipeline run SPEC --force --only --allow-paid --approve-private` |
| Approval gates | IMPL | `approve ID GATE`, digest-bound; gates RESEARCH/SCRIPT/PRODUCTION/PUBLISH |
| Shared production core (retries, failure class) | IMPL | production/core.py: transient (voice, compose, render), output, blocked; 3 tries, wall cap 360 s; one JSON line |
| Queue + worker | PARTIAL | queue.py: jobs table, concurrency default 2, no timeout/retry/process-group kill (per discovery notes), "nothing has run concurrently" |
| Track B job registration | IMPL | `job register PATH --track B` |
| QA of a video | IMPL | `qa VIDEO --format`, nine checks |
| Preview frames and contact sheet | IMPL | `preview TARGET --at --out --sheet` |
| Standalone visual gates, critic validation | IMPL as CLIs, not pipeline-wired | production/visual_gate.py, critic.py |
| Research, competitor, learn, recommend, Jev | IMPL (network/LLM side effects possible) | cli.py; Jev reachable but needs cookie per earlier notes |
| Renderers: HyperFrames (default), Remotion, MPT | HyperFrames IMPL; `pipeline.RENDER_LANES` accepts Remotion and MPT through `spec.render` | All three are registered and reachable in code; the operator contract documents HyperFrames and MPT, and Remotion/MPT operational status was NOT verified here. The first UI slice exposes HyperFrames only |
| Kokoro TTS, whisper.cpp STT | Declared in providers.yaml as local_oss; operational status needs `doctor` on the Mac | NOT run |
| M2 feature hooks (audio bed, phrase captions, backdrops, scene plan, style card, extra gates) | EXPERIMENTAL, opt-in via spec | contentos/features/*, tests test_feature_*.py |
| Publishing | NOT IMPL (dry run; always blocked) | pipeline.s_publish |
| ContentForge exchange (`factory-worker`, CONTRACT v1) | PARKED | adapters/v1/*.mjs; probable `findJobDir` day-folder defect noted earlier |
| Web UI | PARTIAL | read-only dashboard only |

## Job contracts
- `VideoFactoryJobRequest`: absent from this repository. A literal search across `contentos/`, `docs/`, `config/`, and `examples/` returned no definition or schema with that name.
- ContentForge v1: the implemented external contract is `contractVersion: video-factory.contract.v1`, validated and adapted in `contentos/adapters/v1/contract_adapter.mjs`. Fields validated: contractVersion, jobId `^cfvg-[1-9][0-9]{0,9}$`, format 9:16 or 16:9 (1:1 rejected), voice.id in a 12-voice Kokoro allowlist (default af_heart; voice.enabled=false rejected), render.quality draft|medium|high -> HyperFrames draft|looks|delivery, title, brief (required), script/storyboard -> scene derivation, advisory durationMs. Errors are permanent with codes (invalid_contract, unsupported_contract_version, invalid_job_id, unsupported_format, invalid_voice, voiceless_not_supported, unknown_voice_id, invalid_render_quality, missing_brief, empty_derivation).
- Track A spec: YAML with content_id, title, format, voice, script (list of lines); template in docs/AGENT_BRIEF.md section 4 and `examples/`.
- Because ContentForge is parked, the UI's own job-creation path should target the Track A spec, not the v1 contract.
