import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../..");
const worker = path.join(here, "factory_worker.mjs");

function mkTempRoot() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "vsi06-factory-"));
}

test("factory worker permanently rejects 1:1 format with state and failed folder", () => {
  const root = mkTempRoot();
  const id = "cfvg-9000999";
  const jobDir = path.join(root, "queue", id);
  fs.mkdirSync(jobDir, { recursive: true });
  fs.writeFileSync(
    path.join(jobDir, "CONTRACT.json"),
    `${JSON.stringify(
      {
        contractVersion: "video-factory.contract.v1",
        jobId: id,
        title: "Square probe",
        format: "1:1",
        brief: "This should be rejected before render.",
        script: null,
        storyboard: null,
        voice: { enabled: true, id: "af_heart" },
        render: { quality: "draft" },
        durationMs: 5000,
      },
      null,
      2,
    )}\n`,
  );

  const r = spawnSync("node", [worker, "--once", "--port", "0"], {
    cwd: repoRoot,
    env: { ...process.env, VIDEO_FACTORY_ROOT: root, VIDEO_FACTORY_DASHBOARD_PORT: "0" },
    encoding: "utf8",
  });
  assert.equal(r.status, 0, r.stderr || r.stdout);

  const state = JSON.parse(fs.readFileSync(path.join(root, "state", `${id}.json`), "utf8"));
  assert.equal(state.status, "failed");
  assert.equal(state.permanentFailureCode, "unsupported_format");
  assert.match(state.error, /1:1/);
  assert.ok(fs.existsSync(path.join(root, "failed", id)));
  assert.ok(!fs.existsSync(path.join(root, "output", `${id}.mp4`)));

  fs.rmSync(root, { recursive: true, force: true });
});

test("factory worker permanently rejects unknown voice id with state and failed folder", () => {
  const root = mkTempRoot();
  const id = "cfvg-9000998";
  const jobDir = path.join(root, "queue", id);
  fs.mkdirSync(jobDir, { recursive: true });
  fs.writeFileSync(
    path.join(jobDir, "CONTRACT.json"),
    `${JSON.stringify(
      {
        contractVersion: "video-factory.contract.v1",
        jobId: id,
        title: "Unknown voice probe",
        format: "9:16",
        brief: "This should be rejected before render.",
        script: null,
        storyboard: null,
        voice: { enabled: true, id: "not_a_real_voice_id" },
        render: { quality: "draft" },
        durationMs: 5000,
      },
      null,
      2,
    )}\n`,
  );

  const r = spawnSync("node", [worker, "--once", "--port", "0"], {
    cwd: repoRoot,
    env: { ...process.env, VIDEO_FACTORY_ROOT: root, VIDEO_FACTORY_DASHBOARD_PORT: "0" },
    encoding: "utf8",
  });
  assert.equal(r.status, 0, r.stderr || r.stdout);

  const state = JSON.parse(fs.readFileSync(path.join(root, "state", `${id}.json`), "utf8"));
  assert.equal(state.status, "failed");
  assert.equal(state.permanentFailureCode, "unknown_voice_id");
  assert.match(state.error, /not_a_real_voice_id/);
  assert.ok(fs.existsSync(path.join(root, "failed", id)));
  assert.ok(!fs.existsSync(path.join(root, "output", `${id}.mp4`)));

  fs.rmSync(root, { recursive: true, force: true });
});

// ---- the exchange root is hostile input (Round 4, Q19a) ----

function runWorker(root, args = [], env = {}) {
  return spawnSync("node", [worker, "--once", "--port", "0", ...args], {
    cwd: repoRoot,
    env: { ...process.env, VIDEO_FACTORY_ROOT: root, ...env },
    encoding: "utf8",
  });
}

function contract(id, over = {}) {
  return {
    contractVersion: "video-factory.contract.v1",
    jobId: id,
    title: "Probe",
    format: "9:16",
    brief: "Rejected before any render.",
    script: null,
    storyboard: null,
    voice: { enabled: true, id: "af_heart" },
    render: { quality: "draft" },
    durationMs: 5000,
    ...over,
  };
}

function queueJob(root, folder, body) {
  const dir = path.join(root, "queue", folder);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "CONTRACT.json"), JSON.stringify(body));
  return dir;
}

const readState = (root, id) => JSON.parse(fs.readFileSync(path.join(root, "state", `${id}.json`), "utf8"));
const cleanup = (...roots) => roots.forEach((r) => fs.rmSync(r, { recursive: true, force: true }));

test("a folder that is not a cfvg id is rejected under a name that is safe to write", () => {
  const root = mkTempRoot();
  queueJob(root, "bad name!", contract("cfvg-9000990"));
  const r = runWorker(root);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(readState(root, "bad_name_").permanentFailureCode, "invalid_job_id");
  assert.ok(fs.existsSync(path.join(root, "failed", "bad_name_")));
  cleanup(root);
});

test("a contract whose jobId differs from its folder is rejected before any render", () => {
  const root = mkTempRoot();
  queueJob(root, "cfvg-9000997", contract("cfvg-9000996"));
  const r = runWorker(root);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(readState(root, "cfvg-9000997").permanentFailureCode, "job_id_mismatch");
  assert.ok(!fs.existsSync(path.join(repoRoot, "workspace/factory-specs/cfvg-9000997.yaml")), "no spec was written");
  cleanup(root);
});

test("a symlink dropped into the queue is never claimed", () => {
  const root = mkTempRoot();
  const elsewhere = mkTempRoot();
  fs.writeFileSync(path.join(elsewhere, "CONTRACT.json"), JSON.stringify(contract("cfvg-9000995")));
  fs.mkdirSync(path.join(root, "queue"), { recursive: true });
  fs.symlinkSync(elsewhere, path.join(root, "queue", "cfvg-9000995"));
  const r = runWorker(root);
  assert.equal(r.status, 0, r.stderr);
  assert.ok(!fs.existsSync(path.join(root, "state", "cfvg-9000995.json")));
  assert.ok(fs.lstatSync(path.join(root, "queue", "cfvg-9000995")).isSymbolicLink());
  assert.match(r.stderr, /ignoring queue\/cfvg-9000995: not a plain directory/);
  cleanup(root, elsewhere);
});

test("a CONTRACT.json that is a symlink, or too big, is rejected unread", () => {
  const root = mkTempRoot();
  const elsewhere = mkTempRoot();
  const target = path.join(elsewhere, "real.json");
  fs.writeFileSync(target, JSON.stringify(contract("cfvg-9000994")));
  const linked = queueJob(root, "cfvg-9000994", {});
  fs.rmSync(path.join(linked, "CONTRACT.json"));
  fs.symlinkSync(target, path.join(linked, "CONTRACT.json"));
  assert.equal(runWorker(root).status, 0);
  const s1 = readState(root, "cfvg-9000994");
  assert.equal(s1.permanentFailureCode, "invalid_contract");
  assert.match(s1.error, /plain file/);

  queueJob(root, "cfvg-9000993", contract("cfvg-9000993", { brief: "x".repeat(300 * 1024) }));
  assert.equal(runWorker(root).status, 0);
  assert.equal(readState(root, "cfvg-9000993").permanentFailureCode, "invalid_contract");
  cleanup(root, elsewhere);
});

test("state and manifest carry no host paths", () => {
  const root = mkTempRoot();
  queueJob(root, "cfvg-9000992", contract("cfvg-9000992", { format: "1:1" }));
  assert.equal(runWorker(root).status, 0);
  for (const f of ["state/cfvg-9000992.json", "manifest.json"]) {
    const text = fs.readFileSync(path.join(root, f), "utf8");
    assert.ok(!text.includes(root), `${f} leaks the exchange root path`);
    assert.ok(!/"(dir|outputPath)"/.test(text), `${f} carries a host path field`);
  }
  cleanup(root);
});

test("readiness refuses to listen on every interface, before touching anything", () => {
  const root = mkTempRoot();
  for (const host of ["0.0.0.0", "::"]) {
    const r = runWorker(root, ["--host", host]);
    assert.equal(r.status, 2, host);
    assert.match(r.stderr, /every interface/);
  }
  assert.deepEqual(fs.readdirSync(root), []);
  cleanup(root);
});

test("a readiness address that does not exist yet does not stop the worker", () => {
  const root = mkTempRoot();
  queueJob(root, "cfvg-9000991", contract("cfvg-9000991", { format: "1:1" }));
  const r = runWorker(root, ["--host", "192.0.2.1"]); // TEST-NET-1, never assigned
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stderr, /cannot listen on 192\.0\.2\.1/);
  assert.equal(readState(root, "cfvg-9000991").status, "failed");
  cleanup(root);
});
