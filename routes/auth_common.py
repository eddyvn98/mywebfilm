from flask import Blueprint, jsonify, request, session
from security_service import security_manager
import hmac
import os
import secrets
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
from .auth_request import (
    _is_loopback_peer,
    is_direct_local_request,
    rate_limited as _rate_limited,
)

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


def is_recently_authenticated(max_age=300):
    record = get_session_state()
    if not record or record.get("locked"):
        return False
    return (
        time.time()
        - float(record.get("created_at") or 0)
        <= max_age
    )


def _mark_session_authenticated(device=None, remember=True):
    now = time.time()
    previous_session_id = session.get("security_session_id")
    if previous_session_id:
        runtime_db.revoke_security_session(
            previous_session_id,
            now,
        )

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
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("Invalid request host")

    # For the configured public hostname, use the canonical public URL.
    # This keeps Origin/WebAuthn validation correct behind Cloudflare Tunnel
    # even when the backend connection itself is plain HTTP and cloudflared
    # does not forward X-Forwarded-Proto.
    public_url = os.environ.get(
        "CINEMA_PUBLIC_URL",
        "",
    ).strip().rstrip("/")
    if public_url:
        public = urlsplit(public_url)
        public_hostname = (public.hostname or "").lower()
        if public_hostname and hostname == public_hostname:
            public_scheme = (
                "https"
                if public.scheme == "https"
                else "http"
            )
            public_host = public.netloc
            if public_host:
                return (
                    f"{public_scheme}://{public_host}"
                ).rstrip("/")

    # Preserve the exact direct-local host the browser used. Treating
    # 127.0.0.1 as localhost here causes same-origin POSTs from 127.0.0.1
    # to be rejected before authentication is reached.
    if hostname.endswith(".trycloudflare.com"):
        proto = "https"

    return f"{proto}://{host}".rstrip("/")


