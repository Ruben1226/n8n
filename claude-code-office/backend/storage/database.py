"""Persistencia SQLite: entidades, eventos y ajustes (offsets de lectura)."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from ..domain.models import Entity, iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    session_id TEXT,
    status TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0,
    updated_at REAL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_entities_session ON entities(session_id);
CREATE INDEX IF NOT EXISTS ix_entities_updated ON entities(updated_at);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    ts REAL NOT NULL,
    event_type TEXT NOT NULL,
    entity_id TEXT,
    session_id TEXT,
    source TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS ix_events_entity ON events(entity_id, ts);
CREATE INDEX IF NOT EXISTS ix_events_session ON events(session_id, ts);
CREATE INDEX IF NOT EXISTS ix_events_type ON events(event_type);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def public_event(row_data: dict) -> dict:
    d = dict(row_data)
    d["timestamp"] = iso(d.pop("ts", None))
    d.pop("known", None)
    return d


class Database:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def ok(self) -> bool:
        try:
            with self._lock:
                self.conn.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False

    # ---------------------------------------------------------------- events
    def insert_event(self, ev: dict) -> bool:
        """Inserta un evento; False si ya existía (deduplicación por event_id)."""
        data = {k: v for k, v in ev.items() if k != "known"}
        with self._lock:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO events(event_id, ts, event_type, entity_id, session_id, source, data) VALUES (?,?,?,?,?,?,?)",
                (ev["event_id"], ev["ts"], ev["event_type"], ev.get("entity_id"), ev.get("session_id"), ev["source"], json.dumps(data)),
            )
            return cur.rowcount == 1

    def event_exists(self, event_id: str) -> bool:
        with self._lock:
            return self.conn.execute("SELECT 1 FROM events WHERE event_id=?", (event_id,)).fetchone() is not None

    def events(self, *, entity_id: str | None = None, since: float | None = None, event_type: str | None = None, limit: int = 50) -> list[dict]:
        q = "SELECT data FROM events WHERE 1=1"
        args: list = []
        if entity_id:
            q += " AND entity_id=?"
            args.append(entity_id)
        if since is not None:
            q += " AND ts>?"
            args.append(since)
        if event_type:
            q += " AND event_type=?"
            args.append(event_type)
        q += " ORDER BY ts DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self.conn.execute(q, args).fetchall()
        return [public_event(json.loads(r[0])) for r in rows]

    def event_count(self) -> int:
        with self._lock:
            return self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def last_event_ts(self, source: str) -> float | None:
        with self._lock:
            row = self.conn.execute("SELECT MAX(ts) FROM events WHERE source=?", (source,)).fetchone()
        return row[0] if row else None

    # -------------------------------------------------------------- entities
    def save_entities(self, entities: list[Entity]) -> None:
        if not entities:
            return
        with self._lock:
            self.conn.executemany(
                "INSERT INTO entities(id, kind, session_id, status, archived, updated_at, data) VALUES (?,?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET status=excluded.status, archived=excluded.archived, updated_at=excluded.updated_at, data=excluded.data, session_id=excluded.session_id",
                [(e.id, e.kind, e.session_id, e.status, int(e.archived), e.updated_at, json.dumps(e.to_dict())) for e in entities],
            )

    def load_entities(self) -> dict[str, Entity]:
        with self._lock:
            rows = self.conn.execute("SELECT data FROM entities").fetchall()
        out = {}
        for (data,) in rows:
            try:
                e = Entity.from_dict(json.loads(data))
                out[e.id] = e
            except (ValueError, TypeError):
                continue
        return out

    # -------------------------------------------------------------- settings
    def get_setting(self, key: str, default=None):
        with self._lock:
            row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(self, key: str, value) -> None:
        with self._lock:
            self.conn.execute("INSERT INTO settings(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))

    def commit(self) -> None:
        with self._lock:
            self.conn.commit()

    # ------------------------------------------------------------- retention
    def prune(self, before_ts: float) -> int:
        with self._lock:
            n = self.conn.execute("DELETE FROM events WHERE ts<?", (before_ts,)).rowcount
            self.conn.execute("DELETE FROM entities WHERE archived=1 AND updated_at<?", (before_ts,))
            self.conn.commit()
        return n
