"""Job queue + worker. Jobs are rows in workspace/ledger.db; each job runs `production run` in its own session so a
crash cannot take down the worker. Gates are NOT bypassed: a job only auto-approves the private gates if it was
queued with --approve-private. Publishing is never auto-approved."""
import json
import os
import signal
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from . import ledger

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = int(os.environ.get("CONTENTOS_QUEUE_TIMEOUT", "1800"))


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
            if not pid:                                  # no process to probe; os.kill(0, 0) would always succeed
                c.execute("UPDATE jobs SET status='queued', pid=NULL WHERE id=?", (jid,))
                continue
            try:
                os.kill(pid, 0)
            except OSError:
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


def _production_result(stdout):
    for line in reversed((stdout or "").splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "ok" in value:
            return value
    return None


def _kill_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        process.kill()
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            process.kill()


def _run(job):
    jid, spec, cid, ap = job
    cmd = [str(ROOT / "contentos.sh"), "production", "run", spec] + (["--approve-private"] if ap else [])
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_group(process)
        stdout, stderr = process.communicate()
    result = _production_result(stdout)
    if timed_out:
        status, err = "failed", f"timed out after {TIMEOUT}s"
    elif result and result.get("ok"):
        status, err = "done", ""
    elif result and result.get("failureClass") == "blocked":
        status, err = "blocked", str(result.get("error") or "BLOCKED")[:300]
    elif result:
        status, err = "failed", str(result.get("error") or "failed")[:300]
    else:
        text = (stdout or "") + "\n" + (stderr or "")
        status = "blocked" if "BLOCKED" in text else "failed"
        err = "" if process.returncode == 0 else (text.strip().splitlines() or ["failed"])[-1][:300]
        if process.returncode == 0 and result is None:
            status, err = "failed", "production run did not return a result"
    with ledger.db() as c:
        c.execute("UPDATE jobs SET status=?, finished=?, error=? WHERE id=?", (status, time.time(), err, jid))
    print(f"  job {jid} {cid}: {status} {err}")


def view():
    """Queue rows for Creator Studio. This does not start a worker."""
    rows = []
    for job_id, content_id, status, priority, seconds, error in listing():
        rows.append({
            "id": job_id,
            "contentId": content_id,
            "status": status,
            "priority": priority,
            "seconds": seconds,
            "error": error or "",
            "blocked": status == "blocked",
        })
    return {"schema": "creator-studio/queue/1", "concurrencyDefault": 1, "jobs": rows}


def work(concurrency=1, once=False, poll=3):
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
