import { api } from "../api.js";
import { errorPanel, escapeHtml } from "../components.js";

export async function showTrackB(root) {
  root.innerHTML = `<header class="page-head"><div><span class="eyebrow">Track B</span><h1>Track B intake</h1></div></header>
    <form class="form-column" novalidate>
      <p>Enter the workspace job id. Creator Studio reads <code>project/index.html</code>, the script, and an optional scene plan from that job folder.</p>
      <label>Job ID <input id="track-b-id" name="jobId" required autocomplete="off" spellcheck="false"></label>
      <p id="track-b-error" class="field-error multiline"></p>
      <div class="form-actions"><button class="primary" type="submit">Inspect job</button></div>
    </form>
    <section id="track-b-result"></section>`;
  const form = root.querySelector("form");
  const error = root.querySelector("#track-b-error");
  const result = root.querySelector("#track-b-result");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const jobId = root.querySelector("#track-b-id").value.trim();
    error.textContent = "";
    result.innerHTML = "";
    if (!jobId) {
      error.textContent = "A job id is required.";
      return;
    }
    const button = form.querySelector("button");
    button.disabled = true;
    try {
      await api.trackB(jobId, "intake");
      const payload = await api.job(jobId);
      const job = payload?.job ?? payload;
      const evidence = job.trackB ?? {};
      result.innerHTML = `<section class="panel"><h2>Discovered evidence</h2><dl class="review-list">
        <div><dt>Composition</dt><dd><code class="wrap">${escapeHtml(evidence.composition?.path ?? "Missing")}</code></dd></div>
        <div><dt>Script lines</dt><dd>${escapeHtml(evidence.script?.lines ?? 0)}</dd></div>
        <div><dt>Scene plan</dt><dd>${escapeHtml(evidence.scenePlan?.status ?? "NOT_RUN")}</dd></div>
      </dl><a class="button primary" href="#/jobs/${encodeURIComponent(jobId)}/script">Review script</a></section>`;
    } catch (failure) {
      result.innerHTML = errorPanel(failure, "Intake failed");
    } finally {
      button.disabled = false;
    }
  });
}
