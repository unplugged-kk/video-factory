import test from "node:test";
import assert from "node:assert/strict";

import { api, ApiError, request, watchJobEvents } from "./api.js";

function response(body, { status = 200, type = "application/json" } = {}) {
  return new Response(body, { status, headers: { "content-type": type } });
}

test("write requests require an injected token before fetch", async () => {
  let called = false;
  await assert.rejects(
    request("/api/v1/specs", { method: "POST", body: "{}" }, async () => { called = true; }, ""),
    (error) => error instanceof ApiError && error.code === "missing_write_token",
  );
  assert.equal(called, false);
});

test("write requests send the token and same-origin credentials", async () => {
  const data = await request("/api/v1/specs/validate", { method: "POST", body: "{}" }, async (path, options) => {
    assert.equal(path, "/api/v1/specs/validate");
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.headers.get("X-ContentOS-Token"), "secret-token");
    return response('{"valid":true}');
  }, "secret-token");
  assert.deepEqual(data, { valid: true });
});

test("409 JSON errors preserve structured conflict information", async () => {
  await assert.rejects(
    request("/api/v1/jobs/id/approve", { method: "POST", body: "{}" }, async () => response('{"error":{"code":"digest_mismatch","message":"Artifact changed","details":{"current":"b"}}}', { status: 409 }), "token"),
    (error) => error.status === 409 && error.code === "digest_mismatch" && error.details.current === "b" && error.message === "Artifact changed",
  );
});

test("non-JSON failures are distinct from network and JSON errors", async () => {
  await assert.rejects(
    request("/api/v1/jobs/id/run", { method: "POST", body: "{}" }, async () => response("process exited without JSON", { status: 500, type: "text/plain" }), "token"),
    (error) => error.code === "non_json_error" && error.body.includes("without JSON"),
  );
});

test("network errors use a stable error code", async () => {
  await assert.rejects(
    request("/api/v1/health", {}, async () => { throw new Error("offline"); }),
    (error) => error.code === "network_error" && error.details === "offline",
  );
});

test("capabilities client uses the read-only endpoint", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (path, options) => {
    assert.equal(path, "/api/v1/capabilities");
    assert.equal(options.method, "GET");
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.headers.has("X-ContentOS-Token"), false);
    return response('{"schema":"creator-studio/capabilities/1"}');
  };
  try {
    assert.deepEqual(await api.capabilities(), {
      schema: "creator-studio/capabilities/1",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("job events trigger canonical refresh signals", () => {
  let instance;
  class FakeEventSource {
    constructor(url) {
      assert.equal(url, "/api/v1/jobs/job%20id/events");
      this.listeners = {};
      instance = this;
    }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    close() { this.closed = true; }
  }
  const signals = [];
  const stop = watchJobEvents("job id", {
    EventSourceImpl: FakeEventSource,
    onSignal: (signal) => signals.push(signal.type),
  });
  instance.onopen();
  instance.listeners.progress({ data: '{"revision":"one"}' });
  assert.deepEqual(signals, ["reconnect", "progress"]);
  stop();
  assert.equal(instance.closed, true);
});

test("job events fall back when EventSource is unavailable or disconnects", () => {
  const reasons = [];
  watchJobEvents("id", {
    EventSourceImpl: undefined,
    onFallback: (reason) => reasons.push(reason),
  });
  let broken;
  class BrokenEventSource {
    constructor() { broken = this; }
    addEventListener() {}
    close() { this.closed = true; }
  }
  const stop = watchJobEvents("id", {
    EventSourceImpl: BrokenEventSource,
    onFallback: (reason) => reasons.push(reason),
  });
  broken.onerror();
  stop();
  assert.equal(broken.closed, true);
  assert.deepEqual(reasons, ["unsupported", "disconnected"]);
});
