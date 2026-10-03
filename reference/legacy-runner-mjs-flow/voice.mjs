// Universal voice step — the reliable replacement for the template-coupled revoice.py.
// Reads SCRIPT.md, generates one cloned-voice WAV per line into assets/voice/NN.wav,
// loudness-normalized. No storyboard/assemble coupling — works for ANY composition that
// references assets/voice/NN.wav in <audio> elements. Usage: node voice.mjs <projectDir>
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { execFileSync } from "node:child_process";

const dir = process.argv[2];
if (!dir) { console.error("usage: node voice.mjs <projectDir>"); process.exit(1); }
const HOME = os.homedir();
const VENV_PY = path.join(HOME, ".voice-clone-venv/bin/python");
const REF = path.join(HOME, "Desktop/voice-sample.wav");
const MODEL = "mlx-community/chatterbox-turbo-fp16";

// Parse SCRIPT.md: "## Line N (...)" headers, spoken text on following line(s).
function parseLines(scriptPath) {
  const text = fs.readFileSync(scriptPath, "utf8").split("\n");
  const lines = [];
  let cur = null, buf = [];
  const flush = () => { if (cur != null && buf.length) lines.push({ n: cur, text: buf.join(" ").trim() }); buf = []; };
  const hdr = /^##\s+Line\s+(\d+)/i;
  for (const ln of text) {
    const m = ln.match(hdr);
    if (m) { flush(); cur = parseInt(m[1], 10); continue; }
    if (cur == null) continue;
    const t = ln.trim();
    if (t && !t.startsWith("**") && !t.startsWith("#")) buf.push(t);
  }
  flush();
  return lines;
}

const scriptPath = path.join(dir, "SCRIPT.md");
if (!fs.existsSync(scriptPath)) { console.error("no SCRIPT.md"); process.exit(1); }
const lines = parseLines(scriptPath);
if (!lines.length) { console.error("no lines parsed from SCRIPT.md"); process.exit(1); }

const voiceDir = path.join(dir, "assets/voice");
const tmp = path.join(dir, ".vtmp");
fs.mkdirSync(voiceDir, { recursive: true });
fs.mkdirSync(tmp, { recursive: true });

for (const { n, text } of lines) {
  const nn = String(n).padStart(2, "0");
  // "buildcheap.app" etc. reads better spoken with "dot"
  const spoken = text.replace(/\b([a-z0-9-]+)\.(app|io|com|host)\b/gi, "$1 dot $2");
  const prefix = `line${nn}`;
  for (const f of fs.readdirSync(tmp)) if (f.startsWith(prefix)) fs.rmSync(path.join(tmp, f));
  execFileSync(VENV_PY, ["-m", "mlx_audio.tts.generate", "--model", MODEL, "--text", spoken,
    "--ref_audio", REF, "--output_path", tmp, "--file_prefix", prefix], { stdio: "ignore" });
  const raw = fs.readdirSync(tmp).filter((f) => f.startsWith(prefix) && f.endsWith(".wav")).sort()[0];
  if (!raw) { console.error(`no wav for line ${n}`); process.exit(1); }
  // loudness-normalize to hot voice (~-14 LUFS), 24k mono
  execFileSync("ffmpeg", ["-y", "-i", path.join(tmp, raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=8",
    "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", path.join(voiceDir, `${nn}.wav`)], { stdio: "ignore" });
  console.log(`voice ${nn}: ${text.slice(0, 40)}`);
}
fs.rmSync(tmp, { recursive: true, force: true });
console.log(`voiced ${lines.length} lines -> assets/voice/`);
