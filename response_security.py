from flask import request

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

    cacheable_media_artifact = (
        request.path in {"/api/thumbnail", "/api/preview"}
        and response.status_code == 200
    )
    if cacheable_media_artifact:
        response.headers["Cache-Control"] = (
            "private, max-age=86400"
        )
        response.headers.pop("Pragma", None)
    elif (
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
