from flask import jsonify, request
import time
from . import auth_common as core
from .auth_common import (
    ADMIN_USER_ID, auth_bp, can_register_request, get_origin,
    is_authenticated_unlocked, is_direct_local_request,
    is_recently_authenticated, is_token_valid,
    _bootstrap_token, _consume_token, _mark_session_authenticated,
    _mint_token, _rate_limited,
)

@auth_bp.route("/api/auth/tunnel/sync", methods=["POST"])
def sync_tunnel():
    import routes.api_config as cfg_module

    if not is_direct_local_request():
        return jsonify({
            "status": "err",
            "msg": "Sync allowed only from direct localhost",
        }), 403
    if not core.security_manager.has_credentials(ADMIN_USER_ID):
        return jsonify({
            "status": "err",
            "msg": "Hãy đăng ký Passkey đầu tiên trên localhost trước khi bật Tunnel",
        }), 409

    data = request.get_json(silent=True) or {}
    tunnel_url = str(data.get("url") or "").rstrip("/")
    if not tunnel_url.startswith("https://"):
        return jsonify({
            "status": "err",
            "msg": "Tunnel URL must use HTTPS",
        }), 400

    cfg_module.TUNNEL_URL = tunnel_url
    return jsonify({"status": "ok"})


@auth_bp.route("/api/auth/tunnel/info")
def get_tunnel_info():
    from .api_config import TUNNEL_URL

    active = bool(
        core.CURRENT_OTT
        and time.time() < core.CURRENT_OTT_EXPIRES_AT
    )
    base = (TUNNEL_URL or "").rstrip("/")
    return jsonify({
        "url": base or None,
        "token_active": active,
        "expires_at": (
            core.CURRENT_OTT_EXPIRES_AT
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
    if not is_recently_authenticated():
        return jsonify({
            "status": "err",
            "code": "REAUTH_REQUIRED",
            "msg": "Hãy xác thực lại Passkey trước khi thêm thiết bị",
        }), 428

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
        origin = core.get_origin()
        return jsonify(
            core.security_manager.get_registration_options(
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

        origin = core.get_origin()
        data = request.get_json(silent=True) or {}
        credential = data.get("credential", data)
        result = core.security_manager.verify_registration(
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
