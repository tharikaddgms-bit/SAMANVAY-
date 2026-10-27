import sqlite3
import os
from pathlib import Path
from typing import Generator, Any, Dict, List, Optional
from contextlib import contextmanager

from app.core.config import DATABASE_PATH, BASE_DIR
from app.services.audit_ledger import GENESIS_HASH, create_audit_entry_payload

SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initializes tables using schema.sql."""
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        ddl = f.read()

    with get_db() as conn:
        conn.executescript(ddl)

def get_latest_audit_hash(conn: sqlite3.Connection) -> str:
    """Retrieves entry_hash of the latest audit record, or GENESIS_HASH if none exists."""
    cursor = conn.cursor()
    cursor.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()
    if row and row["entry_hash"]:
        return row["entry_hash"]
    return GENESIS_HASH

def record_audit_event(
    conn: sqlite3.Connection,
    actor_id: str,
    actor_role: str,
    action_type: str,
    record_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Appends an event to the audit ledger while preserving cryptographic hash chaining.
    """
    prev_hash = get_latest_audit_hash(conn)
    payload = create_audit_entry_payload(
        previous_hash=prev_hash,
        actor_id=actor_id,
        actor_role=actor_role,
        action_type=action_type,
        record_id=record_id,
        details=details,
    )
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO audit_log (timestamp, actor_id, actor_role, action_type, record_id, details_json, previous_hash, entry_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            payload["timestamp"],
            payload["actor_id"],
            payload["actor_role"],
            payload["action_type"],
            payload["record_id"],
            payload["details_json"],
            payload["previous_hash"],
            payload["entry_hash"],
        ),
    )
    return cursor.lastrowid
