from flask import Blueprint
from .api_ai import ai_bp
from .api_video import video_bp
from .api_process import process_bp
from .api_fs import fs_bp
from .api_config import config_bp
from .api_auth import auth_bp
from .api_history import api_history_bp
from .api_favorites import api_favorites_bp
from .api_sort import sort_bp
from .api_diagnostics import diagnostics_bp

# Aggregated API Blueprint v2
api_bp = Blueprint('api', __name__)

# Register sub-blueprints
# Note: Since they all share the same /api prefix logic in their internal routes,
# we just register them here.
from flask import Flask

def register_api_v2(app: Flask):
    app.register_blueprint(ai_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(process_bp)
    app.register_blueprint(fs_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_history_bp)
    app.register_blueprint(api_favorites_bp)
    app.register_blueprint(sort_bp)
    app.register_blueprint(diagnostics_bp)
