import sqlite3
from datetime import datetime, timezone

import runtime_db


def _now_ts():
    return datetime.now(timezone.utc).timestamp()


def recover_metadata_jobs():
    runtime_db.ensure_schema()
    with runtime_db.db_session() as conn:
        conn.execute(
            """
            UPDATE metadata_jobs
            SET status = 'pending',
                error = 'Interrupted by application restart',
                next_retry_at = 0,
                updated_at = ?
            WHERE status = 'processing'
            """,
            (runtime_db.utc_now(),),
        )


def enqueue_metadata_job(path, code):
    runtime_db.ensure_schema()
    now = runtime_db.utc_now()
    try:
        with runtime_db.db_session() as conn:
            cur = conn.execute(
                """
                INSERT INTO metadata_jobs(
                    path, code, status, attempts, next_retry_at,
                    error, source, created_at, updated_at
                ) VALUES (?, ?, 'pending', 0, 0, '', '', ?, ?)
                """,
                (path, code, now, now),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        # A completed job may need to run again after the catalog/cache was
        # deliberately cleared. Keep not_found jobs terminal so the periodic
        # monitor does not hammer sources for codes that genuinely do not exist.
        with runtime_db.db_session() as conn:
            cur = conn.execute(
                """
                UPDATE metadata_jobs
                SET status = 'pending',
                    attempts = 0,
                    next_retry_at = 0,
                    error = '',
                    updated_at = ?
                WHERE path = ? AND code = ? AND status = 'completed'
                """,
                (runtime_db.utc_now(), path, code),
            )
            return -1 if cur.rowcount else None


def claim_next_metadata_job():
    runtime_db.ensure_schema()
    now_ts = _now_ts()
    with runtime_db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT id, path, code, attempts
            FROM metadata_jobs
            WHERE status IN ('pending', 'retry')
              AND next_retry_at <= ?
            ORDER BY id
            LIMIT 1
            """,
            (now_ts,),
        ).fetchone()
        if not row:
            return None
        conn.execute(
            """
            UPDATE metadata_jobs
            SET status = 'processing',
                attempts = attempts + 1,
                updated_at = ?
            WHERE id = ?
            """,
            (runtime_db.utc_now(), row["id"]),
        )
        return {
            "id": row["id"],
            "path": row["path"],
            "code": row["code"],
            "attempts": row["attempts"] + 1,
        }


def complete_metadata_job(job_id, source):
    runtime_db.ensure_schema()
    with runtime_db.db_session() as conn:
        conn.execute(
            """
            UPDATE metadata_jobs
            SET status = 'completed',
                source = ?,
                error = '',
                next_retry_at = 0,
                updated_at = ?
            WHERE id = ?
            """,
            (source or "", runtime_db.utc_now(), job_id),
        )


def retry_metadata_job(job_id, error, attempts):
    delay = min(6 * 3600, max(60, 60 * (2 ** min(max(attempts - 1, 0), 8))))
    runtime_db.ensure_schema()
    with runtime_db.db_session() as conn:
        conn.execute(
            """
            UPDATE metadata_jobs
            SET status = 'retry',
                error = ?,
                next_retry_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (str(error)[:1000], _now_ts() + delay, runtime_db.utc_now(), job_id),
        )


def mark_metadata_not_found(job_id, error="movie not found"):
    runtime_db.ensure_schema()
    with runtime_db.db_session() as conn:
        conn.execute(
            """
            UPDATE metadata_jobs
            SET status = 'not_found',
                error = ?,
                next_retry_at = 0,
                updated_at = ?
            WHERE id = ?
            """,
            (str(error)[:1000], runtime_db.utc_now(), job_id),
        )


def metadata_job_counts():
    runtime_db.ensure_schema()
    with runtime_db.db_session() as conn:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM metadata_jobs
            GROUP BY status
            """
        ).fetchall()
    return {row["status"]: row["count"] for row in rows}
