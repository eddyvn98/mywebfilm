from datetime import timedelta
import os
from flask import Flask
from logging_config import configure_logging
from routes.api_v2 import register_api_v2
from routes.views import views_bp
from web_security import DATA_DIR, _env_true, _load_secret_key, _public_url

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



register_api_v2(app)
app.register_blueprint(views_bp)
