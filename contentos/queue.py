"""Job queue + worker. Jobs are rows in workspace/ledger.db; each job runs `pipeline run` in its own process so a
crash cannot take down the worker. Gates are NOT bypassed: a job only auto-approves the private gates if it was
queued with --approve-private. Publishing is never auto-approved."""
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from . import ledger

ROOT = Path(__file__).resolve().parent.parent


def add(specs, approve_private=False, priority=0):
    ids = []
    with ledger.db() as c:
        for sp in specs:
            sp = Path(sp).resolve()
            cid = yaml.safe_load(sp.read_text())["content_id"]
            dup = c.execute("SELECT id FROM jobs WHERE content_id=? AND status IN ('queued','running')", (cid,)).fetchone()
            if dup:
                print(f"  skip {cid}: already queued/running as job {dup[0]}"); continue
            cur = c.execute("INSERT INTO jobs(spec,content_id,status,priority,approve_private,created) VALUES (?,?,?,?,?,?)",
                            (str(sp), cid, "queued", priority, int(approve_private), time.time()))
            ids.append(cur.lastrowid)
    return ids


def recover():
    """Jobs left 'running' by a dead worker go back to the queue."""
    with ledger.db() as c:
        for jid, pid in c.execute("SELECT id, pid FROM jobs WHERE status='running'").fetchall():
            try:
                os.kill(pid or 0, 0)
            except (OSError, ProcessLookupError):
                c.execute("UPDATE jobs SET status='queued', pid=NULL WHERE id=?", (jid,))


def claim():
    c = ledger.db()
    c.isolation_level = None
    c.execute("BEGIN IMMEDIATE")
    row = c.execute("SELECT id, spec, content_id, approve_private FROM jobs WHERE status='queued' ORDER BY priority DESC, id LIMIT 1").fetchone()
    if row:
        c.execute("UPDATE jobs SET status='running', started=?, pid=? WHERE id=?", (time.time(), os.getpid(), row[0]))
    c.execute("COMMIT")
    return row


def _run(job):
    jid, spec, cid, ap = job
    cmd = [str(ROOT / "contentos.sh"), "pipeline", "run", spec] + (["--approve-private"] if ap else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    ok = r.returncode == 0
    err = "" if ok else (r.stdout.strip().splitlines() or [r.stderr.strip()])[-1][:300]
    # BLOCKED (waiting on a gate) is not a failure: park as 'blocked' so a human can approve and re-queue
    status = "done" if ok else ("blocked" if "BLOCKED" in r.stdout else "failed")
    with ledger.db() as c:
        c.execute("UPDATE jobs SET status=?, finished=?, error=? WHERE id=?", (status, time.time(), err, jid))
    print(f"  job {jid} {cid}: {status} {err}")


def work(concurrency=2, once=False, poll=3):
    recover()
    print(f"worker pid {os.getpid()} concurrency {concurrency} ({'drain' if once else 'watching'})")
    with ThreadPoolExecutor(concurrency) as ex:
        futs = []
        while True:
            futs = [f for f in futs if not f.done()]
            while len(futs) < concurrency:
                job = claim()
                if not job:
                    break
                futs.append(ex.submit(_run, job))
            if not futs and (once or False):
                break
            time.sleep(poll if not futs else 1)
            if once and not futs and not claim_peek():
                break


def claim_peek():
    return ledger.db().execute("SELECT 1 FROM jobs WHERE status='queued' LIMIT 1").fetchone()


def listing():
    return ledger.db().execute("SELECT id, content_id, status, priority, round(coalesce(finished,strftime('%s','now'))-started,0), error FROM jobs ORDER BY id DESC LIMIT 30").fetchall()


def requeue(job_id):
    with ledger.db() as c:
        c.execute("UPDATE jobs SET status='queued', error=NULL, pid=NULL WHERE id=? AND status IN ('failed','blocked')", (job_id,))
