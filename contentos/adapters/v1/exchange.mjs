/**
 * Exchange-root helpers. The exchange root is the one folder shared with the control plane
 * (ContentForge), so the factory treats everything read from it as hostile data: it never holds
 * the factory's code, and the readiness endpoint never listens on every interface.
 * Pure functions, no process-level side effects, so `node --test` can exercise them.
 * Delete with contentos/adapters/v1/ when contract v2 ships (the v2 worker needs the same rules).
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const DEFAULT_EXCHANGE_ROOT = path.join(os.homedir(), ".contentos", "exchange");
export const JOB_ID_RE = /^cfvg-[1-9][0-9]{0,9}$/;
/** script + storyboard + brief top out near 110 KB; anything bigger is not a contract. */
export const MAX_CONTRACT_BYTES = 256 * 1024;

const real = (p) => {
  try {
    return fs.realpathSync(p);
  } catch {
    return path.resolve(p);
  }
};

/** Data only: the exchange root must not be, or sit above, the factory repo. */
export function assertExchangeRoot(root, repoRoot) {
  const rel = path.relative(real(root), real(repoRoot));
  if (rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel))) {
    throw new Error(
      `VIDEO_FACTORY_ROOT ${root} contains the factory repo ${repoRoot}; use a data-only folder such as ${DEFAULT_EXCHANGE_ROOT}`,
    );
  }
}

const WILDCARD_HOSTS = new Set(["", "0.0.0.0", "::", "[::]", "*"]);

/** Never every interface (ratified Round 4, Q18a): the Tailscale address, or loopback. */
export function assertReadinessHost(host) {
  const h = String(host ?? "").trim();
  if (WILDCARD_HOSTS.has(h)) {
    throw new Error(`readiness host "${h}" would listen on every interface; use the Tailscale address or 127.0.0.1`);
  }
  return h;
}

/** `0` is valid: the OS picks a free port (tests rely on it). */
export function parsePort(value, fallback) {
  if (value === undefined || value === null || value === "") return fallback;
  const n = Number(value);
  if (!Number.isInteger(n) || n < 0 || n > 65535) throw new Error(`invalid port "${value}"`);
  return n;
}

/** What the control plane may read: no host paths, no run-time scratch. */
export function publicJob({ _stderr, dir, outputPath, ...job }) {
  return job;
}

/** A name that is safe as a single path component, for folders that failed the id check. */
export function safeName(name) {
  return String(name).replace(/[^A-Za-z0-9._-]/g, "_").replace(/^\.+/, "_").slice(0, 64) || "_";
}

/** Every state file name goes through safeName: an id can never steer a write out of state/. */
export function stateFileName(id) {
  return `${safeName(id)}.json`;
}

/**
 * A state file lives in the shared folder, so it is hostile input: its file name decides the job id,
 * never its content (an `id` of "../../x" would otherwise redirect the next write). Null means ignore it.
 */
export function loadStateFile(fileName, raw) {
  const m = /^(cfvg-[1-9][0-9]{0,9})\.json$/.exec(fileName);
  if (!m || !raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const { _stderr, dir, outputPath, ...rest } = raw;
  return { ...rest, id: m[1] };
}

/**
 * Bind the readiness server and keep trying. The Tailscale address does not exist while Tailscale is
 * down, so `listen` fails with EADDRNOTAVAIL until it returns; the worker's real job is rendering, so
 * a failed bind is logged and retried, never fatal. While nothing listens, readiness reads "not ready".
 * Limit: this covers an address that is absent at bind time. A listener whose address later disappears
 * is left to the OS, which resumes delivery when the address returns (not exercised in tests).
 */
export function listenWithRetry(server, { port, host, log = () => {}, delays = [2000, 5000, 15000, 30000], unref = false }) {
  let failures = 0;
  let timer = null;
  let stopped = false;
  const bind = () => {
    timer = null;
    if (stopped) return;
    if (server.listening) server.close(() => bind());
    else server.listen({ port, host });
  };
  server.on("listening", () => {
    failures = 0;
    const a = server.address();
    log(`readiness listening on ${typeof a === "string" ? a : `${a.address}:${a.port}`}`);
  });
  server.on("error", (err) => {
    if (stopped) return;
    const wait = delays[Math.min(failures++, delays.length - 1)];
    log(`readiness cannot listen on ${host}:${port} (${err.code ?? err.message}); retrying in ${wait} ms`);
    timer = setTimeout(bind, wait);
    if (unref) timer.unref();
  });
  bind();
  return {
    stop() {
      stopped = true;
      if (timer) clearTimeout(timer);
      if (server.listening) server.close();
    },
  };
}
