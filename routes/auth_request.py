from flask import jsonify, request
import threading
import time
from urllib.parse import urlsplit

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


def rate_limited(action):
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
