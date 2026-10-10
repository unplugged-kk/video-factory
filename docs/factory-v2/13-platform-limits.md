# Platform video limits (research snapshot, 2026-10-11)

Data lives in `config/platforms.json` (schema `platforms/1`); code in `contentos/production/platforms.py`; tests in `tests/test_platforms.py`. Limits change often: re-check any row not marked official before relying on it.

## Owner policy
Short-form: hard ceiling 5 minutes (300 s), default target 3 minutes (180 s); shorter is fine. Long-form: no owner ceiling yet (only platform limits apply). Platform limits are usually tighter than the owner ceiling, and the checker applies both.

## Limits found
| Platform | Short-form | Long-form | Confidence | Notes |
|---|---|---|---|---|
| YouTube | Shorts up to 3 min, vertical or square, max 1080p | 15 min by default; longer after verification, absolute maximum 256 GB or 12 h | Official (YouTube Help) | Shorts limit rose from 60 s in Oct 2024 (vendor report) |
| Instagram | Reels 3 min safe limit; aspect 1.91:1 to 9:16, at least 30 fps and 720 px | Not recorded | Official for aspect, fps, size; length from an Instagram executive's announcement | Vendor and news reports say the in-app camera records 20 min and camera-roll uploads 15 min, but no first-party page; Instagram only recommends Reels under 3 min |
| X | 140 s, 512 MB (standard account) | Premium: under 4 h, 16 GB (720p above 2 h) | Official help page | A vendor page says 3 h and 8 GB; the official page is used. Premium is paid, so off unless opted in |
| Threads | 5 min (300 s), 1 GB, 23-60 fps, HEVC or H.264, MOV or MP4 | None recorded | Official (API docs, Threads account) | 9:16 recommended |
| LinkedIn | 10 min and 5 GB are widely cited | same | Third-party only | LinkedIn's help page could not be read (fetch blocked); verify |
| TikTok | 3 min or 10 min depending on the source | n/a | Conflicting; TikTok's help page gives no number | Blocked in India since 29 June 2020 (vendor report); disabled by default |

Implication: a 3-minute master fits YouTube Shorts, Instagram, Threads and LinkedIn but not X (140 s); a 5-minute master fits only Threads and LinkedIn. Pick the platforms for the episode, or cut an X version of at most 140 s.

## Not researched yet
Facebook Reels, Snapchat Spotlight, and the Indian apps Moj, Josh and ShareChat (vendor lists say they are available in India; no limits checked). Add them to `platforms.json` once researched.

## Commands
```
python -m contentos.production.platforms list
python -m contentos.production.platforms budget --kind short
python -m contentos.production.platforms budget --kind long
python -m contentos.production.platforms check --kind short --seconds 56 --aspect 9:16
python -m contentos.production.director check PLAN --script SCRIPT --kind short
```
Flags: `--platforms a,b`, `--tier youtube=verified`, `--opt-in x`, `--include-disabled`, `--ceiling SECONDS`.

## Sources
- YouTube Help: [Shorts](https://support.google.com/youtube/answer/10059070), [upload limits](https://support.google.com/youtube/answer/71673)
- Instagram Help: [Reels requirements](https://help.instagram.com/1038071743007909); [Mosseri on 3-minute Reels](https://www.threads.com/@mosseri/post/DE-efFqyStv); [Social Media Today on the 20-minute camera](https://www.socialmediatoday.com/news/instagram-update-reels-camera-with-improved-functions/806247/); [Buffer](https://buffer.com/library/instagram-reels-length)
- X Help: [videos on X](https://help.x.com/en/using-x/x-videos)
- Threads: [API docs](https://developers.facebook.com/docs/threads/posts/), [official post](https://www.threads.com/@threads/post/CyyjSsxuCkI/good-question-you-can-attach-videos-up-to-5-minutes-long-to-a-post-on-threads)
- LinkedIn (vendor): [Kompozy](https://kompozy.io/specs/linkedin-file-size-limit)
- TikTok (vendor): [Sendcove](https://www.sendcove.app/integrations/tiktok/video-specs); India status: [Fluxnote](https://fluxnote.io/guides/tiktok-monetization-india-2026)
