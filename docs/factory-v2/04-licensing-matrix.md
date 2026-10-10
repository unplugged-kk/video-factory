# 04 - Provider and licensing matrix

Checked 2026-10-10. "OK" means the license text I read allows commercial use in monetized videos. "Verify" means I did not read the full license terms and a human must before relying on it. This is a working matrix, not legal advice.

| Component | Role | License (as read) | Monetized use | Cost | Action |
|---|---|---|---|---|---|
| HyperFrames 0.8.114 | Renderer | Apache-2.0 | OK | free | none |
| Remotion | Alt renderer | Free <=3 employees, else paid; changing in v5 | OK for you today | free now | Not adopted; re-check at v5 |
| ffmpeg | Encode/QA/mix | LGPL/GPL depending on build | Verify build flags | free | Check `ffmpeg -version` configuration before redistributing binaries; we only run it locally |
| Kokoro-82M (+ONNX) | English/Hindi TTS | Apache-2.0 | OK | free | Training data stated as non-copyrighted/permissive |
| whisper.cpp + Whisper weights | STT | Not read this session | Verify | free | Expected MIT, confirm |
| WhisperX | Word alignment | BSD-2-Clause | OK | free | Mac (MPS) support unconfirmed |
| Indic Parler-TTS | Odia/Hindi TTS | Apache-2.0 (training sets CC BY / CC) | OK per page; verify gated terms | free | Needs your Hugging Face login to accept gate |
| IndicConformer-600M | Odia/Hindi ASR | MIT | OK per page; gated terms unread | free | Needs your Hugging Face login |
| MMS-TTS Odia | Odia TTS | **CC-BY-NC 4.0** | **No** | free | Do not use for monetized content |
| ACE-Step | Music gen | Apache-2.0 | Verify (no commercial statement on page) | free | Read LICENSE; log each track; disclose AI music where required |
| Stable Audio Open 1.0 | SFX/music | Stability AI Community License | Verify (terms on stability.ai/license) | free | Gated; not default |
| YouTube Audio Library | Music/SFX | YouTube terms | OK for YPP members; some tracks need CC attribution | free | Record attribution in rights ledger |
| FLUX.1-schnell | Images | Apache-2.0 | OK | free | Gated; untested on 24 GB |
| Wan2.2 | Video gen | Apache-2.0 | OK | free | No Apple Silicon support stated; not adopted |
| LTX-Video | Video gen | Custom open-weights license | Verify | free | Not adopted |
| OpenShorts | Long-to-short | MIT | OK | free | Reuse via adapter |
| MoneyPrinterTurbo | Stock b-roll lane | MIT | OK for code; **stock-clip terms (Pexels/Pixabay/Coverr) not checked** | free | Rights manifest per clip |
| OpenMontage (vendored) | Reference | **AGPL-3.0** | Code reuse restricted | free | Reference only; no code copied into this project |
| youtube-agent-skill (vendored) | Skills | MIT | OK | free | none |
| video-factory / ContentForge | Own code | No license file | Yours | free | Add a LICENSE if you ever share them |
| YouTube Data API | Publish/analytics | Google API terms | OK | free quota (10,000 units/day per repo config) | OAuth by you; see private-lock conflict in 03 |
| TikTok Content Posting API | Publish | TikTok terms | Public posting only after audit | free | Start in private/upload mode |
| Instagram Graph API | Publish | Meta terms | OK, professional account | free | App review unverified |
| Threads API | Publish | Meta terms | OK | free | Permissions unverified |
| LinkedIn Videos API | Publish | LinkedIn terms | OK with `w_member_social` | free | Approval path unverified |
| X API | Publish | Pay-per-use | OK | ~$0.015 per post create | **Costs money: needs your approval** |

## Content rules that bind every video
1. Every asset (music, stock clip, font, image, voice) gets a row in an `assets-rights.json` ledger with source URL, license, attribution text, and who approved it. QA fails if a used asset has no row.
2. Realistic AI-altered or synthetic content needs YouTube's "AI use" disclosure; clearly animated content is exempt. The pipeline will set a `disclosure` field and require you to confirm it per video.
3. Third-party songs and podcast clips are not used unless you hold written permission or a license. The tool will refuse to start a lyric job without a rights entry.
4. Templates must vary per video (script, structure, visuals); a repeat-detector in QA flags near-identical videos because YouTube judges inauthentic content at the channel level.
5. No AI persona presenting health, legal, financial or political advice as an expert.
