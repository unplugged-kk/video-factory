# 02 - What the two guides teach (and where they fall short)

Sources: `Claude-Code-Lyric-Video-Guide.pdf` (11 pp) and `Claude-Code-Podcast-Explainer-Guide.pdf` (10 pp). Both are beginner guides built on Claude Code + HyperFrames.

## Lyric video workflow
1. Input is an MP3 plus the YouTube link (used only to research the correct lyrics and meaning).
2. Claude separates vocals from music, then times every lyric line to the singing. The guide mentions a ~3 GB voice-detection model downloaded once.
3. Claude proposes a theme and per-line scene/camera plan (examples: eye motif, auto-rickshaw ride, watercolour paper boat, puppet strings).
4. HTML compositions rendered through HyperFrames; style, lyric script (romanized Hindi / Hindi / English) and aspect (16:9 or 9:16) are prompt parameters.
5. Claude snapshots frames, inspects them and fixes issues itself, then renders.
6. Iteration is by "timestamp + what you want", screenshots, one idea per message, and saving versions (v1) before big changes.
- Timings quoted: 20-60 min build for a 3-minute song; render ~3-5x song length (8-15 min); master can exceed 1 GB due to film grain; ask for a 100-150 MB share copy.
- Pitfall: "No composition found" means the wrong folder (must contain `index.html`).

## Podcast explainer workflow
1. Input is a 30-90 s MP3 clip (best: one clear idea). Transcript optional, helps spelling.
2. Word-level transcription, then split into idea chapters ("01 The feeling...").
3. Cartoon host with lip-sync, blinks, nods, gestures; cut to full-screen motion graphics, host kept in a small "LIVE" corner window.
4. Different camera angles on the host (wide, close, over the mic), word-by-word highlighted captions, chapter labels.
5. A screenshot of the speaker and studio makes the cartoon resemble them.
6. 9:16 is a re-arrangement, not a re-draw: graphic on top and host below during explainers, host full-frame otherwise, title banner, captions placed clear of platform buttons.
7. Outputs: a master MP4 and a `-share.mp4` of ~10-15 MB.
- Timing quoted: ~1 hour first video; ~1 minute render per 1 minute of video.

## Technical assumptions both guides make
HyperFrames (HTML + GSAP to MP4 via headless Chrome and ffmpeg), ffmpeg, a local speech-to-text model, Claude Code installed and logged in, ~5 GB free disk, internet for first installs. Neither guide names exact versions, and both rely on Claude installing tools on request.

## Design principles worth keeping
- Every spoken idea gets a visual at the moment it is said (cards pop on each word).
- One scene plan feeds both aspect ratios.
- Captions are word-synced and kept inside safe areas.
- The agent checks frames itself before rendering; the human directs by timestamp.
- Keep versions and a small share copy separate from the master.

## Limitations and risks I found
| Issue | Why it matters |
|---|---|
| Both guides are written for personal use, not monetization | Neither addresses YouTube's inauthentic-content or reused-content rules |
| Lyric guide: the song is a third-party work | A video using it can get claimed or blocked; the guide itself warns about this |
| Podcast guide: step 2 downloads from a third-party converter site | Ripping YouTube audio breaks YouTube's terms; the lyric guide says so explicitly. I will not build this step |
| Podcast guide: re-animating someone else's audio | YouTube's reused-content policy applies even with permission from the creator; commentary or added value is needed. Fine for clips we own or are licensed to use |
| "Cartoon of a real speaker" | Fine as a labeled fan animation per the guide, but a likeness of a real person needs care; for our channel use original characters |
| No quality gate beyond eyeballing frames | The mission requires automated checks |
| No multilingual handling | Hindi/Odia need separate STT, TTS, fonts and review |
| Several figures (render speed, tool sizes) are anecdotal | Treat as unverified until measured on this Mac |

## Decision
Reuse the *ideas* (timestamp direction, chaptered explainer, host-plus-graphics layout, reframe-not-redraw, snapshot-then-fix loop). Build them as templates on top of the existing contentos pipeline. Use only rights-cleared or original audio. The podcast template will work on audio we own, original recordings, or clips with written permission.
