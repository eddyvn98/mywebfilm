from flask import jsonify, request
import time
import runtime_db
from security_service import security_manager
from .auth_common import (
    ADMIN_USER_ID, auth_bp, get_session_state,
    is_recently_authenticated,
)

@auth_bp.route("/api/auth/devices")
def devices():
    record = get_session_state()
    if not record or record.get("locked"):
        return jsonify({
            "status": "err",
            "msg": "Unauthorized",
        }), 401

    current_id = record.get("device_id")
    items = security_manager.list_devices(
        ADMIN_USER_ID
    )
    for item in items:
        item["current"] = (
            item.get("device_id") == current_id
        )
    return jsonify({
        "status": "ok",
        "devices": items,
    })


@auth_bp.route(
    "/api/auth/devices/<device_id>",
    methods=["PATCH"],
)
def rename_device(device_id):
    record = get_session_state()
    if not record or record.get("locked"):
        return jsonify({
            "status": "err",
            "msg": "Unauthorized",
        }), 401
    data = request.get_json(silent=True) or {}
    try:
        name = security_manager.rename_device(
            ADMIN_USER_ID,
            device_id,
            data.get("device_name"),
        )
        return jsonify({
            "status": "ok",
            "device_name": name,
        })
    except ValueError as e:
        return jsonify({
            "status": "err",
            "msg": str(e),
        }), 404


@auth_bp.route(
    "/api/auth/devices/<device_id>",
    methods=["DELETE"],
)
def revoke_device(device_id):
    record = get_session_state()
    if not record or record.get("locked"):
        return jsonify({
            "status": "err",
            "msg": "Unauthorized",
        }), 401
    if record.get("device_id") == device_id:
        return jsonify({
            "status": "err",
            "msg": "Không thể thu hồi thiết bị đang dùng",
        }), 409
    if not is_recently_authenticated():
        return jsonify({
            "status": "err",
            "code": "REAUTH_REQUIRED",
            "msg": "Hãy xác thực lại Passkey trước khi thu hồi thiết bị",
        }), 428

    try:
        security_manager.revoke_device(
            ADMIN_USER_ID,
            device_id,
        )
        runtime_db.revoke_device_sessions(
            device_id,
            time.time(),
        )
        return jsonify({"status": "ok"})
    except ValueError as e:
        return jsonify({
            "status": "err",
            "msg": str(e),
        }), 409
