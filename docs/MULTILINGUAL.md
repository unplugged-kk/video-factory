# Multilingual audio: English, Hindi, Hinglish (TTS routing + ASR)

Verified **2026-11-03** (cloud and Odia work added the same day) on a MacBook Pro M5 Pro, 24 GB, macOS 27, arm64. Evidence labels: **[ran]** executed here, **[read]** read in source or a primary page, **[not verified]**.
Everything below that says "works" was executed and the output inspected, except what section 9 lists as unverified. **Nothing here is labelled production-ready for narration quality: no human has listened to the Hindi or Hinglish audio yet** (section 7).

## 0. Creating a video in English, Hindi, Hinglish or Odia from your cloud

Your cloud (ContentForge) drops a `CONTRACT.json` into the exchange folder; `./contentos.sh factory-worker` picks it up, runs the same pipeline and writes the video to `output/<jobId>.mp4` plus `state/<jobId>.json`. **A language is now part of that contract.** Add `language` (a string, or `{"code": "hi"}`); leave it out for English, exactly as before.

| `language` | Script you must send | Voice (`voice.id`, optional) | Status shown to the cloud | Produced today |
|---|---|---|---|---|
| (absent) or `en` | English | a Kokoro id, default `af_heart` | `production-ready` | yes |
| `hi` | Hindi in Devanagari | `hindi-default` | `experimental` | yes, no human audio review yet |
| `hi-en` | Hindi in Devanagari with English terms in Latin | `hindi-default` | `experimental` | yes, see limits |
| `or` | Odia script | `odia-default` | `blocked` | **no: rejected with the reason** (section 8) |

```json
{ "contractVersion": "video-factory.contract.v1", "jobId": "cfvg-9200002", "title": "पॉड क्या है", "format": "9:16",
  "brief": "Kubernetes pod explainer", "language": "hi", "voice": { "enabled": true },
  "script": "कुबेरनेट्स में पॉड सबसे छोटी इकाई है। एक पॉड में एक या उससे ज़्यादा कंटेनर हो सकते हैं।",
  "storyboard": null, "render": { "quality": "high" }, "durationMs": 30000 }
```

What the adapter does with a non-English job, before anything renders: (1) looks the language up in `config/language-capabilities.json` and **rejects a blocked language** with its reason (`language_blocked`) and an unknown one with the supported list (`unsupported_language`); (2) validates the voice against the language (an English voice id for Hindi is `invalid_voice`); (3) checks the script is really in that language (`script_language_mismatch`, for example English text sent as Hindi); (4) splits the script at the danda `।` and at `. ! ?`, cuts headlines on whole words and grapheme boundaries, and omits the English `HOOK`/`STEP n` tags; (5) writes `language:` and the voice into the spec. The job state the cloud reads carries `language` and `languageStatus`, and `audio/voice-languages.json` in the job records the models and a notice for anything not production-ready. Permanent rejections arrive in `state/<id>.json` as `permanentFailureCode` with a readable `error`, and the job folder moves to `failed/`.

Verified end to end **[ran]** with the real worker, real models and a throwaway workspace: English, Hindi and Hinglish contracts all reached `done` with an MP4 (14.8 s, 20.3 s, 19.9 s, 48 kHz stereo), QA 8 pass plus the documented `frozen_frames` warning; the Odia contract was rejected as `language_blocked` and never started the pipeline. Cloud jobs render with the legacy template, which now applies Indic-safe typography (frames inspected: intact Devanagari headline and mixed-script captions). ContentForge, in its own repo, sends `language` from the video panel and the `generate_video` tool, and shows `errorMessage` plus `languageStatus` when the factory writes them.

The `frozen_frames` warning is a static hold, not a broken file. On `cfvg-9200002` (20.3 s) `freezedetect` reported holds of 6.0 s, 5.4 s and 3.4 s inside the three narration clips, which start at 0.00, 6.95 and 13.98 seconds. The picture stays still after the entrance while the voice continues. The check stays a warning.

Operating notes: refresh the capability snapshot after any model change with `python -m contentos.lang matrix --write` (the Python pipeline re-checks readiness at job time, so a stale snapshot can only produce a clear `Blocked`, never wrong audio). The core retries transient failures within a 360 s cap sized to ContentForge's window; Hindi and Hinglish jobs take about 35 s each on this Mac with the model cached, but the very first Hindi job downloads about 3 GB (about 4 minutes), so run `python -m contentos.lang download-tts` once beforehand.

**A pre-existing bug found and fixed while doing this.** The worker located a finished job at `jobs/YYYY/MM/<id>`, but `contentos/storage.py` has written `jobs/YYYY/MM/DD/<id>` since commit `60fdc30`, so *every* cloud job, English included, was being marked `missing_output` even though the pipeline had succeeded. The worker's tests hid it because their fake launcher still used the old layout. `findJobDir` (now in `exchange.mjs`) resolves both layouts and the new tests use the real one.

### Capability matrix

`python -m contentos.lang matrix` shows each language's status and the evidence behind it; `--write` refreshes the JSON the cloud reads; `--check` fails when it is stale. Rules (`contentos/lang/capabilities.py`): `blocked` = no ready TTS backend or ASR route; `experimental` = ready but not validated end to end; `tested` = ready + end-to-end render + automated tests, no human review; `production-ready` = tested + a native-speaker audio review pass (or a documented production history, which is how English qualifies). Human review, renders and test results are recorded in `config/language-capabilities.evidence.json`; an entry can cap a language lower with a stated reason (that is why Hinglish is `experimental`). Installed models alone never reach `tested`.

```
lang   status            TTS        ASR              render   tests    human review   notes
en     production-ready  ready      ready            pass     pass     not-applicable render + tests pass and documented production history
hi     experimental      ready      ready            pass     pass     not-done       capped: no fluent listener has approved pronunciation or naturalness
hi-en  experimental      ready      ready            pass     pass     not-done       capped: segment-level routing was not evaluated, ...
or     blocked           blocked    timing-fallback  not-run  partial  not-done       TTS: [backend_blocked] ... gated ... PyTorch
```

To mark a language production-ready once a fluent speaker has listened: edit its `human_audio_review` entry to `{"status": "pass", "reviewer": "...", "date": "..."}` in the evidence file and run `matrix --write`. Nothing else changes by hand.

## 1. What changed, in one table

| Area | Before | Now |
|---|---|---|
| TTS | Kokoro only, voice must be one of 12 Kokoro ids | `contentos.lang` routes per narration line: `en` Kokoro (unchanged), `hi` and `hi-en` Chatterbox Multilingual v3 (MLX, isolated venv), Kokoro Hindi voices available as an explicit opt-in backend |
| ASR | `hyperframes transcribe` with `small.en` only | `en` unchanged (same call); other languages use `whisper-cli` directly with `ggml-large-v3-turbo-q5_0.bin` (the CLI's own model list cannot name it) |
| Captions | `align.norm` stripped every non-ASCII letter, so Devanagari words all normalised to `""` | Unicode-aware for non-ASCII words (ASCII path byte-identical), nukta folded, Latin technical terms folded to Devanagari on both sides before matching |
| Specs | `voice` had to be a Kokoro id | `language: en|hi|hi-en|auto`, per-line `lang:`, voice is a profile of the routed backend; invalid combinations are explicit errors |
| Approvals | script digest covered text only | for non-English specs the digest also covers language, voice and per-line lang; **English digests are unchanged** so existing approvals stay valid |

English is untouched, **proved** [ran]: the same script rendered fresh through voice, compose, render and qa under a new job id gave byte-identical audio for all 6 lines and a video with PSNR `inf` against the pre-change render; no language metadata files are written on that path.

## 2. Model inventory

| Component | Artifact (exact) | Size | Installed | Verified | Tested here | Status |
|---|---|---|---|---|---|---|
| English TTS | Kokoro-82M `kokoro-v1.0.onnx` via `hyperframes tts` | 325 MB | yes (pre-existing) | n/a | yes, regression identical | production (unchanged) |
| Kokoro Hindi voices | `hf_alpha hf_beta hm_omega hm_psi` inside `voices-v1.0.bin`, phonemizer `--lang hi` | in the existing 28 MB file | yes (pre-existing) | present [ran] | pure Hindi yes, mixed script no | opt-in backend `kokoro_hindi`, not default |
| Hindi/Hinglish TTS | `mlx-community/chatterbox-multilingual-v3` `model.safetensors`, MIT, base `ResembleAI/chatterbox` | 2.71 GB (+ S3TokenizerV2 weights; 3.0 GB cache total) | yes, `~/.cache/contentos/huggingface` | HF tree size + licence [read]; load and generation [ran] | yes (benchmark + 2 videos) | **tested, intelligible by ASR round trip, awaiting human listening** |
| Runtime | `mlx-audio==0.6.4` (MIT) + `mlx 0.32.4` in `~/.contentos/venv-mlx-audio` | 465 MB, 38 small packages, no torch | yes, isolated | dry-run resolved before install [ran] | yes | pinned |
| English ASR | `ggml-small.en.bin` | 487,614,201 B | yes (pre-existing, not touched) | size matches; sha256 `c6138d6d58ecc832...` recorded (no official checksum published) | yes | production (unchanged) |
| Multilingual ASR | `ggml-large-v3-turbo-q5_0.bin` from `ggerganov/whisper.cpp` (MIT) | 574,041,195 B | yes, `~/.cache/hyperframes/whisper/models` | **size and SHA-256 `3942...a7e2` match the official LFS values** [ran] | yes (benchmark + 2 videos) | tested |
| whisper.cpp | 1.9.5 (Homebrew), `whisper-cli` | | yes (pre-existing) | | yes | |
| IndicConformer, IndicF5, Indic Parler-TTS | `ai4bharat/*` | 2.6 / 1.4 / 3.8 GB | **no** | gated on HF (login + terms) | no | blocked by access, section 6 |
| MediaPipe, rembg | PyPI | 19 / 27 packages | **no** | dry-run only | no | assessment only, section 8 |

Licences (verified from GitHub / HF metadata [read]): whisper.cpp MIT, Chatterbox (source and `ResembleAI/chatterbox` weights) MIT, mlx-audio MIT, the MLX checkpoint MIT, Kokoro Apache-2.0 (existing). **One to confirm before monetizing:** the MLX conversion of the speech tokenizer (`mlx-community/S3TokenizerV2`) declares **no licence of its own**; its base, `FunAudioLLM/CosyVoice2-0.5B`, is Apache-2.0 [read]. I did not find a conflict but a conversion repo with no declared licence is a gap to close.

## 3. How it works

```
spec.language / line.lang  ->  router.resolve()  ->  Route(language, tts_backend, voice, asr_model, asr_language, text_policy)
                                   |                         |
                       config/language.yaml          tts.synthesize_lines()     -> audio/NN.wav (24 kHz mono, -14 LUFS) + NN.tts.json
                                                           |                    -> audio/voice-languages.json (job-level summary)
                                         kokoro: hyperframes tts + loudnorm      (the original commands)
                                         chatterbox_v3: ONE worker process per script, model loaded once, then loudnorm
words_for(wav, workdir, language=) -> en/None: hyperframes transcribe (unchanged) | other: whisper-cli + the routed model
caption_words(..., language=)      -> aligns SCRIPT words to ASR words, folding Latin technical terms to Devanagari
```

Routing is per narration line or per video, never per token. `auto` is accepted **only** with `spec.language_metadata = {language, source: declared}` or `{source: detected, confidence >= 0.9}`; a Unicode-script hint (`router.script_hint`) exists but is explicitly marked `reliable: false` and is never used by `auto`.

Metadata: every generated line writes `NN.tts.json` (backend, exact model id, voice, reference provenance, text policy, the text actually spoken, chunk offsets, sample rate, channels, codec, duration, generation seconds, fallback, warnings). `word_timestamps` is always `"none"`: TTS timing is never claimed; word timing comes from ASR and is labelled as measured. ASR routing is recorded in `audio/txNN/asr-route.json`.

### Fallback policy

`fallback_tts: null` for every language (default). A failure raises a `LangError` with a stable `code` and the fix. If you set `fallback_tts: kokoro_hindi` for `hi`, a Chatterbox failure uses it, and the job records `fallback_from` and a `FALLBACK` warning in the line's metadata. Voice and language errors are **never** masked by a fallback. English-only Kokoro is never used for Hindi unless you configure it and the job says so.

## 4. Configuration (actual keys: `config/language.yaml`)

```yaml
default_language: en
paths: {mlx_python: ~/.contentos/venv-mlx-audio/bin/python, hf_home: ~/.cache/contentos/huggingface,
        whisper_models: ~/.cache/hyperframes/whisper/models, voices: ~/.contentos/voices}
languages:
  en:    {tts: kokoro,        asr: whisper_small_en, asr_language: en, text_policy: as_is,          fallback_tts: null}
  hi:    {tts: chatterbox_v3, asr: whisper_turbo_q5, asr_language: hi, text_policy: as_is,          fallback_tts: null}
  hi-en: {tts: chatterbox_v3, asr: whisper_turbo_q5, asr_language: hi, text_policy: translit_known, fallback_tts: null}
auto: {accept_declared: true, min_detected_confidence: 0.9}
tts_backends:   # kokoro (en) | kokoro_hindi (opt-in, voices hf_alpha hf_beta hm_omega hm_psi) | chatterbox_v3 (model, lang_code, exaggeration, voice_profiles)
asr_models:     # whisper_small_en | whisper_turbo_q5 (file, size_bytes, sha256, source, multilingual)
```

To change a language's engine, edit its `languages:` row (for example `hi: {tts: kokoro_hindi, ...}` to use Kokoro's Hindi voices; the router validates that the backend declares the language). `CONTENTOS_LANGUAGE_CONFIG=/path/other.yaml` overrides the file for experiments. `text_policy`: `as_is`, `translit_known` (lexicon terms to Devanagari, unknown Latin words passed through with a warning), `mixed` (alias of pass-through).

**Voices.** Chatterbox v3 (MLX) has **no default voice**: the checkpoint ships no `conds.safetensors`, so a reference recording is required [read in mlx-audio source, confirmed by the model card examples]. The configured profile `hindi-default` uses `~/.contentos/voices/hi_reference.wav`, a **synthetic** clip made by Kokoro `hf_alpha` speaking original text, so no real person's voice is cloned. To use a recording of a real person you must have their consent: `python -m contentos.lang reference --from my_voice.wav` (refuses to overwrite).

## 5. Commands that work in this environment

```bash
cd ~/git/video-factory; export PATH=/opt/homebrew/bin:$PATH; P=~/.contentos/venv/bin/python

# setup (idempotent; Apple Silicon installs English, Hindi, Hinglish; Odia stays blocked)
$P -m contentos.lang setup
# manual equivalent if you need to repair one piece:
#   uv venv --python 3.12 ~/.contentos/venv-mlx-audio
#   uv pip install --python ~/.contentos/venv-mlx-audio/bin/python "mlx-audio==0.6.4"
#   $P -m contentos.lang reference --make      # synthetic reference voice (refuses to overwrite)
#   $P -m contentos.lang download-tts          # pre-fetch the checkpoint; otherwise the first Hindi job does it

# inspect
$P -m contentos.lang routes
$P -m contentos.lang doctor --require en,hi,hi-en      # READY / NOT READY; Odia blocked is expected
$P -m contentos.lang verify-models                     # size + sha256 vs config

# speak and transcribe one segment
$P -m contentos.lang speak --lang hi    --text "कुबेरनेट्स में पॉड सबसे छोटी इकाई है।" --out /tmp/hi.wav
$P -m contentos.lang speak --lang hi-en --text "Kubernetes में pod सबसे छोटी unit है।"   --out /tmp/hien.wav
$P -m contentos.lang transcribe /tmp/hi.wav --lang hi

# whole videos (gates apply as always; use real approvals for real content)
./contentos.sh pipeline run examples/multilingual/pod-hi.yaml    --approve-private    # sample-* content only
./contentos.sh pipeline run examples/multilingual/pod-hi-en.yaml --approve-private

# benchmark (regenerates audio and results under ~/Desktop/VideoFactory-Workspace/experiments/multilingual)
$P scripts/lang_benchmark.py
$P -m pytest tests/test_lang.py -q
```

English narration is unchanged: a spec without `language` (or `language: en`) takes the original `s_voice`. Hindi: `language: hi`, optional `voice: hindi-default`. Hinglish: `language: hi-en`. See `examples/multilingual/`.

## 6. Benchmark [ran]

Original scripts, same meaning in three registers (`tests/fixtures/multilingual/benchmark.json`). Audio is normalised exactly as the pipeline does (loudnorm -14 LUFS, 24 kHz mono). `gen s` and `RSS` are wall time and measured max resident set size (`/usr/bin/time -l`) of the whole generation process **including model load**. **WER raw** compares ASR text to the reference as written; **WER folded** first folds Latin technical terms to Devanagari on both sides, because Whisper writes English terms in Latin even when the reference spells them in Devanagari, so the raw number mostly measures spelling script, not audio quality.

| sample | TTS | dur s | LUFS | peak dBFS | gen s | RSS GB | ASR model / -l | WER raw | WER folded | CER folded | terms | asr s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| en | kokoro | 12.2 | -14.5 | -1.5 | 2.66 | 0.79 | small.en / en | 0.0 | 0.0 | 0.0 | 7/7 | 0.5 |
| en | kokoro | 12.2 | -14.5 | -1.5 | 2.66 | 0.79 | large-v3-turbo-q5_0 / en | 0.0 | 0.0 | 0.0 | 7/7 | 0.56 |
| hi | kokoro | 17.26 | -14.4 | -1.5 | 3.14 | 0.92 | large-v3-turbo-q5_0 / hi | 0.407 | 0.023 | 0.026 | 7/7 | 0.99 |
| hi | kokoro | 17.26 | -14.4 | -1.5 | 3.14 | 0.92 | large-v3-turbo-q5_0 / auto | 0.407 | 0.023 | 0.026 | 7/7 | 1.12 |
| hi | kokoro | 17.26 | -14.4 | -1.5 | 3.14 | 0.92 | small.en / en | 1.0 | 0.744 | 1.339 | 4/7 | 0.67 |
| hi-en | kokoro | 20.84 | -14.7 | -1.5 | 3.64 | 0.98 | large-v3-turbo-q5_0 / hi | 0.474 | 0.438 | 0.836 | 6/9 | 0.97 |
| hi-en | kokoro | 20.84 | -14.7 | -1.5 | 3.64 | 0.98 | large-v3-turbo-q5_0 / auto | 0.474 | 0.438 | 0.836 | 6/9 | 1.18 |
| hi-en | kokoro | 20.84 | -14.7 | -1.5 | 3.64 | 0.98 | large-v3-turbo-q5_0 / en | 0.474 | 0.438 | 0.793 | 6/9 | 0.95 |
| hi | chatterbox | 18.54 | -14.9 | -1.5 | 11.41 | 3.45 | large-v3-turbo-q5_0 / hi | 0.43 | 0.023 | 0.017 | 7/7 | 0.93 |
| hi | chatterbox | 18.54 | -14.9 | -1.5 | 11.41 | 3.45 | large-v3-turbo-q5_0 / auto | 0.43 | 0.023 | 0.017 | 7/7 | 1.12 |
| hi | chatterbox | 18.54 | -14.9 | -1.5 | 11.41 | 3.45 | small.en / en | 1.0 | 0.744 | 1.374 | 4/7 | 0.65 |
| hi-en | chatterbox | 18.54 | -14.7 | -1.5 | 10.98 | 3.46 | large-v3-turbo-q5_0 / hi | 0.228 | 0.022 | 0.017 | 8/9 | 0.91 |
| hi-en | chatterbox | 18.54 | -14.7 | -1.5 | 10.98 | 3.46 | large-v3-turbo-q5_0 / auto | 0.228 | 0.022 | 0.017 | 8/9 | 1.11 |
| hi-en | chatterbox | 18.54 | -14.7 | -1.5 | 10.98 | 3.46 | large-v3-turbo-q5_0 / en | 0.0 | 0.0 | 0.0 | 9/9 | 0.85 |
| hi-en_translit | chatterbox | 18.62 | -14.7 | -1.5 | 11.04 | 3.46 | large-v3-turbo-q5_0 / hi | 0.517 | 0.0 | 0.0 | 9/9 | 0.89 |
| hi-en_translit | chatterbox | 18.62 | -14.7 | -1.5 | 11.04 | 3.46 | large-v3-turbo-q5_0 / auto | 0.517 | 0.0 | 0.0 | 9/9 | 1.07 |
| hi-en_translit | chatterbox | 18.62 | -14.7 | -1.5 | 11.04 | 3.46 | large-v3-turbo-q5_0 / en | 0.528 | 0.067 | 0.086 | 8/9 | 0.84 |

Reading the table:
- **English:** both ASR models transcribe the Kokoro sample perfectly (7/7 terms). Multilingual turbo is not slower on this clip (0.56 s vs 0.5 s) but one 12 s sample cannot separate their accuracy; English stays on `small.en`.
- **Hindi (Chatterbox):** folded WER 0.023, CER 0.017, 7/7 terms. Residual ASR differences are spelling variants (`ज़्यादा`/`ज्यादा`, `साझा`/`साजा`, `छोटी`/`छोड़ी`): the audio is intelligible to Whisper; whether it is *natural* is not measured.
- **Hindi (Kokoro hf_alpha):** equally intelligible on pure Hindi (folded WER 0.023) and about 4x faster, with a quarter of the memory. A real option, but it is not default because the brief selects Chatterbox and quality has not been compared by ear.
- **Hinglish:** Kokoro's Hindi voice **fails** on mixed script (folded WER 0.44; the transcript reads `In-Unit ही`, `In-Deploy ही`): it spells Latin words out letter by letter. Chatterbox pronounces them natively (mixed script: folded WER 0.022, 8/9 terms, `fail` heard as `फिर`; `translit_known`: WER 0.0, 9/9). That is why `hi-en` routes to Chatterbox with `translit_known`. One sample cannot separate `mixed` from `translit_known`; the policy is configurable.
- **Control:** `small.en` on Hindi audio gives WER 1.0 (folded 0.74), confirming English-only ASR cannot be used for Hindi.
- **Timestamps:** every transcript passes `valid_timestamps` (monotonic, within the audio length). Whisper word times are estimates, not ground truth.
- **Cost:** Chatterbox about 11 s for 18.5 s of audio once the model is cached (warm load 1.5 s), 3.5 GB resident, MLX peak 5.1 GB; first-ever load took 250 s because of the 3 GB download. Kokoro: 2.7-3.6 s, 0.8-1.0 GB.
- **Not measured:** naturalness, accent, speaker consistency, pronunciation of English words by a Hindi voice, prosody. These need a listener. Generated files to play: `~/Desktop/VideoFactory-Workspace/experiments/multilingual/audio/*.wav` (`hi__chatterbox.wav`, `hi__kokoro.wav`, `hi-en__chatterbox.wav`, `hi-en_translit__chatterbox.wav`, `hi-en__kokoro.wav`, `en__kokoro.wav`).

### Captions on real Hindi video [ran]

Script-to-ASR match ratio per line (share of script words that matched an ASR word directly; the rest get interpolated timing between matched neighbours): Hindi 0.69, 0.90, 0.89, 0.79; Hinglish 0.85, 0.68, 0.94, 0.64. Folding raised several of these from 0.54 to 0.69 and 0.72 to 0.89 (unfolded values in the tests). For comparison, English lines on the regression job match 1.0 on all six lines [ran]. So **Hindi caption timing is approximate**: roughly 10-35% of words are interpolated.

## 7. Rendered videos and what was and was not checked

| Job | Language | Result |
|---|---|---|
| `sample-ml-hi-001` | `hi`, Chatterbox, turbo ASR, clean-explainer | voice, compose (lint), render, qa all OK; QA 8 pass + `frozen_frames` WARN; Devanagari renders correctly in headline, diagram labels, steps and captions |
| `sample-ml-hien-001` | `hi-en`, translit_known | same; mixed-script captions render correctly |
| `sample-ml-en-regress` | `en` | byte-identical audio and frame-identical video vs the pre-change baseline |

Previews: `~/Desktop/VideoFactory-Workspace/experiments/multilingual/render/*/contact-sheet.png`. I inspected frames (typography, layout, wrapping). **I cannot listen to audio.** A human listening review of the Hindi and Hinglish files is the gate before any of this narrates published content.

## 8. Feasibility assessments (no installs)

**IndicConformer (AI4Bharat).** `AI4Bharat/IndicConformerASR` is MIT (last push 2025-06-20) [read]. The practical artifact is `ai4bharat/indic-conformer-600m-multilingual`: 2.56 GB of ONNX files with post-nets for 22 languages including `hi` and `or` (Odia) [read from the HF file tree]. ONNX means it could run on `onnxruntime` (already a dependency of kokoro-onnx) with **no NeMo**; the `.nemo` variant (`ai4bharat/IndicConformer`, CC-BY-4.0) would need NeMo and is not recommended. **Blocker: the model is gated on Hugging Face** (login and terms acceptance), so I could not read its card, confirm its runtime requirements, or download it non-interactively. **Recommendation:** run a separate benchmark only if you want Odia or better Hindi accuracy than Whisper turbo's current 0.023 folded WER on this sample (a bar that is already low, so the Hindi benefit is unproven); the real reason to pursue it is Odia. Steps if you approve: accept the terms on HF with your account, `hf auth login`, download to the HF cache, test with onnxruntime in an isolated venv.

**Odia (`or`): registered, routed, validated, rendered, but blocked.** Four levels, kept apart. *Subtitles:* **tested** here: Odia headline, caption highlight and step cards rendered with intact conjuncts in Oriya Sangam MN, `hyperframes lint` clean, using silent placeholder audio so this is a glyph and layout test, not narration (`experiments/multilingual/render/odia_glyph_test.png`); the Odia sentences I wrote for it have not been reviewed by a fluent speaker. *Script handling:* **tested**: `or` scripts must be at least 60% Odia-block letters, NFC-normalised, no control or zero-width characters. *TTS:* **blocked**. *ASR:* **blocked**; captions would use measured audio duration with even word spacing, recorded as unverified (`timing_fallback: even_spacing`). *Production-ready:* no.

Why it is blocked, with the evidence **[read]**:
- **TTS candidates.** `ai4bharat/indic-parler-tts`: Apache-2.0 metadata, 3.75 GB, language list includes `or`, **gated on Hugging Face** (a token whose account accepted the terms), PyTorch. `ai4bharat/IndicF5`: MIT metadata, 1.4 GB, includes `or`, **gated**, PyTorch, and needs an Odia reference recording plus its exact transcript; its `f5-tts` package pulls gradio, wandb, funasr and pins `numpy<=1.26.4`, so it is the heavier path. Excluded: `facebook/mms-tts-ory` (CC-BY-NC-4.0, not usable for monetized video), `twomuchlabs/sarvavox-odia-v1` (model card only, no weights), and Chatterbox v3, which does not list Odia.
- **ASR candidates.** whisper.cpp 1.9.5 has no Odia language id (`-l or` is rejected **[ran]**), so the installed `ggml-large-v3-turbo-q5_0.bin` cannot be used. `ARTPARK-IISc/whisper-large-v3-vaani-odia` (Apache-2.0, ungated, 6.2 GB PyTorch checkpoint) and `chandan3007/Whisper-small-oriya` (Apache-2.0, ungated, 0.97 GB) would need a ggml conversion that itself needs PyTorch. `ARTPARK-IISc/SraVaani-1.0` (MIT, lists `or`, gated, 0.9 GB TorchScript) and the ONNX IndicConformer-600M (22 languages incl. `or`, gated) are the other options. None has been tested because there is no Odia audio to test with.
- **What no model here can do yet:** generate Odia audio. So no Odia ASR benchmark, no pronunciation test and no fluent-speaker review are possible; I did not fabricate any.

**What I need from you to unlock Odia (two decisions, both yours):**
1. **A Hugging Face token** whose account has accepted the terms on the model pages (`ai4bharat/indic-parler-tts` first, then `ai4bharat/IndicF5` if you want the second option). I will not log in on your behalf or store a token in the repo; it would live in `~/.cache/huggingface/token` via `hf auth login`.
2. **Approval for an isolated PyTorch environment** (a major framework install). Dry-run resolution: 38 packages, torch 2.15.0 (139 MB arm64 wheel), torchaudio 2.11.1, transformers 5.22.1; expected total on disk roughly 0.7-1 GB for the venv plus 3.75 GB for the Parler checkpoint. `parler-tts` (Apache-2.0, 0.2.3 on PyPI, last upstream commit 2024-12) predates transformers 5, so its compatibility with that version is **unverified** and may force an older pin; I would test it in the isolated venv before wiring anything.

Exact commands once approved (nothing here has been run):
```bash
uv venv --python 3.12 ~/.contentos/venv-torch-tts
uv pip install --python ~/.contentos/venv-torch-tts/bin/python torch torchaudio "transformers>=4.46" accelerate sentencepiece parler-tts
hf auth login                                    # your token; accept the model terms in the browser first
HF_HOME=~/.cache/contentos/huggingface ~/.contentos/venv-torch-tts/bin/python -c "from huggingface_hub import snapshot_download as s; s('ai4bharat/indic-parler-tts')"
```
Then I add a worker like `chatterbox_worker.py` for Parler, flip `indic_parler_odia.blocked` off, benchmark pronunciation, runtime and memory on native-script sentences, record the results in the evidence file, and the matrix moves Odia from `blocked` to `experimental`. It stays `experimental` until a fluent Odia speaker reviews generated audio. Rollback: `rm -rf ~/.contentos/venv-torch-tts` and delete the cached model folder.

**Person matting (MediaPipe vs rembg).** Dry-run installs in a throwaway venv [ran]: `mediapipe 1.2.0` (Apache-2.0) = 19 packages including `opencv-contrib-python 5.0.0` and `matplotlib`; `rembg 2.0.86` (MIT) = 27 packages including `numba`, `llvmlite`, `scikit-image`. MediaPipe Image Segmenter's published models: SelfieSegmenter (square 256x256, landscape 144x256), SelfieMulticlass, HairSegmenter, DeepLab-v3 [read, Google page]; model files are fetched separately from Google storage and their per-model licences are on model cards I did not verify. **Nothing about segmentation quality, mask stability, edge quality, temporal consistency, speed or memory could be measured:** the nine behind-the-subject skills need real footage of a person and none exists in the repo, and I do not fabricate it. The factory currently has no foreground/background layering over footage, so those skills use the registry's documented no-matte fallback. **Recommendation (reversible):** do not install yet; when you supply one rights-cleared 9:16 talking-head clip, install MediaPipe only, in its own venv (`uv venv ~/.contentos/venv-seg && uv pip install --python ~/.contentos/venv-seg/bin/python mediapipe==1.2.0`, about 19 packages), measure mask quality on that clip, and integrate through a subprocess like the Chatterbox worker. Rollback: `rm -rf ~/.contentos/venv-seg`. rembg only if you need still-image cutouts (adds numba/llvmlite).

## 9. Limitations and unverified items

- **No human listening** to any generated Hindi/Hinglish audio. ASR round trips prove intelligibility to Whisper, not naturalness.
- One benchmark text per language, one voice reference, one run each: differences between strategies or models smaller than a few WER points are not established.
- The Chatterbox reference is a synthetic Kokoro voice, so the Hindi voice inherits that timbre; a better reference would change the result. Voice cloning of a real person is not set up and needs a consent record.
- Hindi caption word timing is partly interpolated (section 6).
- Whisper's Latin-script output for English terms means the ASR text is mixed-script even for pure Hindi lines; only the folded comparison is meaningful.
- Chatterbox needs an Apple-silicon Mac with about 5 GB free for the model; it is not portable to the Linux scheduler without a different runtime.
- The Studio "Track A creator" whitelist rejects `language`, `visual_style` and `visual`; those specs run through `pipeline run`, not the Studio form.
- `contentos doctor` still lists the legacy `chatterbox_mlx` provider (looking for `~/.voice-clone-venv`) as NOT_INSTALLED. That is `config/providers.yaml`, which I did not edit: creating a venv at that path would make the provider selector prefer it for **every** job (higher `quality` than Kokoro) and break English, because `s_voice` has no adapter for that provider id. The new route does not use the provider selector.
- Odia: blocked (section 8); every other language: not supported (`unsupported_language`).

## 10. Model lifecycle and memory

Kokoro runs inside `hyperframes tts` per call (about 0.8-1.0 GB, seconds). Chatterbox runs in a **separate process per script**: spawned only when a line routes to it (English-only jobs never import MLX), loads the 2.7 GB model once for all lines (about 1.5 s warm), runs, and exits, so memory returns to the OS. Whisper turbo runs per line through `whisper-cli` (about 1 s, small footprint). Models are not shared across jobs; a persistent server would save the 1.5 s load per job and is not worth the lifecycle complexity yet.

## 11. Rollback (this task only)

```bash
# code and config (new files only, plus small edits to pipeline.py, specs.py, align.py, scenekit/compose.py, skills/probe.py)
rm -rf contentos/lang config/language.yaml examples/multilingual tests/test_lang.py tests/fixtures/multilingual scripts/lang_benchmark.py docs/MULTILINGUAL.md
git diff contentos/pipeline.py contentos/specs.py contentos/production/align.py contentos/scenekit/compose.py   # then revert only this task's hunks
# installed artifacts (all outside the repo; nothing is installed globally)
rm -rf ~/.contentos/venv-mlx-audio ~/.cache/contentos/huggingface ~/.contentos/voices
rm ~/.cache/hyperframes/whisper/models/ggml-large-v3-turbo-q5_0.bin        # ggml-small.en.bin is untouched
```
Frees about 4.1 GB. Existing English jobs and approvals are unaffected by any of it.
