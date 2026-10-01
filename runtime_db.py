import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CINEMA_DATA_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH = os.path.join(DATA_DIR, "cinema_state.db")

_schema_lock = threading.Lock()
_db_lock = threading.RLock()
_schema_path = None


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _connect():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def database_maintenance():
    with _db_lock:
        yield


@contextmanager
def db_session():
    with _db_lock:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def ensure_schema():
    global _schema_path
    if _schema_path == DB_PATH and os.path.exists(DB_PATH):
        return
    with _schema_lock:
        if _schema_path == DB_PATH and os.path.exists(DB_PATH):
            return
        with db_session() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS list_state (
                    name TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runtime_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS media_catalog (
                    path_key TEXT PRIMARY KEY,
                    full_path TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_media_catalog_position
                ON media_catalog(position);

                CREATE TABLE IF NOT EXISTS media_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_media_jobs_active
                ON media_jobs(path, task_type)
                WHERE status IN ('pending', 'processing');

                CREATE TABLE IF NOT EXISTS operation_journal (
                    id TEXT PRIMARY KEY,
                    op_type TEXT NOT NULL,
                    src_path TEXT,
                    dst_path TEXT,
                    status TEXT NOT NULL,
                    detail TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_operation_journal_status
                ON operation_journal(status, updated_at);

                CREATE TABLE IF NOT EXISTS security_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    device_id TEXT,
                    created_at REAL NOT NULL,
                    last_activity REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    locked INTEGER NOT NULL DEFAULT 0,
                    revoked_at REAL
                );

                CREATE INDEX IF NOT EXISTS idx_security_sessions_device
                ON security_sessions(device_id, revoked_at, expires_at);
                """
            )
        _schema_path = DB_PATH


def _read_legacy_list(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, list) else None
    except Exception:
        return None


def load_list_state(name, legacy_json_path=None):
    ensure_schema()
    with db_session() as conn:
        row = conn.execute(
            "SELECT payload FROM list_state WHERE name = ?",
            (name,),
        ).fetchone()
        if row:
            value = json.loads(row["payload"])
            return value if isinstance(value, list) else []

        legacy = _read_legacy_list(legacy_json_path)
        if legacy is None:
            return []

        now = utc_now()
        conn.execute(
            "INSERT INTO list_state(name, payload, updated_at) VALUES (?, ?, ?)",
            (name, json.dumps(legacy, ensure_ascii=False), now),
        )
        return legacy


def mutate_list_state(name, mutator, legacy_json_path=None):
    """Serialize a read-modify-write list update inside one SQLite write transaction."""
    ensure_schema()
    with db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT payload FROM list_state WHERE name = ?",
            (name,),
        ).fetchone()
        if row:
            items = json.loads(row["payload"])
            if not isinstance(items, list):
                items = []
        else:
            items = _read_legacy_list(legacy_json_path) or []

        updated = mutator(list(items))
        if not isinstance(updated, list):
            raise ValueError("list state mutator must return a list")

        conn.execute(
            """
            INSERT INTO list_state(name, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (name, json.dumps(updated, ensure_ascii=False), utc_now()),
        )
        return updated


def save_list_state(name, items):
    ensure_schema()
    payload = json.dumps(list(items or []), ensure_ascii=False)
    now = utc_now()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO list_state(name, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (name, payload, now),
        )


def create_security_session(session_id, user_id, device_id, created_at, expires_at):
    ensure_schema()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO security_sessions(
                session_id, user_id, device_id, created_at,
                last_activity, expires_at, locked, revoked_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, NULL)
            """,
            (session_id, user_id, device_id, created_at, created_at, expires_at),
        )


def get_security_session(session_id):
    if not session_id:
        return None
    ensure_schema()
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT session_id, user_id, device_id, created_at,
                   last_activity, expires_at, locked, revoked_at
            FROM security_sessions
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def touch_security_session(session_id, when):
    ensure_schema()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE security_sessions
            SET last_activity = ?
            WHERE session_id = ? AND revoked_at IS NULL AND expires_at > ?
            """,
            (when, session_id, when),
        )


def set_security_session_locked(session_id, locked=True):
    ensure_schema()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE security_sessions
            SET locked = ?
            WHERE session_id = ? AND revoked_at IS NULL
            """,
            (1 if locked else 0, session_id),
        )


def revoke_security_session(session_id, when):
    if not session_id:
        return
    ensure_schema()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE security_sessions
            SET revoked_at = COALESCE(revoked_at, ?)
            WHERE session_id = ?
            """,
            (when, session_id),
        )


def revoke_device_sessions(device_id, when):
    if not device_id:
        return
    ensure_schema()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE security_sessions
            SET revoked_at = COALESCE(revoked_at, ?)
            WHERE device_id = ? AND revoked_at IS NULL
            """,
            (when, device_id),
        )


def cleanup_security_sessions(now):
    ensure_schema()
    with db_session() as conn:
        conn.execute(
            """
            DELETE FROM security_sessions
            WHERE expires_at <= ?
               OR (revoked_at IS NOT NULL AND revoked_at <= ?)
            """,
            (now - 86400, now - 7 * 86400),
        )


def revoke_all_security_sessions(when):
    ensure_schema()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE security_sessions
            SET revoked_at = COALESCE(revoked_at, ?)
            WHERE revoked_at IS NULL
            """,
            (when,),
        )
