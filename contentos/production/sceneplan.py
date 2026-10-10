"""Scene plan ("sceneplan/1"): language-neutral scenes anchored to NARRATION WORDS, not to guessed seconds.
Each scene names the first script word it starts on (`starts_at`, a 0-based word index or an exact word-text phrase).
resolve() turns anchors into real times from the aligned audio, so the storyboard is always in sync with the voice,
and the same plan feeds every aspect ratio (the 16:9 and 9:16 builders only differ in layout)."""
import re

from .align import norm


def _find_phrase(words, phrase, after=0):
    target = [norm(x) for x in phrase.split()]
    for i in range(after, len(words) - len(target) + 1):
        if [norm(w[0]) for w in words[i:i + len(target)]] == target:
            return i
    raise ValueError(f"scene anchor phrase not found in narration: {phrase!r}")


def resolve(plan, words, audio_end, lead=0.0, tail=0.0):
    """plan: dict with scenes[{id,title,starts_at,...}]. words: [(word,start,end)] from align_words.
    Returns scenes with t0,t1 (seconds) and word range i0..i1; scene 1 begins at 0, last ends at audio_end+tail."""
    out, cursor = [], 0
    for sc in plan["scenes"]:
        a = sc["starts_at"]
        i = a if isinstance(a, int) else _find_phrase(words, a, cursor)
        if out and i <= out[-1]["i0"]:
            raise ValueError(f"scene {sc['id']} anchor is not after the previous scene")
        out.append({**sc, "i0": i})
        cursor = i + 1
    out[0]["i0"] = 0
    for k, sc in enumerate(out):
        sc["t0"] = 0.0 if k == 0 else round(max(words[sc["i0"]][1] - lead, out[k - 1]["t0"] + 0.5), 3)
    for k, sc in enumerate(out):
        sc["t1"] = out[k + 1]["t0"] if k + 1 < len(out) else round(audio_end + tail, 3)
        sc["i1"] = (out[k + 1]["i0"] if k + 1 < len(out) else len(words)) - 1
        sc["narration"] = " ".join(w[0] for w in words[sc["i0"]:sc["i1"] + 1])
    return out


def storyboard_md(plan, scenes, title, fmt_note=""):
    """Timestamped storyboard table generated from the resolved plan (so it can never drift from the audio)."""
    def ts(x):
        return f"{int(x // 60)}:{x % 60:05.2f}"
    lines = [f"# Storyboard - {title}", "", fmt_note, "",
             "| # | Time | Narration (script words) | Visual action | Transition in | Caption text |",
             "|---|------|--------------------------|---------------|---------------|--------------|"]
    for n, s in enumerate(scenes, 1):
        esc = lambda x: re.sub(r"\s*\n\s*", " ", str(x)).replace("|", "\\|")  # noqa: E731
        lines.append(f"| {n} {esc(s['title'])} | {ts(s['t0'])}-{ts(s['t1'])} | {esc(s['narration'])} | {esc(s.get('visual', ''))} | "
                     f"{esc(s.get('transition', ''))} | {esc(s.get('caption_note', 'word-synced, script words'))} |")
    return "\n".join(lines) + "\n"
