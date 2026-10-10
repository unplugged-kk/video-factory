# 03 - Source-backed research and comparisons

All sources accessed 2026-10-10. Confidence: **High** = read on the primary page; **Medium** = primary page but summarized/partial or version-sensitive; **Low** = could not confirm, treat as an assumption. Pages were read through a summarizer, so anything that drives money or a policy decision should be re-checked on the page before acting.

## A. Verified findings by topic

### Rendering
| Finding | Source | Conf. |
|---|---|---|
| HyperFrames is Apache-2.0, ~60k stars, needs Node 22+ and FFmpeg, renders HTML to MP4 through headless Chrome; no per-render fees or commercial thresholds. Ships 21 official agent skills (`claude plugin marketplace add heygen-com/hyperframes`, or `npx skills add heygen-com/hyperframes`). The GitHub Releases tab was empty; `npm view hyperframes version` returns 0.8.145 (checked 2026-10-10) while this repo pins 0.8.114, so the install is 31 patch versions behind. Upgrade only after re-running tests | https://github.com/heygen-com/hyperframes | High (license), Medium (version) |
| Remotion is free for individuals, non-profits and for-profits with up to 3 employees (commercial use included); larger companies need a paid Company License. Page warns the license "will slightly change" in Remotion 5.0 | https://github.com/remotion-dev/remotion/blob/main/LICENSE.md | Medium (prices not retrieved) |

### Speech
| Finding | Source | Conf. |
|---|---|---|
| Kokoro-82M: Apache-2.0, 82M params, v1.0 has 54 voices. Hindi has 4 voices (hf_alpha, hf_beta, hm_omega, hm_psi), each graded **C**, trained on only 10-100 minutes each. **No Odia** | https://huggingface.co/hexgrad/Kokoro-82M and its VOICES.md | High |
| Whisper's language list has Hindi but **not Odia** | https://github.com/openai/whisper/blob/main/whisper/tokenizer.py | High |
| Installed whisper model is `ggml-small.en.bin` (English-only) | local file listing | High |
| WhisperX: BSD-2-Clause, adds wav2vec2 word alignment; default alignment models only for en/fr/de/es/it, others need a tested HF model; MPS not documented (CPU documented on macOS) | https://github.com/m-bain/whisperX | Medium |
| AI4Bharat IndicConformer-600M: ASR, MIT, includes Odia, gated download; the page recommends the newer Indic-Transcribe | https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual | Medium (Mac speed untested) |
| Indic Parler-TTS: Apache-2.0, ~0.9B params, **includes Odia** (speakers Manas, Debjani; ~19 h training data), gated; page suggests a newer Indic-Speak | https://huggingface.co/ai4bharat/indic-parler-tts | Medium (Mac speed and quality untested) |
| Meta MMS-TTS Odia (`mms-tts-ory`) is **CC-BY-NC 4.0** (non-commercial) | https://huggingface.co/facebook/mms-tts-ory | High |

### Image, video and music generation
| Finding | Source | Conf. |
|---|---|---|
| FLUX.1-schnell: Apache-2.0, 12B params, 4-step; gated; no VRAM figure given, so fit on 24 GB unified memory needs testing | https://huggingface.co/black-forest-labs/FLUX.1-schnell | Medium |
| Wan2.2: Apache-2.0; smallest TI2V-5B documented for a 24 GB NVIDIA GPU (5 s 720p in <9 min); **no Apple Silicon statement** | https://github.com/Wan-Video/Wan2.2 | Medium |
| LTX-Video: custom "open weights" license (revenue terms not read); 1216x704 @30 fps; Apple use only as a code comment | https://huggingface.co/Lightricks/LTX-Video | Low-Medium |
| ACE-Step: Apache-2.0, music with vocals up to ~4 min, 19 vocal languages (Hindi/Odia not in its top-10 list), M2 Max about 26 s per minute of audio, macOS tip `--bf16 false`; its disclaimer asks users to verify originality and disclose AI use | https://github.com/ace-step/ACE-Step | Medium |
| Stable Audio Open 1.0: Stability AI Community License (commercial terms not read), up to 47 s, trained on CC0/CC-BY/CC-Sampling+ audio, gated | https://huggingface.co/stabilityai/stable-audio-open-1.0 | Medium |
| YouTube Audio Library: YPP members may monetize videos using it; copyright-safe downloads are not claimed by Content ID; some tracks need CC attribution in the description | https://support.google.com/youtube/answer/3376882 | High |

### YouTube policy and API
| Finding | Source | Conf. |
|---|---|---|
| "Inauthentic content" (renamed from repetitious, 15 Jul 2025) covers mass-produced/templated videos with minimal variation. Reused content needs substantial commentary or modification and is judged channel-wide; creator permission does not exempt it. AI as a tool is allowed if the video shows the creator's vision. Channels where an AI persona poses as a human expert on health, legal, financial or political advice are not monetizable | https://support.google.com/youtube/answer/1311392 | High |
| AI disclosure is required for realistic altered/synthetic content (real people saying things they did not, altered real events, realistic scenes that did not occur). Clearly animated or fantastical content and AI-assisted scripts, titles, captions are exempt. Repeated non-disclosure can lead to YPP suspension | https://support.google.com/youtube/answer/14328491 | High |
| YPP: 1,000 subscribers plus 4,000 public watch hours (12 months) **or** 10M Shorts views (90 days), in a supported country. The page showed only this tier; a lower tier may exist but was not confirmed | https://support.google.com/youtube/answer/72851 | Medium |
| `videos.insert` scopes: youtube.upload etc.; max file 256 GB. **Conflict:** the page I fetched says uploads from unverified API projects "are not restricted to private viewing mode", while `docs/report.md` in this repo, and my own recollection of older docs, say they are locked to private until an audit. I could not settle this | https://developers.google.com/youtube/v3/docs/videos/insert | **Low (unresolved)** |

### Other platforms
| Platform | Finding | Source | Conf. |
|---|---|---|---|
| TikTok | Content Posting API: Direct Post needs approved `video.publish` scope; content from unaudited clients is private-only until an audit passes | https://developers.tiktok.com/doc/content-posting-api-get-started | High |
| Instagram | Professional account; Reels via `media` container then `media_publish`; media must be at a public URL; limit 100 API posts per 24 h (page also says 50 for carousels: inconsistent); Page Publishing Authorization may be required | https://developers.facebook.com/docs/instagram-platform/content-publishing | Medium |
| Threads | Video via container then `threads_publish`; max 300 s, 1 GB, H.264/HEVC + AAC, 9:16 recommended; 250 posts per 24 h; permissions not stated on that page | https://developers.facebook.com/docs/threads/posts | Medium |
| LinkedIn | Videos API (initializeUpload, 4 MB parts, finalizeUpload); `w_member_social` for members; MP4 3 s-30 min, up to 500 MB; approval process not stated on that page; captions English-only; note the 202510 API version sunsets 15 Oct 2026 | https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/videos-api | Medium |
| X | Pay-per-use only, e.g. $0.015 per post create; media upload price and video-upload permission not shown on the page fetched | https://docs.x.com/x-api/getting-started/pricing | Low-Medium |

### Claude Code extension points
| Finding | Source | Conf. |
|---|---|---|
| A skill is a folder with `SKILL.md` (YAML frontmatter, `description` recommended); lives in `~/.claude/skills`, `.claude/skills` in a repo, or a plugin; keep SKILL.md under 500 lines and move detail to reference files | https://code.claude.com/docs/en/skills | High |
| Hooks: PreToolUse can block (exit 2 or JSON `deny`), PostToolUse, Stop, SubagentStop etc.; configured in `settings.json` or plugin `hooks/hooks.json` | https://code.claude.com/docs/en/hooks | High |

## B. Comparisons and recommendations

**HyperFrames vs Remotion.** HyperFrames: Apache-2.0 with no thresholds, already installed and working here, HTML/GSAP which Claude writes fluently, and 21 official agent skills plus local skills (`hyperframes-*`, `remotion-to-hyperframes`). Remotion: React-based, mature ecosystem, but free only up to 3 employees and its license is changing in v5. **Pick HyperFrames.** Keep a scene-plan layer so Remotion could be added later.

**Local vs hosted rendering.** Measured locally: 24 s 1080x1920 video rendered in 9.8 s (repo report). Local costs nothing and keeps masters private. Hosted (HyperFrames Lambda/Docker) only if batches outgrow the laptop. **Local default**; hosted is an optional adapter.

**Local image generation vs external providers.** FLUX.1-schnell is permissively licensed, but a 12B model on 24 GB needs quantization and was not tested. Our visuals are mostly vector/HTML motion graphics, so image models are for backgrounds and thumbnails only. **Default: none needed for MVP; test FLUX schnell as optional.** External providers stay behind an adapter, off by default.

**Local TTS vs paid voices.** English: Kokoro (local, Apache-2.0). Hindi: Kokoro Hindi voices are grade C on very little data, so quality must be benchmarked by ear before use. Odia: Indic Parler-TTS (Apache-2.0) is the only open licensed candidate found; MMS is non-commercial. **Default local; paid voices only with your approval.**

**Local music vs licensed libraries.** ACE-Step runs on Apple Silicon and is Apache-2.0, but quality, originality risk and Hindi/Odia vocals are unproven. YouTube Audio Library is the safest monetizable default for YouTube; other platforms have their own music rules not yet researched. **Default: Audio Library + ACE-Step instrumentals, each track recorded in a rights ledger.**

**Original animation vs generated footage.** Original HTML animation is deterministic, cheap, editable, and clearly "original work". Generated footage on a Mac is not practical yet (Wan/LTX lack Apple Silicon support statements) and increases AI-disclosure and likeness risk. **Default: original animation.**

**Automated vs approval-based publishing.** Platform audits (TikTok), unverified-app limits (YouTube, unresolved) and YouTube's channel-level inauthentic-content review all argue for a human in the loop. **Default: approval-based; auto-publish only per platform after you enable it.**

## C. Recommended default stack
HyperFrames (render) + Kokoro (English TTS) + whisper.cpp (multilingual model to be added) + ffmpeg (QA, mix, reframe) + contentos (pipeline, ledger, gates) + Claude Code skill pack (orchestration) + YouTube Audio Library/ACE-Step (music) + ContentForge (research, decisions, publications) + approval-gated publishing. Hindi and Odia add Indic Parler-TTS and IndicConformer as optional local adapters pending benchmarks.

## D. Not researched yet
Remotion price list, TikTok/Instagram/Meta AI-label rules and music rules, X video upload, Meta app review, Spotify/Suno-style music licensing, OpenShorts internals, MoneyPrinterTurbo's current stock-footage terms (Pexels/Pixabay licenses), the WhisperX-on-MPS question, and Indic-Speak/Indic-Transcribe.
