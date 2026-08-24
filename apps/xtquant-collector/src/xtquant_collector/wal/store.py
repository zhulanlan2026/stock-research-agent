from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class WalEntry:
    event_id: str
    event_type: str
    payload: dict[str, object]
    status: str
    attempts: int
    created_at: str


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_entry(row: sqlite3.Row) -> WalEntry:
    payload = json.loads(str(row["payload_json"]))
    return WalEntry(
        event_id=str(row["event_id"]),
        event_type=str(row["event_type"]),
        payload=payload,
        status=str(row["status"]),
        attempts=int(row["attempts"]),
        created_at=str(row["created_at"]),
    )


class WalStore:
    """采集器本地 SQLite WAL，用于在推送到后端前做持久化缓冲。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collector_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    sent_at TEXT
                )
                """
            )

    def append(self, event_id: str, event_type: str, payload: dict[str, object]) -> bool:
        created_at = _utcnow_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO collector_outbox
                    (event_id, event_type, payload_json, status, attempts, created_at)
                VALUES (?, ?, ?, 'pending', 0, ?)
                """,
                (event_id, event_type, json.dumps(payload, ensure_ascii=False), created_at),
            )
            return cursor.rowcount == 1

    def list_pending(self, limit: int = 100) -> list[WalEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_id, event_type, payload_json, status, attempts, created_at
                FROM collector_outbox
                WHERE status = 'pending'
                ORDER BY id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def mark_sent(self, event_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE collector_outbox
                SET status = 'sent', sent_at = ?
                WHERE event_id = ? AND status = 'pending'
                """,
                (_utcnow_iso(), event_id),
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn
