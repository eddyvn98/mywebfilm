"""
webfilm.py - Main Cinema web application.
"""
from datetime import timedelta
from functools import wraps
import logging
import os
import secrets
import time

from flask import Flask, jsonify, redirect, request, session, url_for

import ffmpeg_service as ff
from logging_config import configure_logging
from routes.api_auth import IDLE_LOCK_SECONDS, is_token_valid
from routes.api_v2 import register_api_v2
from routes.views import views_bp
from startup_checks import run_startup_checks

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CINEMA_DATA_DIR", os.path.join(BASE_DIR, "data"))
configure_logging(DATA_DIR)


def _load_secret_key():
    env_secret = os.environ.get("CINEMA_SECRET_KEY")
    if env_secret:
        return env_secret

    os.makedirs(DATA_DIR, exist_ok=True)
    secret_path = os.path.join(DATA_DIR, "flask_secret.key")
    if os.path.exists(secret_path):
        with open(secret_path, "r", encoding="utf-8") as f:
            existing = f.read().strip()
            if len(existing) >= 32:
                return existing

    new_secret = secrets.token_hex(32)
    tmp_path = secret_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(new_secret)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, secret_path)
    return new_secret


def _env_true(name, default="0"):
    return os.environ.get(name, default).lower() in {"1", "true", "yes", "on"}


def _request_origin():
    proto = request.scheme
    host = request.host
    if request.remote_addr in {"127.0.0.1", "::1", "localhost"}:
        proto = request.headers.get("X-Forwarded-Proto", proto).split(",")[0].strip()
        host = request.headers.get("X-Forwarded-Host", host).split(",")[0].strip()
    return f"{proto}://{host}".rstrip("/")


def _allowed_host():
    configured = [
        item.strip().lower()
        for item in os.environ.get("CINEMA_ALLOWED_HOSTS", "").split(",")
        if item.strip()
    ]
    if not configured:
        return True
    hostname = (request.host.split(":", 1)[0] or "").lower()
    return hostname in configured or hostname in {"localhost", "127.0.0.1", "::1"}


def _safe_next_path():
    path = request.path if request.path.startswith("/") else "/"
    if path.startswith("//"):
        return "/"
    return path


ALLOWED_PATH_BASES = [
    "/api/auth/login/options",
    "/api/auth/login/verify",
    "/api/auth/status",
    "/api/auth/lock",
    "/api/auth/logout",
    "/static/",
    "/login",
]

SENSITIVE_PATH_BASES = [
    "/register",
    "/api/auth/register/options",
    "/api/auth/register/verify",
]

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = _load_secret_key()
app.config.update(
    SESSION_COOKIE_NAME="cinema_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=_env_true("CINEMA_SECURE_COOKIES"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_REFRESH_EACH_REQUEST=False,
)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated") or session.get("locked"):
            if request.path.startswith("/api/"):
                return jsonify({"status": "err", "msg": "Unauthorized"}), 401
            return redirect(url_for("views.login", next=_safe_next_path()))
        return f(*args, **kwargs)

    return decorated_function


@app.before_request
def check_auth():
    full_path = request.path
    is_api = full_path.startswith("/api/")
    is_localhost = request.remote_addr in {"127.0.0.1", "::1", "localhost"}

    if not _allowed_host():
        return jsonify({"status": "err", "msg": "Host not allowed"}), 400

    # Browser CSRF defense for state-changing requests.
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("Origin")
        if origin and origin.rstrip("/") != _request_origin():
            return jsonify({"status": "err", "msg": "Cross-origin request blocked"}), 403

    # Tunnel sync is only callable by the local helper process.
    if full_path == "/api/auth/tunnel/sync":
        if is_localhost:
            return
        return jsonify({"status": "err", "msg": "Sync allowed only from localhost"}), 403

    # Public authentication/static endpoints.
    if full_path.startswith("/static/"):
        return
    if any(full_path.startswith(path) for path in ALLOWED_PATH_BASES):
        return

    is_authenticated = bool(session.get("authenticated"))
    is_locked = bool(session.get("locked"))
    now = time.time()

    # Continuous playback counts as activity; background polling does not.
    if is_authenticated and not is_locked and full_path.startswith("/api/stream"):
        session["last_activity"] = now

    last_activity = float(session.get("last_activity") or 0)
    if is_authenticated and not is_locked and last_activity and now - last_activity >= IDLE_LOCK_SECONDS:
        session["locked"] = True
        is_locked = True

    token_req = request.headers.get("X-Cinema-Bootstrap") or request.args.get("token")
    has_valid_token = bool(token_req and is_token_valid(token_req))

    # Registration bootstrap is local, from an unlocked authenticated session,
    # or from a short-lived one-time bootstrap token.
    if any(full_path.startswith(path) for path in SENSITIVE_PATH_BASES):
        if is_localhost or (is_authenticated and not is_locked) or has_valid_token:
            return
        if is_api:
            return jsonify({"status": "err", "msg": "Unauthorized"}), 401
        return redirect(url_for("views.login"))

    if is_authenticated and not is_locked:
        return

    if is_locked:
        if is_api:
            return jsonify({"status": "err", "msg": "Locked", "code": "LOCKED"}), 423
        return redirect(url_for("views.login", locked="1", next=_safe_next_path()))

    if is_api:
        return jsonify({"status": "err", "msg": "Unauthorized"}), 401

    if request.host.startswith("127.0.0.1"):
        return redirect(request.url.replace("127.0.0.1", "localhost", 1))

    return redirect(url_for("views.login", next=_safe_next_path()))


@app.after_request
def apply_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")

    if request.is_secure or request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip() == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    if request.path.startswith(("/login", "/register_security", "/api/auth/")):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"

    return response


register_api_v2(app)
app.register_blueprint(views_bp)

if __name__ == "__main__":
    from waitress import serve

    checks = run_startup_checks()
    logger = logging.getLogger(__name__)
    logger.info("startup_readiness checks=%s", checks)
    if not checks["ready"]:
        logger.warning("startup_readiness_degraded checks=%s", checks)

    host = os.environ.get("CINEMA_HOST", "0.0.0.0")
    port = int(os.environ.get("CINEMA_PORT", "5000"))
    threads = max(4, int(os.environ.get("CINEMA_THREADS", "8")))

    if host not in {"127.0.0.1", "localhost"} and not app.config["SESSION_COOKIE_SECURE"]:
        logger.warning(
            "Remote binding without Secure cookies. Set CINEMA_SECURE_COOKIES=1 when serving behind HTTPS."
        )

    print("\n" + "-" * 30)
    print(f"MY CINEMA - http://{host}:{port}")
    print("-" * 30 + "\n")
    serve(app, host=host, port=port, threads=threads)
