import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { adaptV1Contract } from "./contract_adapter.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const samplePath = join(here, "../../../done/cfvg-9000271/CONTRACT.json");

const base = {
  contractVersion: "video-factory.contract.v1",
  jobId: "cfvg-42",
  title: "Thin slice probe",
  format: "9:16",
  brief: "One sentence about data pipelines for social video.",
  script: null,
  storyboard: null,
  voice: { enabled: true, id: "af_heart" },
  render: { quality: "medium" },
  durationMs: 45000,
};

test("maps medium quality to hyperframes looks", () => {
  const r = adaptV1Contract(base);
  assert.equal(r.ok, true);
  assert.equal(r.factorySettings.hyperframesQuality, "looks");
  assert.equal(r.factorySettings.contractRenderQuality, "medium");
  assert.equal(r.contentosSpec.voice, "af_heart");
  assert.ok(r.contentosSpec.script.length >= 1);
});

test("rejects 1:1 format permanently", () => {
  const r = adaptV1Contract({ ...base, format: "1:1" });
  assert.equal(r.ok, false);
  assert.equal(r.code, "unsupported_format");
});

test("rejects voiceless jobs permanently", () => {
  const r = adaptV1Contract({ ...base, voice: { enabled: false } });
  assert.equal(r.ok, false);
  assert.equal(r.code, "voiceless_not_supported");
});

test("rejects unknown voice id permanently", () => {
  const r = adaptV1Contract({ ...base, voice: { enabled: true, id: "not_a_real_voice_id" } });
  assert.equal(r.ok, false);
  assert.equal(r.code, "unknown_voice_id");
});

test("legacy done folder voiceless contract is rejected", () => {
  const legacy = JSON.parse(readFileSync(samplePath, "utf8"));
  const r = adaptV1Contract(legacy);
  assert.equal(r.ok, false);
  assert.equal(r.code, "voiceless_not_supported");
});
