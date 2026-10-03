"""
webfilm.py - Main Cinema web application.
"""
import os
import secrets
import threading
import time
from urllib.parse import urlsplit

from flask import request

from logging_config import configure_logging
from routes.api_auth import (
    can_register_request,
    get_origin as auth_origin,
    get_session_state,
    is_direct_local_request,
)
import runtime_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get(
    "CINEMA_DATA_DIR",
    os.path.join(BASE_DIR, "data"),
)
configure_logging(DATA_DIR)

STREAM_ACTIVITY_TOUCH_INTERVAL_SECONDS = max(
    15,
    int(os.environ.get("CINEMA_STREAM_ACTIVITY_TOUCH_SECONDS", "60")),
)
_stream_activity_lock = threading.RLock()
_stream_activity_last = {}


def _touch_stream_activity(record):
    session_id = record.get("session_id") if record else None
    if not session_id:
        return

    now = time.time()
    with _stream_activity_lock:
        last = _stream_activity_last.get(session_id, 0)
        if now - last < STREAM_ACTIVITY_TOUCH_INTERVAL_SECONDS:
            return
        _stream_activity_last[session_id] = now

        if len(_stream_activity_last) > 512:
            cutoff = now - 3600
            stale = [
                sid for sid, touched_at in _stream_activity_last.items()
                if touched_at < cutoff
            ]
            for sid in stale[:256]:
                _stream_activity_last.pop(sid, None)

    runtime_db.touch_security_session(session_id, now)


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

