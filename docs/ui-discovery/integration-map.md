# Integration map (Phase 1)

Operational status for the Mac-side tools was NOT verified in this phase (no doctor run possible from the VM). Statuses below are "wired in code" unless noted.

| Integration | Role | Wired where | Status (code) | Needs verifying on the Mac |
|---|---|---|---|---|
| HyperFrames 0.8.114 | default renderer; lint/check/render | hf.py, renderers/hyperframes.py, pipeline compose/render | default path | `doctor`, a real render |
| Kokoro | local TTS (`hyperframes tts`, voice af_heart default) | pipeline.s_voice via providers.yaml | wired | doctor |
| whisper.cpp | local STT / word alignment | production/align.py, caption words | wired | doctor; model is English-only per earlier notes |
| FFmpeg/ffprobe | QA, encode, loudness | qa.py, finalcheck.py, preview | wired; Homebrew ffmpeg required (x86 /usr/local ffmpeg fails per notes) | `./contentos.sh` PATH |
| contentos | the orchestrator itself | cli.py, pipeline.py, production/ | core | tests |
| MoneyPrinterTurbo | optional stock-footage render lane via container CLI | mpt.py, renderers/mpt.py, `spec.render == "mpt"` | wired, opt-in; raises `Unavailable` if absent | container availability |
| Remotion | alternate renderer | renderers/remotion.py, `spec.render == "remotion"` | registered; licence limit noted earlier; not default | unknown |
| ContentForge | upstream job source | adapters/v1 (Node, port 4300) | PARKED by owner | n/a |
| Jev (TypeSafe) | decision service | jev.py, `jev`, `recommend --jev` | reachable, needs cookie (earlier notes) | optional |
| Reddit/HN research, YouTube read | research | research.py, competitor.py | network, keyless | optional |
| YouTube publish | upload | pipeline.s_publish | NOT IMPL | n/a |
| Dashboard | read-only UI | dashboard.py :4310 | IMPL | run on the Mac |

UI implication: the UI only ever needs to call into pipeline/production core/ledger/storage on the Python side. Renderer, TTS and STT selection stay behind `providers` and `renderers`.
