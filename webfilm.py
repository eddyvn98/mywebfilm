"""Cinema web application entry point."""
import logging
import os

from app_factory import app, public_url
from web_security import _stream_activity_last, _touch_stream_activity, runtime_db
from request_security import check_auth
from response_security import apply_security_headers
from startup_checks import run_startup_checks

app.before_request(check_auth)
app.after_request(apply_security_headers)


if __name__ == "__main__":
    from waitress import serve
    from metadata_worker import start_metadata_service

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

    start_metadata_service()

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

