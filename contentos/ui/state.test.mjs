import test from "node:test";
import assert from "node:assert/strict";

import {
  canonicalState, checkView, defaultLogStage, filterSortJobs, healthReadiness, jobView, nextAction,
  normalizeJobDraft, persistJobDraft, restoreJobDraft, STAGES, statusMeta,
} from "./state.js";
import { escapeHtml, fieldAttrs, idControl, middleId, statusLabel, timeline } from "./components.js";
import { icon } from "./icons.js";

test("the log screen opens on a real failed stage, not an array lookup miss", () => {
  assert.equal(defaultLogStage({ stages: [{ name: "voice", status: { state: "passed" } }, { name: "render", status: { state: "failed" } }] }), "render");
  assert.equal(defaultLogStage({ currentStage: "qa", stages: [] }), "qa");
  assert.equal(defaultLogStage({ stages: [] }), "script");
});

test("blocked, failed, and stale remain distinct", () => {
  assert.equal(canonicalState("draft"), "draft");
  assert.equal(canonicalState("awaiting approval"), "blocked");
  assert.equal(canonicalState("error"), "failed");
  assert.equal(canonicalState("orphaned"), "stale");
  assert.notEqual(canonicalState("blocked"), canonicalState("failed"));
});

test("canonical job transitions preserve every backend state", () => {
  const transitions = {
    DRAFT: "draft",
    PENDING: "pending",
    RUNNING: "running",
    BLOCKED: "blocked",
    FAILED: "failed",
    STALE: "stale",
    RENDERED: "completed",
    EXPORTED: "completed",
  };
  for (const [source, expected] of Object.entries(transitions)) {
    assert.equal(jobView({ state: source }).status.state, expected);
  }
});

test("missing check result maps to not run", () => {
  const check = checkView({ name: "visual review" });
  assert.equal(check.status.state, "not_run");
  assert.equal(check.status.label, "Not run");
  assert.equal(check.provenance, "not run");
});

test("job view always exposes nine ordered stages", () => {
  const job = jobView({ content_id: "long-job", state: "BLOCKED", stages: { script: { state: "completed" }, voice: { state: "blocked" } } });
  assert.equal(job.status.state, "blocked");
  assert.deepEqual(job.stages.map((stage) => stage.name), STAGES);
  assert.equal(job.stages[1].status.state, "completed");
  assert.equal(job.stages[2].status.state, "blocked");
});

test("next action never treats blocked as failure", () => {
  assert.equal(nextAction({ state: "blocked", gate: "SCRIPT_APPROVED" }).action, "review");
  assert.equal(nextAction({ state: "failed" }).action, "logs");
  assert.equal(nextAction({ state: "stale" }).action, "run");
});

test("backend next action is canonical", () => {
  assert.deepEqual(nextAction({
    state: "FAILED",
    nextAction: { kind: "review", label: "Server decision", detail: "Gate changed", gate: "SCRIPT_APPROVED" },
  }), {
    action: "review", label: "Server decision", detail: "Gate changed", gate: "SCRIPT_APPROVED", href: null,
  });
});

test("Track B next action stays on the backend kind", () => {
  const action = nextAction({
    state: "PENDING",
    nextAction: { kind: "track-b-voice", label: "Generate voice", detail: "Kokoro reads the approved script." },
  });
  assert.equal(action.action, "track-b-voice");
  assert.equal(action.label, "Generate voice");
  assert.notEqual(action.action, "run");
});

test("external evidence is labeled external", () => {
  assert.equal(canonicalState("EXTERNAL"), "external");
  assert.equal(statusMeta("EXTERNAL").label, "External");
});

test("recoverable drafts are capability constrained and never authoritative", () => {
  const capabilities = {
    voices: ["af_heart"], renderLanes: ["hyperframes"],
    platformLimits: { platforms: [{ id: "youtube", defaultEnabled: true }] },
  };
  const values = new Map();
  const storage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
  persistJobDraft(storage, {
    content_id: "../unsafe", title: "Recovered", format: "9:16", kind: "short",
    voice: "not-allowed", render: "paid", platform_targets: ["youtube", "unknown"],
    script: [{ say: "Draft text", headline: "Draft" }],
  });
  const restored = restoreJobDraft(storage, capabilities);
  assert.equal(restored.recovered, true);
  assert.equal(restored.data.voice, "af_heart");
  assert.equal(restored.data.render, "hyperframes");
  assert.deepEqual(restored.data.platform_targets, ["youtube"]);
  assert.equal(normalizeJobDraft(null, capabilities).platform_targets[0], "youtube");
});

test("job filtering and sorting preserves backend workflow fields", () => {
  const jobs = [
    jobView({ id: "b", title: "Beta", state: "FAILED", updated: 1, retries: 2 }),
    jobView({ id: "a", title: "Alpha", state: "DRAFT", updated: 2, draft: true, gate: "SCRIPT_APPROVED" }),
  ];
  assert.deepEqual(filterSortJobs(jobs, { kind: "retry" }).map((job) => job.id), ["b"]);
  assert.deepEqual(filterSortJobs(jobs, { state: "draft" }).map((job) => job.id), ["a"]);
  assert.deepEqual(filterSortJobs(jobs, { sort: "title-asc" }).map((job) => job.id), ["a", "b"]);
});

test("render helpers escape untrusted text and include icon plus label", () => {
  assert.equal(escapeHtml('<script>"x"</script>'), "&lt;script&gt;&quot;x&quot;&lt;/script&gt;");
  const label = statusLabel("failed");
  assert.match(label, /<svg[^>]+aria-hidden="true"/);
  assert.match(label, />Failed</);
  assert.doesNotMatch(label, /<script>/);
  assert.match(timeline([{ name: "script", state: "failed", error: "<boom>" }]), /&lt;boom&gt;/);
  assert.match(timeline([{ name: "render", state: "passed", provider: "hyperframes", seconds: 7.5 }]), /hyperframes · 7\.5s/);
});

test("long ids use deterministic middle truncation", () => {
  assert.equal(middleId("1234567890abcdefghijXYZ"), "123456789…fghijXYZ");
  assert.equal(middleId("short"), "short");
  const control = idControl("1234567890abcdefghijXYZ");
  assert.match(control, /<details class="id-control">/);
  assert.match(control, /1234567890abcdefghijXYZ/);
  assert.match(control, /aria-label="Copy job id/);
});

test("field attributes connect errors and help without empty references", () => {
  assert.equal(fieldAttrs("title", {}, []), "");
  assert.equal(fieldAttrs("content_id", { content_id: "Required" }, ["content_id-help"]), ' aria-invalid="true" aria-describedby="content_id-help content_id-error"');
});

test("icons are native SVG and escape accessible labels", () => {
  assert.match(icon("check"), /^<svg/);
  assert.match(icon("check"), /aria-hidden="true"/);
  assert.match(icon("alert", 'Needs "review"'), /aria-label="Needs &quot;review&quot;"/);
});

test("run readiness uses the server contract instead of every unavailable capability", () => {
  const health = {
    capabilities: [
      { name: "stt", selected: null },
      { name: "llm", selected: null },
      { name: "publish_youtube", selected: null },
    ],
    runReadiness: { profile: "track-a/hyperframes", ready: true, blockers: [] },
  };
  assert.deepEqual(healthReadiness(health), {
    profile: "track-a/hyperframes", ready: true, blockers: [],
  });
});

test("missing readiness contract fails closed", () => {
  const readiness = healthReadiness({ capabilities: [] });
  assert.equal(readiness.ready, false);
  assert.equal(readiness.blockers[0].id, "readiness-contract");
});
