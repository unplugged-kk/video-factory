# Report: what exists, what I chose, what is left

## 1. Existing system inventory (what I found, not assumed)

| Repo / path | What it is | Use here |
|---|---|---|
| `~/git/ContentForge` | TS/Express/Postgres growth app. Research providers (rss, reddit, youtube, hn, web, video), stories, artifacts, publications, experiments, learning. **Jev decision engine** in `server/decision/*` with ledger, 10 decision types, flags | Owns decisions, research, performance feedback, multi-platform publication. Do not duplicate |
| `~/git/ContentForge/JEV_DECISION_MAP.md` | Authoritative Jev status. Only `research_triage` and `format_select` active in prod; quality/publish/opportunity gates built, flags off | Integration contract |
| `~/git/MoneyPrinterTurbo` | MIT, topic to stock-footage short. Cloud TTS (edge/azure/gemini/siliconflow) | Optional backend only |
| `~/git/openshorts` | long video to Shorts | Use for repurposing, do not rebuild |
| `~/git/postiz-app`, `OpenCut`, `clipbrain`, `AI-Content-Studio`, `metube`, `reclip` | posting, editor, misc | Keep |
| `~/git/hermes/*` | Agent OS / mission control UIs | Future consumer of the registry |
| old `video-factory.zip` | hyperframes render queue (works: 35 s per reel). Voice step depended on a chatterbox venv that no longer exists | Superseded by `contentos`; reuse its idea of a queue later |

Why the old factory "did not work" today: voice step points at `~/.voice-clone-venv` and
`~/Desktop/voice-sample.wav`, both missing, and ffmpeg in `/usr/local/bin` is a dead x86 binary.

## 2. Decisions

**Core engine = hyperframes.** One tool gives render + lint + local Kokoro TTS + whisper.cpp transcribe.
OpenMontage (AGPL-3.0) itself calls `npx hyperframes`, so we share the renderer without copying AGPL code.
**OpenMontage**: architecture reference only (stage contracts, checkpoints). **MoneyPrinterTurbo**: optional, fails local-first on voice.
**Rejected for now**: whisperX (not needed), Remotion (hyperframes covers it; license check first).
**Deferred**: youtube-niche-finder (5 stars, needs Postgres), pauling youtube-mcp-server (needs OAuth).
The first pasted research list was not inspected beyond the repos named in `research/tool-catalog.yaml`; entries under `unverified_from_pasted_research` are unverified.

## 3. Jev integration (adapter built; real engine not yet exercised)

Jev stays in ContentForge. `contentos` calls it, it never reimplements it:

```
contentos stage -> POST ContentForge /api/decision/... {type, state, refs}
                <- DecisionResult {decision, confidence, reasons, policyId, fallback}
contentos acts only after its OWN gates (config/execution.yaml approval_gates) pass
```
Rules inherited from `JEV_DECISION_MAP.md`: Jev is soft-level, never authorizes execution, ledger rows carry owner.
Mapping: `opportunity_score` before brief, `quality_gate` before package, `publish_gate` before publish (flag currently off),
`format_select` for Shorts vs long. Needs `CONTENTFORGE_URL` (doctor already probes it) and an auth token. Open question for you:
which ContentForge instance/URL and which user owns the ledger rows.

## 4. M5 Pro measurements

| Test | Result |
|---|---|
| hyperframes doctor | Chrome, ffmpeg, Docker OK; 24 GB RAM but only ~4.6 GB free at test time |
| Kokoro cold first call | 34 s (includes model download) |
| Kokoro warm | 18.7 s for 5 lines (~3.6 s/line), includes loudnorm |
| Render | 9.8 s for 24.1 s, 1080x1920, 30 fps |
| Full pipeline from clean workspace | 31 s wall |
| QA on output | all PASS except frozen_frames WARN; loudness -12.1 LUFS, peak -1.4 dBFS |
| Not measured | whisper.cpp, chatterbox, ollama, MoneyPrinterTurbo, OpenMontage, GPU/CPU utilisation, memory per stage |

## 5. Next engineering tasks (ordered)
1. Real template: word-level captions via `hyperframes transcribe`, brand fonts/colors, motion. Judge by eye, current output is bland.
2. LLM provider: wire ContentForge gateway (`AI_BASE_URL`) so script/hook generation runs from a topic, not a supplied script.
3. Jev adapter (section 3).
4. YouTube OAuth + `videos.insert` adapter, private only, behind PUBLISH_APPROVED. Note: unverified API projects force private until audit.
5. Analytics: Analytics API for targeted queries, Reporting API into Postgres. Evaluate pauling MCP server first.
6. Niche research: evaluate youtube-niche-finder in a sandbox vs ContentForge's existing research providers.
7. Rights manifest per external asset before any stock/footage retrieval.
8. VPS worker + n8n nightly research (needs the VPS host in `config/execution.yaml`).
9. Remove stale x86 binaries in `/usr/local/bin`.

## 6. Done in round 2
- `contentos/jev.py` adapter + local `decisions` table (source jev|local_fallback), `contentos/learn.py` loops 2,3,4,5,6,7,8,9,10 as read-only analysis.
- Loops 1 (niche intelligence) and the data side of 4/5 need YouTube analytics ingestion, which does not exist yet.
- Caught by the recommender: the first smoke script hook scored 33 WEAK; rewritten to 74 STRONG, recommendation flipped REVISE to PUBLISH.
- Still not run: OpenMontage, MoneyPrinterTurbo, chatterbox, ollama, other TTS engines. Opportunity weights in `learn.W` are my defaults, not fitted to data.
