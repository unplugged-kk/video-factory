import { checkView, statusMeta, STAGES } from "./state.js";
import { icon } from "./icons.js";

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function statusLabel(value, fallback = "pending") {
  const status = value?.state ? value : statusMeta(value, fallback);
  return `<span class="status status--${escapeHtml(status.state)}">${icon(status.icon)}<span>${escapeHtml(status.label)}</span></span>`;
}

export function middleId(id) {
  const text = String(id ?? "");
  return text.length <= 20 ? text : `${text.slice(0, 9)}…${text.slice(-8)}`;
}

export function idControl(id) {
  const safe = escapeHtml(id);
  return `<details class="id-control"><summary aria-label="Show full job id ${safe}"><code>${escapeHtml(middleId(id))}</code></summary><span class="id-control__full"><code>${safe}</code><button class="icon-button copy" type="button" data-copy="${safe}" aria-label="Copy job id ${safe}">Copy</button></span></details>`;
}

export function formatTime(value) {
  if (!value) return "—";
  const normalized = typeof value === "number" && value < 1_000_000_000_000 ? value * 1000 : value;
  const date = new Date(normalized);
  return Number.isNaN(date.valueOf()) ? String(value) : date.toLocaleString();
}

export function errorPanel(error, title = "Could not load this page") {
  return `<section class="notice notice--error" role="alert"><h2>${escapeHtml(title)}</h2><p class="multiline">${escapeHtml(error?.message ?? error)}</p></section>`;
}

export function emptyState(title, detail, action = "") {
  return `<section class="empty"><h2>${escapeHtml(title)}</h2><p>${escapeHtml(detail)}</p>${action}</section>`;
}

export function stageMarks(stages = []) {
  const byName = new Map(stages.map((stage) => [stage.name ?? stage.stage, stage]));
  return `<span class="stage-marks" aria-label="Pipeline stages">${STAGES.map((name) => {
    const status = statusMeta(byName.get(name)?.status?.state ?? byName.get(name)?.state ?? byName.get(name)?.status);
    return `<span class="stage-dot stage-dot--${status.state}" title="${escapeHtml(name)}: ${status.label}"><span class="sr-only">${escapeHtml(name)}: ${status.label}</span></span>`;
  }).join("")}</span>`;
}

export function nextActionCard(action) {
  const commands = ["run", "track-b-voice", "track-b-align", "track-b-render", "track-b-qa", "track-b-register"];
  const button = action.action === "run"
    ? '<button class="primary" type="button" data-action="run">Run or resume</button>'
    : commands.includes(action.action)
      ? `<button class="primary" type="button" data-action="${escapeHtml(action.action)}">${escapeHtml(action.label)}</button>`
      : action.href
        ? `<a class="button primary" href="${escapeHtml(action.href)}">${escapeHtml(action.label)}</a>`
        : "";
  return `<section class="next-action"><div><span class="eyebrow">Next safe action</span><h2>${escapeHtml(action.label)}</h2><p>${escapeHtml(action.detail)}</p></div>${button}</section>`;
}

export function timeline(stages = []) {
  const byName = new Map(stages.map((stage) => [stage.name ?? stage.stage, stage]));
  return `<ol class="timeline">${STAGES.map((name) => {
    const stage = byName.get(name) ?? {};
    const status = stage.status?.state ? stage.status : statusMeta(stage.state ?? stage.status);
    const seconds = stage.seconds ?? stage.duration;
    const details = [stage.provider, seconds != null ? `${seconds}s` : null].filter(Boolean).join(" · ");
    return `<li class="timeline__item timeline__item--${status.state}">
      <div class="timeline__head"><strong>${escapeHtml(name)}</strong>${statusLabel(status)}</div>
      ${details ? `<small>${escapeHtml(details)}</small>` : ""}
      ${stage.gate ? `<p>${escapeHtml(stage.gate)}</p>` : ""}
      ${stage.error ? `<details><summary>Error details</summary><pre>${escapeHtml(stage.error)}</pre></details>` : ""}
    </li>`;
  }).join("")}</ol>`;
}

export function qaRows(checks) {
  const rows = checks.map(checkView);
  if (!rows.length) return emptyState("Checks not run", "No quality-check results were returned for this job.");
  return `<ul class="record-list">${rows.map((check) => `<li>
    <div>${statusLabel(check.status)} <strong>${escapeHtml(check.name)}</strong></div>
    <p>${escapeHtml(check.message ?? check.detail ?? "No detail supplied.")}</p>
    <small>Provenance: ${escapeHtml(check.provenance)}</small>
  </li>`).join("")}</ul>`;
}

export function bindCopy(root) {
  root.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        const prior = button.textContent;
        button.textContent = "Copied";
        setTimeout(() => { button.textContent = prior; }, 1200);
      } catch {
        button.textContent = "Copy failed";
      }
    });
  });
}

export function fieldError(name, errors = {}) {
  const error = errors[name];
  return error ? `<p class="field-error multiline" id="${escapeHtml(name)}-error">${escapeHtml(Array.isArray(error) ? error.join("\n") : error)}</p>` : "";
}

export function fieldAttrs(name, errors = {}, describedBy = []) {
  const ids = [...describedBy, ...(errors[name] ? [`${name}-error`] : [])].filter(Boolean);
  return `${errors[name] ? ' aria-invalid="true"' : ""}${ids.length ? ` aria-describedby="${escapeHtml(ids.join(" "))}"` : ""}`;
}
