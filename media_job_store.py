import json
import os
import sqlite3

import runtime_db


def migrate_media_jobs_json(path):
    runtime_db.ensure_schema()
    if not path or not os.path.exists(path):
        return 0
    with runtime_db.db_session() as conn:
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

        now = runtime_db.utc_now()
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
                INSERT INTO media_jobs(
                    path, name, task_type, status, output, error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
    runtime_db.ensure_schema()
    now = runtime_db.utc_now()
    with runtime_db.db_session() as conn:
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
    runtime_db.ensure_schema()
    now = runtime_db.utc_now()
    try:
        with runtime_db.db_session() as conn:
            cur = conn.execute(
                """
                INSERT INTO media_jobs(
                    path, name, task_type, status, created_at, updated_at
                ) VALUES (?, ?, ?, 'pending', ?, ?)
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
    runtime_db.ensure_schema()
    assignments = ["updated_at = ?"]
    values = [runtime_db.utc_now()]
    for column, value in (("status", status), ("output", output), ("error", error)):
        if value is not None:
            assignments.append(f"{column} = ?")
            values.append(value)
    values.append(job_id)
    with runtime_db.db_session() as conn:
        conn.execute(
            f"UPDATE media_jobs SET {', '.join(assignments)} WHERE id = ?",
            values,
        )


def clear_finished_media_jobs():
    runtime_db.ensure_schema()
    with runtime_db.db_session() as conn:
        conn.execute(
            "DELETE FROM media_jobs WHERE status NOT IN ('pending', 'processing')"
        )
