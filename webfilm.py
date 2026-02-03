from flask import Flask, session, redirect, url_for, request
import ffmpeg_service as ff
from routes.api_v2 import register_api_v2
from routes.views import views_bp
from routes.api_auth import is_token_valid
from flask import jsonify
from functools import wraps

import os
import threading

# Pre-calculate common paths to avoid url_for overhead on every request
ALLOWED_PATH_BASES = [
    '/api/auth/login/options',
    '/api/auth/login/verify',
    '/api/auth/tunnel/sync',
    '/static/',
    '/login'
]

# Paths allowed for localhost/authenticated/valid-token
SENSITIVE_PATH_BASES = [
    '/register',
    '/api/auth/register/options',
    '/api/auth/register/verify'
]

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = "my-cinema-secret-key-123" # Stable key prevents logout on restart

# Auth Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            # If it's an API call, return 401
            if request.path.startswith('/api/'):
                return jsonify({"status": "err", "msg": "Unauthorized"}), 401
            return redirect(url_for('views.login'))
        return f(*args, **kwargs)
    return decorated_function

# Protect all routes except login and auth APIs
@app.before_request
def check_auth():
    full_path = request.path
    
    # 1. Media Fast-Pass (Stream, Thumbnail, Preview)
    if full_path.startswith(('/api/stream', '/api/thumbnail', '/api/preview', '/static/')):
        return
    
    # 2. Global Allowed Paths (Login, Sync, etc.)
    if any(full_path.startswith(p) for p in ALLOWED_PATH_BASES):
        return
    
    is_api = full_path.startswith('/api/')
    is_localhost = (request.remote_addr in ['127.0.0.1', '::1', 'localhost'])
    is_authenticated = session.get('authenticated')
    
    # 3. Authenticated or Localhost access to Sensitive/General paths
    if is_localhost or is_authenticated:
        if any(full_path.startswith(p) for p in SENSITIVE_PATH_BASES):
            return
        if is_authenticated:
            return
            
    # 4. Token-based access
    token_req = request.args.get('token')
    if token_req and is_token_valid(token_req):
        return

    # 5. Final Protection
    if not is_authenticated:
        if is_api:
            return jsonify({"status": "err", "msg": "Unauthorized"}), 401
        
        if request.host.startswith('127.0.0.1'):
            return redirect(request.url.replace('127.0.0.1', 'localhost', 1))

        return redirect(url_for('views.login', **request.args))

# Register Blueprints
register_api_v2(app)
app.register_blueprint(views_bp)

if __name__ == '__main__':
    if not ff.check_ffmpeg_presence():
        print("CẢNH BÁO: Không tìm thấy lệnh 'ffmpeg' trong PATH hệ thống.")
    
    print("\n" + "-"*30)
    print("MY CINEMA (Mobile Optimized)")
    print("-" * 30 + "\n")
    
    # Run with threaded=True for stream support
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)