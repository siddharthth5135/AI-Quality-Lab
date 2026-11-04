"""Conversation log store queried with SQL for data validation (Athena-style checks)."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    refused INTEGER NOT NULL,
    refusal_reason TEXT,
    model TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    est_tokens INTEGER NOT NULL,
    created_at TEXT NOT NULL
)
"""


class ConversationLog:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def record(
        self,
        session_id: str,
        question: str,
        answer: str,
        refused: bool,
        refusal_reason: str | None,
        model: str,
        latency_ms: float,
    ) -> None:
        est_tokens = (len(question) + len(answer)) // 4
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations (session_id, question, answer, refused, refusal_reason, "
                "model, latency_ms, est_tokens, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    question,
                    answer,
                    int(refused),
                    refusal_reason,
                    model,
                    latency_ms,
                    est_tokens,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def query(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()
