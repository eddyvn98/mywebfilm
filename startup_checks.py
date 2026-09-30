import os
import shutil
import tempfile

import config_manager as cfg
import runtime_db
from constants import FFMPEG_PATH, FFPROBE_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.environ.get("CINEMA_DATA_DIR", os.path.join(BASE_DIR, "data"))


def _command_available(command):
    if os.path.isabs(command) or os.path.dirname(command):
        return os.path.isfile(command)
    return shutil.which(command) is not None


def _check_data_dir(data_dir):
    try:
        os.makedirs(data_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=data_dir, prefix=".health-", delete=True):
            pass
        return True
    except Exception:
        return False


def _check_sqlite():
    try:
        runtime_db.ensure_schema()
        return True
    except Exception:
        return False


def run_startup_checks(config=None, data_dir=None):
    config = config or cfg.load_config()
    data_dir = data_dir or DEFAULT_DATA_DIR

    roots = [path for path in config.get("video_dirs", []) if path]
    existing_roots = sum(1 for path in roots if os.path.isdir(path))
    missing_roots = len(roots) - existing_roots

    checks = {
        "ffmpeg": _command_available(FFMPEG_PATH),
        "ffprobe": _command_available(FFPROBE_PATH),
        "data_dir_writable": _check_data_dir(data_dir),
        "sqlite": _check_sqlite(),
        "media_roots_configured": len(roots),
        "media_roots_available": existing_roots,
        "media_roots_missing": missing_roots,
    }
    checks["ready"] = all(
        checks[key]
        for key in ("ffmpeg", "ffprobe", "data_dir_writable", "sqlite")
    )
    return checks
