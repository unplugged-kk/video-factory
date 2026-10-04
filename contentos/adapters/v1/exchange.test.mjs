import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  assertExchangeRoot,
  assertReadinessHost,
  listenWithRetry,
  loadStateFile,
  parsePort,
  publicJob,
  safeName,
  stateFileName,
} from "./exchange.mjs";

test("exchange root must not be, or sit above, the factory repo", () => {
  const repo = path.join(os.tmpdir(), "vsi-exchange-test", "video-factory");
  assert.throws(() => assertExchangeRoot(repo, repo), /contains the factory repo/);
  assert.throws(() => assertExchangeRoot(path.dirname(repo), repo), /contains the factory repo/);
  assert.doesNotThrow(() => assertExchangeRoot(path.join(os.tmpdir(), "vsi-exchange-test", "exchange"), repo));
  // a sibling that merely shares the repo's name as a prefix is not the repo
  assert.doesNotThrow(() => assertExchangeRoot(`${repo}-data`, repo));
});

test("readiness never listens on every interface", () => {
  for (const h of ["", "  ", "0.0.0.0", "::", "[::]", "*"]) {
    assert.throws(() => assertReadinessHost(h), /every interface/, JSON.stringify(h));
  }
  assert.equal(assertReadinessHost("100.68.59.17"), "100.68.59.17");
  assert.equal(assertReadinessHost("127.0.0.1"), "127.0.0.1");
});

test("port 0 means any free port, junk is refused", () => {
  assert.equal(parsePort("0", 4300), 0);
  assert.equal(parsePort(undefined, 4300), 4300);
  assert.equal(parsePort("", 4300), 4300);
  assert.equal(parsePort("4301", 1), 4301);
  for (const bad of ["abc", "-1", "70000", "1.5"]) assert.throws(() => parsePort(bad, 4300), /invalid port/, bad);
});

test("what the control plane can read carries no host paths", () => {
  const j = publicJob({
    id: "cfvg-1",
    status: "done",
    dir: "/Users/x/exchange/done/cfvg-1",
    outputPath: "/Users/x/exchange/output/cfvg-1.mp4",
    _stderr: "boom",
    hyperframes: { width: 1080 },
  });
  assert.deepEqual(j, { id: "cfvg-1", status: "done", hyperframes: { width: 1080 } });
});

test("a producer-written id can never steer a write out of state/", () => {
  const stateDir = path.join(os.tmpdir(), "vsi-exchange-test", "state");
  for (const hostile of ["../../.claude/settings", "/etc/passwd", "..", ".", "a/../../b", "x\ny", ""]) {
    const name = stateFileName(hostile);
    assert.equal(path.basename(name), name, hostile);
    assert.ok(!name.startsWith("."), name);
    const rel = path.relative(stateDir, path.join(stateDir, name));
    assert.ok(!rel.startsWith("..") && !path.isAbsolute(rel), `${hostile} -> ${name}`);
  }
  assert.equal(safeName("x".repeat(200)).length, 64);
});

test("state files: the file name decides the job id, the content cannot redirect writes", () => {
  const j = loadStateFile("cfvg-12.json", { id: "../../escape", dir: "/x", outputPath: "/y", status: "failed" });
  assert.deepEqual(j, { id: "cfvg-12", status: "failed" });
  assert.equal(loadStateFile("manifest.json", { id: "cfvg-1" }), null);
  assert.equal(loadStateFile("../cfvg-1.json", {}), null);
  assert.equal(loadStateFile("cfvg-01.json", {}), null);
  assert.equal(loadStateFile("cfvg-1.json", [1]), null);
  assert.equal(loadStateFile("cfvg-1.json", null), null);
});

test("listenWithRetry keeps trying until the address exists", async () => {
  const fake = new EventEmitter();
  let calls = 0;
  fake.listening = false;
  fake.address = () => ({ address: "100.64.0.1", port: 4300 });
  fake.close = (cb) => {
    fake.listening = false;
    cb?.();
  };
  fake.listen = () => {
    calls++;
    setImmediate(() => {
      if (calls < 3) {
        fake.emit("error", Object.assign(new Error("address not available"), { code: "EADDRNOTAVAIL" }));
      } else {
        fake.listening = true;
        fake.emit("listening");
      }
    });
    return fake;
  };
  const logs = [];
  const handle = listenWithRetry(fake, { port: 4300, host: "100.64.0.1", log: (m) => logs.push(m), delays: [5, 5] });
  await new Promise((resolve) => fake.once("listening", resolve));
  assert.equal(calls, 3);
  assert.equal(logs.filter((l) => /cannot listen on 100\.64\.0\.1:4300 \(EADDRNOTAVAIL\)/.test(l)).length, 2, logs.join("|"));
  assert.match(logs.at(-1), /listening on 100\.64\.0\.1:4300/);
  handle.stop();
});

test("listenWithRetry binds only the host it was given", async () => {
  const server = http.createServer();
  const handle = listenWithRetry(server, { port: 0, host: "127.0.0.1" });
  await new Promise((resolve) => server.once("listening", resolve));
  assert.equal(server.address().address, "127.0.0.1");
  handle.stop();
});

test("listenWithRetry survives an address this machine does not have", async () => {
  const server = http.createServer();
  const logs = [];
  // 192.0.2.1 is TEST-NET-1: documentation space, never assigned to an interface
  const handle = listenWithRetry(server, { port: 0, host: "192.0.2.1", log: (m) => logs.push(m), delays: [10] });
  await new Promise((resolve) => setTimeout(resolve, 150));
  assert.equal(server.listening, false);
  assert.ok(logs.some((l) => /cannot listen on 192\.0\.2\.1/.test(l) && /EADDRNOTAVAIL/.test(l)), logs.join("|"));
  handle.stop();
});
