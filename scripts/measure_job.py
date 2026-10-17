#!/usr/bin/env python3
"""Measure the peak memory of a whole process tree while a command runs.

    measure_job.py --out SIDE.json [--interval 1.0] -- <command ...>

The command runs unchanged (stdio inherited) in its own session / process
group.  About once per `--interval` seconds the tool takes a `ps` snapshot and
sums the resident set size (RSS) of every process in the tree: descendants of
the command by parent/child links, plus every process still in the command's
process group (so children re-parented to launchd are not lost).  A JSON
sidecar records the time series and the peaks.  The measured processes are
never signalled, reniced or otherwise altered.  Exit code of the command is
passed through (128+N if it died on signal N; 127 not found; 126 not
executable; 130 if the measurement itself was interrupted).

Standard library only.  Intended for macOS (`ps -axo pid=,ppid=,pgid=,rss=,command=`).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
import time
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set

SCHEMA = "measure_job/1"
PS_ARGV = ["ps", "-axo", "pid=,ppid=,pgid=,rss=,command="]
ENV_FLAGS = ("HF_CAPTURE_PARALLEL_STREAM", "HYPERFRAMES_BIN")

LIMITS = [
    "Summed RSS double counts pages shared between processes (shared libraries, "
    "copy-on-write memory, shared Chrome memory), so the peak over-states true "
    "physical memory use; it is not the macOS footprint or the unified-memory pressure figure.",
    "RSS excludes memory the OS has compressed or swapped out, and GPU / IOSurface memory "
    "that is not attributed to a process's resident set, so real pressure can be higher in those respects.",
    "Sampling is periodic: a spike shorter than the sampling interval can be missed, so the "
    "recorded peak is a lower bound on the instantaneous peak of the summed RSS.",
    "Processes that escape the tree (double-fork daemons that also call setsid, or processes "
    "started via launchd / XPC services) are not seen; work done by system services on the "
    "command's behalf is not counted.",
    "A process that starts and exits between two samples is never seen, so it is not counted "
    "in the process count, worker count or `--workers` values.",
    "Each snapshot is taken by running `ps`, which is itself not instantaneous; the processes "
    "are not sampled at exactly the same instant.",
    "Chrome worker counting is a name heuristic on the executable part of the command line "
    "(chrome / chromium / headless_shell); helper processes count as workers too, and renamed "
    "binaries would be missed.",
    "`--workers` values are parsed from process command lines only; a worker count chosen "
    "internally (auto-sizing) or via environment variable or config file is not visible.",
    "The sampler's own overhead (one `ps` per interval) is not subtracted, and the measured "
    "process is started in its own session, so it has no controlling terminal and terminal "
    "Ctrl-C does not reach it.",
]

_WORKER_RE = re.compile(r"chrome|chromium|headless[_-]shell", re.I)
_WORKERS_ARG_RE = re.compile(r"(?:^|\s)--workers(?:=|\s+)(\d+)(?=\s|$)")


# ---------------------------------------------------------------- parsing

class Proc:
    __slots__ = ("pid", "ppid", "pgid", "rss_kb", "command")

    def __init__(self, pid: int, ppid: int, pgid: int, rss_kb: int, command: str):
        self.pid, self.ppid, self.pgid, self.rss_kb, self.command = pid, ppid, pgid, rss_kb, command

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Proc({self.pid},{self.ppid},{self.pgid},{self.rss_kb},{self.command!r})"


def parse_ps(text: str) -> Dict[int, Proc]:
    """Parse `ps -axo pid=,ppid=,pgid=,rss=,command=` output; skips malformed lines."""
    out: Dict[int, Proc] = {}
    for line in text.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        try:
            pid, ppid, pgid, rss = (int(p) for p in parts[:4])
        except ValueError:
            continue
        out[pid] = Proc(pid, ppid, pgid, rss, parts[4] if len(parts) > 4 else "")
    return out


def run_ps() -> str:
    """Default ps runner.  Tests inject a replacement with the same signature."""
    return subprocess.run(PS_ARGV, capture_output=True, text=True, check=True, timeout=30).stdout


def tree_members(procs: Dict[int, Proc], root_pid: int, pgid: Optional[int],
                 root_alive: bool = True, exclude: Iterable[int] = ()) -> Set[int]:
    """Pids in the measured tree.

    Seeds: the root (if still alive) and every process whose process group is
    `pgid`.  Then every descendant (by ppid) of any seed is added.
    """
    skip = set(exclude)
    seeds: Set[int] = set()
    if root_alive and root_pid in procs:
        seeds.add(root_pid)
    if pgid is not None:
        seeds.update(p.pid for p in procs.values() if p.pgid == pgid)
    children: Dict[int, List[int]] = {}
    for p in procs.values():
        children.setdefault(p.ppid, []).append(p.pid)
    members: Set[int] = set()
    stack = list(seeds)
    while stack:
        pid = stack.pop()
        if pid in members or pid in skip:
            continue
        members.add(pid)
        stack.extend(children.get(pid, ()))
    return members


def is_worker(command: str) -> bool:
    """Heuristic: executable part of the command line names Chrome / Chromium."""
    exe = command.split(" --", 1)[0]
    return bool(_WORKER_RE.search(exe))


def parse_workers_args(command: str) -> List[int]:
    return [int(m) for m in _WORKERS_ARG_RE.findall(command)]


def summarize(procs: Dict[int, Proc], members: Set[int]) -> dict:
    rss = sum(procs[m].rss_kb for m in members if m in procs)
    workers = sum(1 for m in members if m in procs and is_worker(procs[m].command))
    seen: Set[int] = set()
    for m in members:
        if m in procs:
            seen.update(parse_workers_args(procs[m].command))
    return {"rss_kb": rss, "procs": len([m for m in members if m in procs]),
            "workers": workers, "workers_args": seen}


# ---------------------------------------------------------------- measuring

def _iso(ts: float) -> str:
    return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).isoformat()


class Recorder:
    """Accumulates samples and derives the peaks."""

    def __init__(self, interval: float):
        self.interval = interval
        self.samples: List[dict] = []
        self.sample_errors = 0
        self.workers_seen: Set[int] = set()

    def add(self, t: float, summ: dict) -> None:
        self.samples.append({"t": round(t, 3), "rss_kb": summ["rss_kb"],
                             "procs": summ["procs"], "workers": summ["workers"]})
        self.workers_seen.update(summ["workers_args"])

    def result(self) -> dict:
        peak_kb = max((s["rss_kb"] for s in self.samples), default=0)
        return {
            "samples_count": len(self.samples),
            "sample_errors": self.sample_errors,
            "peak_rss_kb": peak_kb,
            "peak_rss_gib": round(peak_kb / 1024 / 1024, 4),
            "peak_process_count": max((s["procs"] for s in self.samples), default=0),
            "peak_worker_count": max((s["workers"] for s in self.samples), default=0),
            "workers_arg_values": sorted(self.workers_seen),
            "samples": self.samples,
        }


def take_sample(rec: Recorder, ps_runner: Callable[[], str], root_pid: int, pgid: Optional[int],
                root_alive: bool, t0: float, clock: Callable[[], float]) -> None:
    try:
        procs = parse_ps(ps_runner())
    except Exception:
        rec.sample_errors += 1
        return
    members = tree_members(procs, root_pid, pgid, root_alive, exclude={os.getpid()})
    rec.add(clock() - t0, summarize(procs, members))


def write_sidecar(path: str, data: dict) -> None:
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".measure_job.", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def exit_code_from(returncode: int) -> int:
    return 128 + (-returncode) if returncode < 0 else returncode


def measure(command: Sequence[str], out: str, interval: float = 1.0,
            ps_runner: Callable[[], str] = run_ps, clock: Callable[[], float] = time.monotonic,
            popen: Callable[..., "subprocess.Popen"] = subprocess.Popen) -> int:
    """Run `command`, sample its tree, write the sidecar to `out`, return the exit code."""
    start_wall = time.time()
    t0 = clock()
    rec = Recorder(interval)
    exit_code: Optional[int] = None
    error: Optional[str] = None
    interrupted = False
    child_still_running = False
    child_pid: Optional[int] = None

    old_term = None
    try:
        old_term = signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    except (ValueError, OSError):  # not in main thread
        old_term = None
    proc = None
    try:
        try:
            proc = popen(list(command), start_new_session=True)
            child_pid = proc.pid
        except FileNotFoundError as e:
            error, exit_code = f"command not found: {e}", 127
        except PermissionError as e:
            error, exit_code = f"command not executable: {e}", 126
        except OSError as e:
            error, exit_code = f"could not start command: {e}", 126

        if proc is not None:
            try:
                pgid = proc.pid  # start_new_session makes the child its own group leader
                while True:
                    take_sample(rec, ps_runner, proc.pid, pgid, proc.poll() is None, t0, clock)
                    if proc.poll() is not None:
                        break
                    try:
                        proc.wait(timeout=interval)
                    except subprocess.TimeoutExpired:
                        pass
                    if proc.poll() is not None:
                        # one last look for lingering group members after the root exited
                        take_sample(rec, ps_runner, proc.pid, pgid, False, t0, clock)
                        break
                exit_code = exit_code_from(proc.returncode)
            except KeyboardInterrupt:
                interrupted = True
                child_still_running = proc.poll() is None
                exit_code = 130
                error = ("measurement interrupted; the measured command was not signalled"
                         + (" and may still be running" if child_still_running else ""))
    finally:
        end_wall = time.time()
        if old_term is not None:
            try:
                signal.signal(signal.SIGTERM, old_term)
            except (ValueError, OSError):
                pass
        data = {
            "schema": SCHEMA,
            "command": list(command),
            "started_at": _iso(start_wall),
            "ended_at": _iso(end_wall),
            "wall_seconds": round(end_wall - start_wall, 3),
            "exit_code": exit_code if exit_code is not None else 1,
            "interval_seconds": interval,
            "interrupted": interrupted,
            "child_pid": child_pid,
            "child_still_running": child_still_running,
            "error": error,
            **rec.result(),
            "peak_rss_basis": "sum of per-process RSS (KB as reported by ps) over the tree, max over samples",
            "env": {k: os.environ.get(k) for k in ENV_FLAGS},
            "platform": {"system": platform.system(), "release": platform.release(),
                         "machine": platform.machine(), "python": platform.python_version()},
            "limits": LIMITS,
        }
        write_sidecar(out, data)
    return data["exit_code"]


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="measure_job.py",
        description="Measure peak summed RSS of a process tree while a command runs.",
        usage="measure_job.py --out SIDE.json [--interval 1.0] -- <command ...>")
    ap.add_argument("--out", required=True, help="path of the JSON sidecar to write")
    ap.add_argument("--interval", type=float, default=1.0, help="seconds between samples (default 1.0)")
    ap.add_argument("command", nargs=argparse.REMAINDER, help="the command to run, after `--`")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    cmd = list(args.command)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        ap.error("no command given (put it after `--`)")
    if args.interval <= 0:
        ap.error("--interval must be positive")
    return measure(cmd, args.out, args.interval)


if __name__ == "__main__":
    sys.exit(main())
