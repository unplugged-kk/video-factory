export const STAGES = [
  "brief", "script", "voice", "compose", "render", "qa", "package", "export", "publish",
];

const LABELS = {
  draft: ["draft", "Draft"],
  pending: ["circle", "Pending"],
  queued: ["clock", "Queued"],
  not_run: ["circle", "Not run"],
  running: ["clock", "Running"],
  blocked: ["alert", "Blocked"],
  failed: ["close", "Failed"],
  stale: ["refresh", "Stale"],
  completed: ["check", "Completed"],
  passed: ["check", "Pass"],
  warning: ["alert", "Warn"],
  optional: ["circle", "Optional"],
  missing: ["close", "Not installed"],
  external: ["circle", "External"],
};

export function canonicalState(value, fallback = "pending") {
  const raw = String(value ?? "").trim().toLowerCase().replaceAll("-", "_").replaceAll(" ", "_");
  if (!raw) return fallback;
  if (["pass", "passed", "ok", "healthy", "success"].includes(raw)) return "passed";
  if (["complete", "completed", "done", "exported"].includes(raw)) return "completed";
  if (["rendered"].includes(raw)) return "completed";
  if (raw === "draft") return "draft";
  if (["run", "running", "in_progress", "active"].includes(raw)) return "running";
  if (["block", "blocked", "waiting", "awaiting_approval", "gate"].includes(raw)) return "blocked";
  if (["fail", "failed", "error", "crashed"].includes(raw)) return "failed";
  if (["stale", "orphaned"].includes(raw)) return "stale";
  if (["warn", "warning"].includes(raw)) return "warning";
  if (["not_run", "unchecked", "unknown"].includes(raw)) return "not_run";
  if (["not_installed", "missing", "unavailable"].includes(raw)) return "missing";
  if (raw === "optional") return "optional";
  if (raw === "pending") return "pending";
  if (raw === "queued") return "queued";
  if (raw === "external") return "external";
  return fallback;
}

export function statusMeta(value, fallback = "pending") {
  const state = canonicalState(value, fallback);
  const [icon, label] = LABELS[state] ?? LABELS.pending;
  return { state, icon, label };
}

export function healthReadiness(health = {}) {
  const source = health?.runReadiness;
  if (source && typeof source.ready === "boolean" && Array.isArray(source.blockers)) {
    return {
      ready: source.ready,
      profile: String(source.profile ?? "track-a/hyperframes"),
      blockers: source.blockers.map((blocker) => ({
        ...blocker,
        label: String(blocker?.label ?? blocker?.id ?? "required prerequisite"),
      })),
    };
  }
  return {
    ready: false,
    profile: "track-a/hyperframes",
    blockers: [{
      kind: "health", id: "readiness-contract", label: "run readiness",
      detail: "The server did not return a Track A readiness result.",
    }],
  };
}

export function jobView(job = {}) {
  const rawState = job.uiState ?? job.state ?? job.status ?? job.current_state;
  const status = statusMeta(rawState);
  return {
    ...job,
    id: String(job.id ?? job.content_id ?? job.job_id ?? ""),
    title: String(job.title ?? job.topic ?? job.content ?? "Untitled job"),
    aspect: String(job.aspect ?? job.format ?? job.resolution ?? "—"),
    updated: job.updated_at ?? job.updatedAt ?? job.updated ?? job.timestamp ?? null,
    status,
    stages: STAGES.map((name) => {
      const source = Array.isArray(job.stages)
        ? job.stages.find((stage) => stage.name === name || stage.stage === name)
        : job.stages?.[name];
      return { name, ...((source && typeof source === "object") ? source : {}), status: statusMeta(source?.state ?? source?.status ?? source) };
    }),
  };
}

export function checkView(check = {}) {
  if (Array.isArray(check)) {
    check = { name: check[0], status: check[1], detail: check[2], provenance: "pipeline" };
  }
  const present = check.state != null || check.status != null || check.result != null;
  const status = statusMeta(present ? (check.state ?? check.status ?? check.result) : "not_run", "not_run");
  return {
    ...check,
    name: String(check.name ?? check.check ?? "Check"),
    status,
    provenance: String(check.provenance ?? check.source ?? "not run"),
  };
}

export function listFrom(payload, ...keys) {
  if (Array.isArray(payload)) return payload;
  for (const key of keys) {
    if (Array.isArray(payload?.[key])) return payload[key];
  }
  return [];
}

export function nextAction(job = {}) {
  if (job.nextAction && typeof job.nextAction === "object") {
    return {
      label: String(job.nextAction.label ?? "No action available"),
      detail: String(job.nextAction.detail ?? ""),
      action: job.nextAction.kind ?? null,
      gate: job.nextAction.gate ?? job.gate ?? null,
      href: job.nextAction.href ?? null,
    };
  }
  const view = job.status?.state ? job : jobView(job);
  if (view.status.state === "running") return { label: "Running", detail: "The current attempt is in progress.", action: null };
  if (view.status.state === "blocked") return { label: "Review required", detail: job.blocked_reason ?? job.gate ?? "A human approval gate is waiting.", action: "review" };
  if (view.status.state === "failed") return { label: "Inspect failure", detail: job.error ?? "The latest attempt failed.", action: "logs" };
  if (view.status.state === "stale") return { label: "Resume safely", detail: "The recorded run is stale and no active lock was reported.", action: "run" };
  if (view.status.state === "completed") return { label: "Review output", detail: "The pipeline attempt completed.", action: "review" };
  return { label: "Run job", detail: "Start the next available pipeline stage.", action: "run" };
}

export const JOB_DRAFT_KEY = "contentos:new-job-draft:v1";

export function newJobDraft(capabilities = {}) {
  const voices = Array.isArray(capabilities.voices) ? capabilities.voices : [];
  const lanes = Array.isArray(capabilities.renderLanes) ? capabilities.renderLanes : [];
  const platforms = Array.isArray(capabilities.platformLimits?.platforms)
    ? capabilities.platformLimits.platforms.filter((item) => item.defaultEnabled).map((item) => item.id)
    : [];
  return {
    content_id: "", title: "", format: "9:16", kind: "short",
    platform_targets: platforms,
    voice: voices[0] ?? "",
    render: lanes[0] ?? "",
    script: [{ say: "", headline: "" }],
  };
}

export function normalizeJobDraft(value, capabilities = {}) {
  const base = newJobDraft(capabilities);
  if (!value || typeof value !== "object") return base;
  const voices = new Set(capabilities.voices ?? []);
  const lanes = new Set(capabilities.renderLanes ?? []);
  const platformIds = new Set((capabilities.platformLimits?.platforms ?? []).map((item) => item.id));
  const lines = Array.isArray(value.script)
    ? value.script.filter((line) => line && typeof line === "object").map((line) => ({
      headline: String(line.headline ?? ""), say: String(line.say ?? ""),
    })).slice(0, 200)
    : [];
  return {
    content_id: String(value.content_id ?? "").slice(0, 128),
    title: String(value.title ?? "").slice(0, 500),
    format: ["9:16", "16:9"].includes(value.format) ? value.format : base.format,
    kind: ["short", "long"].includes(value.kind) ? value.kind : base.kind,
    platform_targets: Array.isArray(value.platform_targets)
      ? [...new Set(value.platform_targets.filter((id) => platformIds.has(id)))]
      : base.platform_targets,
    voice: voices.has(value.voice) ? value.voice : base.voice,
    render: lanes.has(value.render) ? value.render : base.render,
    script: lines.length ? lines : base.script,
  };
}

export function restoreJobDraft(storage, capabilities = {}) {
  try {
    const saved = JSON.parse(storage?.getItem?.(JOB_DRAFT_KEY) ?? "null");
    return { data: normalizeJobDraft(saved?.data, capabilities), recovered: saved?.schemaVersion === 1 };
  } catch {
    return { data: newJobDraft(capabilities), recovered: false };
  }
}

export function persistJobDraft(storage, data) {
  try {
    storage?.setItem?.(JOB_DRAFT_KEY, JSON.stringify({
      schemaVersion: 1, savedAt: Date.now(), data,
    }));
    return true;
  } catch {
    return false;
  }
}

export function clearJobDraft(storage) {
  try { storage?.removeItem?.(JOB_DRAFT_KEY); } catch { /* recovery storage is best effort */ }
}

export function filterSortJobs(jobs, { query = "", state = "", kind = "", sort = "updated-desc" } = {}) {
  const needle = String(query).trim().toLowerCase();
  const selected = jobs.filter((job) => {
    if (needle && !`${job.title} ${job.id}`.toLowerCase().includes(needle)) return false;
    if (state === "draft" && !job.draft) return false;
    if (state && state !== "draft" && job.status.state !== state) return false;
    if (kind === "retry" && !(Number(job.retries) > 0)) return false;
    if (kind === "gate" && !job.gate) return false;
    return true;
  });
  const direction = sort.endsWith("-asc") ? 1 : -1;
  const field = sort.startsWith("title") ? "title" : "updated";
  return [...selected].sort((a, b) => {
    const left = field === "title" ? a.title.toLowerCase() : Number(a.updated ?? 0);
    const right = field === "title" ? b.title.toLowerCase() : Number(b.updated ?? 0);
    return left < right ? -direction : left > right ? direction : a.id.localeCompare(b.id);
  });
}

export function defaultLogStage(job = {}) {
  const stages = Array.isArray(job.stages) ? job.stages : [];
  return job.currentStage ?? job.current_stage ?? job.failedStage ?? job.failed_stage
    ?? stages.find((stage) => (stage.status?.state ?? stage.state) === "failed")?.name
    ?? "script";
}

export function formatDuration(seconds) {
  if (!Number.isFinite(Number(seconds))) return "—";
  const total = Math.max(0, Math.round(Number(seconds)));
  const minutes = Math.floor(total / 60);
  return minutes ? `${minutes}m ${total % 60}s` : `${total}s`;
}
