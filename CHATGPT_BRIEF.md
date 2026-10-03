# Prompt for ChatGPT: how should a local video stack plug into ContentForge?

You are a senior software architect. Attached is `video-factory-for-chatgpt.zip` (about 1 MB, source and text only). Unzip it with your Python tool and read `MANIFEST.md` first, then the files it points to. Answer the six questions in section 4. Disagree with my recommendations wherever you think they are wrong. Cite file paths for any claim about the code. If you cannot verify something from the files, say so instead of guessing.

## 1. Goal (my words)

"If we can integrate all three tools somehow with ContentForge, then it will be good. I want this as a plugin, or it should be available as an API or something, or some other way that ContentForge can call and do other things, or it can pull in some details and do the job in that way."

The three tools:
1. **contentos** (the `video-factory/` folder in the zip): my local video pipeline.
2. **MoneyPrinterTurbo (MPT)**: open-source tool that makes short videos from stock footage (github.com/harry0703/MoneyPrinterTurbo).
3. **OpenMontage**: open-source, AI-assistant-driven video production system (github.com/calesthio/OpenMontage).

**ContentForge** is my separate content control-plane app (Express 5, React, Postgres/Drizzle, pg-boss, single operator). Only excerpts of it are in the zip.

## 2. What each system is (verified by reading code and running tests, 2026-10-03, unless marked unverified)

**contentos** - local-first YouTube pipeline on an Apple Silicon Mac. Python CLI, no server/API yet.
- Stages: `brief > script > voice > compose > render > qa > package > publish`. Each stage writes an artifact under `workspace/projects/<id>/` and resumes if it exists.
- SQLite ledger (`workspace-samples/ledger-schema.sql`), approval gates (SCRIPT_APPROVED before voice, PRODUCTION_APPROVED before render), local-first provider routing with paid providers blocked by default, 9 ffprobe/ffmpeg QA checks, a SQLite job queue and worker, a read-only dashboard on :4310.
- Voice is Kokoro (local). `publish` is DRY_RUN only: there is no YouTube uploader.
- It has a "Jev" adapter that calls ContentForge's decision API, but that only works with a pasted session cookie (ContentForge answers 401 otherwise).
- Render lane is chosen per spec with `render:`. `hyperframes` (HTML+GSAP to MP4) is the default.
- **MPT lane** (`contentos/mpt.py`): contentos supplies script and Kokoro voice track, MPT (in Docker) sources free stock b-roll, cuts it to the voice, burns subtitles. Driven through MPT's CLI inside its container, because MPT's HTTP API only accepts a custom voice track from inside its own task directory. Paid MPT sources and background music are never passed. Verified end to end with local clips only. UNVERIFIED: the stock sources (Pexels/Pixabay/Coverr), no key is set.

**OpenMontage** - an AI assistant reads its guides and runs one of 13 pipeline definitions (`animated-explainer`, `cinematic`, `clip-factory`, `documentary-montage`, `talking-head`, and others). Running in Docker (its "Backlot" board on :4750). NOT wired to contentos. UNVERIFIED: whether it can run headless with no assistant in the loop.

**ContentForge** (see `contentforge-excerpts/`):
- Already has a Phase 21 `video-factory` provider (`server-content/videoFactoryProvider.ts`) behind its media-provider interface, plus a versioned contract `video-factory.contract.v1` (`videoFactoryContract.ts`) and a filesystem transport (`videoFactoryTransport.ts`). A job folder is dropped into `<VIDEO_FACTORY_ROOT>/queue`; it observes `queue/building/work/done/failed`; it is reconcile-first and reuses the same job id (`cfvg-<generationId>`) on retry; it reads the output mp4 from `done`.
- It was built for an older folder-queue `runner.mjs` (still in the zip). `VIDEO_FACTORY_ROOT` is unset by default and the provider is marked `verified: false`. HTTP transport is documented as "not implemented by the current factory".
- It has a real YouTube upload adapter (OAuth, validation, reconcile; real publish gated by an env flag), approval per exact artifact revision, scheduling, publication with no blind retry after a provider call, a research engine, a decision layer (Jev) with triage, metrics-to-learning loops, an agent tool registry (`registerAgentTools`), and pg-boss jobs.
- I found no route that imports an externally produced video file; video assets come from provider generations.
- `CURRENT_ARCHITECTURE.md` is its authoritative architecture doc.

**An earlier plan** (`contentforge-excerpts/old-production-engine-map/`): "ContentForge V2 - Production Engine (Video Factory)". 17 tickets, all still open. Destination: a standalone, API-first video-production service in its own repository, with ContentForge as one client. Locked decisions Q1-Q16 include: Postgres queue, Kokoro default with no silent voice fallback, ten-validator completion gate, HyperFrames only behind a `render_runtime` seam, subscription-ready core, domain-agnostic. It put "ContentForge's client side" out of scope (since built as Phase 21).

## 3. Constraints I tested on this machine (Docker via "Dory" on Apple Silicon)

1. ContentForge runs in Docker containers (port 3000). A container cannot reach a host service through `host.docker.internal`: connection refused, even when the host service binds `0.0.0.0`.
2. A container CAN reach the Mac's Tailscale IP, and bind mounts work.
3. Host to container published ports work (contentos can call ContentForge on localhost:3000).
4. ContentForge auth is session cookie plus CSRF only. There are no service tokens.
5. The Mac is a laptop and may sleep.

## 4. The six questions (my recommended answer follows each; challenge it)

**Q1 - What is "Video Factory" now, and what happens to the old map?** Three things carry the name: legacy `runner.mjs`, contentos, and the standalone service in the old map. Options: (a) re-baseline: "Video Factory" is the role, contentos is its implementation, the old map is closed as superseded, and its still-valid decisions carry over (Kokoro default, no silent voice fallback, ten-validator gate, provider-agnostic render runtime where MPT and OpenMontage plug in); (b) continue the old map unchanged, with contentos, MPT and OpenMontage as runtimes inside its new service; (c) keep both and treat this as a small bridge. My recommendation: (a).

**Q2 - Private executor or product?** The old map locked "ContentForge is one client among several; subscription-ready (identity, keys, plans, quotas)". Options: (a) private single-operator executor with an API shaped for ContentForge and my CLI, keeping an auth seam and "the engine never knows billing exists" but dropping plans, quotas and key management; (b) keep multi-client and subscription-ready. My recommendation: (a).

**Q3 - What can ContentForge call ("do other things"), and what does "pull" mean?** Beyond `generate_video`: (1) research dossiers and competitor teardown; (2) packaging: hook scoring, titles, descriptions; (3) QA of any mp4; (4) analytics ingestion; (5) capability discovery. On "pull": either ContentForge pushes everything a job needs in a bounded payload (contract v1 does this) and then polls status and fetches output, or the factory also pulls context (brand voice, evidence ids) from ContentForge. My recommendation: v1 is `generate_video` plus status, artifact, QA report and capability discovery. ContentForge pushes everything; the factory never reads ContentForge's database. Research, packaging and analytics become later job kinds on the same contract.

**Q4 - Where does ContentForge run, and is the Mac always on?** Today ContentForge runs in Docker on this Mac and the factory is native on the Mac. A `docker-compose.vps.yml` exists in ContentForge and the Mac is on Tailscale. Options: (a) Docker on this Mac only; (b) ContentForge moves to a VPS soon; (c) must work both ways. My recommendation: (c). Jobs wait durably while the Mac sleeps and none are lost. Transport is a shared folder now and HTTP over the tailnet when ContentForge is remote.

**Q5 - OpenMontage: in the first slice or after?** It is assistant-driven, so it cannot be called like MPT. Options: (a) after: first slice is the contentos lanes (hyperframes and MPT) and OpenMontage stays unscheduled until a research step proves it can run headless and shows what auth and cost that needs; (b) in now: the factory spawns a headless assistant session per job, which costs tokens; (c) a manual lane only: the job parks at "needs human" until I drop the video in. My recommendation: (a), with that research step created now.

**Q6 - Where does the effort end?** Options: a build-ready spec only (contract versioning, transports, auth, lane model, governance mapping, rollout order), or that plus one thin-slice prototype (Phase 21's provider driving contentos to one real mp4). My recommendation: spec plus the one prototype, because it finally verifies Phase 21 against a real factory.

## 5. What I want back

1. For each question: pick an option or propose a better one, with the reason and the main risk.
2. One recommended end-state architecture, drawn in text, including which side initiates each call and which transport carries it.
3. A phased rollout where every phase ships and verifies on its own.
4. The five riskiest assumptions and a cheap test for each.
5. Anything in the attached files that contradicts what I wrote above.
