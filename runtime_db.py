import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CINEMA_DATA_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH = os.path.join(DATA_DIR, "cinema_state.db")

_schema_lock = threading.Lock()
_schema_path = None


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _connect():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_schema():
    global _schema_path
    if _schema_path == DB_PATH and os.path.exists(DB_PATH):
        return
    with _schema_lock:
        if _schema_path == DB_PATH and os.path.exists(DB_PATH):
            return
        with _connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS list_state (
                    name TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

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
    with _connect() as conn:
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

        now = _utc_now()
        conn.execute(
            "INSERT INTO list_state(name, payload, updated_at) VALUES (?, ?, ?)",
            (name, json.dumps(legacy, ensure_ascii=False), now),
        )
        return legacy


def mutate_list_state(name, mutator, legacy_json_path=None):
    """Serialize a read-modify-write list update inside one SQLite write transaction."""
    ensure_schema()
    conn = _connect()
    try:
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
            (name, json.dumps(updated, ensure_ascii=False), _utc_now()),
        )
        conn.commit()
        return updated
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_list_state(name, items):
    ensure_schema()
    payload = json.dumps(list(items or []), ensure_ascii=False)
    now = _utc_now()
    with _connect() as conn:
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


def migrate_media_jobs_json(path):
    ensure_schema()
    if not path or not os.path.exists(path):
        return 0
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM media_jobs").fetchone()[0]
        if count:
            return 0
        try:
            with open(path, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            return 0
        if not isinstance(items, list):
            return 0

        now = _utc_now()
        inserted = 0
        for item in items:
            if not isinstance(item, dict) or not item.get("path"):
                continue
            status = item.get("status", "failed")
            if status in {"pending", "processing"}:
                status = "failed"
                item["error"] = "Interrupted by application restart"
            conn.execute(
                """
                INSERT INTO media_jobs(path, name, task_type, status, output, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["path"],
                    item.get("name") or os.path.basename(item["path"]),
                    item.get("type") or "highlight",
                    status,
                    item.get("output"),
                    item.get("error"),
                    now,
                    now,
                ),
            )
            inserted += 1
        return inserted


def load_media_jobs():
    ensure_schema()
    now = _utc_now()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE media_jobs
            SET status = 'failed',
                error = 'Interrupted by application restart',
                updated_at = ?
            WHERE status IN ('pending', 'processing')
            """,
            (now,),
        )
        rows = conn.execute(
            """
            SELECT id, path, name, task_type, status, output, error
            FROM media_jobs
            ORDER BY id
            """
        ).fetchall()
    return [
        {
            "id": row["id"],
            "path": row["path"],
            "name": row["name"],
            "type": row["task_type"],
            "status": row["status"],
            "output": row["output"],
            "error": row["error"],
        }
        for row in rows
    ]


def add_media_job(path, name, task_type):
    ensure_schema()
    now = _utc_now()
    try:
        with _connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO media_jobs(path, name, task_type, status, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?)
                """,
                (path, name, task_type, now, now),
            )
            return {
                "id": cur.lastrowid,
                "path": path,
                "name": name,
                "type": task_type,
                "status": "pending",
                "output": None,
                "error": None,
            }
    except sqlite3.IntegrityError:
        return None


def update_media_job(job_id, *, status=None, output=None, error=None):
    ensure_schema()
    assignments = ["updated_at = ?"]
    values = [_utc_now()]
    for column, value in (("status", status), ("output", output), ("error", error)):
        if value is not None:
            assignments.append(f"{column} = ?")
            values.append(value)
    values.append(job_id)
    with _connect() as conn:
        conn.execute(
            f"UPDATE media_jobs SET {', '.join(assignments)} WHERE id = ?",
            values,
        )


def clear_finished_media_jobs():
    ensure_schema()
    with _connect() as conn:
        conn.execute(
            "DELETE FROM media_jobs WHERE status NOT IN ('pending', 'processing')"
        )


def begin_operation(op_type, src_path=None, dst_path=None, detail=None):
    ensure_schema()
    op_id = uuid.uuid4().hex
    now = _utc_now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO operation_journal(
                id, op_type, src_path, dst_path, status, detail, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'prepared', ?, ?, ?)
            """,
            (op_id, op_type, src_path, dst_path, detail, now, now),
        )
    return op_id


def update_operation(op_id, status, detail=None):
    ensure_schema()
    with _connect() as conn:
        if detail is None:
            conn.execute(
                "UPDATE operation_journal SET status = ?, updated_at = ? WHERE id = ?",
                (status, _utc_now(), op_id),
            )
        else:
            conn.execute(
                """
                UPDATE operation_journal
                SET status = ?, detail = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, detail, _utc_now(), op_id),
            )


def list_incomplete_operations(limit=50):
    ensure_schema()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, op_type, src_path, dst_path, status, detail, created_at, updated_at
            FROM operation_journal
            WHERE status != 'completed'
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 200)),),
        ).fetchall()
    return [dict(row) for row in rows]
