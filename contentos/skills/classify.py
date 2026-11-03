"""Derive each creative skill's contract from the bundle itself (catalog entry + SKILL.md text), then a status from a live probe.

Nothing here is a hand-typed "works" claim. Rules are regexes over the skill's own text; the few curated tables
(SCENEKIT_MAP, IP_SENSITIVE, EFFECT) are explicit, short and tested. A status of integrated-and-tested is never
assigned by this module: it needs recorded render evidence (see EVIDENCE in registry.py).
"""
from __future__ import annotations

import re

# --- inputs the skill needs from the user, from "Original invocation brief" ------------------------------------------
INPUT_RULES = [
    ("song", r"song mp3|rap song|hindi song|aarti mp3|\bsong\b|clip of it"),
    ("lyrics", r"lyrics|devanagari|one sung line"),
    ("voiceover_audio", r"voiceover|voice mp3|dialogue audio|dialogue \(mp3\)|audio clip|podcast clip|pravachan|interview audio|clip audio|show clip|audio \(mp3\)"),
    ("footage", r"talking-head clip|model video|lesson recording|clip of you|three clips|video \(mp4\)|\(mp4|folder of my b-roll|long 16:9 video|video clips|\d clips|clips or photos|your model video"),
    ("photos", r"photos|images|screenshots|cover (art|image)|logo png|drawings"),
    ("script_or_topic", r"\bscript\b|\btopic\b|article links|two places|facts or numbers|joke"),
]
# talking-head skills (ids 52+) say "with a 9:16 talking-head clip"; voiceover-only skills can run on Kokoro audio
OWN_VOICE_OK = {"personal-explainer", "blueprint-explainer", "news-report"}

# --- requirements implied by the skill's text -------------------------------------------------------------------------
REQ_RULES = [
    ("align.forced_mms", r"torchaudio|mms_fa"),
    ("asr.word_timing_en", r"word-level timings|transcribe my audio|caption.{0,40}every word|word-by-word"),
    ("cv.person_matte", r"behind (my|the|your) (head|body)|behind me|cut out|cutout of|around me|my body (cut|in front)|body cut"),
    ("cv.face_detect", r"never cover my face|never re-grade or filter my face|face doodles|keep the person fully in frame"),
    ("audio.beat_detect", r"\bbeat(s)?\b|on the beat|every beat|music hit|downbeat|bpm"),
    ("3d.blender", r"\bblender\b|\bbpy\b"),
    ("data.world_atlas", r"world-atlas|natural earth|great-circle"),
    ("net.yt_dlp", r"youtube link|yt-dlp|find the best moments in a long youtube"),
    ("render.remotion", r"\bremotion\b|usecurrentframe"),
]
HINDI = r"hindi|devanagari|hinglish|haryanvi|odia"

# fallbacks that exist in THIS factory, by missing capability
FALLBACKS = {
    "align.forced_mms": ("asr.word_timing_en", "whisper.cpp word timing (English model only) via `hyperframes transcribe` + production/align.py; "
                                              "lines in other languages get author-supplied timing labelled unverified"),
    "cv.person_matte": (None, "no-matte variant: put the graphic beside or above the speaker instead of behind them; never fake a matte"),
    "cv.face_detect": (None, "fixed face-safe zones from the platform safe-zone config; reviewer checks the contact sheet by eye"),
    "audio.beat_detect": (None, "owner-supplied beat times in the spec, or word onsets from ASR; beat sync is labelled unverified"),
    "render.remotion": ("render.hyperframes", "implement the same pure-function-of-time animation as a HyperFrames GSAP timeline (no second renderer)"),
    "asr.word_timing_multilingual": (None, "author-supplied line/word timing from the lyrics file, labelled unverified; or install a multilingual whisper model after approval"),
    "tts.hindi": (None, "user supplies the Hindi audio (supplied_audio ingest with rights record); no Hindi TTS is generated"),
}
BLOCKING = {   # no verified fallback: the skill's core promise cannot be met without it
    "3d.blender": "Blender is not installed and a 3D look cannot be faked in HyperFrames; install needs owner approval (GPL, ~300 MB)",
    "data.world_atlas": "needs the world-atlas npm dataset for real map boundaries; `npm install` needs owner approval (licence vetting first)",
    "net.yt_dlp": "yt-dlp on PATH is an x86 build that dies with 'bad CPU type'; `brew install yt-dlp` (arm64) needs approval. Also downloads third-party video: rights gate applies",
}

# explicit, reviewable tables ------------------------------------------------------------------------------------------
SCENEKIT_MAP = {   # creative skill -> (scenekit style, what is only approximated)
    "blueprint-explainer": ("blueprint-architecture", "short 9:16 or 16:9 narrated explainer with real diagram, steps and bar-chart scenes; NOT built: sheet title block with numbers, live EMI-style calculation tables, 3-10 minute length"),
    "personal-explainer": ("clean-explainer", "narrated explainer with diagrams, steps, compare and sourced stat scenes; NOT built: embedded real footage with on-screen credit"),
    "news-report": ("kinetic-type", "flat dark ground, hard cuts and hard-hitting type; NOT built: screenshot cards with red boxes, memes, the presenter in frame"),
}
IP_SENSITIVE = {   # name a copyrighted work, character or living creator; original characters and assets only
    "anime-reel": "named anime series", "titan-anime": "Attack on Titan setting", "anime-fight": "One-Punch Man style hero",
    "mirzapur-video": "Mirzapur characters", "comic-reel": "named film scene", "madira-peekar-soo-gaye": "named film dialogue",
    "latent-reel": "India's Got Latent people", "latent-comic": "India's Got Latent people", "woof-woof": "a living streamer",
    "pusho-reel": "a living creator's character", "baba-pusho": "a living creator's character",
    "podcast-comic": "real podcast guests", "podcast-cartoon": "real podcast guests", "podcast-explainer": "real podcast guests",
    "maut-ke-bare-mai-sochte-ho": "real podcast guests", "street-interview": "real interviewees (consent)",
    "katha-video": "a real speaker's recording", "rap-video": "a named rapper's look", "neon-lyrics": "a named rapper's look",
    "red-rap-lyrics": "a named artist", "bairan-style": "a named song", "kids-story": "a named children's story",
}
EXTERNAL_MEDIA_RIGHTS = {"youtube-clips", "latent-comic", "latent-reel", "podcast-comic", "podcast-cartoon", "katha-video", "street-interview"}


def _src(text: str) -> str:
    m = re.search(r"## Creative brief preserved from source(.*?)## Quality checklist", text, re.S)
    return (m.group(1) if m else text).lower()


def brief(text: str) -> str:
    m = re.search(r"Original invocation brief: (.*)", text)
    return re.sub(r"save it as \S+ so i can run /\S+ ", "", m.group(1).lower()) if m else ""


def classify(entry: dict, text: str) -> dict:
    name, sid = entry["name"], entry["id"]
    src, b = _src(text), brief(text)
    inputs = [k for k, r in INPUT_RULES if re.search(r, b)]
    if "footage" in inputs and "voiceover_audio" in inputs and "talking-head" in b:
        inputs.remove("voiceover_audio")
    if name in OWN_VOICE_OK and "voiceover_audio" in inputs:
        inputs.remove("voiceover_audio")        # Kokoro can narrate a script; a supplied voice is optional
        if "script_or_topic" not in inputs:
            inputs.append("script_or_topic")
    reqs = [k for k, r in REQ_RULES if re.search(r, src) or re.search(r, entry["description"].lower())]
    if re.search(HINDI, src + " " + b + " " + entry["description"].lower()):
        reqs += ["asr.word_timing_multilingual"]
    if "song" in inputs or "voiceover_audio" in inputs or "footage" in inputs:
        reqs.append("media.supplied_audio_ingest")
    reqs.append("render.hyperframes")           # every recipe renders through the one renderer
    reqs = list(dict.fromkeys(reqs))
    role = "format" if sid <= 51 else "effect"
    return {"inputs_required": list(dict.fromkeys(inputs)), "requires": reqs, "role": role,
            "ip_sensitive": IP_SENSITIVE.get(name), "external_media_rights": name in EXTERNAL_MEDIA_RIGHTS,
            "scenekit": SCENEKIT_MAP.get(name)}


def readiness(c: dict, status: str) -> str:
    """What stands between this skill and a render today: blocked | needs-user-media | ready-to-run (script/topic only)."""
    if status.startswith("blocked"):
        return "blocked"
    media = {"song", "lyrics", "voiceover_audio", "footage", "photos"} & set(c["inputs_required"])
    return "needs-user-media" if media else "ready-to-run"


def decide(c: dict, probe: dict) -> dict:
    """Status from requirements x probe. Returns {status, missing, fallbacks_used, blockers, limitations}."""
    missing, used, blockers, limits = [], [], [], []
    for r in c["requires"]:
        if probe.get(r, {}).get("ok"):
            continue
        missing.append(r)
        if r in BLOCKING:
            blockers.append(f"{r}: {BLOCKING[r]}")
        elif r in FALLBACKS:
            sub, how = FALLBACKS[r]
            if sub is None or probe.get(sub, {}).get("ok"):
                used.append({"capability": r, "fallback": how})
            else:
                blockers.append(f"{r}: fallback {sub} also unavailable")
        else:
            blockers.append(f"{r}: unavailable")
    if c["ip_sensitive"]:
        limits.append(f"names {c['ip_sensitive']}: use original characters and assets only (bundle AGENTS.md; no copying a living creator's signature)")
    if c["external_media_rights"]:
        limits.append("uses third-party/source media: record rights status before any publish (supplied_audio rights record)")
    media = [i for i in c["inputs_required"] if i != "script_or_topic"]
    if media:
        limits.append("needs user-supplied media: " + ", ".join(media) + " (none is in the repo, so no end-to-end render was possible)")
    if blockers:
        status = "blocked-by-dependency"
    elif used:
        status = "adapted-with-fallback"
    else:
        status = "integrated-but-not-fully-tested"
    return {"status": status, "missing": missing, "fallbacks_used": used, "blockers": blockers, "limitations": limits}
