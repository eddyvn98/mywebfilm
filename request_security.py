from flask import jsonify, redirect, request, url_for
from web_security import (
    ALLOWED_PATH_BASES, SENSITIVE_PATH_BASES, _allowed_host, _safe_next_path,
    _touch_stream_activity, auth_origin, can_register_request,
    get_session_state, is_direct_local_request,
)

def check_auth():
    full_path = request.path
    is_api = full_path.startswith("/api/")

    if not _allowed_host():
        return jsonify({
            "status": "err",
            "msg": "Host not allowed",
        }), 400

    if request.method in {
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    }:
        origin = request.headers.get("Origin")
        if not is_direct_local_request():
            expected = auth_origin()
            if (
                not origin
                or origin.rstrip("/")
                != expected.rstrip("/")
            ):
                return jsonify({
                    "status": "err",
                    "msg": "Cross-origin request blocked",
                }), 403
        elif (
            origin
            and origin.rstrip("/")
            != auth_origin().rstrip("/")
        ):
            return jsonify({
                "status": "err",
                "msg": "Cross-origin request blocked",
            }), 403

    if full_path == "/api/auth/tunnel/sync":
        if is_direct_local_request():
            return
        return jsonify({
            "status": "err",
            "msg": "Sync allowed only from direct localhost",
        }), 403

    if full_path.startswith("/static/img/actors/"):
        actor_record = get_session_state()
        if not actor_record or actor_record.get("locked"):
            return "Unauthorized", 401
        return

    if full_path.startswith("/static/"):
        return
    if any(
        full_path.startswith(path)
        for path in ALLOWED_PATH_BASES
    ):
        return

    record = get_session_state()
    unlocked = bool(
        record
        and not record.get("locked")
    )

    if (
        unlocked
        and full_path.startswith("/api/stream")
    ):
        _touch_stream_activity(record)

    if any(
        full_path.startswith(path)
        for path in SENSITIVE_PATH_BASES
    ):
        if can_register_request():
            return
        if is_api:
            return jsonify({
                "status": "err",
                "msg": "Unauthorized",
            }), 401
        return redirect(
            url_for("views.login")
        )

    if unlocked:
        return

    if record and record.get("locked"):
        if is_api:
            return jsonify({
                "status": "err",
                "msg": "Locked",
                "code": "LOCKED",
            }), 423
        return redirect(
            url_for(
                "views.login",
                locked="1",
                next=_safe_next_path(),
            )
        )

    if is_api:
        return jsonify({
            "status": "err",
            "msg": "Unauthorized",
        }), 401

    if request.host.startswith("127.0.0.1"):
        return redirect(
            request.url.replace(
                "127.0.0.1",
                "localhost",
                1,
            )
        )

    return redirect(
        url_for(
            "views.login",
            next=_safe_next_path(),
        )
    )
