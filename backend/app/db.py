from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from .config import settings


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(settings.db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def cursor():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with cursor() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role            TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content         TEXT NOT NULL,
                api_blocks      TEXT,
                created_at      TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, created_at);

            CREATE TABLE IF NOT EXISTS beliefs (
                id           TEXT PRIMARY KEY,
                parent_id    TEXT REFERENCES beliefs(id) ON DELETE CASCADE,
                statement    TEXT NOT NULL,
                confidence   TEXT NOT NULL,
                evidence     TEXT NOT NULL DEFAULT '',
                created_at   TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_beliefs_parent ON beliefs(parent_id);
            """
        )
        _migrate(c)


def _migrate(conn: sqlite3.Connection) -> None:
    """Additive migrations for databases created by older schema versions.
    Safe to re-run: each step checks before altering."""
    message_cols = {r[1] for r in conn.execute("PRAGMA table_info(messages)")}
    if "api_blocks" not in message_cols:
        conn.execute("ALTER TABLE messages ADD COLUMN api_blocks TEXT")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def create_conversation(title: str) -> dict:
    cid = new_id("conv")
    ts = now()
    with cursor() as c:
        c.execute(
            "INSERT INTO conversations VALUES (?, ?, ?, ?)",
            (cid, title, ts, ts),
        )
    return {"id": cid, "title": title, "created_at": ts, "updated_at": ts}


def list_conversations() -> list[dict]:
    with cursor() as c:
        rows = c.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_conversation(cid: str) -> dict | None:
    with cursor() as c:
        row = c.execute(
            "SELECT * FROM conversations WHERE id = ?", (cid,)
        ).fetchone()
    return dict(row) if row else None


def delete_conversation(cid: str) -> None:
    with cursor() as c:
        c.execute("DELETE FROM conversations WHERE id = ?", (cid,))


def add_message(
    conversation_id: str, role: str, content: str, api_blocks: str | None = None
) -> dict:
    mid = new_id("msg")
    ts = now()
    with cursor() as c:
        c.execute(
            "INSERT INTO messages (id, conversation_id, role, content, api_blocks, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (mid, conversation_id, role, content, api_blocks, ts),
        )
        c.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (ts, conversation_id),
        )
    return {
        "id": mid,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "api_blocks": api_blocks,
        "created_at": ts,
    }


def set_conversation_title(cid: str, title: str) -> None:
    with cursor() as c:
        c.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, cid))


def list_messages(conversation_id: str) -> list[dict]:
    with cursor() as c:
        rows = c.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
            (conversation_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def insert_belief(
    statement: str,
    confidence: str,
    evidence: str = "",
    parent_id: str | None = None,
) -> dict:
    bid = new_id("bel")
    ts = now()
    with cursor() as c:
        c.execute(
            "INSERT INTO beliefs VALUES (?, ?, ?, ?, ?, ?)",
            (bid, parent_id, statement, confidence, evidence, ts),
        )
    return {
        "id": bid,
        "parent_id": parent_id,
        "statement": statement,
        "confidence": confidence,
        "evidence": evidence,
        "created_at": ts,
    }


def get_belief(bid: str) -> dict | None:
    with cursor() as c:
        row = c.execute("SELECT * FROM beliefs WHERE id = ?", (bid,)).fetchone()
    return dict(row) if row else None


def list_beliefs() -> list[dict]:
    with cursor() as c:
        rows = c.execute(
            "SELECT * FROM beliefs ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_belief(bid: str) -> None:
    with cursor() as c:
        c.execute("DELETE FROM beliefs WHERE id = ?", (bid,))
