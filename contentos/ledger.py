"""SQLite run ledger: every stage execution is one row."""
import contextlib
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
CREATE TABLE IF NOT EXISTS approvals(content_id TEXT, gate TEXT, by TEXT, at REAL, note TEXT, subject_sha256 TEXT);
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
    _migrate(c, ws)
    return c


def _migrate(c, ws):
    """Additive only: a ledger written before approvals were bound to content gets a nullable subject_sha256 column.
    The file is copied to <workspace>/recovery/migrations/ first, once, so the pre-migration ledger is always recoverable."""
    if any(r[1] == "subject_sha256" for r in c.execute("PRAGMA table_info(approvals)")):
        return
    dest = ws / "recovery" / "migrations"
    dest.mkdir(parents=True, exist_ok=True)
    with contextlib.closing(sqlite3.connect(dest / f"ledger-{time.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}.db")) as bak:
        c.backup(bak)
    try:
        c.execute("ALTER TABLE approvals ADD COLUMN subject_sha256 TEXT")
        c.commit()
    except sqlite3.OperationalError:                          # another process migrated between the check and the ALTER
        if not any(r[1] == "subject_sha256" for r in c.execute("PRAGMA table_info(approvals)")):
            raise


def new_run_id():
    return uuid.uuid4().hex[:12]


def record(run_id, content_id, stage, provider, status, start, artifacts=(), error="", cash_cost=0.0, target="mac", retries=0):
    with db() as c:
        if status != "RUNNING":   # the in-flight marker is replaced by the final row
            c.execute("DELETE FROM runs WHERE run_id=? AND stage=? AND status='RUNNING'", (run_id, stage))
        c.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (run_id, content_id, stage, provider, target, start, time.time(), status, cash_cost,
                   json.dumps([str(a) for a in artifacts]), error, retries))


def approve(content_id, gate, by="human", note="", subject_sha256=None):
    """Record a grant. subject_sha256 is the digest of the artifact the human reviewed; None is an unbound (legacy-style) grant."""
    with db() as c:
        c.execute("INSERT INTO approvals(content_id,gate,by,at,note,subject_sha256) VALUES (?,?,?,?,?,?)",
                  (content_id, gate, by, time.time(), note, subject_sha256))


def check_gate(content_id, gate, current):
    """Is this gate granted for the content as it is now? Returns (state, approved_digests).
    none: never granted. ok: a grant matches `current`. unbound: only grants with no digest exist (legacy rows, still valid).
    mismatch: digest-bound grants exist but none covers `current`; an unbound row never rescues that."""
    digests = [r[0] for r in db().execute("SELECT subject_sha256 FROM approvals WHERE content_id=? AND gate=? ORDER BY at", (content_id, gate))]
    if not digests:
        return "none", []
    bound = [x for x in digests if x]
    if current is not None and current in bound:
        return "ok", bound
    return ("unbound", []) if not bound else ("mismatch", bound)


def approved(content_id, gate):
    return db().execute("SELECT 1 FROM approvals WHERE content_id=? AND gate=?", (content_id, gate)).fetchone() is not None


def recent(n=15):
    return db().execute("SELECT run_id,content_id,stage,provider,status,round(end-start,1),error FROM runs ORDER BY end DESC LIMIT ?", (n,)).fetchall()
