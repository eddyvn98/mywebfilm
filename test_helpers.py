import secrets
import time

import runtime_db


def authenticate_client(client, *, device_id=None, age_seconds=0):
    now = time.time()
    session_id = "test-" + secrets.token_urlsafe(18)
    created_at = now - max(0, age_seconds)
    runtime_db.create_security_session(
        session_id,
        "admin-123",
        device_id,
        created_at,
        now + 3600,
    )
    with client.session_transaction() as sess:
        sess.clear()
        sess["authenticated"] = True
        sess["security_session_id"] = session_id
        sess["credential_device_id"] = device_id
    return session_id


def set_session_last_activity(session_id, when):
    with runtime_db.db_session() as conn:
        conn.execute(
            """
            UPDATE security_sessions
            SET last_activity = ?
            WHERE session_id = ?
            """,
            (when, session_id),
        )
