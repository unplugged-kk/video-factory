# 06 - Implementation plan, risks and blockers

## Milestones with acceptance tests
| Milestone | Build | Done when (verifiable) |
|---|---|---|
| **B** Local prototype | Scene-plan schema + compiler to HyperFrames; one original 45 s English tech explainer (original script, Kokoro narration, word-synced captions, motion graphics, end card) | MP4 exists, ffprobe shows 1920x1080, 30 fps, h264+aac, duration within 30-60 s; `contentos qa` passes; contact sheet of frames reviewed by me and by you |
| **C** Quality + formats | Extend `qa.py` (caption timing, safe areas, asset rights, loudness/clipping, repeat detector, first-frame check), preview frames, review report; 9:16 reframe from the same plan | Master 16:9 and a 9:16 version from one plan; QA report lists every check with PASS/WARN/NEEDS_HUMAN; deliberately broken fixtures make each check fail |
| **D** More formats | 3-5 min narrated explainer; one music/story workflow using rights-cleared audio (YouTube Audio Library or ACE-Step instrumental, no third-party song) | Both render and pass QA; rights ledger complete |
| **E** Factory | Templates for the eight formats, localization layer (glossary, pronunciation dictionary, subtitle validator), manifests, version snapshots, job recovery tests, `factory-*` skill pack, `CLAUDE.md`, publish-blocking hook | Kill a render mid-run and resume; skills load in a fresh Claude Code session; test suite green |
| **F** Publish + measure | Upload-ready packages; YouTube private upload adapter and analytics read once OAuth exists; docs for other platforms | Package validates; a private test upload succeeds (needs your OAuth) |

## Language plan (benchmark before promising)
1. English: Kokoro + English whisper (works today).
2. Hindi: add a multilingual whisper model for ASR; benchmark Kokoro Hindi voices (grade C) by ear and via round-trip transcription; fall back to Indic Parler-TTS if poor.
3. Odia: Indic Parler-TTS only (needs your Hugging Face gate acceptance); ASR via IndicConformer for QA round-trips. Both unproven on this Mac. Each language needs a native-speaker review step; I cannot judge Odia or Hindi naturalness myself.

## Risks
| Risk | Mitigation |
|---|---|
| YouTube treats templated AI videos as inauthentic content | Vary format, scripts, visuals; repeat-detector; fewer, better videos; no revenue claims |
| Hindi/Odia voices sound poor or mispronounce technical terms | Pronunciation dictionary, human review gate, publish English first |
| 24 GB unified memory pressure with local models | One heavy model at a time; queue concurrency 1 for generation stages |
| Unknown platform terms (music, AI labels on TikTok/Meta/X/LinkedIn) | Listed as unresearched in 03; research before enabling each platform |
| Upload-lock behavior for YouTube API unknown | Test with a private upload first |
| ContentForge branch has 37 uncommitted files | Integrate only through the exchange folder; never switch its branch |

## Blockers and exact actions required from you
Nothing blocks Milestones B-D. These unblock later work:
1. **Hugging Face account:** log in and accept the gated terms for `ai4bharat/indic-parler-tts` and `ai4bharat/indic-conformer-600m-multilingual` (only you can accept; needed for Odia).
2. **YouTube OAuth (Milestone F):** create a Google Cloud project, enable YouTube Data API v3, create an OAuth client, save the JSON to `~/.contentos/secrets/youtube-oauth.json`. Nothing publishes without PUBLISH_APPROVED.
3. **Rights decisions:** name any songs, podcast clips or voices you own or are licensed to use; until then the lyric and podcast templates run on original or Audio Library material only. Decide whether you accept ACE-Step's license after reading it.
4. **Native-speaker reviewer** for Hindi and Odia scripts and audio.
5. **Spend:** no paid service is needed or planned. X API posting costs money; I will not enable it without your approval.

Concise question: **Is English tech explainers for a US audience the right first channel?** I am assuming yes for Milestone B and will change the topic, not the pipeline, if you say otherwise.

## Honest limits
- Revenue is not guaranteed and I will not report projections as facts. YPP needs 1,000 subscribers plus 4,000 watch hours or 10M Shorts views (page read, tier details unconfirmed).
- The podcast guide's audio-ripping step is not implemented.
