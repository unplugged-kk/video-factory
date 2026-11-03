/**
 * Disposable v1 ContentForge contract → contentos factory job adapter.
 * All v1 mapping lives here; delete this folder when contract v2 ships.
 */
import { readFileSync } from "node:fs";

import { deriveScenes } from "./scene-derivation.mjs";

export const DISPOSABLE_ADAPTER_MODULE = "contentos/adapters/v1/contract_adapter.mjs";

export const CONTRACT_VERSION = "video-factory.contract.v1";

/** Kokoro ids from `hyperframes tts --list` (research 02). */
export const KOKORO_VOICE_IDS = new Set(
  JSON.parse(readFileSync(new URL("../../kokoro_voice_ids.json", import.meta.url), "utf8")),
);

/** Machine-readable capability matrix written by `python -m contentos.lang matrix --write`. Read at call time so a refresh needs no restart. */
const CAPS_URL = new URL("../../../config/language-capabilities.json", import.meta.url);

export function loadLanguageCaps(url = CAPS_URL) {   // url is a seam for tests; production always reads the repo snapshot
  return JSON.parse(readFileSync(url, "utf8"));
}

/** Share of letters (and combining marks) that fall in the language's Unicode ranges, as the Python validator computes it. */
export function scriptShare(text, ranges) {
  const bounds = ranges.map((r) => r.split("-").map((h) => parseInt(h, 16)));
  const letters = [...text.normalize("NFC")].filter((c) => /[\p{L}\p{M}]/u.test(c));
  if (!letters.length || !bounds.length) return 0;
  return letters.filter((c) => bounds.some(([a, b]) => c.codePointAt(0) >= a && c.codePointAt(0) <= b)).length / letters.length;
}

const JOB_ID_RE = /^cfvg-[1-9][0-9]{0,9}$/;

const QUALITY_TO_HYPERFRAMES = {
  draft: "draft",
  medium: "looks",
  high: "delivery",
};

/**
 * @param {unknown} raw CONTRACT.json payload
 * @param {{ authorizedBy?: string }} opts factory-mode authorization (production job submitter)
 * @returns {{ ok: true, contentosSpec: object, factorySettings: object } | { ok: false, permanent: true, code: string, message: string }}
 */
export function adaptV1Contract(raw, opts = {}) {
  if (!raw || typeof raw !== "object") {
    return permanent("invalid_contract", "Video Factory contract must be an object");
  }
  const record = raw;

  if (record.contractVersion !== CONTRACT_VERSION) {
    return permanent(
      "unsupported_contract_version",
      `unsupported Video Factory contract version "${String(record.contractVersion ?? "")}"`,
    );
  }

  const jobId = String(record.jobId ?? "");
  if (!JOB_ID_RE.test(jobId)) {
    return permanent("invalid_job_id", `Video Factory job id "${jobId.slice(0, 60)}" is not allowlisted`);
  }

  const format = record.format;
  if (format === "1:1") {
    return permanent("unsupported_format", "format 1:1 is not supported in contentos v1 adapter");
  }
  if (format !== "9:16" && format !== "16:9") {
    return permanent("unsupported_format", `format "${String(format)}" is not supported`);
  }

  const voice = record.voice;
  if (!voice || typeof voice !== "object") {
    return permanent("invalid_voice", "voice spec is required");
  }
  if (voice.enabled === false) {
    return permanent("voiceless_not_supported", "voiceless jobs are not supported; voice.enabled must be true");
  }

  // Language: absent means English and takes exactly the original path. Others are gated by the capability matrix.
  const langField = record.language;
  const languageCode = langField === undefined || langField === null ? "en" : typeof langField === "string" ? langField : String(langField?.code ?? "");
  let caps = null;
  if (languageCode !== "en") {
    let matrix;
    try {
      matrix = opts.languageCaps ?? loadLanguageCaps(opts.languageCapsUrl);
    } catch (e) {
      return permanent("language_matrix_unavailable", `cannot read config/language-capabilities.json: ${e.message}`);
    }
    caps = matrix.languages?.[languageCode];
    if (!caps) {
      return permanent("unsupported_language", `language "${languageCode.slice(0, 12)}" is not supported; supported: ${["en", ...Object.keys(matrix.languages ?? {}).filter((k) => k !== "en")].join(", ")}`);
    }
    if (caps.status === "blocked") {
      return permanent("language_blocked", `${caps.name} (${languageCode}) cannot be produced on this factory yet: ${String(caps.status_reason).slice(0, 400)}`);
    }
  }

  const defaultVoice = caps ? caps.default_voice : "af_heart";
  const voiceId = typeof voice.id === "string" && voice.id.trim() ? voice.id.trim() : defaultVoice;
  if (!caps && !KOKORO_VOICE_IDS.has(voiceId)) {
    return permanent("unknown_voice_id", `Kokoro voice id "${voiceId}" is not in the factory allowlist`);
  }
  if (caps && !caps.voices.includes(voiceId)) {
    return permanent("invalid_voice", `voice "${voiceId}" is not valid for ${caps.name}; valid: ${caps.voices.join(", ")}`);
  }

  const render = record.render && typeof record.render === "object" ? record.render : {};
  const contractQuality = render.quality ?? "high";
  if (contractQuality !== "draft" && contractQuality !== "medium" && contractQuality !== "high") {
    return permanent("invalid_render_quality", `render quality "${String(contractQuality)}" is not allowlisted`);
  }
  const hyperframesQuality = QUALITY_TO_HYPERFRAMES[contractQuality];

  const title = typeof record.title === "string" && record.title.trim() ? record.title.trim() : jobId;
  const brief = typeof record.brief === "string" ? record.brief.trim() : "";
  if (!brief) {
    return permanent("missing_brief", "brief is required");
  }

  const script = deriveScenes({
    title,
    brief,
    script: record.script ?? null,
    storyboard: record.storyboard ?? null,
    language: languageCode,
  });
  if (!script.length) {
    return permanent("empty_derivation", "scene derivation produced no script lines");
  }
  if (caps && caps.subtitle.min_script_share > 0) {
    const bad = script
      .map((ln, i) => [i + 1, scriptShare(ln.say, caps.subtitle.unicode_ranges)])
      .filter(([, share]) => share < caps.subtitle.min_script_share);
    if (bad.length) {
      return permanent(
        "script_language_mismatch",
        `the script is not in ${caps.name}: scene ${bad.map(([n, s]) => `${n} (${Math.round(s * 100)}% ${caps.subtitle.script})`).join(", ")}; needs at least ${Math.round(caps.subtitle.min_script_share * 100)}% of letters in ${caps.subtitle.script} script`,
      );
    }
  }

  const advisoryDurationMs =
    typeof record.durationMs === "number" && Number.isInteger(record.durationMs) && record.durationMs > 0
      ? record.durationMs
      : null;

  const authorizedBy = typeof opts.authorizedBy === "string" && opts.authorizedBy.trim()
    ? opts.authorizedBy.trim()
    : "factory-mode:production-job";

  const contentosSpec = {
    content_id: jobId,
    title,
    format,
    voice: voiceId,
    ...(caps ? { language: languageCode } : {}),
    script,
    /** Passed through to render stage by factory worker (not standalone pipeline today). */
    _v1_hyperframes_quality: hyperframesQuality,
  };

  const factorySettings = {
    contractVersion: CONTRACT_VERSION,
    jobId,
    format,
    voiceId,
    language: languageCode,
    languageStatus: caps ? caps.status : "production-ready",
    contractRenderQuality: contractQuality,
    hyperframesQuality,
    advisoryDurationMs,
    authorizedBy,
    sceneCount: script.length,
  };

  return { ok: true, contentosSpec, factorySettings };
}

function permanent(code, message) {
  return { ok: false, permanent: true, code, message };
}
