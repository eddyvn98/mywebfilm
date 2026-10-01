from flask import Blueprint, jsonify, request, session
from security_service import security_manager
import hmac
import os
import secrets
import threading
import time
from urllib.parse import urlsplit

import runtime_db

auth_bp = Blueprint("api_auth", __name__)

ADMIN_USER_ID = "admin-123"
ADMIN_USERNAME = "CinemaAdmin"
CURRENT_OTT = None
CURRENT_OTT_EXPIRES_AT = 0.0
DEFAULT_OTT_TTL_SECONDS = 120
IDLE_LOCK_SECONDS = max(
    300,
    int(os.environ.get("CINEMA_IDLE_LOCK_SECONDS", "900")),
)
REMEMBER_SESSION_SECONDS = 7 * 24 * 60 * 60
SHORT_SESSION_SECONDS = 12 * 60 * 60
RATE_WINDOW_SECONDS = 60
_RATE_LIMITS = {
    "login_options": 12,
    "login_verify": 12,
    "register_options": 6,
    "register_verify": 6,
    "bootstrap": 6,
}
_rate_lock = threading.RLock()
_rate_buckets = {}


def _is_loopback_peer():
    return request.remote_addr in {"127.0.0.1", "::1", "localhost"}


def _host_name(value=None):
    raw = value or request.host or ""
    try:
        return (urlsplit("//" + raw).hostname or "").lower()
    except Exception:
        return ""


def is_direct_local_request():
    if not _is_loopback_peer():
        return False
    if _host_name() not in {"localhost", "127.0.0.1", "::1"}:
        return False
    if request.headers.get("CF-Connecting-IP"):
        return False
    forwarded_host = request.headers.get("X-Forwarded-Host")
    if forwarded_host:
        forwarded = forwarded_host.split(",")[0].strip()
        if _host_name(forwarded) not in {"localhost", "127.0.0.1", "::1"}:
            return False
    return True


def _client_identity():
    cf_ip = request.headers.get("CF-Connecting-IP", "").strip()
    if cf_ip and not is_direct_local_request():
        return cf_ip[:80]
    return str(request.remote_addr or "unknown")[:80]


def _check_rate_limit(action):
    limit = _RATE_LIMITS.get(action)
    if not limit or is_direct_local_request():
        return None

    now = time.time()
    key = (action, _client_identity())
    with _rate_lock:
        cutoff = now - RATE_WINDOW_SECONDS
        timestamps = [
            ts for ts in _rate_buckets.get(key, [])
            if ts > cutoff
        ]
        if len(timestamps) >= limit:
            retry_after = max(
                1,
                int(RATE_WINDOW_SECONDS - (now - timestamps[0])),
            )
            _rate_buckets[key] = timestamps
            return retry_after
        timestamps.append(now)
        _rate_buckets[key] = timestamps

        if len(_rate_buckets) > 2048:
            stale_keys = [
                bucket_key
                for bucket_key, values in _rate_buckets.items()
                if not values or values[-1] <= cutoff
            ]
            for stale_key in stale_keys[:1024]:
                _rate_buckets.pop(stale_key, None)
    return None


def _rate_limited(action):
    retry_after = _check_rate_limit(action)
    if retry_after is None:
        return None
    response = jsonify({
        "status": "err",
        "msg": "Quá nhiều yêu cầu xác thực. Hãy thử lại sau.",
    })
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response


def _bootstrap_token():
    return (
        request.headers.get("X-Cinema-Bootstrap")
        or request.args.get("token")
    )


def is_token_valid(token):
    if (
        not token
        or not CURRENT_OTT
        or time.time() >= CURRENT_OTT_EXPIRES_AT
    ):
        return False
    return hmac.compare_digest(str(token), str(CURRENT_OTT))


def _consume_token():
    global CURRENT_OTT, CURRENT_OTT_EXPIRES_AT
    CURRENT_OTT = None
    CURRENT_OTT_EXPIRES_AT = 0.0


def _mint_token(ttl=None):
    global CURRENT_OTT, CURRENT_OTT_EXPIRES_AT
    ttl = ttl or int(
        os.environ.get(
            "CINEMA_OTT_TTL_SECONDS",
            DEFAULT_OTT_TTL_SECONDS,
        )
    )
    ttl = max(60, min(int(ttl), 300))
    CURRENT_OTT = os.urandom(24).hex()
    CURRENT_OTT_EXPIRES_AT = time.time() + ttl
    return CURRENT_OTT, ttl


def _server_session_record():
    sid = session.get("security_session_id")
    record = runtime_db.get_security_session(sid)
    if not record:
        return None

    now = time.time()
    if record.get("revoked_at") is not None:
        return None
    if float(record.get("expires_at") or 0) <= now:
        return None

    device_id = record.get("device_id")
    if device_id and not security_manager.has_device(
        ADMIN_USER_ID,
        device_id,
    ):
        runtime_db.revoke_security_session(sid, now)
        return None
    return record


def get_session_state():
    record = _server_session_record()
    if not record:
        return None

    now = time.time()
    if (
        not record.get("locked")
        and now - float(record.get("last_activity") or 0)
        >= IDLE_LOCK_SECONDS
    ):
        runtime_db.set_security_session_locked(
            record["session_id"],
            True,
        )
        record["locked"] = 1
    return record


def is_authenticated_unlocked():
    record = get_session_state()
    return bool(record and not record.get("locked"))


def _mark_session_authenticated(device=None, remember=True):
    now = time.time()
    ttl = (
        REMEMBER_SESSION_SECONDS
        if remember
        else SHORT_SESSION_SECONDS
    )
    session_id = secrets.token_urlsafe(32)
    device_id = (
        device.get("device_id")
        if isinstance(device, dict)
        else None
    )
    runtime_db.cleanup_security_sessions(now)
    runtime_db.create_security_session(
        session_id,
        ADMIN_USER_ID,
        device_id,
        now,
        now + ttl,
    )

    session.clear()
    session["authenticated"] = True
    session["security_session_id"] = session_id
    session["credential_device_id"] = device_id
    session.permanent = bool(remember)


def _revoke_current_session():
    sid = session.get("security_session_id")
    runtime_db.revoke_security_session(sid, time.time())
    session.clear()


def can_register_request():
    token_req = _bootstrap_token()
    if is_token_valid(token_req):
        return True
    if is_authenticated_unlocked():
        return True
    return (
        is_direct_local_request()
        and not security_manager.has_credentials(ADMIN_USER_ID)
    )


def get_origin():
    proto = request.scheme
    host = request.host

    if _is_loopback_peer() and not is_direct_local_request():
        proto = request.headers.get(
            "X-Forwarded-Proto",
            proto,
        ).split(",")[0].strip()
        host = request.headers.get(
            "X-Forwarded-Host",
            host,
        ).split(",")[0].strip()

    proto = "https" if proto == "https" else "http"
    parsed = urlsplit(f"{proto}://{host}")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid request host")

    if hostname == "127.0.0.1":
        hostname = "localhost"
        port = parsed.port
        host = (
            f"localhost:{port}"
            if port
            else "localhost"
        )

    if hostname.endswith(".trycloudflare.com"):
        proto = "https"

    return f"{proto}://{host}".rstrip("/")


@auth_bp.route("/api/auth/tunnel/sync", methods=["POST"])
def sync_tunnel():
    global CURRENT_OTT, CURRENT_OTT_EXPIRES_AT
    import routes.api_config as cfg_module

    if not is_direct_local_request():
        return jsonify({
            "status": "err",
            "msg": "Sync allowed only from direct localhost",
        }), 403

    data = request.get_json(silent=True) or {}
    token = str(data.get("token") or "")
    tunnel_url = str(data.get("url") or "").rstrip("/")
    if (
        len(token) < 32
        or not tunnel_url.startswith("https://")
    ):
        return jsonify({
            "status": "err",
            "msg": "Invalid tunnel credentials",
        }), 400

    ttl = int(
        os.environ.get(
            "CINEMA_OTT_TTL_SECONDS",
            DEFAULT_OTT_TTL_SECONDS,
        )
    )
    ttl = max(60, min(ttl, 300))
    cfg_module.TUNNEL_URL = tunnel_url
    CURRENT_OTT = token
    CURRENT_OTT_EXPIRES_AT = time.time() + ttl
    return jsonify({"status": "ok", "expires_in": ttl})


@auth_bp.route("/api/auth/tunnel/info")
def get_tunnel_info():
    from .api_config import TUNNEL_URL

    active = bool(
        CURRENT_OTT
        and time.time() < CURRENT_OTT_EXPIRES_AT
    )
    base = (TUNNEL_URL or "").rstrip("/")
    return jsonify({
        "url": base or None,
        "token_active": active,
        "expires_at": (
            CURRENT_OTT_EXPIRES_AT
            if active
            else None
        ),
        "login_url": (
            f"{base}/login"
            if base
            else None
        ),
    })


@auth_bp.route("/api/auth/bootstrap", methods=["POST"])
def create_bootstrap():
    limited = _rate_limited("bootstrap")
    if limited:
        return limited
    if not is_authenticated_unlocked():
        return jsonify({
            "status": "err",
            "msg": "Unauthorized",
        }), 401

    from .api_config import TUNNEL_URL

    base = (TUNNEL_URL or "").rstrip("/")
    if not base:
        return jsonify({
            "status": "err",
            "msg": "Tunnel chưa sẵn sàng",
        }), 409

    token, ttl = _mint_token()
    return jsonify({
        "status": "ok",
        "expires_in": ttl,
        "register_url": (
            f"{base}/register_security#t={token}"
        ),
        "login_url": f"{base}/login",
    })


@auth_bp.route("/api/auth/register/options")
def register_options():
    limited = _rate_limited("register_options")
    if limited:
        return limited
    try:
        if not can_register_request():
            return jsonify({
                "status": "err",
                "msg": "Unauthorized registration",
            }), 403
        origin = get_origin()
        return jsonify(
            security_manager.get_registration_options(
                ADMIN_USER_ID,
                ADMIN_USERNAME,
                origin,
            )
        )
    except Exception as e:
        return jsonify({
            "status": "err",
            "msg": str(e),
        }), 500


@auth_bp.route(
    "/api/auth/register/verify",
    methods=["POST"],
)
def register_verify():
    limited = _rate_limited("register_verify")
    if limited:
        return limited
    try:
        token_req = _bootstrap_token()
        remote_bootstrap = is_token_valid(token_req)
        if not can_register_request():
            return jsonify({
                "status": "err",
                "msg": "Unauthorized registration",
            }), 403

        origin = get_origin()
        data = request.get_json(silent=True) or {}
        credential = data.get("credential", data)
        result = security_manager.verify_registration(
            ADMIN_USER_ID,
            origin,
            credential,
            data.get("challenge_id"),
            (
                data.get("device_name")
                or request.headers.get(
                    "User-Agent",
                    "Thiết bị mới",
                )
            ),
        )
        _mark_session_authenticated(
            result,
            remember=True,
        )
        if remote_bootstrap:
            _consume_token()
        return jsonify({
            "status": "ok",
            "device": result,
        })
    except Exception as e:
        return jsonify({
            "status": "err",
            "msg": str(e),
        }), 400


@auth_bp.route("/api/auth/login/options")
def login_options():
    limited = _rate_limited("login_options")
    if limited:
        return limited
    try:
        origin = get_origin()
        return jsonify(
            security_manager.get_authentication_options(
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
        origin = get_origin()
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
