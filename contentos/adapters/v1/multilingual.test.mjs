import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { findJobDir } from "./exchange.mjs";
import { adaptV1Contract, loadLanguageCaps, scriptShare } from "./contract_adapter.mjs";
import { cutGraphemes, deriveScenes } from "./scene-derivation.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../..");
const worker = path.join(here, "factory_worker.mjs");

const HI = "कुबेरनेट्स में पॉड सबसे छोटी इकाई है जिसे आप डिप्लॉय कर सकते हैं और यह बहुत उपयोगी है। एक पॉड में एक या उससे ज़्यादा कंटेनर हो सकते हैं, जो एक ही नेटवर्क और स्टोरेज साझा करते हैं। अगर कोई पॉड फेल हो जाए, तो शेड्यूलर एक स्वस्थ नोड पर नया पॉड शुरू कर देता है।";
const HIEN = "Kubernetes में pod सबसे छोटी unit है जिसे आप deploy कर सकते हैं और यह बहुत useful है। एक pod में एक या ज़्यादा container हो सकते हैं, जो same network और storage share करते हैं।";
const OR = "ଓଡ଼ିଶା ଭାରତର ପୂର୍ବ ଉପକୂଳରେ ଥିବା ଏକ ରାଜ୍ୟ। କୁବେରନେଟିସରେ ପଡ୍ ହେଉଛି ସବୁଠାରୁ ଛୋଟ ଏକକ।";

const base = {
  contractVersion: "video-factory.contract.v1", jobId: "cfvg-9100001", title: "Probe", format: "9:16", brief: "brief",
  script: null, storyboard: null, voice: { enabled: true }, render: { quality: "draft" }, durationMs: 5000,
};
const CAPS = (over = {}) => ({
  languages: {
    hi: { name: "Hindi", status: "tested", status_reason: "x", default_voice: "hindi-default", voices: ["hindi-default", "hf_alpha"], subtitle: { script: "devanagari", unicode_ranges: ["0900-097F"], min_script_share: 0.6 } },
    "hi-en": { name: "Hinglish", status: "experimental", status_reason: "x", default_voice: "hindi-default", voices: ["hindi-default"], subtitle: { script: "devanagari", unicode_ranges: ["0900-097F"], min_script_share: 0.3 } },
    or: { name: "Odia", status: "blocked", status_reason: "TTS: backend blocked (gated model, PyTorch needs approval)", default_voice: "odia-default", voices: ["odia-default"], subtitle: { script: "odia", unicode_ranges: ["0B00-0B7F"], min_script_share: 0.6 } },
    ...over,
  },
});
const run = (over, caps = CAPS()) => adaptV1Contract({ ...base, ...over }, { languageCaps: caps });

// ---- English is unchanged ----------------------------------------------------------------------------------------

test("a contract without a language takes the original English path and carries no language in the spec", () => {
  const r = run({ script: "Hello world. This is a test.", voice: { enabled: true, id: "af_heart" } });
  assert.ok(r.ok);
  assert.equal(r.contentosSpec.language, undefined);
  assert.equal(r.factorySettings.language, "en");
  assert.equal(r.factorySettings.languageStatus, "production-ready");
  assert.equal(r.contentosSpec.voice, "af_heart");
});

test("English still rejects a non-Kokoro voice exactly as before", () => {
  const r = run({ script: "Hello.", voice: { enabled: true, id: "hindi-default" } });
  assert.equal(r.ok, false);
  assert.equal(r.code, "unknown_voice_id");
});

test("an explicit language en behaves like no language", () => {
  const a = run({ script: "Hello world. This is a test." });
  const b = run({ script: "Hello world. This is a test.", language: "en" });
  assert.deepEqual(a.contentosSpec.script, b.contentosSpec.script);
});

// ---- Hindi, Hinglish -----------------------------------------------------------------------------------------------

test("Hindi is accepted, defaults its voice, splits at the danda and drops English tags", () => {
  const r = run({ language: "hi", script: HI });
  assert.ok(r.ok, r.message);
  assert.equal(r.contentosSpec.language, "hi");
  assert.equal(r.contentosSpec.voice, "hindi-default");
  assert.equal(r.factorySettings.languageStatus, "tested");
  assert.equal(r.contentosSpec.script.length, 3);
  assert.ok(r.contentosSpec.script.every((s) => s.tag === "" && !/STEP|HOOK|CLOSE/.test(s.headline)));
  assert.ok(r.contentosSpec.script.every((s) => s.say.normalize("NFC") === s.say));
});

test("Hinglish is accepted and its experimental status is carried to the job", () => {
  const r = run({ language: "hi-en", script: HIEN });
  assert.ok(r.ok, r.message);
  assert.equal(r.factorySettings.languageStatus, "experimental");
});

test("a Hindi job whose script is English is rejected before any render", () => {
  const r = run({ language: "hi", script: "This is English text sent as a Hindi job." });
  assert.equal(r.ok, false);
  assert.equal(r.code, "script_language_mismatch");
  assert.match(r.message, /Hindi/);
});

test("an English voice id is not valid for Hindi", () => {
  const r = run({ language: "hi", script: HI, voice: { enabled: true, id: "af_heart" } });
  assert.equal(r.code, "invalid_voice");
  assert.match(r.message, /hindi-default/);
});

test("language may be given as an object", () => {
  assert.ok(run({ language: { code: "hi" }, script: HI }).ok);
});

// ---- Odia and unknown languages -------------------------------------------------------------------------------------

test("a blocked language is rejected with the reason, not silently produced with another voice", () => {
  const r = run({ language: "or", script: OR });
  assert.equal(r.ok, false);
  assert.equal(r.code, "language_blocked");
  assert.match(r.message, /Odia/);
  assert.match(r.message, /blocked|gated|PyTorch/);
});

test("when Odia is unblocked it is accepted and script-validated", () => {
  const open = CAPS({ or: { ...CAPS().languages.or, status: "experimental" } });
  assert.ok(run({ language: "or", script: OR }, open).ok);
  assert.equal(run({ language: "or", script: "English text" }, open).code, "script_language_mismatch");
});

test("an unsupported language lists the supported ones", () => {
  const r = run({ language: "ta", script: "x" });
  assert.equal(r.code, "unsupported_language");
  assert.match(r.message, /en, hi, hi-en, or/);
});

test("an unreadable capability matrix fails closed for non-English and does not affect English", () => {
  const missing = new URL("file:///nonexistent/language-capabilities.json");
  const bad = adaptV1Contract({ ...base, language: "hi", script: HI }, { languageCapsUrl: missing });
  assert.equal(bad.ok, false);
  assert.equal(bad.code, "language_matrix_unavailable");
  const en = adaptV1Contract({ ...base, script: "Hello world." }, { languageCapsUrl: missing });
  assert.ok(en.ok, "English never consults the matrix");
});

test("the real capability snapshot gates Odia and allows English, Hindi and Hinglish", () => {
  const caps = loadLanguageCaps();
  assert.equal(caps.languages.en.status, "production-ready");
  assert.notEqual(caps.languages.hi.status, "blocked");
  assert.notEqual(caps.languages["hi-en"].status, "blocked");
  assert.equal(caps.languages.or.status, "blocked");
});

// ---- derivation ------------------------------------------------------------------------------------------------------

test("script share counts letters and combining marks in the language's ranges", () => {
  assert.equal(scriptShare("abc", ["0900-097F"]), 0);
  assert.ok(scriptShare(HI, ["0900-097F"]) > 0.95);
  assert.ok(scriptShare(HIEN, ["0900-097F"]) > 0.3 && scriptShare(HIEN, ["0900-097F"]) < 0.95);
  assert.ok(scriptShare(OR, ["0B00-0B7F"]) > 0.95);
});

test("grapheme-safe cutting keeps whole clusters where slice() would sever one", () => {
  const s = "कंटेनर".repeat(20);                       // each unit is several UTF-16 code units: क + ं, ट + े, न, र
  const seg = new Intl.Segmenter(undefined, { granularity: "grapheme" });
  const cut = cutGraphemes(s, 7);
  assert.equal([...seg.segment(cut)].length, 7);
  assert.ok(s.startsWith(cut) && cut.length > 7, "7 clusters are more than 7 code units");
  const naive = s.slice(0, 7);
  assert.equal([...seg.segment(naive)].length, [...seg.segment(naive)].length);
  assert.notEqual(naive, cut, "the naive slice and the grapheme cut must differ for this input");
  assert.ok(!/^[\u093e-\u094d\u0900-\u0903]/.test(cut), "never starts with a dangling mark");
});

test("a long Hindi headline drops whole words and never ends in an ellipsis inside a conjunct", () => {
  const scenes = deriveScenes({ title: "t", brief: "b", script: "कुबेरनेट्स में पॉड सबसे छोटी इकाई है जिसे आप डिप्लॉय कर सकते हैं और भी बहुत कुछ।", storyboard: null, language: "hi" });
  const h = scenes[0].headline;
  assert.ok([...new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(h)].length <= 48);
  assert.ok(!h.endsWith("…"));
  assert.ok(scenes[0].say.startsWith(h));
});

test("English derivation reproduces the original module's output exactly (golden values captured from git HEAD before this change)", () => {
  const a = deriveScenes({ title: "It’s “smart”", brief: "x", script: "It’s a “quoted” thing. Café owners love résumé drafts. Dr. Smith said e.g. this works. 3.5 is a number.", storyboard: null });
  assert.deepEqual(a.map((s) => [s.say, s.headline, s.tag]), [
    ["It’s a “quoted” thing. Café owners love résumé drafts. Dr. Smith said e.g. this works. 3.5 is a number.", "It’s a “quoted” thing. Café owners love résumé", "HOOK"],
  ]);
  const b = deriveScenes({ title: "T", brief: "x", script: "Hello world. This is a test sentence that is definitely long enough to stand alone. Follow for part two!", storyboard: null });
  assert.deepEqual(b.map((s) => [s.say, s.headline, s.tag]), [
    ["Hello world.", "Hello world.", "HOOK"],
    ["This is a test sentence that is definitely long enough to stand alone. Follow for part two!", "This is a test sentence that is definitely", "CTA"],
  ]);
});

// ---- the real worker, with a fake pipeline: what lands in the spec and in the published state -------------------------

const FAKE = `#!/bin/bash
spec="$3"; id=$(basename "$spec" .yaml)
cp "$spec" "$FAKE_STAMPS/spec-$id.yaml"
mkdir -p "$FAKE_WS/jobs/2026/10/17/$id/project"   # the REAL layout: per-day folders (contentos/storage.py)
printf mp4 > "$FAKE_WS/jobs/2026/10/17/$id/video.mp4"
printf '{"width":1080,"height":1920,"fps":30,"duration":3.4}' > "$FAKE_WS/jobs/2026/10/17/$id/project/hyperframes.json"
echo '{"ok":true,"failureClass":null,"stage":null,"error":null,"attempts":1,"elapsedS":0.1}'
`;

function workerRun(over, id) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vf-ml-"));
  const root = path.join(dir, "exchange"), ws = path.join(dir, "ws"), stamps = path.join(dir, "stamps"), launcher = path.join(dir, "fake.sh");
  for (const d of [root, ws, stamps]) fs.mkdirSync(d, { recursive: true });
  fs.writeFileSync(launcher, FAKE, { mode: 0o755 });
  const jd = path.join(root, "queue", id);
  fs.mkdirSync(jd, { recursive: true });
  fs.writeFileSync(path.join(jd, "CONTRACT.json"), JSON.stringify({ ...base, jobId: id, ...over }));
  const r = spawnSync("node", [worker, "--once", "--port", "0"], {
    cwd: repoRoot, encoding: "utf8",
    env: { ...process.env, VIDEO_FACTORY_ROOT: root, VIDEO_FACTORY_WORKSPACE: ws, VIDEO_FACTORY_CONTENTOS: launcher, FAKE_STAMPS: stamps, FAKE_WS: ws, VIDEO_FACTORY_DASHBOARD_PORT: "0", VIDEO_FACTORY_POLL_MS: "50" },
  });
  const state = JSON.parse(fs.readFileSync(path.join(root, "state", `${id}.json`), "utf8"));
  const specFile = path.join(stamps, `spec-${id}.yaml`);
  const yaml = fs.existsSync(specFile) ? fs.readFileSync(specFile, "utf8") : null;
  return { r, state, yaml, root, dir, failed: fs.existsSync(path.join(root, "failed", id)) };
}

test("worker: a Hindi cloud job writes language, voice and intact Devanagari into the spec and publishes its status", () => {
  const o = workerRun({ language: "hi", script: HI }, "cfvg-9100010");
  assert.equal(o.r.status, 0, o.r.stderr);
  assert.equal(o.state.status, "done");
  assert.equal(o.state.language, "hi");
  assert.equal(o.state.languageStatus, "experimental");
  assert.match(o.yaml, /^language: "hi"$/m);
  assert.match(o.yaml, /^voice: "hindi-default"$/m);
  assert.ok(o.yaml.includes("कुबेरनेट्स में पॉड"), "Devanagari must survive the YAML writer unescaped or correctly escaped");
  assert.equal((o.yaml.match(/^  - say:/gm) || []).length, 3);
  assert.ok(!/^    tag:/m.test(o.yaml));
  fs.rmSync(o.dir, { recursive: true, force: true });
});

test("worker: an English cloud job writes a spec with no language line (original behaviour)", () => {
  const o = workerRun({ script: "Hello world. This is a test.", voice: { enabled: true, id: "af_heart" } }, "cfvg-9100011");
  assert.equal(o.state.status, "done");
  assert.ok(!/^language:/m.test(o.yaml));
  assert.match(o.yaml, /^voice: "af_heart"$/m);
  assert.equal(o.state.language, "en");
  fs.rmSync(o.dir, { recursive: true, force: true });
});

test("worker: an Odia cloud job is permanently rejected with the blocker and never reaches the pipeline", () => {
  const o = workerRun({ language: "or", script: OR }, "cfvg-9100012");
  assert.equal(o.state.status, "failed");
  assert.equal(o.state.permanentFailureCode, "language_blocked");
  assert.match(o.state.error, /Odia/);
  assert.equal(o.yaml, null, "the pipeline must not have been started");
  assert.ok(o.failed);
  fs.rmSync(o.dir, { recursive: true, force: true });
});

test("findJobDir resolves the per-day layout storage.py writes, and the older month layout", () => {
  const ws = fs.mkdtempSync(path.join(os.tmpdir(), "vf-find-"));
  fs.mkdirSync(path.join(ws, "jobs/2026/11/03/cfvg-1"), { recursive: true });
  fs.mkdirSync(path.join(ws, "jobs/2026/10/cfvg-2"), { recursive: true });
  assert.equal(findJobDir(ws, "cfvg-1"), path.join(ws, "jobs/2026/11/03/cfvg-1"));
  assert.equal(findJobDir(ws, "cfvg-2"), path.join(ws, "jobs/2026/10/cfvg-2"));
  assert.equal(findJobDir(ws, "cfvg-3"), null);
  assert.equal(findJobDir(ws, "../escape"), null);
  fs.rmSync(ws, { recursive: true, force: true });
});
