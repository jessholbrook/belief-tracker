import sqlite3

from app import db
from app.beliefs import belief_tree
from app.config import settings


def test_init_is_idempotent(test_db):
    db.init_db()
    db.init_db()
    conv = db.create_conversation("t")
    assert db.get_conversation(conv["id"])


def test_migration_adds_api_blocks_to_existing_db(tmp_path, monkeypatch):
    """A database created by the pre-api_blocks schema gets the column added."""
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE conversations (
            id TEXT PRIMARY KEY, title TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE beliefs (
            id TEXT PRIMARY KEY,
            parent_id TEXT REFERENCES beliefs(id) ON DELETE CASCADE,
            statement TEXT NOT NULL, confidence TEXT NOT NULL,
            evidence TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(settings, "db_path", str(path))
    db.init_db()
    db.init_db()  # re-run: migration must be idempotent

    conv = db.create_conversation("t")
    msg = db.add_message(conv["id"], "assistant", "hi", api_blocks='[{"type":"text"}]')
    stored = db.list_messages(conv["id"])[0]
    assert stored["api_blocks"] == '[{"type":"text"}]'
    assert stored["id"] == msg["id"]


def test_message_round_trip_and_cascade(test_db):
    conv = db.create_conversation("chat")
    db.add_message(conv["id"], "user", "hello")
    db.add_message(conv["id"], "assistant", "hi there", api_blocks="[]")
    msgs = db.list_messages(conv["id"])
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["api_blocks"] is None

    db.delete_conversation(conv["id"])
    assert db.list_messages(conv["id"]) == []


def test_set_conversation_title(test_db):
    conv = db.create_conversation("New conversation")
    db.set_conversation_title(conv["id"], "Renamed")
    assert db.get_conversation(conv["id"])["title"] == "Renamed"


def test_belief_tree_nesting_and_cascade(test_db):
    root = db.insert_belief(statement="root", confidence="high")
    child = db.insert_belief(statement="child", confidence="low", parent_id=root["id"])

    tree = belief_tree()
    assert len(tree) == 1
    assert tree[0]["id"] == root["id"]
    assert [c["id"] for c in tree[0]["children"]] == [child["id"]]

    db.delete_belief(root["id"])
    assert belief_tree() == []
    assert db.get_belief(child["id"]) is None
