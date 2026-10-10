/**
 * The worker's lifecycle, end to end: the real worker against a fake `contentos` launcher in throwaway folders.
 * The fake stands in for `contentos production run`: it records its pid, can sleep, and ends in a chosen way.
 */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { processAlive } from "./lifecycle.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const worker = path.join(here, "factory_worker.mjs");
const repoRoot = path.resolve(here, "../../..");
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function until(fn, { ms = 20_000, every = 25, what = "the condition" } = {}) {
  const end = Date.now() + ms;
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() > end) throw new Error(`timed out waiting for ${what}`);
    await sleep(every);
  }
}

const FAKE = `#!/bin/bash
# fake \`contentos production run <spec> --approve-private\`
spec="$3"; id=$(basename "$spec" .yaml)
echo $$ > "$FAKE_STAMPS/child-$id.pid"
echo started >> "$FAKE_STAMPS/runs-$id.log"
[ -n "$FAKE_SLEEP" ] && sleep "$FAKE_SLEEP"
case "\${FAKE_MODE:-ok}" in
  ok)
    mkdir -p "$FAKE_WS/jobs/2026/10/$id/project"
    printf mp4 > "$FAKE_WS/jobs/2026/10/$id/video.mp4"
    printf '{"width":1080,"height":1920,"fps":30,"duration":3.4}' > "$FAKE_WS/jobs/2026/10/$id/project/hyperframes.json"
    echo '{"ok":true,"failureClass":null,"stage":null,"error":null,"attempts":1,"elapsedS":0.1}' ;;
  transient) echo '{"ok":false,"failureClass":"transient","stage":"render","error":"render failed: chrome died (after 3 attempts)","attempts":3,"elapsedS":65}'; exit 1 ;;
  output) echo '{"ok":false,"failureClass":"output","stage":"qa","error":"qa failed: QA failed: [frozen_frames]","attempts":1,"elapsedS":2}'; exit 1 ;;
  blocked) echo '{"ok":false,"failureClass":"blocked","stage":"voice","error":"voice blocked: no healthy TTS provider","attempts":1,"elapsedS":0}'; exit 1 ;;
  leak) echo "{\\"ok\\":false,\\"failureClass\\":\\"output\\",\\"stage\\":\\"render\\",\\"error\\":\\"render failed: tool -o $FAKE_WS/jobs/2026/10/$id/video.mp4 -> $HOME/.secret\\",\\"attempts\\":1,\\"elapsedS\\":0}"; exit 1 ;;
  crash) kill -9 $$ ;;
esac
`;

function makeFactory() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vsi-p3-"));
  const f = {
    dir,
    root: path.join(dir, "exchange"),
    ws: path.join(dir, "ws"),
    stamps: path.join(dir, "stamps"),
    launcher: path.join(dir, "contentos-fake.sh"),
    children: [],
  };
  for (const d of [f.root, f.ws, f.stamps]) fs.mkdirSync(d, { recursive: true });
  fs.writeFileSync(f.launcher, FAKE, { mode: 0o755 });
  f.env = (extra = {}) => ({
    ...process.env,
    VIDEO_FACTORY_ROOT: f.root,
    VIDEO_FACTORY_WORKSPACE: f.ws,
    VIDEO_FACTORY_CONTENTOS: f.launcher,
    FAKE_STAMPS: f.stamps,
    FAKE_WS: f.ws,
    VIDEO_FACTORY_POLL_MS: "50",
    VIDEO_FACTORY_HEARTBEAT_MS: "100",
    ...extra,
  });
  f.contract = (id, over = {}) => ({
    contractVersion: "video-factory.contract.v1",
    jobId: id,
    title: "Probe",
    format: "9:16",
    brief: "A brief the fake pipeline never reads.",
    script: null,
    storyboard: null,
    voice: { enabled: true, id: "af_heart" },
    render: { quality: "draft" },
    durationMs: 5000,
    ...over,
  });
  f.plant = (folder, id, over) => {
    const d = path.join(f.root, folder, id);
    fs.mkdirSync(d, { recursive: true });
    fs.writeFileSync(path.join(d, "CONTRACT.json"), JSON.stringify(f.contract(id, over)));
    return d;
  };
  f.queue = (id, over) => f.plant("queue", id, over);
  f.state = (id) => JSON.parse(fs.readFileSync(path.join(f.root, "state", `${id}.json`), "utf8"));
  f.hasStatus = (id, ...statuses) => {
    try {
      return statuses.includes(f.state(id).status);
    } catch {
      return false;
    }
  };
  f.heartbeatFile = path.join(f.ws, ".factory_worker.heartbeat");
  f.beat = () => JSON.parse(fs.readFileSync(f.heartbeatFile, "utf8"));
  f.pidFile = (id) => path.join(f.stamps, `child-${id}.pid`);
  f.started = (id) => fs.existsSync(f.pidFile(id));
  f.childPid = (id) => Number(fs.readFileSync(f.pidFile(id), "utf8"));
  f.runs = (id) => {
    try {
      return fs.readFileSync(path.join(f.stamps, `runs-${id}.log`), "utf8").trim().split("\n").length;
    } catch {
      return 0;
    }
  };
  f.cleanup = () => {
    // Stop everything that could still write into the folder, then remove it; a cleanup problem must not mask a result.
    for (const child of f.children) child.kill("SIGKILL");
    for (const name of fs.readdirSync(f.stamps).filter((n) => n.startsWith("child-"))) {
      const pid = Number(fs.readFileSync(path.join(f.stamps, name), "utf8"));
      for (const target of [-pid, pid]) {
        try {
          process.kill(target, "SIGKILL");
        } catch {
          /* already gone */
        }
      }
    }
    try {
      fs.rmSync(dir, { recursive: true, force: true, maxRetries: 20, retryDelay: 50 });
    } catch (e) {
      console.error(`cleanup of ${dir} failed: ${e.message}`);
    }
  };
  return f;
}

function startWorker(f, { once = true, env = {}, args = [] } = {}) {
  const child = spawn("node", [worker, ...(once ? ["--once"] : []), "--port", "0", ...args], {
    cwd: repoRoot,
    env: f.env(env),
    stdio: ["ignore", "pipe", "pipe"],
  });
  f.children.push(child);
  let log = "";
  child.stdout.on("data", (d) => (log += d));
  child.stderr.on("data", (d) => (log += d));
  const exited = new Promise((resolve) => child.on("exit", (code, signal) => resolve({ code, signal })));
  return {
    child,
    exited,
    log: () => log,
    port: async () => Number((await until(() => /readiness listening on [\d.]+:(\d+)/.exec(log), { what: "the readiness port" }))[1]),
    stop: async () => {
      child.kill("SIGTERM");
      return exited;
    },
  };
}

function getJson(port, route) {
  return new Promise((resolve, reject) => {
    const req = http.get({ host: "127.0.0.1", port, path: route, timeout: 1500 }, (res) => {
      let body = "";
      res.on("data", (d) => (body += d));
      res.on("end", () => resolve(JSON.parse(body)));
    });
    req.on("timeout", () => req.destroy(new Error("readiness did not answer within 1.5 s")));
    req.on("error", reject);
  });
}

test("readiness answers and the heartbeat moves while a job renders", async () => {
  const f = makeFactory();
  try {
    f.queue("cfvg-501");
    const w = startWorker(f, { env: { FAKE_SLEEP: "2" } });
    await until(() => f.started("cfvg-501"), { what: "the job to start" });
    const manifest = await getJson(await w.port(), "/manifest.json"); // a worker blocked on the render never answers
    assert.equal(manifest.worker.pid, w.child.pid);
    assert.equal(manifest.worker.activeJob, "cfvg-501");
    assert.equal(manifest.jobs.find((j) => j.id === "cfvg-501").status, "rendering");
    const first = f.beat();
    await sleep(400);
    const second = f.beat();
    assert.ok(second.heartbeatAt > first.heartbeatAt, "the heartbeat must keep moving during the render");
    assert.equal(second.activeJob.childPid, f.childPid("cfvg-501"));
    const { code } = await w.exited;
    assert.equal(code, 0, w.log());
    assert.equal(f.state("cfvg-501").status, "done");
    assert.ok(fs.existsSync(path.join(f.root, "output", "cfvg-501.mp4")));
    assert.ok(!fs.existsSync(f.heartbeatFile), "a clean stop removes the heartbeat");
  } finally {
    f.cleanup();
  }
});

test("a second worker refuses to start while one is running", async () => {
  const f = makeFactory();
  let a;
  try {
    f.queue("cfvg-502");
    a = startWorker(f, { once: false, env: { FAKE_SLEEP: "30" } });
    await until(() => f.started("cfvg-502"), { what: "the job to start" });
    const b = startWorker(f, { once: false });
    const { code } = await b.exited;
    assert.equal(code, 3, b.log());
    assert.match(b.log(), /another factory worker is running \(pid \d+\)/);
    assert.ok(processAlive(a.child.pid));
    assert.equal(f.beat().pid, a.child.pid, "the first worker still owns the heartbeat");
  } finally {
    a?.child.kill("SIGKILL");
    await a?.exited;
    f.cleanup();
  }
});

test("after a kill -9 the next worker stops the orphaned pipeline and resumes the job", async () => {
  const f = makeFactory();
  try {
    f.queue("cfvg-503");
    const a = startWorker(f, { env: { FAKE_SLEEP: "30" } });
    await until(() => f.started("cfvg-503"), { what: "the job to start" });
    const orphan = f.childPid("cfvg-503");
    a.child.kill("SIGKILL");
    await a.exited;
    assert.ok(processAlive(orphan), "the pipeline outlives its worker");
    assert.ok(fs.existsSync(f.heartbeatFile), "a crash leaves the heartbeat for the next start to read");
    assert.ok(fs.existsSync(path.join(f.root, "work", "cfvg-503")));

    const b = startWorker(f); // no FAKE_SLEEP: the retry is quick
    const { code } = await b.exited;
    assert.equal(code, 0, b.log());
    assert.match(b.log(), /stopped an orphaned pipeline/);
    await until(() => !processAlive(orphan), { what: "the orphan to be gone" });
    const state = f.state("cfvg-503");
    assert.equal(state.status, "done");
    assert.equal(state.reclaimCount, 1);
    assert.ok(fs.existsSync(path.join(f.root, "output", "cfvg-503.mp4")));
    assert.equal(f.runs("cfvg-503"), 2, "the job ran twice: once killed, once resumed");
  } finally {
    f.cleanup();
  }
});

test("SIGTERM stops the worker and its pipeline, and leaves the job to resume", async () => {
  const f = makeFactory();
  try {
    f.queue("cfvg-504");
    const a = startWorker(f, { once: false, env: { FAKE_SLEEP: "30" } });
    await until(() => f.started("cfvg-504"), { what: "the job to start" });
    const kid = f.childPid("cfvg-504");
    const { code } = await a.stop();
    assert.equal(code, 0, a.log());
    await until(() => !processAlive(kid), { what: "the pipeline to be stopped with its worker" });
    assert.ok(!fs.existsSync(f.heartbeatFile));
    assert.ok(fs.existsSync(path.join(f.root, "work", "cfvg-504")), "the job stays in work/");
    assert.equal(f.state("cfvg-504").status, "rendering", "a stop is not a failure");

    const b = startWorker(f);
    assert.equal((await b.exited).code, 0, b.log());
    assert.equal(f.state("cfvg-504").status, "done");
  } finally {
    f.cleanup();
  }
});

for (const [mode, code, failureClass, stage] of [
  ["transient", "transient_exhausted", "transient", "render"],
  ["output", "pipeline_failed", "output", "qa"],
  ["blocked", "pipeline_blocked", "blocked", "voice"],
]) {
  test(`a ${mode} result from the core is reported as ${code}`, async () => {
    const f = makeFactory();
    try {
      f.queue("cfvg-505");
      const w = startWorker(f, { env: { FAKE_MODE: mode } });
      assert.equal((await w.exited).code, 0, w.log());
      const state = f.state("cfvg-505");
      assert.equal(state.status, "failed");
      assert.equal(state.permanentFailureCode, code);
      assert.equal(state.failureClass, failureClass);
      assert.equal(state.failedStage, stage);
      assert.match(state.error, new RegExp(stage));
      assert.ok(fs.existsSync(path.join(f.root, "failed", "cfvg-505")));
      assert.ok(!fs.existsSync(path.join(f.root, "output", "cfvg-505.mp4")));
    } finally {
      f.cleanup();
    }
  });
}

test("a core that dies without a result is reported as a crash", async () => {
  const f = makeFactory();
  try {
    f.queue("cfvg-506");
    const w = startWorker(f, { env: { FAKE_MODE: "crash" } });
    assert.equal((await w.exited).code, 0, w.log());
    const state = f.state("cfvg-506");
    assert.equal(state.permanentFailureCode, "pipeline_crashed");
    assert.match(state.error, /SIGKILL/);
  } finally {
    f.cleanup();
  }
});

test("a core that hangs is stopped at the job limit", async () => {
  const f = makeFactory();
  try {
    f.queue("cfvg-507");
    const w = startWorker(f, { env: { FAKE_SLEEP: "30", VIDEO_FACTORY_JOB_TIMEOUT_MS: "600" } });
    assert.equal((await w.exited).code, 0, w.log());
    const state = f.state("cfvg-507");
    assert.equal(state.permanentFailureCode, "pipeline_timeout");
    assert.match(state.error, /exceeded/);
    await until(() => !processAlive(f.childPid("cfvg-507")), { what: "the hung pipeline to be stopped" });
  } finally {
    f.cleanup();
  }
});

test("host paths in a tool's error never reach the shared folder", async () => {
  const f = makeFactory();
  try {
    f.queue("cfvg-508");
    const w = startWorker(f, { env: { FAKE_MODE: "leak" } });
    assert.equal((await w.exited).code, 0, w.log());
    const text = fs.readFileSync(path.join(f.root, "state", "cfvg-508.json"), "utf8") + fs.readFileSync(path.join(f.root, "manifest.json"), "utf8");
    assert.ok(!text.includes(f.ws) && !text.includes(fs.realpathSync(f.ws)), "the workspace path leaked");
    assert.ok(!text.includes(os.homedir()), "the home folder leaked");
    assert.match(f.state("cfvg-508").error, /<workspace>\/jobs\/2026\/10\/cfvg-508\/video\.mp4 -> ~\/\.secret/);
  } finally {
    f.cleanup();
  }
});

test("jobs run oldest first by number", async () => {
  const f = makeFactory();
  let w;
  try {
    for (const n of [10, 9, 2]) f.queue(`cfvg-${n}`);
    w = startWorker(f, { once: false });
    await until(() => [10, 9, 2].every((n) => f.hasStatus(`cfvg-${n}`, "done")), { what: "all three jobs" });
    const order = [2, 9, 10].map((n) => f.state(`cfvg-${n}`).finishedAt);
    assert.deepEqual([...order].sort((a, b) => a - b), order, "cfvg-10 must not jump ahead of cfvg-9");
  } finally {
    await w?.stop();
    f.cleanup();
  }
});

test("a claim nobody is working on goes back to the queue and runs", async () => {
  const f = makeFactory();
  let w;
  try {
    w = startWorker(f, { once: false, env: { VIDEO_FACTORY_STALE_MS: "400" } });
    await w.port();
    f.plant("work", "cfvg-70"); // dropped in after start-up, with nobody running it
    await until(() => f.hasStatus("cfvg-70", "done"), { what: "the stale claim to be reclaimed and finished" });
    assert.equal(f.state("cfvg-70").reclaimCount, 1);
    assert.match(w.log(), /reclaim/i);
  } finally {
    await w?.stop();
    f.cleanup();
  }
});

test("a job taken over too many times is failed instead of looped", async () => {
  const f = makeFactory();
  try {
    f.plant("work", "cfvg-71");
    fs.mkdirSync(path.join(f.root, "state"), { recursive: true });
    fs.writeFileSync(path.join(f.root, "state", "cfvg-71.json"), JSON.stringify({ id: "cfvg-71", status: "rendering", reclaimCount: 3, updatedAt: Date.now() }));
    const w = startWorker(f);
    assert.equal((await w.exited).code, 0, w.log());
    const state = f.state("cfvg-71");
    assert.equal(state.status, "failed");
    assert.equal(state.permanentFailureCode, "reclaim_limit");
    assert.equal(f.runs("cfvg-71"), 0, "a poisoned job must not start another pipeline");
  } finally {
    f.cleanup();
  }
});
