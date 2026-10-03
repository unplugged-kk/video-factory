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
