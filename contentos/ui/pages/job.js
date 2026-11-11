import { api, mediaUrl, watchJobEvents } from "../api.js";
import { bindCopy, emptyState, errorPanel, escapeHtml, formatTime, idControl, nextActionCard, qaRows, statusLabel, timeline } from "../components.js";
import { defaultLogStage, formatDuration, jobView, listFrom, nextAction, STAGES } from "../state.js";

const TABS = ["overview", "script", "review", "logs", "files"];

function tabNav(id, active) {
  return `<nav class="tabs" aria-label="Job sections">${TABS.map((tab) => `<a href="#/jobs/${encodeURIComponent(id)}/${tab}" ${tab === active ? 'aria-current="page"' : ""}>${tab[0].toUpperCase()}${tab.slice(1)}</a>`).join("")}</nav>`;
}

function approvalState(job, gate) {
  const key = gate === "SCRIPT_APPROVED" ? "script" : "production";
  const approval = job.approvals?.[gate] ?? job.approvals?.[key] ?? {};
  const digest = job.digests?.[key] ?? job[`${key}_digest`] ?? approval.currentDigest ?? "";
  const approvedDigest = approval.digest ?? approval.seenDigest ?? job[`${key}_approved_digest`] ?? "";
  return { digest, approved: Boolean(approval.approved ?? (digest && approvedDigest === digest)), mismatch: Boolean(approvedDigest && digest && approvedDigest !== digest) };
}

function approvalPanel(id, gate, state, evidence) {
  if (!state.digest) return `<section class="approval-panel"><h2>${gate === "SCRIPT_APPROVED" ? "Script approval" : "Production approval"}</h2><p>The server did not return a current digest, so approval is unavailable.</p></section>`;
  if (state.mismatch) return `<section class="approval-panel notice--warning"><h2>Digest changed</h2><p>The artifact changed after an earlier review. Review the current evidence before granting again.</p><code class="wrap">${escapeHtml(state.digest)}</code>${evidence ? `<button class="primary open-approval" data-gate="${gate}" data-digest="${escapeHtml(state.digest)}" type="button">Review and approve current digest</button>` : ""}</section>`;
  if (state.approved) return `<section class="approval-panel"><h2>${statusLabel("passed")} Approved</h2><p>The grant matches the current artifact digest.</p><code class="wrap">${escapeHtml(state.digest)}</code></section>`;
  return `<section class="approval-panel"><h2>Approval required</h2><p>This grant is bound to the exact digest shown below. A later edit requires a new grant.</p><code class="wrap">${escapeHtml(state.digest)}</code>${evidence ? `<button class="primary open-approval" data-gate="${gate}" data-digest="${escapeHtml(state.digest)}" type="button">Approve</button>` : "<p>Required review evidence is not available yet.</p>"}</section>`;
}

function scriptPage(job, id) {
  const lines = listFrom(job.script ?? job.spec?.script, "lines", "script");
  const approval = approvalState(job, "SCRIPT_APPROVED");
  const script = lines.length ? `<article class="script"><h2>${escapeHtml(job.title ?? job.spec?.title ?? "Script")}</h2><ol>${lines.map((line) => `<li><h3>${escapeHtml(line.headline ?? line.tag ?? `Scene`)}</h3><p>${escapeHtml(line.say ?? line.text ?? line)}</p></li>`).join("")}</ol></article>` : emptyState("Script not written", "No spoken lines were returned for this job.");
  const lint = job.script_lint ?? job.lint;
  const plan = job.trackB?.scenePlan;
  const planPanel = plan ? `<section class="panel"><h2>Scene plan</h2>${statusLabel(plan.status ?? "not_run", "not_run")}<p>${escapeHtml(plan.detail ?? (plan.scenes != null ? `${plan.scenes} scenes` : "No scene plan was found."))}</p>${plan.path ? `<code class="wrap">${escapeHtml(plan.path)}</code>` : ""}</section>` : "";
  return `<div class="split split--script">${script}<aside>${planPanel}${lint ? `<section class="panel"><h2>Lint evidence</h2>${statusLabel(lint.status ?? lint.state ?? "not_run", "not_run")}<p>${escapeHtml(lint.message ?? lint.detail ?? "No detail supplied.")}</p></section>` : `<section class="panel"><h2>Lint evidence</h2>${statusLabel("not_run", "not_run")}<p>Script lint has not reported a result.</p></section>`}${approvalPanel(id, "SCRIPT_APPROVED", approval, lines.length > 0)}</aside></div>`;
}

function reviewPage(job, id) {
  const video = job.video ?? job.media?.video ?? job.artifacts?.find?.((item) => item.name === "video.mp4");
  const videoName = typeof video === "string" ? video.split("/").pop() : video?.name ?? video?.filename;
  const frames = listFrom(job.preview, "frames", "images").concat(listFrom(job.preview_frames, "frames"));
  const checks = listFrom(job.qa, "checks", "rows").concat(listFrom(job.checks, "checks"));
  if (job.quality?.visualGate) checks.push({ name: "Visual background gate", provenance: "standalone visual check", ...job.quality.visualGate });
  if (job.quality?.critic) checks.push({ name: "Independent visual review", provenance: "independent critic report", ...job.quality.critic });
  for (const [name, check] of [
    ["Visual plan", job.trackB?.quality?.visualPlan],
    ["Visual check", job.trackB?.quality?.visualCheck],
    ["Rendered scenes", job.trackB?.quality?.visualScenes],
  ]) {
    if (check) checks.push({ name, ...check });
  }
  const production = approvalState(job, "PRODUCTION_APPROVED");
  const hasEvidence = frames.length > 0 || Boolean(videoName);
  const format = String(job.format ?? job.spec?.format ?? "16:9").replace(":", "-");
  const player = videoName
    ? `<div class="video-shell video-shell--${escapeHtml(format)}"><video controls preload="metadata" src="${mediaUrl(id, videoName)}">${job.captions ? `<track kind="captions" src="${mediaUrl(id, job.captions)}" label="Captions" default>` : ""}Your browser cannot play this video.</video></div>`
    : emptyState("No rendered video", "Generate preview evidence for a composition, or run through render.");
  const composition = job.track === "B" ? `<p>Composition: <code class="wrap">${escapeHtml(job.trackB?.composition?.path ?? "project/index.html is not in this job")}</code></p>` : "";
  return `<div class="split split--review"><section><h2>Video and preview evidence</h2>${composition}${player}
    <div class="frame-strip">${frames.map((frame, index) => {
      const name = typeof frame === "string" ? frame.split("/").pop() : frame.name ?? frame.filename;
      return `<figure><img src="${mediaUrl(id, name)}" alt="Preview frame ${index + 1}" loading="lazy"><figcaption>${escapeHtml(frame.label ?? frame.at ?? `Frame ${index + 1}`)}</figcaption></figure>`;
    }).join("")}</div>
    <button class="secondary" type="button" data-action="preview">Generate preview</button><button class="secondary" type="button" data-action="${job.track === "B" ? "track-b-qa" : "qa"}">${job.track === "B" ? "Run diagnostics" : "Rerun QA"}</button></section>
    <aside><section class="panel"><h2>Quality checks</h2>${qaRows(checks)}</section>${approvalPanel(id, "PRODUCTION_APPROVED", production, hasEvidence)}</aside></div>`;
}

function logsPage(job, id) {
  const selected = defaultLogStage(job);
  return `<section><header class="section-head"><div><h2>Stage logs</h2><p>Logs are escaped text from the selected stage.</p></div><label>Stage <select id="log-stage">${STAGES.map((stage) => `<option ${stage === selected ? "selected" : ""}>${stage}</option>`).join("")}</select></label></header>
    <div class="log-actions"><label>Find <input id="log-search" type="search" autocomplete="off"></label><label class="choice"><input id="log-wrap" type="checkbox" checked> Wrap lines</label><button class="secondary" id="copy-log" type="button">Copy log</button><button class="secondary" id="download-log" type="button">Download</button></div>
    <div id="log-result" aria-live="polite"><div class="skeleton" aria-label="Loading log"></div></div></section>`;
}

function filesPage(job) {
  const files = listFrom(job.artifacts, "files", "artifacts").concat(listFrom(job.files, "files"));
  if (!files.length) return emptyState("No artifacts yet", "Artifacts appear here as pipeline stages complete.");
  return `<section><h2>Artifacts</h2><button class="primary" type="button" data-action="export">Review export</button><ul class="artifact-list">${files.map((file) => {
    const path = typeof file === "string" ? file : file.path ?? file.name;
    return `<li><div><strong>${escapeHtml(file.name ?? path?.split("/").pop() ?? "Artifact")}</strong><code class="path">${escapeHtml(path)}</code><small>${escapeHtml([file.type, file.size ?? file.bytes].filter((value) => value != null).join(" · "))}</small></div><button class="secondary copy" type="button" data-copy="${escapeHtml(path)}">Copy path</button></li>`;
  }).join("")}</ul><p class="muted">Export copies the validated video into the publishing library. It does not publish the video or choose an arbitrary path.</p></section>`;
}

function diagnosticRow(label, status, provenance) {
  return `<div><dt>${escapeHtml(label)}</dt><dd>${statusLabel(status ?? "not_run", "not_run")}${provenance ? `<small>${escapeHtml(provenance)}</small>` : ""}</dd></div>`;
}

function trackBPanel(job, id) {
  const quality = job.trackB?.quality ?? {};
  const voice = job.stages.find((stage) => stage.name === "voice");
  const render = job.stages.find((stage) => stage.name === "render");
  const register = job.hasVideo && !job.trackB?.registration?.finalOutput
    ? '<button class="secondary" type="button" data-action="track-b-register">Register finished video</button>'
    : "";
  return `<section class="panel"><h2>Track B diagnostics</h2><dl class="review-list">
    ${diagnosticRow("Voice", voice?.status, voice?.provider)}
    ${diagnosticRow("Alignment", job.trackB?.timing?.status, job.trackB?.timing?.provenance)}
    ${diagnosticRow("Render", render?.status, render?.provider)}
    ${diagnosticRow("Technical QA", quality.technical?.status, quality.technical?.provenance)}
    ${diagnosticRow("Visual plan", quality.visualPlan?.status, quality.visualPlan?.provenance)}
    ${diagnosticRow("Visual check", quality.visualCheck?.status, quality.visualCheck?.provenance)}
    ${diagnosticRow("Rendered scenes", quality.visualScenes?.status, quality.visualScenes?.provenance)}
    ${diagnosticRow("Critic", quality.critic?.status, quality.critic?.provenance)}
    ${diagnosticRow("Registration", job.trackB?.registration?.status, job.trackB?.registration?.finalOutput)}
  </dl>${register}<p class="muted"><a href="#/jobs/${encodeURIComponent(id)}/files">Export</a> uses the existing confirmation and reports the ready-library path.</p></section>`;
}

function overviewPage(job, id) {
  const action = nextAction(job);
  if (!action.href && action.action === "review") action.href = `#/jobs/${encodeURIComponent(id)}/${action.gate === "SCRIPT_APPROVED" ? "script" : "review"}`;
  if (action.action === "logs") action.href = `#/jobs/${encodeURIComponent(id)}/logs`;
  const attempts = job.stages.flatMap((stage) => stage.attempts ?? [])
    .sort((left, right) => Number(right.started ?? 0) - Number(left.started ?? 0));
  const rerun = job.track === "B" ? "" : `<section class="panel"><h2>Rerun one stage</h2><p>Forcing a stage removes later sentinels and revokes approvals whose reviewed artifact would change. Publish cannot be rerun here.</p><label>Stage <select id="rerun-stage">${STAGES.filter((stage) => stage !== "publish").map((stage) => `<option>${stage}</option>`).join("")}</select></label><button class="secondary" type="button" data-action="rerun-preview">Preview rerun</button><div id="rerun-preview"></div></section>`;
  return `${nextActionCard(action)}${job.track === "B" ? trackBPanel(job, id) : ""}<section><h2>Stage timeline</h2>${timeline(job.stages)}</section>
    <section class="panel"><h2>Current attempt</h2><dl class="review-list"><div><dt>State</dt><dd>${statusLabel(job.status)}</dd></div><div><dt>Updated</dt><dd>${escapeHtml(formatTime(job.updated))}</dd></div><div><dt>Elapsed</dt><dd>${escapeHtml(formatDuration(job.elapsedSeconds))}</dd></div><div><dt>Attempts</dt><dd>${escapeHtml(job.attempts ?? 0)}</dd></div><div><dt>Retries</dt><dd>${escapeHtml(job.retries ?? 0)}${job.retryReason ? ` · ${escapeHtml(job.retryReason)}` : ""}</dd></div><div><dt>Gate</dt><dd>${escapeHtml(job.gate ?? "—")}</dd></div></dl>${job.failure?.error ? `<details><summary>Failure details</summary><pre>${escapeHtml(job.failure.error)}</pre></details>` : ""}</section>
    <details class="panel"><summary>Stage attempts</summary>${attempts.length ? `<ul>${attempts.map((run) => `<li>${statusLabel(run.status)} ${escapeHtml(run.stage)} · ${escapeHtml(formatTime(run.started))} · ${escapeHtml(formatDuration(run.seconds))}${run.error ? ` · ${escapeHtml(run.error)}` : ""}</li>`).join("")}</ul>` : "<p>No prior attempts were returned.</p>"}</details>
    ${rerun}
    <div id="state-announcement" class="sr-only" role="status" aria-live="polite"></div>`;
}

export async function showJob(root, id, requestedTab = "overview") {
  const watchToken = Symbol("job-watch");
  root.__watchToken = watchToken;
  const tab = TABS.includes(requestedTab) ? requestedTab : "overview";
  root.innerHTML = '<div class="skeleton skeleton--large" aria-label="Loading job"></div>';
  try {
    const payload = await api.job(id);
    const raw = payload?.job ?? payload;
    const job = jobView(raw);
    const content = tab === "overview" ? overviewPage(job, id) : tab === "script" ? scriptPage(raw, id) : tab === "review" ? reviewPage(raw, id) : tab === "logs" ? logsPage(raw, id) : filesPage(raw);
    const badge = raw.track === "B" ? '<span class="eyebrow">Track B</span>' : "";
    root.innerHTML = `<header class="page-head"><div><span class="eyebrow">Jobs / ${escapeHtml(tab)}</span>${badge}<h1>${escapeHtml(job.title)}</h1>${idControl(id)}</div>${statusLabel(job.status)}</header>${tabNav(id, tab)}${content}
      <dialog id="approval-dialog" aria-labelledby="approval-title" aria-describedby="approval-copy approval-digest"><form method="dialog"><h2 id="approval-title" tabindex="-1">Confirm approval</h2><p id="approval-copy">This grants the displayed gate for the exact artifact digest. The pipeline may continue.</p><code id="approval-digest" class="wrap"></code><p id="approval-error" class="field-error multiline" role="alert"></p><div class="dialog-actions"><button class="secondary" value="cancel">Go back</button><button class="primary" id="confirm-approval" value="default">Grant approval</button></div></form></dialog>
      <dialog id="action-dialog" aria-labelledby="action-title"><form method="dialog"><h2 id="action-title" tabindex="-1">Confirm action</h2><p id="action-copy"></p><p id="action-error" class="field-error multiline" role="alert"></p><div class="dialog-actions"><button class="secondary" value="cancel">Go back</button><button class="primary" id="confirm-action" value="default">Continue</button></div></form></dialog>`;
    bindCopy(root);
    bindActions(root, id, tab, job);
  } catch (error) {
    root.innerHTML = `<header class="page-head"><h1>Job</h1></header>${errorPanel(error, "Job is unavailable")}<a href="#/jobs">Back to jobs</a>`;
  }
}

function bindActions(root, id, tab, currentJob) {
  root.querySelector('[data-action="run"]')?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "Starting…";
    try {
      await api.run(id);
      await showJob(root, id, "overview");
    } catch (error) {
      const holder = document.createElement("div");
      holder.innerHTML = errorPanel(error, error.status === 409 ? "Already running" : "Could not start job");
      button.closest(".next-action").after(holder.firstElementChild);
      button.disabled = false;
      button.textContent = "Run or resume";
    }
  });
  const actionDialog = root.querySelector("#action-dialog");
  let pendingAction = null;
  const openAction = (title, copy, action) => {
    pendingAction = action;
    actionDialog.querySelector("#action-title").textContent = title;
    actionDialog.querySelector("#action-copy").textContent = copy;
    actionDialog.querySelector("#action-error").textContent = "";
    actionDialog.showModal();
    actionDialog.querySelector("#action-title").focus();
  };
  root.querySelector('[data-action="rerun-preview"]')?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const stage = root.querySelector("#rerun-stage").value;
    button.disabled = true;
    try {
      const preview = await api.rerunPreview(id, stage);
      root.querySelector("#rerun-preview").innerHTML = `<p>Later stages marked not current: ${escapeHtml((preview.removesDownstream || []).join(", ") || "none")}.</p><p>Approvals revoked: ${escapeHtml((preview.revokesApprovals || []).join(", ") || "none")}.</p><button class="primary" type="button" id="confirm-rerun">Force rerun</button>`;
      root.querySelector("#confirm-rerun").addEventListener("click", () => openAction(
        `Rerun ${stage}`,
        `This deletes stale downstream results and revokes ${((preview.revokesApprovals || []).join(", ")) || "no approvals"}.`,
        async () => { await api.rerun(id, stage); await showJob(root, id, "overview"); },
      ));
    } catch (error) {
      root.querySelector("#rerun-preview").innerHTML = errorPanel(error, "Rerun preview failed");
    } finally { button.disabled = false; }
  });
  const trackActions = {
    "track-b-voice": ["Generate voice", "Kokoro writes audio takes for the approved script. The composition file stays as written.", () => api.trackB(id, "voice")],
    "track-b-align": ["Align words", "Word timing is written from the audio takes already in this job.", () => api.trackB(id, "align")],
    "track-b-render": ["Render HyperFrames", "Render writes video.mp4 from the existing project directory.", () => api.trackB(id, "render")],
    "track-b-qa": ["Run diagnostics", "Technical QA, visual checks, and the critic reader are stored separately.", () => api.trackB(id, "qa")],
    "track-b-register": ["Register finished video", "Registration records the finished video and external stage evidence when this studio did not render it.", () => api.trackB(id, "register")],
  };
  root.querySelectorAll("[data-action^='track-b-']").forEach((button) => button.addEventListener("click", () => {
    const [title, copy, action] = trackActions[button.dataset.action] ?? [];
    if (action) openAction(title, copy, async () => { await action(); await showJob(root, id, tab); });
  }));
  root.querySelector('[data-action="qa"]')?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try { await api.rerunQa(id); await showJob(root, id, "review"); }
    catch (error) { button.insertAdjacentHTML("afterend", errorPanel(error, "QA rerun failed")); button.disabled = false; }
  });
  root.querySelector('[data-action="export"]')?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      const preview = await api.exportPreview(id);
      openAction("Export validated video", `Copy ${preview.source} (${preview.bytes} bytes, ${preview.sha256}) to ${preview.destination}. Existing export: ${preview.existing || "none"}. Publishing stays disabled.`, async () => {
        await api.exportJob(id, preview.existing === "already-exported");
        await showJob(root, id, "files");
      });
    } catch (error) {
      button.insertAdjacentHTML("afterend", errorPanel(error, "Export preview failed"));
    } finally { button.disabled = false; }
  });
  actionDialog?.querySelector("#confirm-action")?.addEventListener("click", async (event) => {
    event.preventDefault();
    const button = event.currentTarget;
    button.disabled = true;
    try {
      await pendingAction?.();
      actionDialog.close();
    } catch (error) {
      actionDialog.querySelector("#action-error").textContent = error.message;
      button.disabled = false;
    }
  });
  root.querySelector('[data-action="preview"]')?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "Generating…";
    try { await api.preview(id); await showJob(root, id, "review"); }
    catch (error) { button.insertAdjacentHTML("afterend", errorPanel(error, "Preview failed")); button.disabled = false; button.textContent = "Generate preview"; }
  });

  const dialog = root.querySelector("#approval-dialog");
  let opener = null;
  root.querySelectorAll(".open-approval").forEach((button) => button.addEventListener("click", () => {
    opener = button;
    dialog.dataset.gate = button.dataset.gate;
    dialog.dataset.digest = button.dataset.digest;
    dialog.querySelector("#approval-digest").textContent = button.dataset.digest;
    dialog.querySelector("#approval-error").textContent = "";
    dialog.showModal();
    dialog.querySelector("#approval-title").focus();
  }));
  dialog?.addEventListener("close", () => opener?.focus());
  root.querySelector("#confirm-approval")?.addEventListener("click", async (event) => {
    event.preventDefault();
    const button = event.currentTarget;
    button.disabled = true;
    try {
      await api.approve(id, dialog.dataset.gate, dialog.dataset.digest);
      dialog.close();
      await showJob(root, id, dialog.dataset.gate === "SCRIPT_APPROVED" ? "script" : "review");
    } catch (error) {
      dialog.querySelector("#approval-error").textContent = error.status === 409 ? "The artifact changed. Close this dialog and review the current digest." : error.message;
      button.disabled = false;
    }
  });

  if (tab === "logs") {
    const select = root.querySelector("#log-stage");
    const load = async () => {
      const holder = root.querySelector("#log-result");
      holder.innerHTML = "<p>Loading log…</p>";
      try {
        const payload = await api.log(id, select.value);
        const text = typeof payload === "string" ? payload : payload?.log ?? payload?.text ?? payload?.tail;
        holder.dataset.log = text ?? "";
        const query = root.querySelector("#log-search").value.trim().toLowerCase();
        const visible = !query ? holder.dataset.log : holder.dataset.log.split("\n").filter((line) => line.toLowerCase().includes(query)).join("\n");
        holder.innerHTML = payload?.status === "NOT_RUN"
          ? emptyState("Stage not run", "This stage has not produced a log.")
          : text == null
            ? emptyState("Log unavailable", payload?.message ?? "This stage did not return a captured log.")
            : `<pre class="log-viewer">${escapeHtml(visible || "No matching log lines.")}</pre>`;
      } catch (error) { holder.innerHTML = errorPanel(error, "Log unavailable"); }
    };
    select.addEventListener("change", load);
    root.querySelector("#log-search").addEventListener("input", load);
    root.querySelector("#log-wrap").addEventListener("change", (event) => root.querySelector(".log-viewer")?.classList.toggle("nowrap", !event.target.checked));
    root.querySelector("#copy-log").addEventListener("click", () => navigator.clipboard.writeText(root.querySelector("#log-result")?.dataset.log ?? ""));
    root.querySelector("#download-log").addEventListener("click", () => {
      const text = root.querySelector("#log-result")?.dataset.log;
      if (text == null) return;
      const link = document.createElement("a");
      const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
      link.href = url;
      link.download = `${id}-${select.value}.log`;
      link.click();
      URL.revokeObjectURL(url);
    });
    load();
  }

  if (tab === "overview" && ["running", "pending", "draft"].includes(currentJob.status.state)) {
    const expectedHash = `#/jobs/${encodeURIComponent(id)}/overview`;
    const fingerprint = (job) => JSON.stringify({
      state: job.status.state,
      updated: job.updated,
      gate: job.gate,
      stages: job.stages.map((stage) => [stage.name, stage.status.state, stage.attemptCount]),
    });
    let current = fingerprint(currentJob);
    let timer = null;
    let closeEvents = () => {};
    const active = () => root.isConnected && root.__watchToken === watchToken && location.hash === expectedHash;
    const refresh = async () => {
      if (!active()) { closeEvents(); clearTimeout(timer); return; }
      try {
        const payload = await api.job(id);
        const fresh = jobView(payload?.job ?? payload);
        const next = fingerprint(fresh);
        if (next !== current) {
          current = next;
          root.querySelector("#state-announcement").textContent = `Job state changed to ${fresh.status.label}.`;
          closeEvents();
          await showJob(root, id, "overview");
        }
      } catch { /* polling retries while this route remains active */ }
    };
    const poll = async () => {
      await refresh();
      if (active()) timer = setTimeout(poll, 2000);
    };
    closeEvents = watchJobEvents(id, {
      onSignal: refresh,
      onFallback: () => {
        refresh();
        if (active() && timer == null) timer = setTimeout(poll, 2000);
      },
    });
  }
}
