import uuid

import runtime_db


def begin_operation(op_type, src_path=None, dst_path=None, detail=None):
    runtime_db.ensure_schema()
    op_id = uuid.uuid4().hex
    now = runtime_db.utc_now()
    with runtime_db.db_session() as conn:
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
    runtime_db.ensure_schema()
    with runtime_db.db_session() as conn:
        if detail is None:
            conn.execute(
                """
                UPDATE operation_journal
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, runtime_db.utc_now(), op_id),
            )
        else:
            conn.execute(
                """
                UPDATE operation_journal
                SET status = ?, detail = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, detail, runtime_db.utc_now(), op_id),
            )


def list_incomplete_operations(limit=50):
    runtime_db.ensure_schema()
    with runtime_db.db_session() as conn:
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
