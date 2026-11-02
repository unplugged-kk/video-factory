import { api, ApiError } from "../api.js";
import { emptyState, escapeHtml, fieldAttrs, fieldError } from "../components.js";
import { clearJobDraft, persistJobDraft, restoreJobDraft } from "../state.js";

function errorsFrom(error) {
  const source = error?.details ?? error?.body?.errors ?? [];
  if (Array.isArray(source)) {
    return Object.fromEntries(source.map((item) => {
      const path = String(item.path ?? item.field ?? "$")
        .replace(/^script\[(\d+)\]\.(.+)$/, "script-$1-$2")
        .replace(/^script(?:\[\d+\])?$/, "script-lines");
      return [path, item.message ?? item.error];
    }));
  }
  return source && typeof source === "object" ? source : { $: error?.message ?? String(error) };
}

function errorSummary(errors) {
  const entries = Object.entries(errors);
  if (!entries.length) return "";
  return `<section class="error-summary" id="error-summary" tabindex="-1" role="alert"><h2>Fix these fields</h2><ul>${entries.map(([field, message]) => `<li>${field === "$" ? escapeHtml(message) : `<a href="#${escapeHtml(field)}">${escapeHtml(message)}</a>`}</li>`).join("")}</ul></section>`;
}

function scriptRow(index, line = {}, errors = {}) {
  return `<fieldset class="script-row" data-script-row><legend>Line ${index + 1}</legend>
    <label for="script-${index}-headline">Headline <input id="script-${index}-headline" name="headline" value="${escapeHtml(line.headline ?? "")}"${fieldAttrs(`script-${index}-headline`, errors, [`script-${index}-headline-help`])}></label>
    <small id="script-${index}-headline-help">Short on-screen context.</small>${fieldError(`script-${index}-headline`, errors)}
    <label for="script-${index}-say">Spoken text <textarea id="script-${index}-say" name="say" rows="3" required${fieldAttrs(`script-${index}-say`, errors)}>${escapeHtml(line.say ?? "")}</textarea></label>
    ${fieldError(`script-${index}-say`, errors)}
    ${index ? '<button class="secondary remove-line" type="button">Remove line</button>' : ""}
  </fieldset>`;
}

function option(value, selected) {
  return `<option value="${escapeHtml(value)}" ${selected === value ? "selected" : ""}>${escapeHtml(value)}</option>`;
}

function budgetFor(capabilities, data) {
  const owner = capabilities.platformLimits?.ownerLimits?.[data.kind];
  const limits = (capabilities.platformLimits?.platforms ?? [])
    .filter((platform) => data.platform_targets.includes(platform.id))
    .map((platform) => ({ id: platform.id, max: platform.formats?.[data.kind]?.max_seconds }))
    .filter((item) => Number.isFinite(item.max));
  const all = [...limits, ...(Number.isFinite(owner) ? [{ id: "owner", max: owner }] : [])];
  return all.length ? all.reduce((left, right) => left.max <= right.max ? left : right) : null;
}

function validationSummary(validation) {
  if (!validation?.summary) return "";
  const { summary } = validation;
  const narration = summary.narration ?? {};
  const budget = summary.platformBudget ?? {};
  const issues = summary.issues ?? [];
  return `<section class="notice ${summary.status === "PASS" ? "notice--success" : "notice--warning"}">
    <strong>Backend validation: ${escapeHtml(summary.status)}</strong>
    <p>${escapeHtml(narration.word_count ?? 0)} words · ${escapeHtml(narration.estimated_seconds ?? 0)}s estimated${budget.max_seconds != null ? ` · ${escapeHtml(budget.max_seconds)}s budget` : ""}</p>
    ${issues.length ? `<ul>${issues.map((issue) => `<li>${escapeHtml(issue.message)}</li>`).join("")}</ul>` : "<p>No validation or budget issues.</p>"}
  </section>`;
}

function stepContent(step, data, errors, validation, capabilities) {
  const platforms = capabilities.platformLimits?.platforms ?? [];
  if (step === 0) return `<h2>Identity and format</h2><p>Choose a stable id. Saving creates a Track A spec inside the configured workspace.</p>
    <label for="content_id">Job id <input id="content_id" name="content_id" required pattern="[A-Za-z0-9][A-Za-z0-9._-]{0,127}" value="${escapeHtml(data.content_id)}"${fieldAttrs("content_id", errors, ["content_id-help"])}></label>
    <small id="content_id-help">Letters, numbers, dots, underscores, and hyphens; no paths.</small>${fieldError("content_id", errors)}
    <label for="title">Title <input id="title" name="title" required value="${escapeHtml(data.title)}"${fieldAttrs("title", errors)}></label>${fieldError("title", errors)}
    <fieldset id="format" tabindex="-1"${fieldAttrs("format", errors)}><legend>Format</legend><label class="choice"><input type="radio" name="format" value="9:16" ${data.format !== "16:9" ? "checked" : ""}> Vertical 9:16</label><label class="choice"><input type="radio" name="format" value="16:9" ${data.format === "16:9" ? "checked" : ""}> Landscape 16:9</label>${fieldError("format", errors)}</fieldset>
    <label for="kind">Duration class <select id="kind" name="kind">${option("short", data.kind)}${option("long", data.kind)}</select></label>${fieldError("kind", errors)}
    <fieldset id="platform_targets" tabindex="-1"${fieldAttrs("platform_targets", errors)}><legend>Platforms</legend>${platforms.map((platform) => `<label class="choice"><input type="checkbox" name="platform_target" value="${escapeHtml(platform.id)}" ${data.platform_targets.includes(platform.id) ? "checked" : ""}> ${escapeHtml(platform.name)}</label>`).join("")}${fieldError("platform_targets", errors)}</fieldset>`;
  if (step === 1) return `<h2>Voice</h2><p>Voice generation stays local through the configured Kokoro provider.</p>
    <label for="voice">Kokoro voice <select id="voice" name="voice"${fieldAttrs("voice", errors)}>${capabilities.voices.map((voice) => option(voice, data.voice)).join("")}</select></label>${fieldError("voice", errors)}
    <label for="render">Render lane <select id="render" name="render"${fieldAttrs("render", errors)}>${capabilities.renderLanes.map((lane) => option(lane, data.render)).join("")}</select></label>${fieldError("render", errors)}`;
  if (step === 2) {
    const count = data.script.reduce((total, line) => total + String(line.say ?? "").trim().split(/\s+/).filter(Boolean).length, 0);
    const budget = budgetFor(capabilities, data);
    return `<h2>Script lines</h2><p>Write at least one spoken line. The estimate uses 2.5 words per second and is illustrative until voice alignment.</p>
      <div id="script-lines">${data.script.map((line, index) => scriptRow(index, line, errors)).join("")}</div>
      <button class="secondary" id="add-line" type="button">Add line</button>
      <p class="estimate"><strong>${count} words</strong> · approximately ${Math.ceil(count / 2.5)} seconds${budget ? ` · ${escapeHtml(budget.max)}s ${escapeHtml(budget.id)} limit` : ""}</p>`;
  }
  return `<h2>Review and save</h2><p>Validate this exact draft with the backend, review the summary, then save. Saving does not run or approve the job.</p>
    ${validationSummary(validation)}
    <dl class="review-list"><div><dt>Job id</dt><dd><code>${escapeHtml(data.content_id)}</code></dd></div><div><dt>Title</dt><dd>${escapeHtml(data.title)}</dd></div><div><dt>Format</dt><dd>${escapeHtml(data.format)} ${escapeHtml(data.kind)}</dd></div><div><dt>Platforms</dt><dd>${escapeHtml(data.platform_targets.join(", "))}</dd></div><div><dt>Voice</dt><dd>${escapeHtml(data.voice)}</dd></div><div><dt>Lane</dt><dd>${escapeHtml(data.render)}</dd></div><div><dt>Script lines</dt><dd>${data.script.length}</dd></div></dl>`;
}

export async function showNewJob(root, recoveryStorage = globalThis.localStorage) {
  root.innerHTML = '<div class="skeleton skeleton--large" aria-label="Loading authoring capabilities"></div>';
  let capabilities;
  try {
    capabilities = await api.capabilities();
  } catch (error) {
    root.innerHTML = `<header class="page-head"><h1>New job</h1></header>${emptyState("Authoring unavailable", error.message, '<a class="button secondary" href="#/jobs">Back to jobs</a>')}`;
    return;
  }
  if (!capabilities.actions?.validateSpec || !capabilities.actions?.createSpec ||
      !capabilities.voices?.length || !capabilities.renderLanes?.length) {
    root.innerHTML = `<header class="page-head"><h1>New job</h1></header>${emptyState("Authoring unavailable", "The backend did not advertise the required safe authoring capabilities.", '<a class="button secondary" href="#/jobs">Back to jobs</a>')}`;
    return;
  }
  let step = 0;
  let validation = null;
  let errors = {};
  let collision = null;
  const restored = restoreJobDraft(recoveryStorage, capabilities);
  let data = restored.data;

  const render = () => {
    root.innerHTML = `<header class="page-head"><div><span class="eyebrow">Jobs / New</span><h1>New job</h1></div></header>
      ${restored.recovered ? '<div class="notice"><strong>Recovered unsaved draft</strong><p>Review it before saving. The server remains authoritative.</p></div>' : ""}
      ${collision ? `<div class="notice notice--warning" role="alert"><strong>Job id already exists</strong><p>Your unsaved draft is preserved. Change its id or <a href="#/jobs/${encodeURIComponent(collision)}/overview">open the existing job</a>.</p></div>` : ""}
      <ol class="steps" aria-label="Wizard progress">${["Identity", "Voice", "Script", "Review"].map((name, index) => `<li class="${index === step ? "current" : index < step ? "complete" : ""}"><span>${index + 1}</span>${name}</li>`).join("")}</ol>
      <form class="form-column" novalidate>${errorSummary(errors)}<div id="step-content">${stepContent(step, data, errors, validation, capabilities)}</div>
        <div class="form-actions">${step < 3 ? '<button class="primary" type="submit">Continue</button>' : `<button class="primary" type="submit">${validation ? "Save job" : "Validate draft"}</button>`}${step ? '<button class="secondary" id="back" type="button">Back</button>' : '<a class="button secondary" href="#/jobs">Back to jobs</a>'}</div>
      </form>`;
    const form = root.querySelector("form");
    root.querySelector("#back")?.addEventListener("click", () => { capture(); validation = null; step -= 1; errors = {}; render(); });
    root.querySelector("#add-line")?.addEventListener("click", () => { capture(); validation = null; data.script.push({ say: "", headline: "" }); persistJobDraft(recoveryStorage, data); render(); });
    root.querySelectorAll(".remove-line").forEach((button) => button.addEventListener("click", () => {
      const row = button.closest("[data-script-row]");
      const index = [...row.parentElement.children].indexOf(row);
      capture();
      validation = null;
      data.script.splice(index, 1);
      persistJobDraft(recoveryStorage, data);
      render();
    }));
    form.addEventListener("input", () => {
      capture();
      validation = null;
      collision = null;
      persistJobDraft(recoveryStorage, data);
    });
    form.addEventListener("submit", submit);
    root.querySelectorAll("#error-summary a").forEach((link) => link.addEventListener("click", (event) => {
      const target = root.querySelector(link.hash);
      if (!target) return;
      event.preventDefault();
      target.focus();
      target.scrollIntoView({ block: "center" });
    }));
    root.querySelector("#error-summary")?.focus();
  };

  const capture = () => {
    if (step === 0) {
      data.content_id = root.querySelector("#content_id").value.trim();
      data.title = root.querySelector("#title").value.trim();
      data.format = root.querySelector('[name="format"]:checked')?.value ?? "";
      data.kind = root.querySelector("#kind").value;
      data.platform_targets = [...root.querySelectorAll('[name="platform_target"]:checked')].map((input) => input.value);
    } else if (step === 1) {
      data.voice = root.querySelector("#voice").value;
      data.render = root.querySelector("#render").value;
    } else if (step === 2) {
      data.script = [...root.querySelectorAll("[data-script-row]")].map((row) => ({
        headline: row.querySelector('[name="headline"]').value.trim(),
        say: row.querySelector('[name="say"]').value.trim(),
      }));
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    capture();
    persistJobDraft(recoveryStorage, data);
    errors = {};
    if (step === 0) {
      if (!data.content_id) errors.content_id = "Job id is required.";
      else if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(data.content_id) || data.content_id.includes("..")) errors.content_id = "Use letters, numbers, dots, underscores, or hyphens; do not use '..'.";
      if (!data.title) errors.title = "Title is required.";
      if (!data.platform_targets.length) errors.platform_targets = "Select at least one platform.";
    }
    if (step === 2) {
      if (!data.script.length || data.script.every((line) => !line.say)) errors["script-0-say"] = "Add at least one spoken line.";
      data.script.forEach((line, index) => {
        if (!line.say) errors[`script-${index}-say`] = "Spoken text is required.";
      });
    }
    if (Object.keys(errors).length) { render(); return; }
    if (step < 3) { validation = null; step += 1; render(); return; }
    const button = event.submitter;
    button.disabled = true;
    button.textContent = "Validating…";
    try {
      if (!validation) {
        validation = await api.validateSpec(data);
        if (validation?.valid === false || validation?.errors?.length) throw new ApiError("Validation failed.", { details: validation.errors });
        render();
        root.querySelector(".notice--success, .notice--warning")?.scrollIntoView({ block: "center" });
        return;
      }
      const saved = await api.createSpec(data);
      clearJobDraft(recoveryStorage);
      root.innerHTML = emptyState("Job saved", `The spec was written${saved?.path ? ` to ${saved.path}` : " inside the configured workspace"}.`, `<a class="button primary" href="#/jobs/${encodeURIComponent(data.content_id)}/overview">Open job</a>`);
    } catch (error) {
      if (error.status === 409) {
        collision = error.details?.contentId ?? data.content_id;
        validation = null;
        errors.$ = error.message;
        render();
        return;
      }
      errors = errorsFrom(error);
      const fields = Object.keys(errors);
      if (fields.some((field) => field === "content_id" || field === "title" || field === "format")) step = 0;
      else if (fields.some((field) => field === "voice" || field === "render")) step = 1;
      else if (fields.some((field) => field.startsWith("script"))) step = 2;
      render();
    }
  };
  render();
}
