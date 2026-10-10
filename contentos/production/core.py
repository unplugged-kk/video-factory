"""Shared production core (ticket 07): the one place that decides what a failed stage means and when to try again, so
the folder bridge and any later transport behave the same. pipeline.py stays the stage engine; this wraps it."""
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

from .. import ledger, pipeline, storage

TRANSIENT_STAGES = ("voice", "compose", "render")   # the stages that shell out to flaky tools (TTS, lint, headless Chrome)
RETRY_BACKOFF = (15, 45)                             # seconds before retry 1 and 2: three tries in all
WALL_CLOCK_CAP = 360                                 # seconds from the first try; keeps a retried render inside ContentForge's ~7 minute window


def classify(stage, status):
    """A pipeline report row to a failure class. transient: worth trying again. output: the work itself is wrong (QA, bad
    input to a tool), so a retry would repeat it. blocked: a gate or prerequisite is missing, which an operator must fix."""
    if status.startswith("BLOCKED"):
        return "blocked"
    return "transient" if stage in TRANSIENT_STAGES else "output"


@dataclass
class RunResult:
    ok: bool
    failure_class: str | None = None
    stage: str | None = None
    error: str | None = None
    attempts: int = 0
    elapsed_s: float = 0.0

    def as_json(self):
        return {"ok": self.ok, "failureClass": self.failure_class, "stage": self.stage, "error": self.error,
                "attempts": self.attempts, "elapsedS": round(self.elapsed_s, 1)}


def scrub_interrupted(content_id, spec, project_dir=None):
    """Resume trusts any artifact it finds, and a kill leaves artifacts behind: compose writes index.html and then lints for
    seconds, voice writes a wav under ffmpeg. Keep an artifact only if the ledger recorded its stage OK and every stage
    before it; anything later is redone. Returns the artifacts it removed."""
    d = Path(project_dir) if project_dir else storage.find_job_dir(content_id)
    if d is None:
        return []                                   # no job folder yet: nothing a killed run could have left behind
    with ledger.db() as c:
        done = {r[0] for r in c.execute("SELECT DISTINCT stage FROM runs WHERE content_id=? AND status='OK'", (content_id,))}
    removed, dirty = [], False
    for scratch in d.glob("work-*"):              # hyperframes' render scratch: a killed render never cleans it up, and nothing is rendering now
        if scratch.is_dir():
            shutil.rmtree(scratch, ignore_errors=True)
            removed.append(f"render:{scratch.name}")
    for st in pipeline.STAGES:
        dirty = dirty or st not in done
        if not dirty:
            continue
        target = d / ("audio" if st == "voice" else pipeline.artifact(st, spec).replace("%02d", "01"))
        if target.is_dir():
            had_files = any(target.iterdir())     # a failed try leaves an empty folder: tidy it, but it is not a leftover
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
            had_files = True
        else:
            continue
        if had_files:
            removed.append(f"{st}:{target.relative_to(d)}")
    return removed


def run_until_blocked_or_done(spec_path, *, approve_private=False, run=None, sleep=time.sleep, clock=time.monotonic,
                              backoff=RETRY_BACKOFF, cap=WALL_CLOCK_CAP, log=None):
    """Run the pipeline to the end, trying a transient failure again from the failed stage (finished stages are skipped by
    the pipeline's own resume) until the retries or the wall-clock cap run out. Never raises for a failed job: the result
    says what happened. `run`, `sleep` and `clock` are seams for tests."""
    log = log or (lambda m: print(m, file=sys.stderr, flush=True))
    run = run or pipeline.run
    spec = yaml.safe_load(Path(spec_path).read_text())
    cid = spec["content_id"]
    t0, attempts, delays = clock(), 0, list(backoff)
    while True:
        attempts += 1
        removed = scrub_interrupted(cid, spec)
        if removed:
            log(f"{cid}: redoing artifacts a killed run left unfinished: {', '.join(removed)}")
        _, report = run(spec_path, approve_private=approve_private)
        bad = next(((s, st) for s, st, _ in report if not st.startswith(("OK", "SKIP"))), None)
        elapsed = clock() - t0
        if bad is None:
            return RunResult(True, attempts=attempts, elapsed_s=elapsed)
        stage, status = bad
        cls = classify(stage, status)
        error = f"{stage} {'blocked' if cls == 'blocked' else 'failed'}: {status.split(': ', 1)[-1]}"[:600]
        if cls != "transient":
            return RunResult(False, cls, stage, error, attempts, elapsed)
        if not delays:
            return RunResult(False, cls, stage, f"{error} (after {attempts} attempts)", attempts, elapsed)
        wait = delays.pop(0)
        if elapsed + wait > cap:
            return RunResult(False, cls, stage, f"{error} (another try would pass the {cap} s cap, after {attempts} attempts)", attempts, elapsed)
        log(f"{cid}: {stage} failed (attempt {attempts}), trying again in {wait} s: {error[:200]}")
        sleep(wait)
