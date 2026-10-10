#!/usr/bin/env node
/**
 * ContentForge v1 filesystem transport worker.
 * Watches VIDEO_FACTORY_ROOT/queue, adapts CONTRACT.json via contract_adapter.mjs, and runs the production core
 * (`contentos production run`, factory mode) for each job, writing state and output atomically.
 *
 * VIDEO_FACTORY_ROOT is the exchange root: data only, shared with the control plane, never the repo
 * (default ~/.contentos/exchange). Everything read from it is hostile input. Readiness is served on
 * VIDEO_FACTORY_DASHBOARD_HOST (default 127.0.0.1; set it to the Tailscale address), never every interface.
 *
 * Lifecycle (ticket 07): the pipeline runs as a child process group, so this process keeps answering readiness and
 * keeps its heartbeat (VIDEO_FACTORY_WORKSPACE/.factory_worker.heartbeat, outside the exchange root) while a job renders.
 * One worker per workspace: a live worker's heartbeat refuses a second start. After a crash the next start stops the
 * pipeline the dead worker left running, then resumes what is in work/ (finished stages are skipped). A claim nobody is
 * working on for VIDEO_FACTORY_STALE_MS goes back to queue/; a job taken over more than MAX_RECLAIMS times is failed.
 * SIGTERM/SIGINT stop the pipeline and leave the job in work/ for the next start.
 *
 * Test seams: VIDEO_FACTORY_WORKSPACE (default ~/Desktop/VideoFactory-Workspace, the same as the pipeline; jobs live in jobs/YYYY/MM/<id>),
 * VIDEO_FACTORY_CONTENTOS (the launcher to run), VIDEO_FACTORY_POLL_MS, VIDEO_FACTORY_HEARTBEAT_MS,
 * VIDEO_FACTORY_STALE_MS, VIDEO_FACTORY_JOB_TIMEOUT_MS.
 * Delete with contentos/adapters/v1/ when contract v2 ships.
 */
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

import { adaptV1Contract, CONTRACT_VERSION, DISPOSABLE_ADAPTER_MODULE } from "./contract_adapter.mjs";
import {
  DEFAULT_EXCHANGE_ROOT,
  JOB_ID_RE,
  MAX_CONTRACT_BYTES,
  assertExchangeRoot,
  assertReadinessHost,
  assertWorkspaceOutsideRoot,
  listenWithRetry,
  loadStateFile,
  makeRedactor,
  parsePort,
  publicJob,
  safeName,
  stateFileName,
} from "./exchange.mjs";
import {
  acquireLock,
  commandOf,
  killProcessGroup,
  numericJobOrder,
  processAlive,
  removeHeartbeat,
  writeHeartbeat,
} from "./lifecycle.mjs";

const ADAPTER_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(ADAPTER_DIR, "../../..");
const ONCE = process.argv.includes("--once");

const envMs = (name, fallback) => {
  const n = Number(process.env[name]);
  return Number.isFinite(n) && n > 0 ? n : fallback;
};
const POLL_MS = envMs("VIDEO_FACTORY_POLL_MS", 2000);
const HEARTBEAT_MS = envMs("VIDEO_FACTORY_HEARTBEAT_MS", 10_000);
/** A work/ claim with no owner, quiet this long, goes back to queue/ (ticket 07: 600 s). */
const STALE_WORK_MS = envMs("VIDEO_FACTORY_STALE_MS", 600_000);
/** Backstop for a core that hangs: the core's own retry cap and per-tool timeouts normally end a job far sooner. */
const JOB_TIMEOUT_MS = envMs("VIDEO_FACTORY_JOB_TIMEOUT_MS", 45 * 60_000);
/** A job taken over this many times after a worker went away is failed, not looped (a poison job would crash-loop a service). */
const MAX_RECLAIMS = 3;
const TAIL_BYTES = 16 * 1024;

// Same default as contentos/storage.py: generated work lives OUTSIDE the repo. Python and this worker must agree on it.
const WORKSPACE = path.resolve(process.env.VIDEO_FACTORY_WORKSPACE?.trim() || path.join(os.homedir(), "Desktop", "VideoFactory-Workspace"));
/** The job folder is <workspace>/jobs/YYYY/MM/<jobId> (chosen by contentos/storage.py on first use). */
export function findJobDir(workspace, jobId) {
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(jobId) || jobId.includes("..")) return null;
  const jobs = path.join(workspace, "jobs");
  let years = [];
  try { years = fs.readdirSync(jobs).filter((n) => /^\d{4}$/.test(n)).sort(); } catch { return null; }
  for (const y of years) {
    let months = [];
    try { months = fs.readdirSync(path.join(jobs, y)).filter((n) => /^[01]\d$/.test(n)).sort(); } catch { continue; }
    for (const m of months) {
      const p = path.join(jobs, y, m, jobId);
      try { if (fs.statSync(p).isDirectory()) return p; } catch { /* not here */ }
    }
  }
  return null;
}
const CONTENTOS = process.env.VIDEO_FACTORY_CONTENTOS?.trim() || path.join(REPO_ROOT, "contentos.sh");
const HEARTBEAT_FILE = path.join(WORKSPACE, ".factory_worker.heartbeat");

const now = () => Date.now();
const log = (m) => console.error(`[factory-worker ${new Date().toISOString()}] ${m}`);

/** What this process is doing; the heartbeat file and the readiness manifest both report it. */
const life = { startedAt: now(), active: null, stopping: false };
let redact = (s) => s;

const argValue = (flag) => {
  const i = process.argv.indexOf(flag);
  return i >= 0 ? process.argv[i + 1] : undefined;
};

/** Everything that can be misconfigured, checked once, before any folder is touched. */
function settings() {
  const raw = process.env.VIDEO_FACTORY_ROOT?.trim();
  const root = raw ? path.resolve(raw) : DEFAULT_EXCHANGE_ROOT;
  assertExchangeRoot(root, REPO_ROOT);
  assertWorkspaceOutsideRoot(root, WORKSPACE);
  return {
    root,
    port: parsePort(argValue("--port") ?? process.env.VIDEO_FACTORY_DASHBOARD_PORT, 4300),
    host: assertReadinessHost(argValue("--host") ?? process.env.VIDEO_FACTORY_DASHBOARD_HOST ?? "127.0.0.1"),
  };
}

/** Directory entries that are real directories, oldest job first; a symlink dropped in by the producer is not one. */
function realDirNames(dir, warned) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return [];
  }
  for (const e of entries) {
    if (!e.isDirectory() && !e.name.startsWith(".") && !warned.has(e.name)) {
      warned.add(e.name);
      log(`ignoring ${path.basename(dir)}/${safeName(e.name)}: not a plain directory`);
    }
  }
  return entries.filter((e) => e.isDirectory()).map((e) => e.name).sort(numericJobOrder);
}
const warnedEntries = new Set();

function dirs(root) {
  return {
    building: path.join(root, "building"),
    queue: path.join(root, "queue"),
    work: path.join(root, "work"),
    done: path.join(root, "done"),
    failed: path.join(root, "failed"),
    output: path.join(root, "output"),
    state: path.join(root, "state"),
  };
}

function ensureDirs(D) {
  for (const p of [...Object.values(D), WORKSPACE]) fs.mkdirSync(p, { recursive: true });
}

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function writeJsonAtomic(p, obj) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  const tmp = `${p}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(obj, null, 2)}\n`);
  fs.renameSync(tmp, p);
}

function moveDir(from, to) {
  fs.mkdirSync(path.dirname(to), { recursive: true });
  if (fs.existsSync(to)) fs.rmSync(to, { recursive: true, force: true });
  fs.renameSync(from, to);
  return to;
}

function yamlQuote(s) {
  return JSON.stringify(String(s));
}

function contentosSpecToYaml(spec) {
  const lines = [
    `content_id: ${spec.content_id}`,
    `title: ${yamlQuote(spec.title)}`,
    `format: ${yamlQuote(spec.format)}`,
    `voice: ${yamlQuote(spec.voice)}`,
  ];
  if (spec._v1_hyperframes_quality) {
    lines.push(`_v1_hyperframes_quality: ${yamlQuote(spec._v1_hyperframes_quality)}`);
  }
  lines.push("script:");
  for (const ln of spec.script) {
    lines.push(`  - say: ${yamlQuote(ln.say)}`);
    lines.push(`    headline: ${yamlQuote(ln.headline)}`);
    if (ln.tag) lines.push(`    tag: ${yamlQuote(ln.tag)}`);
    if (ln.broll) lines.push(`    broll: ${yamlQuote(ln.broll)}`);
  }
  return `${lines.join("\n")}\n`;
}

// ---- state, manifest, heartbeat ---------------------------------------------------------------------------------

/** @type {Map<string, object>} */
const jobMap = new Map();
let manifestJSON = "{}";

function persistState(D, job) {
  writeJsonAtomic(path.join(D.state, stateFileName(job.id)), publicJob(job, redact));
  refreshManifest(D, { write: true });
}

function manifestObject(D) {
  const all = [...jobMap.values()].map((j) => publicJob(j, redact));
  const counts = { queued: 0, rendering: 0, done: 0, failed: 0 };
  for (const j of all) {
    if (j.status === "queued") counts.queued++;
    else if (j.status === "rendering" || j.status === "voicing" || j.status === "voiced") counts.rendering++;
    else if (j.status === "done") counts.done++;
    else if (j.status === "failed") counts.failed++;
  }
  return {
    updatedAt: now(),
    adapterModule: DISPOSABLE_ADAPTER_MODULE,
    contractVersion: CONTRACT_VERSION,
    counts,
    worker: {
      pid: process.pid,
      startedAt: life.startedAt,
      heartbeatAt: now(),
      queueDepth: realDirNames(D.queue, warnedEntries).length,
      activeJob: life.active?.id ?? null,
    },
    jobs: all.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0)),
  };
}

/** The served manifest is rebuilt on every heartbeat; the file in the exchange root only when a job changes. */
function refreshManifest(D, { write }) {
  const manifest = manifestObject(D);
  manifestJSON = JSON.stringify(manifest);
  if (write) writeJsonAtomic(path.join(path.dirname(D.state), "manifest.json"), manifest);
}

function writeBeat() {
  try {
    writeHeartbeat(HEARTBEAT_FILE, {
      pid: process.pid,
      startedAt: life.startedAt,
      heartbeatAt: now(),
      activeJob: life.active ? { id: life.active.id, startedAt: life.active.startedAt, childPid: life.active.childPid ?? null } : null,
    });
  } catch (e) {
    log(`heartbeat not written: ${e.message}`);
  }
}

function failPermanent(D, job, code, message) {
  job.status = "failed";
  job.error = message;
  job.permanentFailureCode = code;
  job.finishedAt = now();
  job.updatedAt = now();
  log(`PERMANENT REJECT ${safeName(job.id)} [${code}]: ${redact(message)}`);
  try {
    if (job.dir && fs.existsSync(job.dir) && !job.dir.startsWith(D.failed)) {
      job.dir = moveDir(job.dir, path.join(D.failed, safeName(job.id)));
    }
  } catch (e) {
    log(`move to failed/ failed for ${job.id}: ${e.message}`);
  }
  jobMap.set(job.id, job);
  persistState(D, job);
}

// ---- running the production core ---------------------------------------------------------------------------------

const keepTail = (buf, chunk) => (buf + chunk).slice(-TAIL_BYTES);
const lastLines = (text, n = 4) => text.trim().split("\n").slice(-n).join(" | ").slice(-600);

/** The core prints one JSON result line on stdout; anything else (or nothing) means it did not finish its job. */
function parseResult(stdout) {
  for (const line of stdout.trim().split("\n").reverse()) {
    if (!line.startsWith("{")) continue;
    try {
      const r = JSON.parse(line);
      if (typeof r.ok === "boolean") return r;
    } catch {
      /* not the result line */
    }
  }
  return null;
}

/**
 * Run `contentos production run` as its own process group, so one signal stops npx, node and Chrome with it, and so this
 * process stays free to answer readiness and write its heartbeat. Never rejects: the outcome says what happened.
 */
function runCore(D, job, specPath, authorizedBy) {
  return new Promise((resolve) => {
    const child = spawn(CONTENTOS, ["production", "run", specPath, "--approve-private"], {
      cwd: REPO_ROOT,
      env: { ...process.env, CONTENTOS_FACTORY_AUTHORIZED_BY: authorizedBy },
      detached: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let pending = "";
    let timedOut = false;
    let settled = false;
    if (child.pid) {
      life.active = { id: job.id, startedAt: now(), childPid: child.pid };
      writeBeat(); // the pid is on disk before anything can kill us, so the next start can find the pipeline
      refreshManifest(D, { write: false });
    }
    child.stdout?.on("data", (d) => (stdout = keepTail(stdout, d)));
    child.stderr?.on("data", (d) => {
      stderr = keepTail(stderr, d);
      const lines = (pending + d).split("\n");
      pending = lines.pop();
      for (const line of lines) if (line.trim()) log(`${safeName(job.id)}: ${line}`);
    });
    const timer = setTimeout(() => {
      timedOut = true;
      void killProcessGroup(child.pid, { graceMs: 5000 });
    }, JOB_TIMEOUT_MS);
    const settle = (code, signal, spawnError) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      life.active = null;
      writeBeat();
      refreshManifest(D, { write: false });
      resolve({ code, signal, timedOut, spawnError, stdout, stderr });
    };
    const reapGroup = () => {
      try {
        process.kill(-child.pid, "SIGKILL"); // whatever a tool left behind in the group (Chrome, a worker)
      } catch {
        /* the group is already empty */
      }
    };
    child.on("error", (e) => settle(null, null, e));
    // `close` waits for every holder of the output pipes, so a straggler could hold it back: reap the group when the
    // leader exits, then give the pipes a moment to drain before settling.
    child.on("exit", (code, signal) => {
      reapGroup();
      const wait = setTimeout(() => settle(code, signal, null), 1500);
      child.once("close", () => {
        clearTimeout(wait);
        settle(code, signal, null);
      });
    });
  });
}

function atomicCopyOutput(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  const tmp = `${dest}.${process.pid}.part`;
  fs.copyFileSync(src, tmp);
  fs.renameSync(tmp, dest);
}

function finishSuccess(D, job, mp4Src, hyperSrc) {
  const hyper = readJson(hyperSrc);
  // The producer can write work/<id> too: never write through a directory it swapped for a symlink.
  if (!fs.lstatSync(job.dir).isDirectory()) throw new Error("job folder is no longer a plain directory");
  writeJsonAtomic(path.join(job.dir, "hyperframes.json"), hyper);
  const outDest = path.join(D.output, `${job.id}.mp4`);
  atomicCopyOutput(mp4Src, outDest);
  job.status = "done";
  job.error = null;
  job.finishedAt = now();
  job.updatedAt = now();
  job.hyperframes = hyper;
  job.dir = moveDir(job.dir, path.join(D.done, job.id));
  jobMap.set(job.id, job);
  persistState(D, job);
  log(`done: ${job.id}`);
}

const FAILURE_CODES = { transient: "transient_exhausted", blocked: "pipeline_blocked" };
const describeLimit = (ms) => {
  const minutes = Math.round(ms / 60_000);
  return ms >= 60_000 ? `${minutes} minute${minutes === 1 ? "" : "s"}` : `${Math.max(1, Math.round(ms / 1000))} s`;
};

async function processJob(D, jobId, jobDir) {
  if (life.stopping) return;
  if (!JOB_ID_RE.test(jobId)) {
    const job = { id: safeName(jobId), status: "failed", dir: jobDir, updatedAt: now() };
    failPermanent(D, job, "invalid_job_id", `job folder "${safeName(jobId)}" is not a cfvg-<n> id`);
    return;
  }
  const contractPath = path.join(jobDir, "CONTRACT.json");
  let contractStat = null;
  try {
    contractStat = fs.lstatSync(contractPath);
  } catch {
    /* absent */
  }
  if (!contractStat) {
    const job = { ...jobMap.get(jobId), id: jobId, status: "failed", dir: jobDir, updatedAt: now() };
    failPermanent(D, job, "missing_contract", "CONTRACT.json is required in the job folder");
    return;
  }
  if (!contractStat.isFile() || contractStat.size > MAX_CONTRACT_BYTES) {
    const job = { ...jobMap.get(jobId), id: jobId, status: "failed", dir: jobDir, updatedAt: now() };
    failPermanent(D, job, "invalid_contract", `CONTRACT.json must be a plain file under ${MAX_CONTRACT_BYTES / 1024} KiB`);
    return;
  }

  let raw;
  try {
    raw = readJson(contractPath);
  } catch {
    const job = { ...jobMap.get(jobId), id: jobId, status: "failed", dir: jobDir, updatedAt: now() };
    failPermanent(D, job, "invalid_contract", "CONTRACT.json is not valid JSON");
    return;
  }

  const adapted = adaptV1Contract(raw, {
    authorizedBy: process.env.CONTENTOS_FACTORY_AUTHORIZED_BY || "factory-mode:production-job",
  });
  if (!adapted.ok) {
    const job = { ...jobMap.get(jobId), id: jobId, contractVersion: CONTRACT_VERSION, status: "failed", dir: jobDir, updatedAt: now() };
    failPermanent(D, job, adapted.code, adapted.message);
    return;
  }

  const { contentosSpec, factorySettings } = adapted;
  if (factorySettings.jobId !== jobId) {
    const job = { ...jobMap.get(jobId), id: jobId, contractVersion: CONTRACT_VERSION, status: "failed", dir: jobDir, updatedAt: now() };
    failPermanent(D, job, "job_id_mismatch", `contract jobId "${factorySettings.jobId}" does not match its folder "${jobId}"`);
    return;
  }
  // The derived spec is what the pipeline executes: keep it out of the shared folder so the producer
  // cannot swap it between this write and the pipeline's read.
  const specDir = path.join(WORKSPACE, "factory-specs");
  fs.mkdirSync(specDir, { recursive: true });
  const specPath = path.join(specDir, `${jobId}.yaml`);
  fs.writeFileSync(specPath, contentosSpecToYaml(contentosSpec));

  const job = jobMap.get(jobId) || { id: jobId };
  job.title ??= contentosSpec.title;
  job.format ??= factorySettings.format;
  job.createdAt ??= now();
  job.contractVersion = CONTRACT_VERSION;
  job.status = "rendering";
  job.dir = jobDir;
  job.authorizedBy = factorySettings.authorizedBy;
  job.advisoryDurationMs = factorySettings.advisoryDurationMs;
  job.factorySettings = factorySettings;
  job.updatedAt = now();
  job.error = null;
  jobMap.set(jobId, job);
  persistState(D, job);
  log(`rendering: ${jobId} authorizedBy=${factorySettings.authorizedBy} quality=${factorySettings.hyperframesQuality}`);

  const run = await runCore(D, job, specPath, factorySettings.authorizedBy);
  if (life.stopping) {
    log(`stopped while ${jobId} was running; it stays in work/ and resumes on the next start`);
    return;
  }
  if (run.timedOut) {
    job._stderr = run.stderr;
    failPermanent(D, job, "pipeline_timeout", `contentos exceeded its ${describeLimit(JOB_TIMEOUT_MS)} limit for this job and was stopped`);
    return;
  }
  const result = run.spawnError ? null : parseResult(run.stdout);
  if (!result) {
    job._stderr = run.stderr;
    const how = run.spawnError ? `could not start: ${run.spawnError.message}` : run.signal ? `ended by ${run.signal}` : `exited ${run.code}`;
    failPermanent(D, job, "pipeline_crashed", `contentos ${how} without a result: ${lastLines(run.stderr || run.stdout)}`);
    return;
  }
  job.attempts = result.attempts;
  if (!result.ok) {
    job._stderr = run.stderr;
    job.failureClass = result.failureClass;
    job.failedStage = result.stage;
    failPermanent(D, job, FAILURE_CODES[result.failureClass] ?? "pipeline_failed", result.error || "contentos reported a failure");
    return;
  }

  const proj = findJobDir(WORKSPACE, jobId) ?? path.join(WORKSPACE, "jobs", "missing", jobId);
  const mp4 = path.join(proj, "video.mp4");
  const hyper = path.join(proj, "project/hyperframes.json");
  if (!fs.existsSync(mp4)) {
    failPermanent(D, job, "missing_output", "pipeline succeeded but video.mp4 is missing");
    return;
  }
  if (!fs.existsSync(hyper)) {
    failPermanent(D, job, "missing_hyperframes", "pipeline succeeded but project/hyperframes.json is missing");
    return;
  }
  try {
    finishSuccess(D, job, mp4, hyper);
  } catch (e) {
    failPermanent(D, job, "output_io", e.message);
  }
}

// ---- claims, recovery, reclaim -----------------------------------------------------------------------------------

function claimOne(D) {
  const names = realDirNames(D.queue, warnedEntries);
  if (!names.length) return null;
  const id = names[0];
  const from = path.join(D.queue, id);
  const to = path.join(D.work, id);
  try {
    moveDir(from, to);
  } catch (e) {
    log(`claim failed for ${id}: ${e.message}`);
    return null;
  }
  return { id, dir: to };
}

function savedState(D, id) {
  try {
    return loadStateFile(`${id}.json`, readJson(path.join(D.state, `${id}.json`)));
  } catch {
    return null; // no usable state: start from nothing
  }
}

/** Count one more takeover of a job whose worker went away. False means the cap is hit and the job was failed. */
function takeOver(D, id, dir) {
  const job = { ...(jobMap.get(id) ?? savedState(D, id) ?? { id, createdAt: now() }), dir };
  job.reclaimCount = (job.reclaimCount ?? 0) + 1;
  jobMap.set(id, job);
  if (job.reclaimCount > MAX_RECLAIMS) {
    failPermanent(D, job, "reclaim_limit", `taken over ${MAX_RECLAIMS} times after the worker went away; not trying again`);
    return false;
  }
  return true;
}

/** Start-up: the last worker is gone (the lock says so), so whatever it left in work/ resumes where its stages stopped. */
async function recoverWork(D) {
  for (const id of realDirNames(D.work, warnedEntries)) {
    const dir = path.join(D.work, id);
    if (JOB_ID_RE.test(id)) {
      if (!takeOver(D, id, dir)) continue;
      log(`resume in work/: ${id} (taken over ${jobMap.get(id).reclaimCount} time(s))`);
    }
    await processJob(D, id, dir); // a folder that is not a cfvg id is rejected for good in there
  }
}

/** A claim in work/ that this process is not running and that has been quiet for STALE_WORK_MS goes back to queue/. */
async function reclaimStale(D) {
  for (const id of realDirNames(D.work, warnedEntries)) {
    const dir = path.join(D.work, id);
    let touched = 0;
    try {
      touched = fs.statSync(dir).mtimeMs;
    } catch {
      continue;
    }
    const quietFor = now() - Math.max(touched, jobMap.get(id)?.updatedAt ?? 0);
    if (quietFor < STALE_WORK_MS) continue;
    if (!JOB_ID_RE.test(id)) {
      await processJob(D, id, dir); // rejects it for good
      continue;
    }
    if (!takeOver(D, id, dir)) continue;
    const queued = path.join(D.queue, id);
    if (fs.existsSync(queued)) {
      fs.rmSync(dir, { recursive: true, force: true });
      log(`work/${safeName(id)} was stale and a newer copy waits in queue/: dropped the stale one`);
      continue;
    }
    const job = jobMap.get(id);
    job.dir = moveDir(dir, queued);
    job.status = "queued";
    job.error = null;
    job.updatedAt = now();
    persistState(D, job);
    log(`reclaimed ${safeName(id)}: nobody worked on it for ${Math.round(quietFor / 1000)} s, back in queue/ (taken over ${job.reclaimCount} time(s))`);
  }
}

function bootState(D) {
  try {
    for (const f of fs.readdirSync(D.state)) {
      try {
        const job = loadStateFile(f, readJson(path.join(D.state, f)));
        if (job) jobMap.set(job.id, job);
      } catch {
        /* skip corrupt */
      }
    }
  } catch {
    /* no state dir */
  }
  refreshManifest(D, { write: true });
}

let busy = false;
/** One pass: reclaim stale claims, then take the oldest queued job if the lane is free. True if a job was handled. */
async function tick(D) {
  if (busy || life.stopping) return false;
  busy = true;
  try {
    await reclaimStale(D);
    if (realDirNames(D.work, warnedEntries).length) return false; // someone else's fresh claim: the lane is taken
    const claimed = claimOne(D);
    if (!claimed) return false;
    await processJob(D, claimed.id, claimed.dir);
    return true;
  } catch (e) {
    log(`tick failed: ${e.stack || e.message}`);
    return false;
  } finally {
    busy = false;
  }
}

// ---- process lifecycle ---------------------------------------------------------------------------------------------

function startHttp({ port, host }) {
  const server = http.createServer((req, res) => {
    if (req.method === "GET" && (req.url || "/").split("?")[0] === "/manifest.json") {
      res.writeHead(200, { "content-type": "application/json", "cache-control": "no-store" });
      res.end(manifestJSON);
      return;
    }
    res.writeHead(404);
    res.end("not found");
  });
  if (ONCE) server.unref();
  return listenWithRetry(server, { port, host, log, unref: ONCE });
}

/** The last worker died with a pipeline running: it still holds the job's folders, so stop it before resuming. */
async function stopOrphan(previous) {
  const pid = previous?.activeJob?.childPid;
  if (!Number.isInteger(pid) || !processAlive(pid) || !/contentos/.test(commandOf(pid))) return;
  await killProcessGroup(pid, { graceMs: 5000 });
  log(`stopped an orphaned pipeline (pid ${pid}) that worker ${previous.pid} left behind`);
}

let heartbeatTimer = null;
let pollTimer = null;
let httpHandle = null;

function releaseProcess(code) {
  clearInterval(heartbeatTimer);
  clearInterval(pollTimer);
  removeHeartbeat(HEARTBEAT_FILE, process.pid);
  httpHandle?.stop();
  process.exitCode = code;
}

async function shutdown(reason, code = 0) {
  if (life.stopping) return;
  life.stopping = true;
  log(`stopping (${reason})`);
  clearInterval(pollTimer);
  clearInterval(heartbeatTimer);
  if (life.active?.childPid) await killProcessGroup(life.active.childPid, { graceMs: 5000 });
  releaseProcess(code);
  setTimeout(() => process.exit(code), 2000).unref(); // a backstop; normally nothing is left to keep the process alive
}

async function main() {
  let cfg;
  try {
    cfg = settings();
  } catch (e) {
    console.error(`[factory-worker] ${e.message}`);
    process.exit(2);
  }
  const D = dirs(cfg.root);
  redact = makeRedactor([
    [cfg.root, "<exchange>"],
    [WORKSPACE, "<workspace>"],
    [REPO_ROOT, "<factory>"],
    [os.homedir(), "~"],
  ]);

  fs.mkdirSync(WORKSPACE, { recursive: true });
  const lock = acquireLock({ file: HEARTBEAT_FILE, pid: process.pid });
  if (!lock.ok) {
    console.error(`[factory-worker] ${lock.message}`);
    process.exit(3);
  }
  ensureDirs(D);
  log(`exchange root ${cfg.root}; readiness ${cfg.host}:${cfg.port}`);
  if (lock.previous) {
    log(`the last worker (pid ${lock.previous.pid}) did not stop cleanly`);
    await stopOrphan(lock.previous);
  }

  for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => void shutdown(sig));
  for (const event of ["uncaughtException", "unhandledRejection"]) {
    process.on(event, (e) => {
      log(`fatal ${event}: ${e?.stack || e}`);
      void shutdown(event, 1);
    });
  }

  writeBeat();
  bootState(D);
  httpHandle = startHttp(cfg);
  heartbeatTimer = setInterval(() => {
    writeBeat();
    refreshManifest(D, { write: false });
  }, HEARTBEAT_MS);

  await recoverWork(D);
  if (ONCE) {
    while (await tick(D)); // drain what is queued, then leave
    releaseProcess(0);
    return;
  }
  pollTimer = setInterval(() => void tick(D), POLL_MS);
  void tick(D);
}

main();
