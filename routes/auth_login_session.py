from flask import jsonify, request
import time
import runtime_db
from . import auth_common as core
from .auth_common import (
    ADMIN_USER_ID, IDLE_LOCK_SECONDS, auth_bp,
    get_session_state, _mark_session_authenticated,
    _rate_limited, _revoke_current_session,
)

@auth_bp.route("/api/auth/login/options")
def login_options():
    limited = _rate_limited("login_options")
    if limited:
        return limited
    try:
        origin = core.get_origin()
        return jsonify(
            core.security_manager.get_authentication_options(
                ADMIN_USER_ID,
                origin,
            )
        )
    except Exception as e:
        return jsonify({
            "status": "err",
            "msg": str(e),
        }), 400


@auth_bp.route(
    "/api/auth/login/verify",
    methods=["POST"],
)
def login_verify():
    limited = _rate_limited("login_verify")
    if limited:
        return limited
    try:
        origin = core.get_origin()
        data = request.get_json(silent=True) or {}
        credential = data.get("credential", data)
        result = core.security_manager.verify_authentication(
            ADMIN_USER_ID,
            origin,
            credential,
            data.get("challenge_id"),
        )
        if not isinstance(result, dict):
            result = {}
        _mark_session_authenticated(
            result,
            remember=data.get("remember", True),
        )
        return jsonify({
            "status": "ok",
            "device": result,
        })
    except Exception as e:
        return jsonify({
            "status": "err",
            "msg": str(e),
        }), 400


@auth_bp.route("/api/auth/status")
def auth_status():
    record = get_session_state()
    if not record:
        return jsonify({
            "authenticated": False,
            "locked": False,
            "idle_lock_seconds": IDLE_LOCK_SECONDS,
            "idle_remaining": 0,
        })

    idle_for = max(
        0,
        time.time()
        - float(record.get("last_activity") or 0),
    )
    locked = bool(record.get("locked"))
    return jsonify({
        "authenticated": True,
        "locked": locked,
        "idle_lock_seconds": IDLE_LOCK_SECONDS,
        "idle_remaining": (
            max(0, int(IDLE_LOCK_SECONDS - idle_for))
            if not locked
            else 0
        ),
    })


@auth_bp.route(
    "/api/auth/activity",
    methods=["POST"],
)
def auth_activity():
    record = get_session_state()
    if not record or record.get("locked"):
        return jsonify({
            "status": "err",
            "msg": "Locked",
        }), 401
    runtime_db.touch_security_session(
        record["session_id"],
        time.time(),
    )
    return jsonify({"status": "ok"})


@auth_bp.route(
    "/api/auth/lock",
    methods=["POST"],
)
def lock():
    record = get_session_state()
    if not record:
        return jsonify({
            "status": "err",
            "msg": "Unauthorized",
        }), 401
    runtime_db.set_security_session_locked(
        record["session_id"],
        True,
    )
    return jsonify({"status": "ok"})


@auth_bp.route(
    "/api/auth/logout",
    methods=["POST"],
)
def logout():
    _revoke_current_session()
    response = jsonify({"status": "ok"})
    response.headers["Clear-Site-Data"] = (
        '"cache", "cookies", "storage"'
    )
    return response
