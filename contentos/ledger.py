"""SQLite run ledger: every stage execution is one row."""
import json
import sqlite3
import time
import uuid

from . import storage

DDL = """CREATE TABLE IF NOT EXISTS runs(
 run_id TEXT, content_id TEXT, stage TEXT, provider TEXT, target TEXT,
 start REAL, end REAL, status TEXT, cash_cost REAL, artifacts TEXT, error TEXT, retries INT);
CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT, spec TEXT, content_id TEXT, status TEXT, priority INT,
 approve_private INT, pid INT, created REAL, started REAL, finished REAL, error TEXT);
CREATE TABLE IF NOT EXISTS approvals(content_id TEXT, gate TEXT, by TEXT, at REAL, note TEXT);
CREATE TABLE IF NOT EXISTS decisions(id TEXT, type TEXT, subject TEXT, decision TEXT, confidence REAL, source TEXT,
 reasons TEXT, predicted TEXT, actual TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS video_metrics(content_id TEXT, platform TEXT, views INT, ctr REAL, avg_view_pct REAL,
 title TEXT, hook_score REAL, duration REAL, ts REAL);"""


def db():
    ws = storage.workspace_root()
    if not ws.is_dir():
        storage.ensure_dir(ws, "workspace")
    c = sqlite3.connect(ws / "ledger.db")
    c.executescript(DDL)
    return c


def new_run_id():
    return uuid.uuid4().hex[:12]


def record(run_id, content_id, stage, provider, status, start, artifacts=(), error="", cash_cost=0.0, target="mac", retries=0):
    with db() as c:
        if status != "RUNNING":   # the in-flight marker is replaced by the final row
            c.execute("DELETE FROM runs WHERE run_id=? AND stage=? AND status='RUNNING'", (run_id, stage))
        c.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (run_id, content_id, stage, provider, target, start, time.time(), status, cash_cost,
                   json.dumps([str(a) for a in artifacts]), error, retries))


def approve(content_id, gate, by="human", note=""):
    with db() as c:
        c.execute("INSERT INTO approvals VALUES (?,?,?,?,?)", (content_id, gate, by, time.time(), note))


def approved(content_id, gate):
    return db().execute("SELECT 1 FROM approvals WHERE content_id=? AND gate=?", (content_id, gate)).fetchone() is not None


def recent(n=15):
    return db().execute("SELECT run_id,content_id,stage,provider,status,round(end-start,1),error FROM runs ORDER BY end DESC LIMIT ?", (n,)).fetchall()
