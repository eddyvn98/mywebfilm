from flask import Blueprint, request, jsonify, session
from security_service import security_manager
import uuid

auth_bp = Blueprint('api_auth', __name__)

# Security Globals
ADMIN_USER_ID = "admin-123"
ADMIN_USERNAME = "CinemaAdmin"
CURRENT_OTT = None # One-Time Token for QR Login

def is_token_valid(token):
    return CURRENT_OTT is not None and token == CURRENT_OTT

def get_origin():
    # 1. Determine protocol: Default to http, but trust X-Forwarded-Proto from Cloudflare
    proto = request.headers.get('X-Forwarded-Proto', 'http')
    
    # 2. Determine host: Default to request.host, but trust X-Forwarded-Host
    host = request.headers.get('X-Forwarded-Host', request.host)
    
    # 3. Security: All .trycloudflare.com domains REQUIRE https for WebAuthn
    if 'trycloudflare.com' in host:
        proto = 'https'
        
    # 4. WebAuthn Requirement: RP ID must be a valid domain string.
    # IP addresses like 127.0.0.1 are NOT allowed. Standardize to localhost.
    if host.startswith('127.0.0.1'):
        host = host.replace('127.0.0.1', 'localhost')
        
    origin = f"{proto}://{host}".rstrip('/')
    # Only print if origin changes or periodically to avoid spam
    print(f"[DEBUG] WebAuthn Origin: {origin}")
    return origin

@auth_bp.route('/api/auth/tunnel/sync', methods=['POST'])
def sync_tunnel():
    global CURRENT_OTT
    from .api_config import TUNNEL_URL
    import routes.api_config as cfg_module
    
    # Restrict synchronization to localhost to prevent token hijack
    is_local = request.remote_addr in ['127.0.0.1', '::1', 'localhost']
    if not is_local:
        return jsonify({"status": "err", "msg": "Sync allowed only from localhost"}), 403
        
    data = request.json
    cfg_module.TUNNEL_URL = data.get('url')
    CURRENT_OTT = data.get('token')
    return jsonify({"status": "ok"})

@auth_bp.route('/api/auth/tunnel/info')
def get_tunnel_info():
    from .api_config import TUNNEL_URL
    return jsonify({
        "url": TUNNEL_URL,
        "token": CURRENT_OTT
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
        # Use get_json() to ensure we pass a dict
        security_manager.verify_authentication(ADMIN_USER_ID, origin, request.get_json())
        session['authenticated'] = True
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
