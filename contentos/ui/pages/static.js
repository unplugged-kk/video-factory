import { api } from "../api.js";
import { bindCopy, emptyState, errorPanel, escapeHtml, formatTime, statusLabel } from "../components.js";
import { canonicalState, healthReadiness, listFrom, statusMeta } from "../state.js";

function capabilityRows(payload) {
  const groups = listFrom(payload, "required", "capabilities", "providers");
  const required = groups.flatMap((group) => Array.isArray(group.candidates)
    ? group.candidates.map((candidate) => ({
      ...candidate,
      capability: group.name,
      optional: candidate.optional ?? candidate.requiredForRun === false,
    }))
    : [{ ...group, optional: group.optional ?? group.requiredForRun === false }]);
  const optional = listFrom(payload, "optional");
  const tools = Object.entries(payload?.tools ?? {}).map(([name, value]) => ({
    name, ...value, optional: value.optional ?? value.requiredForRun === false,
  }));
  return [...required, ...optional.map((item) => ({ ...item, optional: true })), ...tools];
}

function healthState(item) {
  const raw = item.status ?? item.state ?? item.result;
  if (item.optional && ["missing", "not_installed", "unavailable"].includes(String(raw).toLowerCase())) return statusMeta("optional");
  return statusMeta(canonicalState(raw, "not_run"), "not_run");
}

export async function showHealth(root, force = false) {
  root.innerHTML = `<header class="page-head"><div><span class="eyebrow">Capabilities</span><h1>Health</h1></div><button class="primary" id="recheck" type="button">Re-check</button></header><div id="health-result"><div class="skeleton skeleton--large" aria-label="Checking health"></div></div><div class="sr-only" id="health-status" role="status" aria-live="polite"></div>`;
  const result = root.querySelector("#health-result");
  root.querySelector("#recheck").addEventListener("click", () => showHealth(root, true));
  try {
    const payload = await api.health(force);
    const items = capabilityRows(payload);
    const storage = listFrom(payload, "storage", "roots", "paths").map((item) => ({
      ...item,
      state: item.status ?? (item.writable === true ? "passed" : item.writable === false ? "missing" : "not_run"),
    }));
    const readiness = healthReadiness(payload);
    const blockerNames = readiness.blockers.map((blocker) => blocker.label).join(", ");
    result.innerHTML = `${readiness.ready ? '<section class="notice notice--success"><h2>Ready for Track A</h2><p>Kokoro, HyperFrames, FFmpeg, and both storage roots are available. Optional capabilities may remain unavailable.</p></section>' : `<section class="notice notice--error"><h2>Run is blocked</h2><p>${escapeHtml(blockerNames)} ${readiness.blockers.length === 1 ? "is" : "are"} unavailable. Resolve only the listed Track A prerequisites.</p></section>`}
      <section><h2>Providers and tools</h2>${items.length ? `<ul class="health-list">${items.map((item) => {
        const status = healthState(item);
        const remediation = status.state === "passed" ? null : item.fix ?? item.command ?? item.remediation;
        return `<li><div>${statusLabel(status)}<div><strong>${escapeHtml(item.name ?? item.id ?? "Capability")}</strong>${item.capability ? `<small>${escapeHtml(item.capability)}</small>` : ""}<p>${escapeHtml(item.message ?? item.detail ?? (remediation ? "Follow the remediation below." : "No remediation needed."))}</p>${remediation ? `<code class="path">${escapeHtml(remediation)}</code><button class="icon-button" data-copy="${escapeHtml(remediation)}" type="button">Copy</button>` : ""}</div></div></li>`;
      }).join("")}</ul>` : emptyState("No capability data", "The Health API returned no provider rows.")}</section>
      <section><h2>Storage</h2>${storage.length ? `<ul class="health-list">${storage.map((item) => `<li><div>${statusLabel(item.status ?? item.state ?? "not_run", "not_run")}<div><strong>${escapeHtml(item.name ?? item.kind ?? "Storage root")}</strong><code class="path">${escapeHtml(item.path ?? item.root)}</code><p>${escapeHtml(item.message ?? "")}</p></div></div></li>`).join("")}</ul>` : emptyState("Storage not reported", "No configured storage roots were returned.")}</section>
      <p class="muted">Last checked: ${escapeHtml(formatTime(payload?.checkedAt ?? payload?.checked_at ?? payload?.timestamp ?? new Date()))}</p>`;
    bindCopy(result);
    window.dispatchEvent(new CustomEvent("contentos:health", { detail: payload }));
    root.querySelector("#health-status").textContent = "Health check complete.";
  } catch (error) {
    result.innerHTML = errorPanel(error, "Health check failed");
    root.querySelector("#health-status").textContent = "Health check failed.";
  }
}

export async function showQueue(root) {
  root.innerHTML = `<header class="page-head"><div><span class="eyebrow">Operations</span><h1>Queue</h1></div></header><form id="queue-add" class="toolbar"><label>Saved job id <input id="queue-content" required pattern="[A-Za-z0-9][A-Za-z0-9._-]{0,127}"></label><button class="primary" type="submit">Add to queue</button></form><div id="queue-result"><div class="skeleton" aria-label="Loading queue"></div></div>`;
  const result = root.querySelector("#queue-result");
  const render = (payload) => {
    const jobs = listFrom(payload, "jobs");
    const state = root.querySelector("#queue-state")?.value ?? "";
    const shown = jobs.filter((job) => !state || job.status === state);
    result.innerHTML = `<section class="toolbar" aria-label="Queue filters"><label>State <select id="queue-state"><option value="">All states</option>${["queued", "running", "blocked", "failed", "done"].map((item) => `<option ${item === state ? "selected" : ""}>${item}</option>`).join("")}</select></label></section>
      ${shown.length ? `<ul class="record-list">${shown.map((job) => `<li><div>${statusLabel(job.status)} <a href="#/jobs/${encodeURIComponent(job.contentId)}/overview"><strong>${escapeHtml(job.contentId)}</strong></a></div><p>${escapeHtml(job.error || "No error recorded.")}</p><small>Queue ${escapeHtml(job.id)} · ${escapeHtml(job.seconds ?? "—")}s</small>${["failed", "blocked"].includes(job.status) ? `<button class="secondary" type="button" data-requeue="${escapeHtml(job.id)}">Requeue</button>` : ""}</li>`).join("")}</ul>` : emptyState(jobs.length ? "No matching queue rows" : "Queue is empty", "Add a saved job from its overview, or use the local CLI. Creator Studio does not start a worker or cancel a running process.")}
      <p class="muted">The worker default is one job at a time. Publishing and private approval shortcuts stay out of this screen.</p>`;
    result.querySelector("#queue-state").addEventListener("change", () => render(payload));
    result.querySelectorAll("[data-requeue]").forEach((button) => button.addEventListener("click", async () => {
      button.disabled = true;
      try { render(await api.queueRequeue(button.dataset.requeue).then(() => api.queue())); }
      catch (error) { button.insertAdjacentHTML("afterend", errorPanel(error, "Requeue failed")); button.disabled = false; }
    }));
  };
  root.querySelector("#queue-add").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = root.querySelector("#queue-content");
    const button = event.submitter;
    button.disabled = true;
    try {
      await api.queueAdd(input.value.trim());
      input.value = "";
      render(await api.queue());
    } catch (error) {
      result.insertAdjacentHTML("afterbegin", errorPanel(error, "Could not queue job"));
    } finally { button.disabled = false; }
  });
  try { render(await api.queue()); }
  catch (error) { result.innerHTML = errorPanel(error, "Queue is unavailable"); }
}

export function showHelp(root) {
  root.innerHTML = `<header class="page-head"><div><span class="eyebrow">Reference</span><h1>Help</h1></div></header>
    <article class="help">
      <h2>Primary journey</h2><ol><li>Create and validate a Track A job.</li><li>Run until the script gate.</li><li>Review the exact script digest and grant <code>SCRIPT_APPROVED</code>.</li><li>Review composition evidence and grant <code>PRODUCTION_APPROVED</code>.</li><li>Run through render and inspect QA evidence.</li></ol>
      <h2>Human gates</h2><p>Approvals are deliberate, digest-bound grants. Creator Studio never skips or reorders gates.</p>
      <h2>Publishing</h2><p>Publishing is disabled and is not available in Creator Studio.</p>
      <h2>CLI map</h2><dl class="review-list"><div><dt>Health</dt><dd><code>./contentos.sh doctor</code></dd></div><div><dt>Storage</dt><dd><code>./contentos.sh storage paths --check</code></dd></div><div><dt>Jobs</dt><dd><code>./contentos.sh status</code></dd></div><div><dt>Queue</dt><dd><code>./contentos.sh queue list</code></dd></div><div><dt>Quality</dt><dd><code>./contentos.sh qa VIDEO.mp4</code></dd></div></dl>
      <h2>CLI-only operations</h2><p>Starting or stopping the worker, research, competitor inspection, destructive storage cleanup, and publishing remain in the CLI. Queue add and requeue, validated export, and one-stage rerun are available in Creator Studio.</p>
    </article>`;
}
