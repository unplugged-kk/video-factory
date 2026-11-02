export class ApiError extends Error {
  constructor(message, { status = 0, code = "request_failed", details = null, body = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.body = body;
  }
}

export function tokenFromDocument(doc = globalThis.document) {
  return doc?.querySelector?.('meta[name="contentos-token"]')?.content?.trim() ?? "";
}

export async function request(path, options = {}, fetchImpl = globalThis.fetch, token = tokenFromDocument()) {
  const method = String(options.method ?? "GET").toUpperCase();
  const writes = !["GET", "HEAD", "OPTIONS"].includes(method);
  if (writes && !token) {
    throw new ApiError("This page is missing its write token. Reload Creator Studio.", {
      code: "missing_write_token",
    });
  }

  const headers = new Headers(options.headers ?? {});
  headers.set("Accept", "application/json");
  if (options.body != null && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (writes) headers.set("X-ContentOS-Token", token);

  let response;
  try {
    response = await fetchImpl(path, { ...options, method, headers, credentials: "same-origin" });
  } catch (error) {
    throw new ApiError("Creator Studio could not reach the local API.", {
      code: "network_error",
      details: error instanceof Error ? error.message : String(error),
    });
  }

  const text = response.status === 204 ? "" : await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      throw new ApiError(response.ok ? "The API returned an invalid JSON response." : `Request failed (${response.status}).`, {
        status: response.status,
        code: response.ok ? "invalid_json" : "non_json_error",
        body: text,
      });
    }
  }
  if (!response.ok) {
    throw new ApiError(data?.message ?? data?.error?.message ?? data?.error ?? `Request failed (${response.status}).`, {
      status: response.status,
      code: data?.code ?? data?.error?.code ?? (response.status === 409 ? "conflict" : "request_failed"),
      details: data?.details ?? data?.errors ?? data?.error?.details ?? null,
      body: data,
    });
  }
  return data;
}

const enc = (value) => encodeURIComponent(String(value));
const json = (body) => JSON.stringify(body);

export const api = {
  health: (refresh = false) => request(`/api/v1/health${refresh ? "?refresh=1" : ""}`),
  capabilities: () => request("/api/v1/capabilities"),
  jobs: () => request("/api/v1/jobs"),
  job: (id) => request(`/api/v1/jobs/${enc(id)}`),
  validateSpec: (spec) => request("/api/v1/specs/validate", { method: "POST", body: json(spec) }),
  createSpec: (spec) => request("/api/v1/specs", { method: "POST", body: json(spec) }),
  run: (id) => request(`/api/v1/jobs/${enc(id)}/run`, { method: "POST", body: "{}" }),
  log: (id, stage) => request(`/api/v1/jobs/${enc(id)}/stages/${enc(stage)}/log`),
  preview: (id) => request(`/api/v1/jobs/${enc(id)}/preview`, { method: "POST", body: "{}" }),
  approve: (id, gate, seenDigest) => request(`/api/v1/jobs/${enc(id)}/approve`, {
    method: "POST",
    body: json({ gate, seenDigest }),
  }),
  rerunPreview: (id, stage) => request(`/api/v1/jobs/${enc(id)}/rerun?stage=${enc(stage)}`),
  rerun: (id, stage) => request(`/api/v1/jobs/${enc(id)}/rerun`, {
    method: "POST", body: json({ stage, force: true, confirm: true }),
  }),
  rerunQa: (id) => request(`/api/v1/jobs/${enc(id)}/qa`, { method: "POST", body: "{}" }),
  exportPreview: (id) => request(`/api/v1/jobs/${enc(id)}/export`),
  exportJob: (id, force = false) => request(`/api/v1/jobs/${enc(id)}/export`, {
    method: "POST", body: json({ confirm: true, force }),
  }),
  queue: () => request("/api/v1/queue"),
  queueAdd: (contentId) => request("/api/v1/queue", { method: "POST", body: json({ contentId }) }),
  queueRequeue: (id) => request(`/api/v1/queue/${enc(id)}/requeue`, { method: "POST", body: "{}" }),
  trackB: (id, action) => request(`/api/v1/jobs/${enc(id)}/track-b/${enc(action)}`, { method: "POST", body: "{}" }),
};

export function mediaUrl(id, name) {
  return `/media/${enc(id)}/${enc(name)}`;
}

export function watchJobEvents(id, {
  EventSourceImpl = globalThis.EventSource,
  onSignal = () => {},
  onFallback = () => {},
} = {}) {
  let closed = false;
  let source = null;
  const fallback = (reason) => {
    if (closed) return;
    source?.close?.();
    source = null;
    onFallback(reason);
  };
  if (typeof EventSourceImpl !== "function") {
    fallback("unsupported");
    return () => { closed = true; };
  }
  try {
    source = new EventSourceImpl(`/api/v1/jobs/${enc(id)}/events`);
    source.addEventListener("progress", (event) => {
      if (!closed) onSignal({ type: "progress", data: event.data });
    });
    source.onopen = () => {
      if (!closed) onSignal({ type: "reconnect" });
    };
    source.onerror = () => fallback("disconnected");
  } catch {
    fallback("unavailable");
  }
  return () => {
    closed = true;
    source?.close?.();
  };
}
