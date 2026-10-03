/**
 * Disposable v1 ContentForge contract → contentos factory job adapter.
 * All v1 mapping lives here; delete this folder when contract v2 ships.
 */
import { deriveScenes } from "./scene-derivation.mjs";

export const DISPOSABLE_ADAPTER_MODULE = "contentos/adapters/v1/contract_adapter.mjs";

export const CONTRACT_VERSION = "video-factory.contract.v1";

/** Kokoro ids from `hyperframes tts --list` (research 02). */
export const KOKORO_VOICE_IDS = new Set([
  "af_heart",
  "af_nova",
  "af_sky",
  "am_adam",
  "am_michael",
  "bf_emma",
  "bf_isabella",
  "bm_george",
  "ef_dora",
  "ff_siwis",
  "jf_alpha",
  "zf_xiaobei",
]);

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

  const voiceId = typeof voice.id === "string" && voice.id.trim() ? voice.id.trim() : "af_heart";
  if (!KOKORO_VOICE_IDS.has(voiceId)) {
    return permanent("unknown_voice_id", `Kokoro voice id "${voiceId}" is not in the factory allowlist`);
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
  });
  if (!script.length) {
    return permanent("empty_derivation", "scene derivation produced no script lines");
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
    script,
    /** Passed through to render stage by factory worker (not standalone pipeline today). */
    _v1_hyperframes_quality: hyperframesQuality,
  };

  const factorySettings = {
    contractVersion: CONTRACT_VERSION,
    jobId,
    format,
    voiceId,
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
