"""Private collector lifecycle evidence; no scheduler or process-management effects."""
from contextlib import closing
import datetime as dt
import hashlib
import os
from pathlib import Path
import sqlite3
import time
import uuid
from . import __version__


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def store_identity(path):
    return hashlib.sha256(os.path.normcase(str(Path(path).resolve())).encode()).hexdigest()[:24]


class CollectorRun:
    def __init__(self, path, heartbeat_seconds=5):
        self.path = Path(path)
        self.identity = uuid.uuid4().hex  # Non-secret run identity, not a credential.
        self.started_at = now()
        self.last_heartbeat = self.started_at
        self.heartbeat_seconds = heartbeat_seconds
        self.next_heartbeat = 0
        self.store_identity = store_identity(path)
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS collector_runs(
                id TEXT PRIMARY KEY, started_at TEXT NOT NULL, last_heartbeat TEXT NOT NULL,
                ended_at TEXT, process_id INTEGER NOT NULL)''')
            db.execute('''CREATE TABLE IF NOT EXISTS collector_gaps(
                run_id TEXT NOT NULL, gap_start TEXT NOT NULL, gap_end TEXT NOT NULL,
                reason TEXT NOT NULL)''')
            db.execute('INSERT INTO collector_runs VALUES(?,?,?,?,?)',
                       (self.identity, self.started_at, self.last_heartbeat, None, os.getpid()))

    def heartbeat(self):
        if time.monotonic() < self.next_heartbeat:
            return
        stamp = now()
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            elapsed = (dt.datetime.fromisoformat(stamp) - dt.datetime.fromisoformat(self.last_heartbeat)).total_seconds()
            if elapsed > max(30, self.heartbeat_seconds * 3):
                db.execute('INSERT INTO collector_gaps VALUES(?,?,?,?)',
                           (self.identity, self.last_heartbeat, stamp, 'collector_heartbeat_gap'))
            db.execute('UPDATE collector_runs SET last_heartbeat=? WHERE id=?', (stamp, self.identity))
        self.last_heartbeat = stamp
        self.next_heartbeat = time.monotonic() + self.heartbeat_seconds

    def health(self):
        return {'service': 'cherry-meter', 'status': 'listening', 'store_identity': self.store_identity,
                'runtime_version': __version__,
                'run_id': self.identity, 'started_at': self.started_at, 'last_heartbeat': self.last_heartbeat,
                'meaning': 'receiver is reachable; this does not prove provider delivery or full coverage'}

    def finish(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute('UPDATE collector_runs SET ended_at=?,last_heartbeat=? WHERE id=?',
                       (now(), self.last_heartbeat, self.identity))


def read_lifecycle(path, stale_seconds=30):
    """Read retained run metadata without creating a store or changing its schema."""
    path = Path(path)
    if not path.is_file():
        return {'status': 'unavailable', 'reason': 'collector_store_missing'}
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='collector_runs'").fetchone()
            if not exists:
                return {'status': 'unknown', 'reason': 'no_collector_lifecycle_observations'}
            rows = db.execute('SELECT id,started_at,last_heartbeat,ended_at FROM collector_runs ORDER BY started_at').fetchall()
            gap_table = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='collector_gaps'").fetchone()
            retained_gaps = db.execute('SELECT gap_start,gap_end,reason FROM collector_gaps ORDER BY gap_start').fetchall() if gap_table else []
    except sqlite3.Error:
        return {'status': 'unavailable', 'reason': 'collector_lifecycle_unreadable'}
    current = dt.datetime.now(dt.timezone.utc)
    runs = []
    gaps = [{'from': start, 'to': end, 'reason': reason} for start, end, reason in retained_gaps]
    previous = None
    for index, (identity, started, heartbeat, ended) in enumerate(rows):
        age = (current - dt.datetime.fromisoformat(heartbeat)).total_seconds()
        state = 'stopped' if ended else 'stale_or_interrupted' if age > stale_seconds else 'recent_heartbeat'
        if ended is None and index < len(rows) - 1:
            state = 'interrupted_without_shutdown'
        runs.append({'run_id': identity, 'started_at': started, 'last_heartbeat': heartbeat,
                     'ended_at': ended, 'status': state})
        if previous:
            boundary = previous[3] or previous[2]
            if boundary < started:
                gaps.append({'from': boundary, 'to': started,
                             'reason': 'collector_unobserved_between_runs; delayed exports may recover some usage'})
        previous = (identity, started, heartbeat, ended)
    return {'status': runs[-1]['status'] if runs else 'unknown', 'runs': runs, 'gaps': gaps,
            'qualification': 'A heartbeat shows collector activity, not continuous source or export delivery.'}
