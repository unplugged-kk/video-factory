/**
 * Worker lifecycle: what a healthy worker is, and how a dead one is recovered from.
 *
 * Healthy means the process is alive and its heartbeat is younger than HEARTBEAT_STALE_MS. The heartbeat file lives in
 * the factory's workspace and never in the exchange root, because the producer can write there and could forge it.
 * The same file is the single-instance lock and tells the next start which pipeline process the last worker left running.
 * Pure helpers with injectable seams, so `node --test` can exercise them. Delete with contentos/adapters/v1/.
 */
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

/** A worker whose heartbeat is older than this is treated as gone (ticket 07: 60 s). */
export const HEARTBEAT_STALE_MS = 60_000;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function readHeartbeat(file) {
  try {
    const beat = JSON.parse(fs.readFileSync(file, "utf8"));
    return beat && typeof beat === "object" && Number.isInteger(beat.pid) ? beat : null;
  } catch {
    return null;
  }
}

export function writeHeartbeat(file, beat) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(beat));
  fs.renameSync(tmp, file);
}

/** Only the owner removes it: a clean stop leaves no file, a crash leaves one for the next start to read. */
export function removeHeartbeat(file, pid) {
  if (readHeartbeat(file)?.pid === pid) fs.rmSync(file, { force: true });
}

export function processAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (e) {
    return e.code === "EPERM";
  }
}

export function commandOf(pid) {
  const r = spawnSync("ps", ["-p", String(pid), "-o", "command="], { encoding: "utf8" });
  return r.status === 0 ? r.stdout.trim() : "";
}

/**
 * One worker per exchange root. A live factory worker, silent or not, refuses a second one (two workers would break the
 * one-job-in-work/ rule); a dead one, or a pid some other program now holds, is taken over and returned as `previous`.
 * ponytail: two workers started in the same instant can both pass; starts are human-paced, a lock file would not close it either.
 */
export function acquireLock({ file, pid, now = Date.now(), staleMs = HEARTBEAT_STALE_MS, alive = processAlive, command = commandOf }) {
  const previous = readHeartbeat(file);
  if (!previous || previous.pid === pid) return { ok: true, previous: null };
  if (alive(previous.pid) && /factory_worker\.mjs/.test(command(previous.pid))) {
    const ageMs = now - (previous.heartbeatAt ?? 0);
    const message =
      ageMs <= staleMs
        ? `another factory worker is running (pid ${previous.pid}); stop it first`
        : `factory worker pid ${previous.pid} is alive but silent for ${Math.round(ageMs / 1000)} s; stop it first`;
    return { ok: false, pid: previous.pid, ageMs, message };
  }
  return { ok: true, previous };
}

function signalGroup(pgid, signal) {
  try {
    process.kill(-pgid, signal);
    return true;
  } catch (e) {
    if (e.code === "ESRCH") return false;
    throw e;
  }
}

/**
 * Stop a process group: SIGTERM, then SIGKILL once the grace period is over. The pipeline starts as a group leader, so
 * this takes npx, node and Chrome with it. Resolves true if there was a group to stop.
 */
export async function killProcessGroup(pgid, { graceMs = 5000 } = {}) {
  if (!signalGroup(pgid, "SIGTERM")) return false;
  const deadline = Date.now() + graceMs;
  while (Date.now() < deadline) {
    await sleep(25);
    if (!signalGroup(pgid, 0)) return true;
  }
  signalGroup(pgid, "SIGKILL");
  for (let i = 0; i < 80 && signalGroup(pgid, 0); i++) await sleep(25); // SIGKILL cannot be ignored; wait for the reap
  return true;
}

const jobNumber = (name) => {
  const m = /^cfvg-(\d+)$/.exec(name);
  return m ? Number(m[1]) : Infinity;
};

/** Oldest job first. Generation ids only grow, so numeric order is arrival order; plain text sorts cfvg-10 before cfvg-9. */
export const numericJobOrder = (a, b) => jobNumber(a) - jobNumber(b) || (a < b ? -1 : a > b ? 1 : 0);
