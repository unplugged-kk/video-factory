/**
 * Deterministic v1 adapter scene derivation (ticket 01).
 * Disposable with contentos/adapters/v1/contract_adapter.mjs when v2 arrives.
 */

const MAX_SCENES = 12;
const MAX_SAY = 420;
const MAX_HEADLINE = 48;
const MAX_BROLL = 80;

const STOP = new Set(
  "a an the and or but in on at to for of is are was were be been being it this that with from as by not you your we they".split(
    " ",
  ),
);

export function normalizeText(raw, maxLen) {
  if (typeof raw !== "string") return "";
  let s = raw.replace(/\0/g, "").replace(/\r\n/g, "\n").trim();
  if (!s) return "";
  if (s.length > maxLen) s = s.slice(0, maxLen);
  return s;
}

export function stripMarkdownInline(s) {
  return s
    .replace(/<[^>]+>/g, " ")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/_([^_]+)_/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .trim();
}

function splitSentences(text) {
  const cleaned = stripMarkdownInline(text.replace(/\n+/g, " "));
  if (!cleaned) return [];
  const protectedText = cleaned
    .replace(/\b(e\.g\.|i\.e\.|U\.S\.|U\.K\.|Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.|Sr\.|Jr\.|vs\.|etc\.)/gi, (m) => m.replace(/\./g, "\u0000"))
    .replace(/(\d)\.(\d)/g, "$1\u0001$2");
  const parts = protectedText
    .split(/(?<=[.!?])\s+(?=[A-Z0-9"'(])/)
    .map((p) => p.replace(/\u0000/g, ".").replace(/\u0001/g, ".").trim())
    .filter(Boolean);
  return parts.length ? parts : [cleaned];
}

const SCENE_MARKER = /^(?:#{1,3}\s+|scene\s+\d+\s*[:.\-–]\s*|\d+[.)]\s+|[-*•]\s+)/i;

export function splitStoryboardBlocks(storyboard) {
  const lines = storyboard.split("\n");
  const blocks = [];
  let cur = [];
  for (const line of lines) {
    const t = line.trim();
    if (!t) {
      if (cur.length) {
        blocks.push(cur.join(" ").trim());
        cur = [];
      }
      continue;
    }
    if (SCENE_MARKER.test(t) && cur.length) {
      blocks.push(cur.join(" ").trim());
      cur = [t.replace(SCENE_MARKER, "").trim()];
    } else {
      cur.push(t.replace(SCENE_MARKER, "").trim());
    }
  }
  if (cur.length) blocks.push(cur.join(" ").trim());
  return blocks.filter(Boolean);
}

function headlineFromSay(say) {
  const plain = stripMarkdownInline(say).replace(/\s+/g, " ").trim();
  if (!plain) return "Untitled scene";
  const words = plain.split(/\s+/);
  const isAllCaps = plain === plain.toUpperCase() && /[A-Z]/.test(plain);
  let h = words.slice(0, 8).join(" ");
  if (h.length > MAX_HEADLINE) h = `${h.slice(0, MAX_HEADLINE - 1)}…`;
  if (!isAllCaps) {
    h = h.charAt(0).toUpperCase() + h.slice(1);
  }
  return h;
}

function tagForIndex(i, total, say) {
  const lower = say.toLowerCase();
  if (i === 0) return "HOOK";
  if (i === total - 1 && /\b(follow|subscribe|link|comment|share|part two|next)\b/.test(lower)) return "CTA";
  if (i === total - 1 && total > 1) return "CLOSE";
  return `STEP ${i + 1}`;
}

function brollPhrase(say, headline) {
  const raw = `${headline} ${say}`.toLowerCase();
  const tokens = raw
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(/\s+/)
    .filter((w) => w.length > 2 && !STOP.has(w));
  const uniq = [...new Set(tokens)].slice(0, 5);
  const phrase = uniq.join(" ").trim();
  if (!phrase) return "technology abstract background";
  return phrase.length > MAX_BROLL ? phrase.slice(0, MAX_BROLL) : phrase;
}

function mergeShortSentences(sentences) {
  const out = [];
  for (const s of sentences) {
    if (out.length && s.length < 40 && out[out.length - 1].length + s.length + 1 <= MAX_SAY) {
      out[out.length - 1] = `${out[out.length - 1]} ${s}`;
    } else if (s.length > MAX_SAY) {
      const words = s.split(/\s+/);
      let chunk = "";
      for (const w of words) {
        const next = chunk ? `${chunk} ${w}` : w;
        if (next.length > MAX_SAY && chunk) {
          out.push(chunk);
          chunk = w;
        } else chunk = next;
      }
      if (chunk) out.push(chunk);
    } else out.push(s);
  }
  return out.slice(0, MAX_SCENES);
}

export function deriveScenes(job) {
  const title = normalizeText(job.title, 200);
  const brief = normalizeText(job.brief, 8000);
  const script = normalizeText(job.script, 50000);
  const storyboard = normalizeText(job.storyboard, 50000);

  let segments;
  if (storyboard) {
    segments = splitStoryboardBlocks(storyboard);
  } else if (script) {
    segments = splitSentences(script);
  } else {
    segments = splitSentences(brief);
  }
  if (!segments.length && brief) segments = [brief];
  if (!segments.length && title) segments = [title];

  segments = mergeShortSentences(segments);
  if (!segments.length) {
    return [{ say: title || "Video", headline: headlineFromSay(title || "Video"), tag: "HOOK", broll: "abstract motion background" }];
  }

  return segments.map((say, i) => {
    const headline = headlineFromSay(say);
    return {
      say: say.slice(0, MAX_SAY),
      headline,
      tag: tagForIndex(i, segments.length, say),
      broll: brollPhrase(say, headline),
    };
  });
}
