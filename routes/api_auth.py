from flask import Blueprint, jsonify, request, session
from security_service import security_manager
import hmac
import os
import time
from urllib.parse import urlsplit

auth_bp = Blueprint("api_auth", __name__)

ADMIN_USER_ID = "admin-123"
ADMIN_USERNAME = "CinemaAdmin"
CURRENT_OTT = None
CURRENT_OTT_EXPIRES_AT = 0.0
DEFAULT_OTT_TTL_SECONDS = 120
IDLE_LOCK_SECONDS = max(300, int(os.environ.get("CINEMA_IDLE_LOCK_SECONDS", "900")))


def _is_local_request():
    return request.remote_addr in ["127.0.0.1", "::1", "localhost"]


def _bootstrap_token():
    return request.headers.get("X-Cinema-Bootstrap") or request.args.get("token")


def is_token_valid(token):
    if not token or not CURRENT_OTT or time.time() >= CURRENT_OTT_EXPIRES_AT:
        return False
    return hmac.compare_digest(str(token), str(CURRENT_OTT))


def _consume_token():
    global CURRENT_OTT, CURRENT_OTT_EXPIRES_AT
    CURRENT_OTT = None
    CURRENT_OTT_EXPIRES_AT = 0.0


def _session_can_authenticate_remote():
    return bool(session.get("authenticated"))


def _mark_session_authenticated(device=None, remember=True):
    session.clear()
    session["authenticated"] = True
    session["locked"] = False
    session["last_activity"] = time.time()
    if isinstance(device, dict) and device.get("device_id"):
        session["credential_device_id"] = device["device_id"]
    session.permanent = bool(remember)


def get_origin():
    if _is_local_request():
        proto = request.headers.get("X-Forwarded-Proto", request.scheme)
        host = request.headers.get("X-Forwarded-Host", request.host)
    else:
        proto = request.scheme
        host = request.host

    proto = "https" if proto == "https" else "http"
    host = host.split(",")[0].strip()
    parsed = urlsplit(f"{proto}://{host}")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid request host")

    if hostname == "127.0.0.1":
        hostname = "localhost"
        port = parsed.port
        host = f"localhost:{port}" if port else "localhost"

    if hostname.endswith(".trycloudflare.com"):
        proto = "https"

    return f"{proto}://{host}".rstrip("/")


@auth_bp.route("/api/auth/tunnel/sync", methods=["POST"])
def sync_tunnel():
    global CURRENT_OTT, CURRENT_OTT_EXPIRES_AT
    import routes.api_config as cfg_module

    if not _is_local_request():
        return jsonify({"status": "err", "msg": "Sync allowed only from localhost"}), 403

    data = request.get_json(silent=True) or {}
    token = str(data.get("token") or "")
    tunnel_url = str(data.get("url") or "").rstrip("/")
    if len(token) < 32 or not tunnel_url.startswith("https://"):
        return jsonify({"status": "err", "msg": "Invalid tunnel credentials"}), 400

    ttl = int(os.environ.get("CINEMA_OTT_TTL_SECONDS", DEFAULT_OTT_TTL_SECONDS))
    ttl = max(60, min(ttl, 300))
    cfg_module.TUNNEL_URL = tunnel_url
    CURRENT_OTT = token
    CURRENT_OTT_EXPIRES_AT = time.time() + ttl
    return jsonify({"status": "ok", "expires_in": ttl})


@auth_bp.route("/api/auth/tunnel/info")
def get_tunnel_info():
    from .api_config import TUNNEL_URL

    active = bool(CURRENT_OTT and time.time() < CURRENT_OTT_EXPIRES_AT)
    base = (TUNNEL_URL or "").rstrip("/")
    return jsonify({
        "url": base or None,
        "token_active": active,
        "expires_at": CURRENT_OTT_EXPIRES_AT if active else None,
        "login_url": f"{base}/login#t={CURRENT_OTT}" if base and active else None,
        "register_url": f"{base}/register_security#t={CURRENT_OTT}" if base and active else None,
    })


@auth_bp.route("/api/auth/register/options")
def register_options():
    try:
        origin = get_origin()
        token_req = _bootstrap_token()
        if not _is_local_request() and not is_token_valid(token_req) and not session.get("authenticated"):
            return jsonify({"status": "err", "msg": "Unauthorized registration"}), 403
        return jsonify(security_manager.get_registration_options(ADMIN_USER_ID, ADMIN_USERNAME, origin))
    except Exception as e:
        return jsonify({"status": "err", "msg": str(e)}), 500


@auth_bp.route("/api/auth/register/verify", methods=["POST"])
def register_verify():
    try:
        origin = get_origin()
        token_req = _bootstrap_token()
        remote_bootstrap = not _is_local_request() and is_token_valid(token_req)
        if not _is_local_request() and not remote_bootstrap and not session.get("authenticated"):
            return jsonify({"status": "err", "msg": "Unauthorized registration"}), 403

        data = request.get_json(silent=True) or {}
        credential = data.get("credential", data)
        result = security_manager.verify_registration(
            ADMIN_USER_ID,
            origin,
            credential,
            data.get("challenge_id"),
            data.get("device_name") or request.headers.get("User-Agent", "Thiết bị mới"),
        )
        _mark_session_authenticated(result, remember=True)
        if remote_bootstrap:
            _consume_token()
        return jsonify({"status": "ok", "device": result})
    except Exception as e:
        return jsonify({"status": "err", "msg": str(e)}), 400


@auth_bp.route("/api/auth/login/options")
def login_options():
    try:
        origin = get_origin()
        token_req = _bootstrap_token()
        if not _is_local_request() and not is_token_valid(token_req) and not _session_can_authenticate_remote():
            return jsonify({"status": "err", "msg": "Link xác thực không hợp lệ hoặc đã hết hạn"}), 403
        return jsonify(security_manager.get_authentication_options(ADMIN_USER_ID, origin))
    except Exception as e:
        return jsonify({"status": "err", "msg": str(e)}), 400


@auth_bp.route("/api/auth/login/verify", methods=["POST"])
def login_verify():
    try:
        origin = get_origin()
        token_req = _bootstrap_token()
        is_local = _is_local_request()
        remote_bootstrap = not is_local and is_token_valid(token_req)
        if not is_local and not remote_bootstrap and not _session_can_authenticate_remote():
            return jsonify({"status": "err", "msg": "Link xác thực không hợp lệ hoặc đã hết hạn"}), 403

        data = request.get_json(silent=True) or {}
        credential = data.get("credential", data)
        result = security_manager.verify_authentication(
            ADMIN_USER_ID,
            origin,
            credential,
            data.get("challenge_id"),
        )
        if not isinstance(result, dict):
            result = {}
        _mark_session_authenticated(result, remember=data.get("remember", True))
        if remote_bootstrap:
            _consume_token()
        return jsonify({"status": "ok", "device": result})
    except Exception as e:
        return jsonify({"status": "err", "msg": str(e)}), 400


@auth_bp.route("/api/auth/status")
def auth_status():
    authenticated = bool(session.get("authenticated"))
    locked = bool(session.get("locked"))
    last_activity = float(session.get("last_activity") or 0)
    idle_for = max(0, time.time() - last_activity) if last_activity else 0
    if authenticated and not locked and last_activity and idle_for >= IDLE_LOCK_SECONDS:
        session["locked"] = True
        locked = True

    return jsonify({
        "authenticated": authenticated,
        "locked": locked,
        "idle_lock_seconds": IDLE_LOCK_SECONDS,
        "idle_remaining": max(0, int(IDLE_LOCK_SECONDS - idle_for)) if authenticated and not locked else 0,
    })


@auth_bp.route("/api/auth/activity", methods=["POST"])
def auth_activity():
    if not session.get("authenticated") or session.get("locked"):
        return jsonify({"status": "err", "msg": "Locked"}), 401
    session["last_activity"] = time.time()
    return jsonify({"status": "ok"})


@auth_bp.route("/api/auth/lock", methods=["POST"])
def lock():
    if not session.get("authenticated"):
        return jsonify({"status": "err", "msg": "Unauthorized"}), 401
    session["locked"] = True
    return jsonify({"status": "ok"})


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "ok"})


@auth_bp.route("/api/auth/devices")
def devices():
    if not session.get("authenticated") or session.get("locked"):
        return jsonify({"status": "err", "msg": "Unauthorized"}), 401
    current_id = session.get("credential_device_id")
    items = security_manager.list_devices(ADMIN_USER_ID)
    for item in items:
        item["current"] = item.get("device_id") == current_id
    return jsonify({"status": "ok", "devices": items})


@auth_bp.route("/api/auth/devices/<device_id>", methods=["PATCH"])
def rename_device(device_id):
    if not session.get("authenticated") or session.get("locked"):
        return jsonify({"status": "err", "msg": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    try:
        name = security_manager.rename_device(ADMIN_USER_ID, device_id, data.get("device_name"))
        return jsonify({"status": "ok", "device_name": name})
    except ValueError as e:
        return jsonify({"status": "err", "msg": str(e)}), 404


@auth_bp.route("/api/auth/devices/<device_id>", methods=["DELETE"])
def revoke_device(device_id):
    if not session.get("authenticated") or session.get("locked"):
        return jsonify({"status": "err", "msg": "Unauthorized"}), 401
    if session.get("credential_device_id") == device_id:
        return jsonify({"status": "err", "msg": "Không thể thu hồi thiết bị đang dùng"}), 409
    try:
        security_manager.revoke_device(ADMIN_USER_ID, device_id)
        return jsonify({"status": "ok"})
    except ValueError as e:
        return jsonify({"status": "err", "msg": str(e)}), 409
