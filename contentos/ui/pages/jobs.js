import { api } from "../api.js";
import { bindCopy, emptyState, errorPanel, escapeHtml, formatTime, idControl, stageMarks, statusLabel } from "../components.js";
import { filterSortJobs, formatDuration, jobView, listFrom, nextAction } from "../state.js";

function rows(jobs) {
  return jobs.map((job) => {
    const action = nextAction(job);
    const operation = [
      job.draft ? "Draft" : null,
      job.retries ? `${job.retries} ${job.retries === 1 ? "retry" : "retries"}` : null,
      job.gate ? job.gate : null,
      job.stale ? "Stale" : null,
    ].filter(Boolean).join(" · ");
    return `<li class="job-row">
    <div class="job-row__title" data-label="Job"><a href="#/jobs/${encodeURIComponent(job.id)}/overview">${escapeHtml(job.title)}</a>${job.track === "B" ? '<span class="eyebrow">Track B</span>' : ""}${statusLabel(job.status)}</div>
    <div data-label="Progress">${stageMarks(job.stages)}</div>
    <div data-label="ID">${idControl(job.id)}</div>
    <div data-label="Attempt"><strong>${escapeHtml(formatDuration(job.elapsedSeconds))}</strong><small>${escapeHtml(operation || "First attempt")}</small></div>
    <div data-label="Next"><a href="#/jobs/${encodeURIComponent(job.id)}/overview">${escapeHtml(action.label)}</a></div>
    <div data-label="Updated"><time>${escapeHtml(formatTime(job.updated))}</time></div>
  </li>`;
  }).join("");
}

function jobQuery() {
  return new URLSearchParams(location.hash.split("?")[1] || "");
}

export async function showJobs(root) {
  root.innerHTML = `<header class="page-head"><div><span class="eyebrow">Creator Studio</span><h1>Jobs</h1></div><div class="form-actions"><a class="button secondary" href="#/track-b">Track B intake</a><a class="button primary" href="#/jobs/new">New job</a></div></header>
    <section class="toolbar" aria-label="Job filters">
      <label>Search <input id="job-search" type="search" autocomplete="off" placeholder="Title or job id"></label>
      <label>State <select id="job-state"><option value="">All states</option><option value="draft">Draft</option><option>running</option><option>blocked</option><option>failed</option><option>stale</option><option>completed</option><option>pending</option></select></label>
      <label>Attention <select id="job-kind"><option value="">All jobs</option><option value="retry">Has retries</option><option value="gate">At a gate</option></select></label>
      <label>Sort <select id="job-sort"><option value="updated-desc">Newest update</option><option value="updated-asc">Oldest update</option><option value="title-asc">Title A–Z</option><option value="title-desc">Title Z–A</option></select></label>
    </section>
    <div id="jobs-result"><div class="skeleton" aria-label="Loading jobs"></div><div class="skeleton"></div><div class="skeleton"></div></div>`;
  const result = root.querySelector("#jobs-result");
  try {
    const payload = await api.jobs();
    const all = listFrom(payload, "jobs", "items", "results").map(jobView);
    const initial = jobQuery();
    root.querySelector("#job-search").value = initial.get("q") ?? "";
    root.querySelector("#job-state").value = initial.get("state") ?? "";
    root.querySelector("#job-kind").value = initial.get("kind") ?? "";
    root.querySelector("#job-sort").value = initial.get("sort") ?? "updated-desc";
    const remember = () => {
      const next = new URLSearchParams();
      const query = root.querySelector("#job-search").value.trim();
      const state = root.querySelector("#job-state").value;
      const kind = root.querySelector("#job-kind").value;
      const sort = root.querySelector("#job-sort").value;
      if (query) next.set("q", query);
      if (state) next.set("state", state);
      if (kind) next.set("kind", kind);
      if (sort && sort !== "updated-desc") next.set("sort", sort);
      const suffix = next.toString();
      history.replaceState(null, "", `#/jobs${suffix ? `?${suffix}` : ""}`);
    };
    const render = () => {
      const query = root.querySelector("#job-search").value.trim().toLowerCase();
      const state = root.querySelector("#job-state").value;
      const shown = filterSortJobs(all, {
        query,
        state,
        kind: root.querySelector("#job-kind").value,
        sort: root.querySelector("#job-sort").value,
      });
      remember();
      result.innerHTML = shown.length
        ? `<div class="job-table-head" aria-hidden="true"><span>Job</span><span>Progress</span><span>ID</span><span>Attempt</span><span>Next action</span><span>Updated</span></div><ul class="job-table">${rows(shown)}</ul>`
        : emptyState(all.length ? "No matching jobs" : "No jobs yet", all.length ? "Change the search or state filter." : "Create a validated Track A job to begin.", '<a class="button primary" href="#/jobs/new">New job</a><p><code>./contentos.sh pipeline run SPEC.yaml</code></p>');
      bindCopy(result);
    };
    root.querySelector("#job-search").addEventListener("input", render);
    root.querySelector("#job-state").addEventListener("change", render);
    root.querySelector("#job-kind").addEventListener("change", render);
    root.querySelector("#job-sort").addEventListener("change", render);
    render();
  } catch (error) {
    result.innerHTML = errorPanel(error, "Jobs are unavailable");
  }
}
