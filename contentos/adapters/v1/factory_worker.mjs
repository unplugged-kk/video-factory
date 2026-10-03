#!/usr/bin/env node
/**
 * ContentForge v1 filesystem transport worker.
 * Watches VIDEO_FACTORY_ROOT/queue, adapts CONTRACT.json via contract_adapter.mjs,
 * runs contentos pipeline in factory mode (--approve-private), writes state/output atomically.
 * Delete with contentos/adapters/v1/ when contract v2 ships.
 */
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { adaptV1Contract, CONTRACT_VERSION, DISPOSABLE_ADAPTER_MODULE } from "./contract_adapter.mjs";

const ADAPTER_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(ADAPTER_DIR, "../../..");
const POLL_MS = Number(process.env.VIDEO_FACTORY_POLL_MS || 2000);
const PORT = (() => {
  const i = process.argv.indexOf("--port");
  if (i >= 0 && process.argv[i + 1]) return Number(process.argv[i + 1]) || 4300;
  return Number(process.env.VIDEO_FACTORY_DASHBOARD_PORT || 4300);
})();
const ONCE = process.argv.includes("--once");

const now = () => Date.now();
const log = (m) => console.error(`[factory-worker ${new Date().toISOString()}] ${m}`);

function factoryRoot() {
  const raw = process.env.VIDEO_FACTORY_ROOT?.trim();
  return raw ? path.resolve(raw) : REPO_ROOT;
}

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
  const { _stderr, ...clean } = job;
  writeJsonAtomic(path.join(D.state, `${job.id}.json`), clean);
  rebuildManifest(D, jobMap);
}

/** @type {Map<string, object>} */
const jobMap = new Map();
let manifestJSON = "{}";

function rebuildManifest(D, jobs) {
  const all = [...jobs.values()].map(({ _stderr, ...j }) => j);
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
  fs.writeFileSync(path.join(factoryRoot(), "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
}

function failPermanent(D, job, code, message) {
  job.status = "failed";
  job.error = message;
  job.permanentFailureCode = code;
  job.finishedAt = now();
  job.updatedAt = now();
  log(`PERMANENT REJECT ${job.id} [${code}]: ${message}`);
  try {
    if (job.dir && fs.existsSync(job.dir) && !job.dir.startsWith(D.failed)) {
      job.dir = moveDir(job.dir, path.join(D.failed, job.id));
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
  writeJsonAtomic(path.join(job.dir, "hyperframes.json"), hyper);
  const outDest = path.join(D.output, `${job.id}.mp4`);
  atomicCopyOutput(mp4Src, outDest);
  job.status = "done";
  job.error = null;
  job.outputPath = outDest;
  job.finishedAt = now();
  job.updatedAt = now();
  job.hyperframes = hyper;
  job.dir = moveDir(job.dir, path.join(D.done, job.id));
  jobMap.set(job.id, job);
  persistState(D, job);
  log(`done: ${job.id} -> ${outDest}`);
}

function processJob(D, jobId, jobDir) {
  const contractPath = path.join(jobDir, "CONTRACT.json");
  if (!fs.existsSync(contractPath)) {
    const job = {
      id: jobId,
      status: "failed",
      dir: jobDir,
      updatedAt: now(),
    };
    failPermanent(D, job, "missing_contract", "CONTRACT.json is required in the job folder");
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
  const specPath = path.join(jobDir, "contentos-spec.yaml");
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
  finishSuccess(D, job, mp4, hyper);
}

function claimOne(D) {
  let names;
  try {
    names = fs
      .readdirSync(D.queue)
      .filter((n) => fs.statSync(path.join(D.queue, n)).isDirectory())
      .sort();
  } catch {
    return null;
  }
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
  let names;
  try {
    names = fs.readdirSync(D.work).filter((n) => fs.statSync(path.join(D.work, n)).isDirectory());
  } catch {
    return;
  }
  for (const id of names) {
    const dir = path.join(D.work, id);
    const stateFile = path.join(D.state, `${id}.json`);
    if (fs.existsSync(stateFile)) {
      try {
        const job = readJson(stateFile);
        jobMap.set(id, { ...job, dir });
      } catch {
        /* re-process below */
      }
    }
    log(`resume in work/: ${id}`);
    processJob(D, id, dir);
  }
}

function bootState(D) {
  try {
    for (const f of fs.readdirSync(D.state)) {
      if (!f.endsWith(".json")) continue;
      try {
        const job = readJson(path.join(D.state, f));
        jobMap.set(job.id, job);
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
  const inWork = fs.existsSync(D.work) && fs.readdirSync(D.work).some((n) => {
    try {
      return fs.statSync(path.join(D.work, n)).isDirectory();
    } catch {
      return false;
    }
  });
  if (inWork) return;
  const claimed = claimOne(D);
  if (!claimed) return;
  processJob(D, claimed.id, claimed.dir);
}

function startHttp(root) {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url || "/", `http://127.0.0.1:${PORT}`);
    if (url.pathname === "/manifest.json") {
      res.writeHead(200, { "content-type": "application/json", "cache-control": "no-store" });
      res.end(manifestJSON);
      return;
    }
    res.writeHead(404);
    res.end("not found");
  });
  server.listen(PORT, () => log(`manifest http://127.0.0.1:${PORT}/manifest.json (root=${root})`));
  if (ONCE) server.unref();
}

function main() {
  const root = factoryRoot();
  const D = dirs(root);
  ensureDirs(D);
  bootState(D);
  recoverWork(D);
  startHttp(root);

  if (ONCE) {
    tick(D);
    return;
  }
  setInterval(() => tick(D), POLL_MS);
  tick(D);
}

main();
