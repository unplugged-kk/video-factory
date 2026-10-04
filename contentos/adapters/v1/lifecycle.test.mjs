import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  acquireLock,
  killProcessGroup,
  numericJobOrder,
  processAlive,
  readHeartbeat,
  removeHeartbeat,
  writeHeartbeat,
} from "./lifecycle.mjs";

const made = [];
const tmp = () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vsi-life-"));
  made.push(dir);
  return dir;
};
test.after(() => made.forEach((dir) => fs.rmSync(dir, { recursive: true, force: true })));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

test("a heartbeat file round-trips, and only its owner removes it", () => {
  const file = path.join(tmp(), "hb.json");
  assert.equal(readHeartbeat(file), null);
  writeHeartbeat(file, { pid: 11, heartbeatAt: 5, activeJob: null });
  assert.deepEqual(readHeartbeat(file), { pid: 11, heartbeatAt: 5, activeJob: null });
  removeHeartbeat(file, 12);
  assert.ok(fs.existsSync(file), "another pid must not remove it");
  removeHeartbeat(file, 11);
  assert.ok(!fs.existsSync(file));
  fs.writeFileSync(file, "{not json");
  assert.equal(readHeartbeat(file), null);
  fs.writeFileSync(file, JSON.stringify({ heartbeatAt: 1 }));
  assert.equal(readHeartbeat(file), null, "a heartbeat without a pid is not a heartbeat");
});

test("the lock: free, our own, a live worker, a silent worker, a dead one, and a reused pid", () => {
  const file = path.join(tmp(), "hb.json");
  const worker = () => "node /x/contentos/adapters/v1/factory_worker.mjs --host 100.1.1.1";
  const base = { file, pid: 100, now: 1_000_000, staleMs: 60_000 };

  assert.deepEqual(acquireLock({ ...base, alive: () => true, command: worker }), { ok: true, previous: null });

  writeHeartbeat(file, { pid: 100, heartbeatAt: 1 });
  assert.deepEqual(acquireLock({ ...base, alive: () => true, command: worker }), { ok: true, previous: null }, "our own pid");

  writeHeartbeat(file, { pid: 4242, heartbeatAt: 999_000 });
  const live = acquireLock({ ...base, alive: () => true, command: worker });
  assert.equal(live.ok, false);
  assert.equal(live.pid, 4242);
  assert.match(live.message, /another factory worker is running \(pid 4242\)/);

  writeHeartbeat(file, { pid: 4242, heartbeatAt: 880_000 });
  const silent = acquireLock({ ...base, alive: () => true, command: worker });
  assert.equal(silent.ok, false);
  assert.match(silent.message, /alive but silent for 120 s/);

  const dead = acquireLock({ ...base, alive: () => false, command: worker });
  assert.equal(dead.ok, true);
  assert.equal(dead.previous.pid, 4242);

  const reused = acquireLock({ ...base, alive: () => true, command: () => "/usr/bin/some-editor" });
  assert.equal(reused.ok, true, "a live pid that is not a factory worker is a recycled pid");
  assert.equal(reused.previous.pid, 4242);
});

test("jobs sort by number, not by text", () => {
  const names = ["cfvg-10", "cfvg-9", "zzz", "cfvg-2", "cfvg-100", "aaa"];
  assert.deepEqual(names.sort(numericJobOrder), ["cfvg-2", "cfvg-9", "cfvg-10", "cfvg-100", "aaa", "zzz"]);
});

function spawnGroup(script, dir) {
  const pidfile = path.join(dir, "grandchild.pid");
  const child = spawn("sh", ["-c", script.replace("PIDFILE", pidfile)], { detached: true, stdio: "ignore" });
  const exited = once(child, "exit"); // listen from the start: the exit can land while we are still killing
  return { child, pidfile, exited };
}

async function grandchildPid(pidfile) {
  for (let i = 0; i < 100 && !fs.existsSync(pidfile); i++) await sleep(20);
  return Number(fs.readFileSync(pidfile, "utf8"));
}

test("killProcessGroup ends the leader and everything it started", async () => {
  const dir = tmp();
  const { child, pidfile, exited } = spawnGroup("sleep 30 & echo $! > PIDFILE; wait", dir);
  const grand = await grandchildPid(pidfile);
  assert.ok(processAlive(grand) && processAlive(child.pid));
  assert.equal(await killProcessGroup(child.pid, { graceMs: 2000 }), true);
  await exited;
  assert.ok(!processAlive(grand), "the process under the leader survived");
  assert.ok(!processAlive(child.pid));
  assert.equal(await killProcessGroup(child.pid), false, "a group that is gone reports false");
});

test("a group that ignores SIGTERM is killed once the grace period is over", async () => {
  const dir = tmp();
  const { child, pidfile, exited } = spawnGroup('trap "" TERM; sleep 30 & echo $! > PIDFILE; wait', dir);
  const grand = await grandchildPid(pidfile);
  const started = Date.now();
  assert.equal(await killProcessGroup(child.pid, { graceMs: 300 }), true);
  await exited;
  assert.ok(Date.now() - started >= 300, "it should have waited out the grace period first");
  assert.ok(!processAlive(grand) && !processAlive(child.pid));
});
