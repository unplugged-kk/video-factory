#!/usr/bin/env node
// Video Factory runner — watcher + serial TTS lane + render pool + tiny HTTP server.
// Zero npm deps (Node 22 built-ins only). Write once, run forever. Do not edit per-video.
//
// Flow: drop a built HyperFrames project folder into queue/. This process runs
// TTS one-at-a-time (Chatterbox locks) and renders up to RENDER_CONCURRENCY at once,
// writing each job's status to state/<id>.json and the aggregate to manifest.json.
// The dashboard polls http://localhost:PORT/manifest.json.

import fs from "node:fs";
import path from "node:path";
import http from "node:http";
import os from "node:os";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

// ---------- config (the only knobs) ----------
const RENDER_CONCURRENCY = 3;     // safe on M2 Max / 32GB; each render spawns Chrome workers
const PORT = 4300;
const POLL_MS = 2000;             // how often we reconcile the queue/ folder
const EST_RENDER_S = 200;         // rough per-video render estimate, for the dashboard ETA
const HOME = os.homedir();
const REVOICE = path.join(HOME, "Desktop/software/videos/revoice.py");
const READY_TO_POST = path.join(HOME, "Desktop/ready-to-post");

// ---------- paths ----------
const ROOT = path.dirname(fileURLToPath(import.meta.url));
const DIR = {
  building: path.join(ROOT, "building"), // Claude Code is still creating the project here
  queue: path.join(ROOT, "queue"),
  work: path.join(ROOT, "work"),
  drafts: path.join(ROOT, "drafts"), // rendered, awaiting your approval
  done: path.join(ROOT, "done"), // approved by you

  failed: path.join(ROOT, "failed"),
  output: path.join(ROOT, "output"),
  state: path.join(ROOT, "state"),
  thumbs: path.join(ROOT, "thumbs"),
};
for (const p of [...Object.values(DIR), READY_TO_POST]) fs.mkdirSync(p, { recursive: true });

// ---------- in-memory state ----------
const jobs = new Map();        // id -> job record (persisted to state/<id>.json)
const children = new Map();    // id -> ChildProcess (never serialized)
let ttsBusy = false;
let renderCount = 0;
let paused = false;

const now = () => Date.now();
const log = (m) => console.log(`[${new Date().toISOString().slice(11, 19)}] ${m}`);

// ---------- persistence ----------
function persist(job) {
  const { _stderr, ...clean } = job;
  fs.writeFileSync(path.join(DIR.state, `${job.id}.json`), JSON.stringify(clean, null, 2));
  rebuildManifest();
}

let manifestJSON = "{}";
function rebuildManifest() {
  const all = [...jobs.values()].map(({ _stderr, ...j }) => j);
  const counts = { queued: 0, voicing: 0, voiced: 0, rendering: 0, done: 0, failed: 0 };
  for (const j of all) counts[j.status] = (counts[j.status] || 0) + 1;
  const manifest = {
    updatedAt: now(),
    paused,
    concurrency: RENDER_CONCURRENCY,
    estRenderS: EST_RENDER_S,
    counts,
    jobs: all.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0)),
  };
  manifestJSON = JSON.stringify(manifest);
  fs.writeFileSync(path.join(ROOT, "manifest.json"), JSON.stringify(manifest, null, 2));
}

// ---------- helpers ----------
function readJobConfig(dir) {
  try {
    return JSON.parse(fs.readFileSync(path.join(dir, "job.json"), "utf8"));
  } catch {
    return {};
  }
}

// The human-readable instructions for a job — shown on its dashboard card.
function readBrief(dir) {
  for (const f of ["BRIEF.md", "brief.md", "SCRIPT.md", "instructions.md", "README.md"]) {
    const p = path.join(dir, f);
    if (fs.existsSync(p)) { try { return fs.readFileSync(p, "utf8").slice(0, 1200); } catch {} }
  }
  try {
    const md = fs.readdirSync(dir).find((x) => x.endsWith(".md"));
    if (md) return fs.readFileSync(path.join(dir, md), "utf8").slice(0, 1200);
  } catch {}
  return null;
}

// A project needs the TTS lane if it looks like a product-launch-video project
// (revoice.py needs SCRIPT.md + STORYBOARD.md + audio_meta.json). job.json can override.
function detectNeedsVoice(dir, cfg) {
  if (typeof cfg.voice === "boolean") return cfg.voice;
  return fs.existsSync(path.join(dir, "SCRIPT.md")); // universal voice.mjs handles any project
}

// A building job is "actively being authored" once the agent has started writing the
// composition (vs a folder that still only has the seed job.json/BRIEF/RESEARCH files).
function authoringActive(dir) {
  // "being authored NOW" = a non-seed file was written in the last 3 minutes (a live agent).
  // Stale partial files from a dead agent have old mtimes and don't count.
  const seed = new Set(["job.json", "BRIEF.md", "RESEARCH.md"]);
  const cutoff = now() - 180000;
  try {
    return fs.readdirSync(dir).some((f) => {
      if (seed.has(f)) return false;
      try { return fs.statSync(path.join(dir, f)).mtimeMs > cutoff; } catch { return false; }
    });
  } catch { return false; }
}

// Aspect ratio for the little shape icon on the card — from job.json or the folder name.
function detectFormat(id, cfg) {
  const s = `${cfg.format || cfg.aspect || ""} ${id || ""}`.toLowerCase();
  if (/9x16|9-16|9:16|vertical|portrait|1080x1920/.test(s)) return "9:16";
  if (/16x9|16-9|16:9|horizontal|landscape|1920x1080/.test(s)) return "16:9";
  return null;
}

// Where the composition's index.html lives. Handles both conventions:
// root index.html (revoice/PLV projects) and public/index.html (older builds).
function detectRenderDir(dir, cfg) {
  if (cfg.renderDir) return cfg.renderDir;
  if (fs.existsSync(path.join(dir, "index.html"))) return ".";
  if (fs.existsSync(path.join(dir, "public", "index.html"))) return "public";
  return ".";
}

function moveDir(from, to) {
  fs.mkdirSync(path.dirname(to), { recursive: true });
  if (fs.existsSync(to)) fs.rmSync(to, { recursive: true, force: true }); // avoid ENOTEMPTY on re-renders
  fs.renameSync(from, to);
  return to;
}

// ---------- discovery / reconcile ----------
function registerQueued(name, src) {
  const cfg = readJobConfig(src);
  const prev = jobs.get(name);
  const job = {
    id: name,
    title: cfg.title || name,
    brief: readBrief(src),
    format: detectFormat(name, cfg),
    status: "queued",
    dir: src,
    needsVoice: detectNeedsVoice(src, cfg),
    skill: cfg.skill || (fs.existsSync(path.join(src, "STORYBOARD.md")) ? "product-launch-video" : null),
    renderArgs: Array.isArray(cfg.renderArgs) ? cfg.renderArgs : ["--quality", "high"],
    createdAt: prev ? prev.createdAt : now(),
    error: null,
    outputPath: null,
    renderSeconds: null,
  };
  jobs.set(name, job);
  log(`queued: ${name} (voice=${job.needsVoice})`);
  persist(job);
}

function reconcile() {
  // 1. building/ — Claude Code is still creating these. Show them, don't process them.
  for (const name of fs.readdirSync(DIR.building)) {
    const src = path.join(DIR.building, name);
    if (!fs.statSync(src).isDirectory()) continue;
    const existing = jobs.get(name);
    if (existing) {
      // Keep the card's title + brief live as Claude writes the files.
      if (existing.status === "building") {
        const cfg = readJobConfig(src), brief = readBrief(src);
        if (cfg.title && cfg.title !== existing.title) { existing.title = cfg.title; persist(existing); }
        if (brief && brief !== existing.brief) { existing.brief = brief; persist(existing); }
        if (!existing.format) { const f = detectFormat(name, cfg); if (f) { existing.format = f; persist(existing); } }
        const act = authoringActive(src);
        if (existing.active !== act) { existing.active = act; persist(existing); }
      }
      continue;
    }
    const cfg = readJobConfig(src);
    const job = { id: name, title: cfg.title || name, brief: readBrief(src), format: detectFormat(name, cfg),
      status: "building", active: authoringActive(src), dir: src, createdAt: now(), error: null, outputPath: null, renderSeconds: null };
    jobs.set(name, job);
    log(`building: ${name}`);
    persist(job);
  }
  // 2. queue/ — folders dropped here are ready. A "building" job that lands here has finished building.
  for (const name of fs.readdirSync(DIR.queue)) {
    const src = path.join(DIR.queue, name);
    if (!fs.statSync(src).isDirectory()) continue;
    const j = jobs.get(name);
    if (!j || j.status === "done" || j.status === "failed" || j.status === "building") {
      registerQueued(name, src);
    }
    // queued/voicing/voiced/rendering already tracked — leave as-is
  }
}

// ---------- TTS lane (serial) ----------
function startVoicing() {
  if (paused || ttsBusy) return;
  const job = [...jobs.values()]
    .filter((j) => j.status === "queued" && j.needsVoice)
    .sort((a, b) => a.createdAt - b.createdAt)[0];
  if (!job) return;

  ttsBusy = true;
  job.status = "voicing";
  job.startedAt = now();
  job.dir = moveDir(job.dir, path.join(DIR.work, job.id));
  log(`voicing: ${job.id}`);
  persist(job);

  const child = spawn("node", [path.join(ROOT, "voice.mjs"), job.dir], { cwd: job.dir });
  trackChild(job, child, (ok) => {
    ttsBusy = false;
    if (ok) {
      job.status = "voiced";
      job.voicedAt = now();
      log(`voiced: ${job.id}`);
      persist(job);
    } else {
      fail(job, "TTS/voice step failed");
    }
    tick();
  });
}

// ---------- render lane (pool) ----------
function startRenders() {
  while (!paused && renderCount < RENDER_CONCURRENCY) {
    // Ready to render: a voiced job, or a queued job that needs no voice.
    const job = [...jobs.values()]
      .filter((j) => j.status === "voiced" || (j.status === "queued" && !j.needsVoice))
      .sort((a, b) => a.createdAt - b.createdAt)[0];
    if (!job) return;

    renderCount++;
    if (job.dir.startsWith(DIR.queue)) job.dir = moveDir(job.dir, path.join(DIR.work, job.id));
    job.status = "rendering";
    job.renderStartedAt = now();
    log(`rendering: ${job.id} (${renderCount}/${RENDER_CONCURRENCY})`);
    persist(job);

    const renderDir = detectRenderDir(job.dir, readJobConfig(job.dir));
    const outAbs = path.join(job.dir, "renders", `${job.id}.mp4`);
    job.renderOut = outAbs;
    const args = ["hyperframes@0.7.60", "render", renderDir, ...(job.skill ? [`--skill=${job.skill}`] : []),
      ...job.renderArgs, "--output", outAbs];
    const child = spawn("npx", args, { cwd: job.dir });
    trackChild(job, child, (ok) => {
      renderCount--;
      if (ok) finishRender(job, outAbs);
      else fail(job, "render failed");
      tick();
    });
  }
}

function finishRender(job, mp4) {
  try {
    if (!fs.existsSync(mp4)) return fail(job, "render reported success but MP4 missing");
    const dest = path.join(DIR.output, `${job.id}.mp4`);
    fs.copyFileSync(mp4, dest);
    fs.copyFileSync(mp4, path.join(READY_TO_POST, `${job.id}.mp4`));
    makeThumb(dest, job.id);
    job.status = "done";
    job.finishedAt = now();
    job.renderSeconds = Math.round((job.finishedAt - job.renderStartedAt) / 1000);
    job.outputPath = dest;
    job.dir = moveDir(job.dir, path.join(DIR.done, job.id));
    log(`done: ${job.id} in ${job.renderSeconds}s -> ${dest}`);
    persist(job);
  } catch (e) {
    fail(job, `post-render copy failed: ${e.message}`);
  }
}

function makeThumb(mp4, id) {
  const thumb = path.join(DIR.thumbs, `${id}.jpg`);
  const c = spawn("ffmpeg", ["-y", "-i", mp4, "-vframes", "1", "-vf", "scale=240:-1", thumb]);
  c.on("error", () => {});
}

function fail(job, reason) {
  job.status = "failed";
  job.finishedAt = now();
  job.error = `${reason}${job._stderr ? "\n" + job._stderr.slice(-1500) : ""}`;
  try {
    if (!job.dir.startsWith(DIR.failed)) job.dir = moveDir(job.dir, path.join(DIR.failed, job.id));
  } catch {}
  log(`FAILED: ${job.id} — ${reason}`);
  persist(job);
}

function trackChild(job, child, done) {
  children.set(job.id, child);
  let err = "";
  child.stderr?.on("data", (d) => { err += d; if (err.length > 8000) err = err.slice(-8000); });
  child.stdout?.on("data", (d) => { /* progress; ignored to keep logs clean */ void d; });
  child.on("error", (e) => { job._stderr = (err + "\n" + e.message); children.delete(job.id); done(false); });
  child.on("close", (code) => { job._stderr = err; children.delete(job.id); done(code === 0); });
}

// ---------- scheduler tick ----------
let ticking = false;
function tick() {
  if (ticking) return;
  ticking = true;
  try {
    reconcile();
    startVoicing();
    startRenders();
  } catch (e) {
    log(`tick error: ${e.message}`);
  } finally {
    ticking = false;
  }
}

// ---------- boot: restore state, recover interrupted jobs ----------
function boot() {
  for (const f of fs.readdirSync(DIR.state)) {
    if (!f.endsWith(".json")) continue;
    try {
      const job = JSON.parse(fs.readFileSync(path.join(DIR.state, f), "utf8"));
      // A job mid-flight when the runner died: requeue it.
      if (job.status === "voicing" || job.status === "rendering" || job.status === "voiced") {
        const back = path.join(DIR.queue, job.id);
        if (fs.existsSync(job.dir) && !fs.existsSync(back)) job.dir = moveDir(job.dir, back);
        job.status = "queued";
        job.error = null;
      }
      if (!job.format) job.format = detectFormat(job.id, {});
      jobs.set(job.id, job);
    } catch {}
  }
  rebuildManifest();
  log(`booted: ${jobs.size} known jobs restored`);
}

// ---------- HTTP server ----------
function serveFile(res, file, type, req) {
  fs.stat(file, (e, st) => {
    if (e) { res.writeHead(404); res.end("not found"); return; }
    const range = req && req.headers.range;
    if (range) {
      // browsers require 206 + Content-Range to play/seek mp4
      const mm = /bytes=(\d*)-(\d*)/.exec(range) || [];
      let start = mm[1] ? parseInt(mm[1], 10) : 0;
      let end = mm[2] ? parseInt(mm[2], 10) : st.size - 1;
      if (isNaN(start)) start = 0;
      if (isNaN(end) || end >= st.size) end = st.size - 1;
      if (start > end) { res.writeHead(416, { "content-range": `bytes */${st.size}` }); return res.end(); }
      res.writeHead(206, {
        "content-type": type, "accept-ranges": "bytes",
        "content-range": `bytes ${start}-${end}/${st.size}`,
        "content-length": end - start + 1, "cache-control": "no-store",
      });
      fs.createReadStream(file, { start, end }).pipe(res);
    } else {
      res.writeHead(200, { "content-type": type, "accept-ranges": "bytes", "content-length": st.size, "cache-control": "no-store" });
      fs.createReadStream(file).pipe(res);
    }
  });
}

const MIME = { ".mp4": "video/mp4", ".jpg": "image/jpeg", ".html": "text/html", ".json": "application/json" };

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const p = url.pathname;

  if (req.method === "POST") {
    const id = url.searchParams.get("job");
    if (p === "/pause") { paused = true; rebuildManifest(); log("paused"); return json(res, { paused }); }
    if (p === "/resume") { paused = false; rebuildManifest(); log("resumed"); tick(); return json(res, { paused }); }
    if (p === "/retry" && id && jobs.has(id)) {
      const job = jobs.get(id);
      if (job.status === "failed") {
        try { if (fs.existsSync(job.dir)) job.dir = moveDir(job.dir, path.join(DIR.queue, id)); } catch {}
        jobs.delete(id);
        try { fs.rmSync(path.join(DIR.state, `${id}.json`)); } catch {}
        log(`retry: ${id}`); tick();
      }
      return json(res, { ok: true });
    }
    if (p === "/cancel" && id && jobs.has(id)) {
      const job = jobs.get(id);
      const child = children.get(id);
      if (child) child.kill("SIGKILL");
      if (job.status === "voicing") ttsBusy = false;
      if (job.status === "rendering") renderCount = Math.max(0, renderCount - 1);
      if (job.status === "building" || job.status === "queued") {
        // not yet processing — drop it entirely (removes the folder + card)
        try { if (fs.existsSync(job.dir)) fs.rmSync(job.dir, { recursive: true, force: true }); } catch {}
        jobs.delete(id);
        try { fs.rmSync(path.join(DIR.state, `${id}.json`)); } catch {}
        log(`cancelled + removed: ${id}`);
        rebuildManifest();
      } else {
        fail(job, "cancelled by user"); // in-flight work → keep in failed/ so it can be retried
      }
      tick();
      return json(res, { ok: true });
    }
    res.writeHead(400); return res.end("bad request");
  }

  if (p === "/" || p === "/dashboard.html") return serveFile(res, path.join(ROOT, "dashboard.html"), "text/html", req);
  if (p === "/gallery.html") return serveFile(res, path.join(ROOT, "gallery.html"), "text/html", req);
  if (p === "/manifest.json") { res.writeHead(200, { "content-type": "application/json", "cache-control": "no-store" }); return res.end(manifestJSON); }
  if (p.startsWith("/output/")) return serveFile(res, path.join(DIR.output, path.basename(p)), MIME[path.extname(p)] || "application/octet-stream", req);
  if (p.startsWith("/thumbs/")) return serveFile(res, path.join(DIR.thumbs, path.basename(p)), "image/jpeg", req);
  res.writeHead(404); res.end("not found");
});

function json(res, obj) { res.writeHead(200, { "content-type": "application/json" }); res.end(JSON.stringify(obj)); }

// ---------- go ----------
boot();
server.listen(PORT, () => log(`listening on http://localhost:${PORT}  (dashboard: /dashboard.html)`));
setInterval(tick, POLL_MS);
tick();
