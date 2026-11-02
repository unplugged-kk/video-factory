import { escapeHtml } from "./components.js";
import { api } from "./api.js";
import { showJob } from "./pages/job.js";
import { showTrackB } from "./pages/track-b.js";
import { showJobs } from "./pages/jobs.js";
import { showNewJob } from "./pages/new-job.js";
import { showHealth, showHelp, showQueue } from "./pages/static.js";
import { healthReadiness } from "./state.js";

const app = document.querySelector("#app");
const nav = document.querySelector("#primary-nav");
const globalNotice = document.querySelector("#global-notice");

function routeParts() {
  const raw = location.hash.replace(/^#\/?/, "").split("?")[0];
  return raw.split("/").filter(Boolean).map((part) => decodeURIComponent(part));
}

async function route() {
  const parts = routeParts();
  const section = parts[0] || "jobs";
  document.querySelectorAll("#primary-nav a").forEach((link) => link.toggleAttribute("aria-current", link.dataset.section === section));
  app.setAttribute("aria-busy", "true");
  app.innerHTML = "";
  try {
    if (section === "track-b") await showTrackB(app);
    else if (section === "jobs" && parts[1] === "new") await showNewJob(app);
    else if (section === "jobs" && parts[1]) await showJob(app, parts[1], parts[2]);
    else if (section === "jobs") await showJobs(app);
    else if (section === "queue") await showQueue(app);
    else if (section === "health") await showHealth(app);
    else if (section === "help") showHelp(app);
    else {
      app.innerHTML = `<section class="empty"><h1>Page not found</h1><p>No Creator Studio page matches <code>${escapeHtml(location.hash)}</code>.</p><a class="button primary" href="#/jobs">View jobs</a></section>`;
    }
  } finally {
    app.removeAttribute("aria-busy");
    applyRunBlock(document.documentElement.dataset.runBlocked === "true");
    app.focus({ preventScroll: true });
  }
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("contentos-theme", theme);
  const button = document.querySelector("#theme-toggle");
  button.textContent = theme === "dark" ? "Use light theme" : "Use dark theme";
  button.setAttribute("aria-label", `${theme === "dark" ? "Dark" : "Light"} theme active. Use ${theme === "dark" ? "light" : "dark"} theme`);
  button.setAttribute("aria-pressed", String(theme === "dark"));
}

function applyRunBlock(blocked) {
  document.documentElement.dataset.runBlocked = String(blocked);
  app.querySelectorAll('[data-action="run"]').forEach((button) => {
    button.disabled = blocked;
    button.title = blocked ? "Resolve required Health checks before running" : "";
    if (blocked && !button.parentElement.querySelector(".health-run-link")) {
      button.insertAdjacentHTML("afterend", '<a class="health-run-link" href="#/health">Review Health</a>');
    }
  });
}

function applyGlobalHealth(health) {
  const readiness = healthReadiness(health);
  const labels = readiness.blockers.map((blocker) => blocker.label);
  globalNotice.innerHTML = readiness.ready
    ? ""
    : `<section class="notice notice--error" role="status"><strong>Run blocked by Health</strong><p>${escapeHtml(labels.join(", "))} ${labels.length === 1 ? "is" : "are"} unavailable. <a href="#/health">Review remediation</a>.</p></section>`;
  applyRunBlock(!readiness.ready);
}

async function checkGlobalHealth() {
  try {
    applyGlobalHealth(await api.health());
  } catch {
    globalNotice.innerHTML = '<section class="notice notice--warning"><strong>Health status unavailable</strong><p>Creator Studio could not verify run prerequisites. <a href="#/health">Open Health</a>.</p></section>';
    applyRunBlock(true);
  }
}

document.querySelector("#theme-toggle").addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
setTheme(localStorage.getItem("contentos-theme") || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"));
window.addEventListener("hashchange", route);
nav.addEventListener("click", (event) => {
  if (event.target.closest("a")?.hash === location.hash) route();
});
window.addEventListener("contentos:health", (event) => applyGlobalHealth(event.detail));
checkGlobalHealth();
route();
