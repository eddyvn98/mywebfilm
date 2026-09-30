from flask import Blueprint, request, jsonify, session
from security_service import security_manager
import hmac
import os
import time
from urllib.parse import urlsplit

auth_bp = Blueprint('api_auth', __name__)

# Security Globals
ADMIN_USER_ID = "admin-123"
ADMIN_USERNAME = "CinemaAdmin"
CURRENT_OTT = None # One-Time Token for QR Login
CURRENT_OTT_EXPIRES_AT = 0.0
DEFAULT_OTT_TTL_SECONDS = 300

def _is_local_request():
    return request.remote_addr in ['127.0.0.1', '::1', 'localhost']

def is_token_valid(token):
    if not token or not CURRENT_OTT or time.time() >= CURRENT_OTT_EXPIRES_AT:
        return False
    return hmac.compare_digest(str(token), str(CURRENT_OTT))

def _consume_token():
    global CURRENT_OTT, CURRENT_OTT_EXPIRES_AT
    CURRENT_OTT = None
    CURRENT_OTT_EXPIRES_AT = 0.0

def get_origin():
    # Trust proxy headers only when the request comes from a local reverse proxy.
    if _is_local_request():
        proto = request.headers.get('X-Forwarded-Proto', request.scheme)
        host = request.headers.get('X-Forwarded-Host', request.host)
    else:
        proto = request.scheme
        host = request.host

    proto = 'https' if proto == 'https' else 'http'
    host = host.split(',')[0].strip()
    parsed = urlsplit(f"{proto}://{host}")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid request host")

    if hostname == '127.0.0.1':
        hostname = 'localhost'
        port = parsed.port
        host = f"localhost:{port}" if port else "localhost"

    if hostname.endswith('.trycloudflare.com'):
        proto = 'https'

    return f"{proto}://{host}".rstrip('/')

@auth_bp.route('/api/auth/tunnel/sync', methods=['POST'])
def sync_tunnel():
    global CURRENT_OTT, CURRENT_OTT_EXPIRES_AT
    from .api_config import TUNNEL_URL
    import routes.api_config as cfg_module
    
    # Restrict synchronization to localhost to prevent token hijack
    is_local = request.remote_addr in ['127.0.0.1', '::1', 'localhost']
    if not is_local:
        return jsonify({"status": "err", "msg": "Sync allowed only from localhost"}), 403
        
    data = request.get_json(silent=True) or {}
    token = str(data.get('token') or '')
    tunnel_url = str(data.get('url') or '')
    if len(token) < 32 or not tunnel_url.startswith("https://"):
        return jsonify({"status": "err", "msg": "Invalid tunnel credentials"}), 400

    ttl = int(os.environ.get("CINEMA_OTT_TTL_SECONDS", DEFAULT_OTT_TTL_SECONDS))
    ttl = max(60, min(ttl, 1800))
    cfg_module.TUNNEL_URL = tunnel_url
    CURRENT_OTT = token
    CURRENT_OTT_EXPIRES_AT = time.time() + ttl
    return jsonify({"status": "ok", "expires_in": ttl})

@auth_bp.route('/api/auth/tunnel/info')
def get_tunnel_info():
    from .api_config import TUNNEL_URL
    return jsonify({
        "url": TUNNEL_URL,
        "token_active": bool(CURRENT_OTT and time.time() < CURRENT_OTT_EXPIRES_AT),
        "expires_at": CURRENT_OTT_EXPIRES_AT if CURRENT_OTT else None
    })
@auth_bp.route('/api/auth/register/options')
def register_options():
    try:
        origin = get_origin()
        token_req = request.args.get('token')
        
        # Security: Allow registration if local OR has valid OTT
        is_local = request.remote_addr in ['127.0.0.1', '::1']
        if not is_local and not is_token_valid(token_req) and not session.get('authenticated'):
            return jsonify({"status": "err", "msg": "Unauthorized registration"}), 403

        return security_manager.get_registration_options(ADMIN_USER_ID, ADMIN_USERNAME, origin)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "err", "msg": str(e)}), 500

@auth_bp.route('/api/auth/register/verify', methods=['POST'])
def register_verify():
    try:
        origin = get_origin()
        token_req = request.args.get('token')
        
        # Security: Allow registration if local OR has valid OTT
        is_local = request.remote_addr in ['127.0.0.1', '::1']
        if not is_local and not is_token_valid(token_req) and not session.get('authenticated'):
            return jsonify({"status": "err", "msg": "Unauthorized registration"}), 403

        # Use get_json() to ensure we pass a dict
        security_manager.verify_registration(ADMIN_USER_ID, origin, request.get_json())
        return jsonify({"status": "ok"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "err", "msg": str(e)}), 500

@auth_bp.route('/api/auth/login/options')
def login_options():
    global CURRENT_OTT
    origin = get_origin()
    token_req = request.args.get('token')
    
    # Validation: If remote, MUST have a valid OTT. If local, optional.
    is_local = request.remote_addr == '127.0.0.1' or request.remote_addr == '::1'
    if not is_local:
        if not CURRENT_OTT or token_req != CURRENT_OTT:
            return jsonify({"status": "err", "msg": "Mã xác thực (Token) không hợp lệ hoặc đã hết hạn"}), 403
    
    try:
        return security_manager.get_authentication_options(ADMIN_USER_ID, origin)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "err", "msg": str(e)}), 500

@auth_bp.route('/api/auth/login/verify', methods=['POST'])
def login_verify():
    try:
        origin = get_origin()
        token_req = request.args.get('token')
        is_local = _is_local_request()
        if not is_local and not is_token_valid(token_req):
            return jsonify({"status": "err", "msg": "Mã xác thực (Token) không hợp lệ hoặc đã hết hạn"}), 403

        # Use get_json() to ensure we pass a dict
        security_manager.verify_authentication(ADMIN_USER_ID, origin, request.get_json())
        session['authenticated'] = True
        if not is_local:
            _consume_token()
        return jsonify({"status": "ok"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "err", "msg": str(e)}), 500

@auth_bp.route('/api/auth/status')
def auth_status():
    return jsonify({"authenticated": session.get('authenticated', False)})

@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('authenticated', None)
    return jsonify({"status": "ok"})
