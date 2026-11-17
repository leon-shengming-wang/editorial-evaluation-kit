"""Append-only SQLite review history for local calibration exercises.

Initial labels are authored reference decisions, not independent human ratings.
The store is not tamper-proof: a person with filesystem access can edit it.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from .core import validate

SCHEMA = '''
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS cases (
 id TEXT PRIMARY KEY,
 category TEXT NOT NULL,
 payload TEXT NOT NULL,
 sha256 TEXT NOT NULL,
 reference_winner TEXT NOT NULL CHECK(reference_winner IN ('A','B','tie','abstain'))
);
CREATE TABLE IF NOT EXISTS reviews (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
 case_id TEXT NOT NULL REFERENCES cases(id),
 reviewer TEXT NOT NULL,
 winner TEXT NOT NULL CHECK(winner IN ('A','B','tie','abstain')),
 reason TEXT NOT NULL,
 recorded_at TEXT NOT NULL
);
CREATE VIEW IF NOT EXISTS latest_reviews AS
 SELECT r.* FROM reviews r
 WHERE r.sequence = (SELECT MAX(newer.sequence) FROM reviews newer
 WHERE newer.case_id = r.case_id AND newer.reviewer = r.reviewer);
'''

class AuditStore:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.executescript(SCHEMA)
    def close(self): self.connection.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def import_cases(self, records):
        """Atomic import; reject changed payloads under an existing case ID."""
        with self.connection:
            for record in records:
                errors = validate(record)
                if errors: raise ValueError('; '.join(errors))
                payload = json.dumps(record, sort_keys=True, separators=(',', ':'))
                digest = hashlib.sha256(payload.encode()).hexdigest()
                previous = self.connection.execute('SELECT sha256 FROM cases WHERE id=?', (record['id'],)).fetchone()
                if previous:
                    if previous[0] != digest: raise ValueError('case changed under existing id: ' + record['id'])
                    continue
                self.connection.execute('INSERT INTO cases VALUES (?,?,?,?,?)',
                    (record['id'], record['category'], payload, digest, record['winner']))
    def add_review(self, case_id, reviewer, winner, reason):
        """Record a new decision; prior judgments remain available."""
        if winner not in ('A','B','tie','abstain'): raise ValueError('invalid winner')
        for label, value in (('case_id',case_id),('reviewer',reviewer),('reason',reason)):
            if not isinstance(value,str) or not value.strip(): raise ValueError(label + ' must be nonempty text')
        now = datetime.now(timezone.utc).isoformat(timespec='microseconds')
        with self.connection:
            cursor = self.connection.execute('INSERT INTO reviews(case_id,reviewer,winner,reason,recorded_at) VALUES (?,?,?,?,?)',
                (case_id, reviewer.strip(), winner, reason.strip(), now))
        return cursor.lastrowid
    def history(self, case_id):
        return self.connection.execute('SELECT sequence,reviewer,winner,reason,recorded_at FROM reviews WHERE case_id=? ORDER BY sequence', (case_id,)).fetchall()
    def disagreements(self):
        """Latest judgments differing from authored references; not accuracy."""
        return self.connection.execute('''SELECT r.case_id,r.reviewer,c.reference_winner,r.winner,r.reason
            FROM latest_reviews r JOIN cases c ON c.id=r.case_id
            WHERE r.winner != c.reference_winner ORDER BY r.case_id,r.reviewer''').fetchall()
