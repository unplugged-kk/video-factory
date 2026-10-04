#!/usr/bin/env node
/**
 * ContentForge v1 filesystem transport worker.
 * Watches VIDEO_FACTORY_ROOT/queue, adapts CONTRACT.json via contract_adapter.mjs,
 * runs contentos pipeline in factory mode (--approve-private), writes state/output atomically.
 *
 * VIDEO_FACTORY_ROOT is the exchange root: data only, shared with the control plane, never the repo
 * (default ~/.contentos/exchange). Everything read from it is hostile input. Readiness is served on
 * VIDEO_FACTORY_DASHBOARD_HOST (default 127.0.0.1; set it to the Tailscale address), never every interface.
 * Delete with contentos/adapters/v1/ when contract v2 ships.
 */
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { adaptV1Contract, CONTRACT_VERSION, DISPOSABLE_ADAPTER_MODULE } from "./contract_adapter.mjs";
import {
  DEFAULT_EXCHANGE_ROOT,
  JOB_ID_RE,
  MAX_CONTRACT_BYTES,
  assertExchangeRoot,
  assertReadinessHost,
  listenWithRetry,
  loadStateFile,
  parsePort,
  publicJob,
  safeName,
  stateFileName,
} from "./exchange.mjs";

const ADAPTER_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(ADAPTER_DIR, "../../..");
const POLL_MS = Number(process.env.VIDEO_FACTORY_POLL_MS || 2000);
const ONCE = process.argv.includes("--once");

const now = () => Date.now();
const log = (m) => console.error(`[factory-worker ${new Date().toISOString()}] ${m}`);

const argValue = (flag) => {
  const i = process.argv.indexOf(flag);
  return i >= 0 ? process.argv[i + 1] : undefined;
};

/** Everything that can be misconfigured, checked once, before any folder is touched. */
function settings() {
  const raw = process.env.VIDEO_FACTORY_ROOT?.trim();
  const root = raw ? path.resolve(raw) : DEFAULT_EXCHANGE_ROOT;
  assertExchangeRoot(root, REPO_ROOT);
  return {
    root,
    port: parsePort(argValue("--port") ?? process.env.VIDEO_FACTORY_DASHBOARD_PORT, 4300),
    host: assertReadinessHost(argValue("--host") ?? process.env.VIDEO_FACTORY_DASHBOARD_HOST ?? "127.0.0.1"),
  };
}

/** Directory entries that are real directories; a symlink dropped in by the producer is not one. */
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
  return entries.filter((e) => e.isDirectory()).map((e) => e.name).sort();
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
  for (const p of Object.values(D)) fs.mkdirSync(p, { recursive: true });
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

function persistState(D, job) {
  writeJsonAtomic(path.join(D.state, stateFileName(job.id)), publicJob(job));
  rebuildManifest(D, jobMap);
}

/** @type {Map<string, object>} */
const jobMap = new Map();
let manifestJSON = "{}";

function rebuildManifest(D, jobs) {
  const all = [...jobs.values()].map(publicJob);
  const counts = { queued: 0, rendering: 0, done: 0, failed: 0 };
  for (const j of all) {
    if (j.status === "queued") counts.queued++;
    else if (j.status === "rendering" || j.status === "voicing" || j.status === "voiced") counts.rendering++;
    else if (j.status === "done") counts.done++;
    else if (j.status === "failed") counts.failed++;
  }
  const manifest = {
    updatedAt: now(),
    adapterModule: DISPOSABLE_ADAPTER_MODULE,
    contractVersion: CONTRACT_VERSION,
    counts,
    jobs: all.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0)),
  };
  manifestJSON = JSON.stringify(manifest);
  writeJsonAtomic(path.join(path.dirname(D.state), "manifest.json"), manifest);
}

function failPermanent(D, job, code, message) {
  job.status = "failed";
  job.error = message;
  job.permanentFailureCode = code;
  job.finishedAt = now();
  job.updatedAt = now();
  log(`PERMANENT REJECT ${safeName(job.id)} [${code}]: ${message}`);
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

function runPipeline(specPath, authorizedBy) {
  const sh = path.join(REPO_ROOT, "contentos.sh");
  const env = {
    ...process.env,
    CONTENTOS_FACTORY_AUTHORIZED_BY: authorizedBy,
  };
  const r = spawnSync(sh, ["pipeline", "run", specPath, "--approve-private"], {
    cwd: REPO_ROOT,
    env,
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  const tail = (r.stdout || r.stderr || "").trim().split("\n").slice(-8).join("\n");
  return { ok: r.status === 0, tail, code: r.status };
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
  log(`done: ${job.id} -> ${outDest}`);
}

function processJob(D, jobId, jobDir) {
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
    const job = {
      id: jobId,
      status: "failed",
      dir: jobDir,
      updatedAt: now(),
    };
    failPermanent(D, job, "missing_contract", "CONTRACT.json is required in the job folder");
    return;
  }
  if (!contractStat.isFile() || contractStat.size > MAX_CONTRACT_BYTES) {
    const job = { id: jobId, status: "failed", dir: jobDir, updatedAt: now() };
    failPermanent(D, job, "invalid_contract", `CONTRACT.json must be a plain file under ${MAX_CONTRACT_BYTES / 1024} KiB`);
    return;
  }

  let raw;
  try {
    raw = readJson(contractPath);
  } catch {
    const job = { id: jobId, status: "failed", dir: jobDir, updatedAt: now() };
    failPermanent(D, job, "invalid_contract", "CONTRACT.json is not valid JSON");
    return;
  }

  const adapted = adaptV1Contract(raw, {
    authorizedBy: process.env.CONTENTOS_FACTORY_AUTHORIZED_BY || "factory-mode:production-job",
  });
  if (!adapted.ok) {
    const job = {
      id: jobId,
      contractVersion: CONTRACT_VERSION,
      status: "failed",
      dir: jobDir,
      updatedAt: now(),
    };
    failPermanent(D, job, adapted.code, adapted.message);
    return;
  }

  const { contentosSpec, factorySettings } = adapted;
  if (factorySettings.jobId !== jobId) {
    const job = { id: jobId, contractVersion: CONTRACT_VERSION, status: "failed", dir: jobDir, updatedAt: now() };
    failPermanent(D, job, "job_id_mismatch", `contract jobId "${factorySettings.jobId}" does not match its folder "${jobId}"`);
    return;
  }
  // The derived spec is what the pipeline executes: keep it out of the shared folder so the producer
  // cannot swap it between this write and the pipeline's read.
  const specDir = path.join(REPO_ROOT, "workspace", "factory-specs");
  fs.mkdirSync(specDir, { recursive: true });
  const specPath = path.join(specDir, `${jobId}.yaml`);
  fs.writeFileSync(specPath, contentosSpecToYaml(contentosSpec));

  let job = jobMap.get(jobId) || {
    id: jobId,
    title: contentosSpec.title,
    format: factorySettings.format,
    createdAt: now(),
  };
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

  const pipe = runPipeline(specPath, factorySettings.authorizedBy);
  if (!pipe.ok) {
    job._stderr = pipe.tail;
    failPermanent(D, job, "pipeline_failed", `contentos pipeline failed (exit ${pipe.code}): ${pipe.tail}`);
    return;
  }

  const proj = path.join(REPO_ROOT, "workspace/projects", jobId);
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

function recoverWork(D) {
  for (const id of realDirNames(D.work, warnedEntries)) {
    const dir = path.join(D.work, id);
    const stateFile = path.join(D.state, `${id}.json`);
    try {
      const job = loadStateFile(`${id}.json`, readJson(stateFile));
      if (job) jobMap.set(id, { ...job, dir });
    } catch {
      /* no usable state: re-process below */
    }
    log(`resume in work/: ${safeName(id)}`);
    processJob(D, id, dir);
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
  rebuildManifest(D, jobMap);
}

function tick(D) {
  if (realDirNames(D.work, warnedEntries).length) return;
  const claimed = claimOne(D);
  if (!claimed) return;
  processJob(D, claimed.id, claimed.dir);
}

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

function main() {
  let cfg;
  try {
    cfg = settings();
  } catch (e) {
    console.error(`[factory-worker] ${e.message}`);
    process.exit(2);
  }
  const D = dirs(cfg.root);
  ensureDirs(D);
  log(`exchange root ${cfg.root}; readiness ${cfg.host}:${cfg.port}`);
  bootState(D);
  recoverWork(D);
  startHttp(cfg);

  if (ONCE) {
    tick(D);
    return;
  }
  setInterval(() => tick(D), POLL_MS);
  tick(D);
}

main();
