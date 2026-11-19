# Open-source research

Verified against the GitHub and Hugging Face APIs on **2026-11-18**. Repo/licence/date cells are read from
those APIs; anything I could not read is marked `unverified`. No package was installed for this document.

Already present and therefore not candidates: **HyperFrames** (pinned 0.8.114, HTML+GSAP), **Remotion**,
**MoneyPrinterTurbo**, **Kokoro** (the only working TTS here), **whisper.cpp** (installed mid-audit).
The question for every row is *what can this do that those four cannot*.

## Candidate table

| Candidate | Repo | Last release / commit | Maint. | Licence + monetised YouTube OK? | Core capability | Hardware | Overlap with this repo | Effort | Risk | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| Motion Canvas | github.com/motion-canvas/motion-canvas | v3.17.2 (2024-12-14); pushed 2026-07-02 | releases stalled, repo alive | MIT — yes | Deterministic timeline animation in TS, generator-based `yield` sequencing, editor UI | Node + headless Chrome (already have both) | Duplicates HyperFrames' job. Adds a real **timeline DSL** and a scene-graph editor HyperFrames lacks | L | Two render stacks to maintain; release cadence stopped | **DEFER** — only if timeline authoring becomes the bottleneck |
| Revideo | github.com/midrender/revideo | no tagged release; pushed 2026-07-15 | active, moved from `redotvideo` | MIT — yes | Motion Canvas fork with programmatic API + faster parallel rendering | Node + Chrome | Same overlap; the parallel-render story is the only differentiator | M | Project renamed org once already; no releases to pin | **EVALUATE** — render speed only |
| Manim Community | github.com/ManimCommunity/manim | v0.22.1 (2026-10-27) | very active | MIT — yes | Mathematical/technical animation with LaTeX, precise geometric scenes | Python + LaTeX + cairo; CPU | **Nothing here does this.** HyperFrames can draw a chart; it cannot do rigorous math/geometry animation | M | LaTeX install; slow renders; one more Python dep tree | **ADOPT as a specialist lane** for science/maths explainers — highest-value gap of any row |
| Lottie | github.com/airbnb/lottie-web | no tagged release; pushed 2025-09-01 | low activity, stable | MIT — yes | Plays After Effects JSON vectors in the browser | none (JS in the page) | Complementary, not overlapping: HyperFrames already renders HTML/JS, so Lottie is a **library inside the composition, not an integration** | S | None material; needs AE-authored assets | **ADOPT (as a library)** — cheapest way to add real vector motion |
| Three.js | github.com/mrdoob/three.js | r187 (2026-10-30) | very active | MIT — yes | WebGL 3D | GPU (Apple Silicon fine) | Same — a library in the composition, not a renderer | S | Render-time cost per frame in headless Chrome | **ADOPT (as a library)** for 3D hooks/transitions |
| p5.js | github.com/processing/p5.js | v2.4.0 (2026-11-12) | very active | **LGPL-2.1** — usable, but copyleft-ish | Generative/sketch graphics, `p5.brush` painterly effects | none (JS) | Generative backgrounds HyperFrames templates cannot produce | S | LGPL obligations if ever bundled into a distributed product | **EVALUATE** — good for generative b-roll; mind the licence |
| librosa | github.com/librosa/librosa | 1.0.1 (2026-11-12) | very active | ISC — yes | Beat tracking, onset detection, tempo, spectral analysis | CPU, numpy | **Nothing here does beat detection**, which is why the lyric-video workflow has no beat analysis | S | Adds numpy/scipy to the venv | **ADOPT** — the missing half of lyric + music-driven editing |
| Chatterbox MLX | huggingface.co/ResembleAI/chatterbox | 2.58M downloads, 1,920 likes | active | **MIT** — yes | Multilingual TTS + zero-shot voice cloning; card lists **`hi`** | MLX on Apple Silicon; ~3–4 GB | Already the configured `chatterbox_mlx` route; **not installed** (`~/.voice-clone-venv` absent) | S| Cloning needs a reference clip; Hindi quality unproven here | **ADOPT** — cheapest path to a Hindi voice, already wired |
| Indic Parler-TTS | huggingface.co/ai4bharat/indic-parler-tts | Apache-2.0, 178k downloads | active | Apache-2.0 — yes | 22 Indic languages, description-conditioned voice control | ~0.94B params (938M safetensors); PyTorch CPU/MPS | No overlap — nothing local speaks Hindi today | M | **Gated model** (access request + HF token); 0.94B in torch on 24 GB is feasible but slow on MPS | **ADOPT as benchmark candidate #2** |
| Indic-Speak | huggingface.co/bodhan-ai/indic-speak | 3.3B params; pushed 2025-09 | active | **Indic Open Model License v1** — commercial use granted, credit required; **hosted-API use for third parties needs written sign-off** | 22 Indic languages, built on Llama-3.2-3B | 3.3B — heaviest option; ~7–8 GB in fp16 | No overlap | L | **Gated**; biggest RAM ask; the hosting clause matters if this ever becomes a service | **EVALUATE as benchmark candidate #3** |
| MMS-TTS | huggingface.co/facebook/mms-tts-hin | 9k downloads | low | **CC-BY-NC-4.0** — **NO.** Non-commercial only | Single-language VITS TTS | tiny (36M) | Only virtue is size | — | Licence disqualifies it for a monetised channel | **REJECT** — non-commercial licence |
| Ayase | *not found* | — | — | unverified | The brief describes a broad video-quality metric tool; **no such GitHub project exists under this name** (top hits are a keyboard tool and a 4chan archiver) | — | — | — | Wrong tool or wrong name | **REJECT (unverifiable)** — ask for the URL before spending time |
| vidqa | github.com/DSmereski/vidqa | pushed 2026-08-20; 1 star | new, single author | MIT — yes | Deterministic local video QA CLI/MCP: OCR, captions, frame comparison | CPU | **Overlaps the existing QA** (`qa.py`, `finalcheck.py`) which already re-runs 9 checks at export | S | One-star project, no track record | **DEFER** — only the OCR and frame-comparison ideas are worth borrowing; do not add a second QA framework |
| whisper.cpp | github.com/ggml-org/whisper.cpp | v1.9.5 (2026-10-06) | very active | MIT — yes | ASR + word timings | CPU | Already installed and the configured ASR | — | — | **KEEP as-is** |

## Three notes on the table

1. **Lottie, Three.js and p5.js are not integrations.** HyperFrames renders an HTML page, so these are `<script>`
   tags inside a composition that already loads GSAP (`contentos/renderers/hyperframes.py`,
   `contentos/scenekit/compose.py`). The effort is authoring the scene, not plumbing a new renderer. This is
   the cheapest creative-capability-per-hour available, and it contradicts the instinct to "add a renderer".
2. **Manim is the only row that adds a capability nothing here has.** Everything else either duplicates
   HyperFrames or is a library. If exactly one new engine is ever adopted, it should be this one.
3. **Ayase does not appear to exist.** Before any work is scheduled against it, get the actual URL.

## Hindi TTS decision

Facts from the model cards and the local machine (arm64, 24 GB RAM, Kokoro the only working TTS,
`~/.voice-clone-venv` absent):

| | Chatterbox | Indic Parler-TTS | Indic-Speak |
|---|---|---|---|
| Licence | MIT | Apache-2.0 | Indic Open Model License v1 (commercial OK, **credit + no third-party hosted API without sign-off**) |
| Size | ~0.5B class (`unverified` — card lists no safetensors total) | 0.94B | 3.3B (Llama-3.2-3B base) |
| Hindi on card | yes | yes | yes (22 Indic languages) |
| Gated | no | **yes** | **yes** |
| RAM on 24 GB | comfortable | workable, slow on MPS | tight; ~7–8 GB fp16 plus overhead |
| Already wired | **yes** — `chatterbox_mlx` in `providers.yaml` | no | no |
| Installed | no (`~/.voice-clone-venv` missing) | no | no |

**Recommended benchmark priority: Chatterbox → Indic Parler-TTS → Indic-Speak.** Chatterbox first because it is
MIT, ungated, the smallest, and the only one the routing table already names — a benchmark there costs a venv
and a reference clip, not a licence negotiation. Indic Parler-TTS is the strongest quality candidate, but it
needs a gated-access token before any test can start. Indic-Speak is the heaviest and carries the hosting
clause; keep it as the tie-breaker if the first two fail a listener test.

**Correction to the brief:** Indic-Speak is published by **Bodhan AI**, not AI4Bharat (AI4Bharat is co-credited
in the licence text). The claim that AI4Bharat's Parler card points to Indic-Speak is `unverified` — both
cards are access-gated, so I could not read them.

None of the three can be called production-ready until a fluent listener passes a fixed Hindi benchmark. Until
then Hindi stays experimental, and `contentos.lang doctor` must stop printing `hi READY` for a backend that is
not installed.

## HyperFrames upstream

**There is a release newer than the pin.** `registry.npmjs.org/hyperframes` reports `dist-tags.latest =
0.9.66`, with recent tags `0.9.59 → 0.9.66`; the repo pins `0.8.114` in `package.json`. That is a **0.8 → 0.9
minor-version jump**, not a patch, so it may carry breaking changes.

What changes between them: `unverified` — I did not read the changelog. Do not upgrade on this evidence.
The pin is deliberate ("upgrade on purpose: `npm install hyperframes@<version>`, then run the tests and one
render"). If you do want it, that is the procedure, plus one real render and a frame comparison, because this
audit found that the render path is exactly where the visual output is least understood.
