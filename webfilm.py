"""
webfilm.py - Main Cinema web application.
"""
from datetime import timedelta
from functools import wraps
import logging
import os
import secrets
from urllib.parse import urlsplit

from flask import Flask, jsonify, redirect, request, url_for

import ffmpeg_service as ff
from logging_config import configure_logging
from routes.api_auth import (
    can_register_request,
    get_origin as auth_origin,
    get_session_state,
    is_direct_local_request,
)
from routes.api_v2 import register_api_v2
from routes.views import views_bp
from startup_checks import run_startup_checks
import runtime_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get(
    "CINEMA_DATA_DIR",
    os.path.join(BASE_DIR, "data"),
)
configure_logging(DATA_DIR)


def _load_secret_key():
    env_secret = os.environ.get("CINEMA_SECRET_KEY")
    if env_secret:
        if len(env_secret) < 32:
            raise RuntimeError(
                "CINEMA_SECRET_KEY must be at least 32 characters"
            )
        return env_secret

    os.makedirs(DATA_DIR, exist_ok=True)
    secret_path = os.path.join(
        DATA_DIR,
        "flask_secret.key",
    )
    if os.path.exists(secret_path):
        with open(
            secret_path,
            "r",
            encoding="utf-8",
        ) as f:
            existing = f.read().strip()
            if len(existing) >= 32:
                return existing

    new_secret = secrets.token_hex(32)
    tmp_path = secret_path + ".tmp"
    with open(
        tmp_path,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(new_secret)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, secret_path)
    return new_secret


def _env_true(name, default="0"):
    return os.environ.get(
        name,
        default,
    ).lower() in {"1", "true", "yes", "on"}


def _public_url():
    return os.environ.get(
        "CINEMA_PUBLIC_URL",
        "",
    ).strip().rstrip("/")


def _public_hostname():
    url = _public_url()
    if not url:
        return None
    try:
        return (
            urlsplit(url).hostname or ""
        ).lower() or None
    except Exception:
        return None


def _allowed_host():
    hostname = (
        urlsplit("//" + request.host).hostname
        or ""
    ).lower()
    if hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        return True

    configured = {
        item.strip().lower()
        for item in os.environ.get(
            "CINEMA_ALLOWED_HOSTS",
            "",
        ).split(",")
        if item.strip()
    }
    public_hostname = _public_hostname()
    if public_hostname:
        configured.add(public_hostname)

    try:
        from routes.api_config import TUNNEL_URL
        tunnel_host = (
            urlsplit(TUNNEL_URL).hostname
            if TUNNEL_URL
            else None
        )
        if tunnel_host:
            configured.add(tunnel_host.lower())
    except Exception:
        pass

    return bool(
        hostname
        and hostname in configured
    )


def _safe_next_path():
    path = (
        request.path
        if request.path.startswith("/")
        else "/"
    )
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
    "/register_security",
]

SENSITIVE_PATH_BASES = [
    "/api/auth/register/options",
    "/api/auth/register/verify",
]

public_url = _public_url()
secure_cookie = _env_true(
    "CINEMA_SECURE_COOKIES",
    "1" if public_url.startswith("https://") else "0",
)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)
app.secret_key = _load_secret_key()
app.config.update(
    SESSION_COOKIE_NAME="cinema_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=secure_cookie,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_REFRESH_EACH_REQUEST=False,
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,
)


def _session_is_unlocked():
    record = get_session_state()
    return bool(
        record
        and not record.get("locked")
    )


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not _session_is_unlocked():
            if request.path.startswith("/api/"):
                return jsonify({
                    "status": "err",
                    "msg": "Unauthorized",
                }), 401
            return redirect(
                url_for(
                    "views.login",
                    next=_safe_next_path(),
                )
            )
        return f(*args, **kwargs)

    return decorated_function


@app.before_request
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
        runtime_db.touch_security_session(
            record["session_id"],
            __import__("time").time(),
        )

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


@app.after_request
def apply_security_headers(response):
    response.headers.setdefault(
        "X-Content-Type-Options",
        "nosniff",
    )
    response.headers.setdefault(
        "X-Frame-Options",
        "DENY",
    )
    response.headers.setdefault(
        "Referrer-Policy",
        "no-referrer",
    )
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    response.headers.setdefault(
        "Cross-Origin-Opener-Policy",
        "same-origin",
    )
    response.headers.setdefault(
        "Cross-Origin-Resource-Policy",
        "same-origin",
    )

    auth_surface = request.path.startswith((
        "/login",
        "/register_security",
        "/api/auth/",
    ))
    if auth_surface:
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'none'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "media-src 'none'; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-src 'none'; "
            "frame-ancestors 'none'; "
            "worker-src 'none'; "
            "form-action 'self'"
        )
    else:
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
            "https://cdn.tailwindcss.com "
            "https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://cdnjs.cloudflare.com; "
            "font-src 'self' data: "
            "https://cdnjs.cloudflare.com; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'"
        )
    response.headers.setdefault(
        "Content-Security-Policy",
        csp,
    )

    forwarded_proto = request.headers.get(
        "X-Forwarded-Proto",
        "",
    ).split(",")[0].strip()
    if (
        request.is_secure
        or forwarded_proto == "https"
    ):
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )

    if (
        request.path.startswith("/api/")
        or request.path.startswith("/login")
        or request.path.startswith("/register_security")
        or request.path.startswith("/static/img/actors/")
    ):
        response.headers["Cache-Control"] = (
            "no-store, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"

    return response


register_api_v2(app)
app.register_blueprint(views_bp)


if __name__ == "__main__":
    from waitress import serve

    checks = run_startup_checks()
    logger = logging.getLogger(__name__)
    logger.info(
        "startup_readiness checks=%s",
        checks,
    )
    if not checks["ready"]:
        logger.warning(
            "startup_readiness_degraded checks=%s",
            checks,
        )

    host = os.environ.get(
        "CINEMA_HOST",
        "127.0.0.1",
    )
    port = int(
        os.environ.get(
            "CINEMA_PORT",
            "5000",
        )
    )
    threads = max(
        4,
        int(
            os.environ.get(
                "CINEMA_THREADS",
                "8",
            )
        ),
    )

    if public_url:
        if not public_url.startswith("https://"):
            raise RuntimeError(
                "CINEMA_PUBLIC_URL must use HTTPS"
            )
        if not app.config["SESSION_COOKIE_SECURE"]:
            raise RuntimeError(
                "Public deployment requires Secure session cookies"
            )
        if host not in {"127.0.0.1", "localhost"}:
            logger.warning(
                "Public deployment should bind Cinema to localhost only"
            )

    print("\n" + "-" * 30)
    print(f"MY CINEMA - http://{host}:{port}")
    print("-" * 30 + "\n")
    serve(
        app,
        host=host,
        port=port,
        threads=threads,
    )
