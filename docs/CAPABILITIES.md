# What Video Factory can do

Local pipeline on one machine. A topic or a script goes in. A captioned MP4 comes out. HyperFrames renders the picture. Publishing is off. Nothing in the default path spends money.

An agent sets the machine up from `docs/AGENT_SETUP.md`, then uses the commands below. Do not invent a second pipeline.

## Languages

| Language | Can it render today? | Voice | Status an agent must report |
|---|---|---|---|
| English, or no `language` field | Yes | Kokoro `af_heart` | production-ready |
| Hindi `hi` | Yes on Apple Silicon, after setup | Chatterbox `hindi-default` | experimental until a person approves the audio |
| Hinglish `hi-en` | Yes on Apple Silicon, after setup | same Chatterbox voice | experimental |
| Odia `or` | No. The job is rejected with `language_blocked` | not installed | blocked |
| Anything else | No. `unsupported_language` | none | not supported |

Hindi and Hinglish do not run on Ubuntu. The voice runtime is MLX. Do not route those jobs to Kokoro or to a paid API to hide that.

A Hindi or Hinglish script must actually be in Devanagari. An English subject tagged `language: hi` is rejected as `script_language_mismatch`. An English voice id on a Hindi job is rejected as `invalid_voice`.

Check the live table with `python -m contentos.lang matrix`. Installed weights are not the same thing as production-ready.

## Two ways to make a video

Track A is the automated path. A spec YAML goes through brief, script, voice, compose, render, QA, package, and export. Voice waits for `SCRIPT_APPROVED`. Render waits for `PRODUCTION_APPROVED`. Publish is a dry run because `config/youtube.yaml` has `publish.enabled: false`.

```bash
./contentos.sh pipeline run SPEC.yaml
./contentos.sh pipeline run SPEC.yaml --approve-private   # only after the owner approved, or for a sample id
```

Track B is a planned explainer. An agent writes the HyperFrames composition. The builder does not read scene plans yet.

Creator Studio is the local web UI at `http://127.0.0.1:4310` via `./contentos.sh dashboard`. It can resume a job, grant script or production approval when the digest still matches, rerun one stage, preview, and export. It cannot publish, and it does not talk to ContentForge.

## What a cloud job can do

ContentForge is a separate app. It drops `CONTRACT.json` into the exchange folder. This factory's worker reads it.

```bash
./contentos.sh factory-worker
```

Leave `language` out for English. Set `language` to `hi` or `hi-en` and send a Devanagari script. `or` is rejected before the pipeline starts. The worker finds the finished file at `jobs/YYYY/MM/DD/<job-id>/video.mp4`.

## Picture, sound, and checks

- Default renderer is HyperFrames. Remotion and MoneyPrinterTurbo are registered lanes. Use them only when the spec sets `render:` and the host has that lane installed. Do not claim a lane works unless a render on this machine passed QA.
- Six visual styles are available when a spec sets `visual_style`. A cloud contract has no style field, so those jobs use the legacy template.
- QA is `./contentos.sh qa VIDEO.mp4`. A long still frame during narration is a `frozen_frames` warning, not a failed file.
- Research is keyless Reddit and Hacker News via `./contentos.sh research "topic"`. Every claim in the script needs a source, or it stays out.
- A queue and a worker can run specs that are already on this machine: `./contentos.sh queue add SPEC.yaml` and `./contentos.sh worker`.

## What it cannot do

- Upload to YouTube or any other platform.
- Odia narration.
- Hindi or Hinglish on Linux.
- A human-approved Hindi or Hinglish voice. The clips to listen to are under `~/Desktop/VideoFactory-Workspace/experiments/multilingual/audio/` when that folder exists.
- Thumbnails, analytics, or niche discovery.
- Paid stock, paid APIs, or `--allow-paid` unless the owner asks.

## How an agent uses it

1. Run the setup script in `docs/AGENT_SETUP.md` if `./contentos.sh doctor` or `python -m contentos.lang doctor` is not already green for the languages the job needs.
2. Read `AGENTS.md` and follow its gates. Show the script, then wait. Show the composed project, then wait. Do not publish.
3. Put generated media only in `$VIDEO_FACTORY_WORKSPACE`.
4. Report the absolute path to `video.mp4`, the QA table, and anything not checked. Do not call a language production-ready when the matrix says experimental or blocked.

Length comes from the registry, not a guess: `python -m contentos.production.platforms budget --kind short`.
