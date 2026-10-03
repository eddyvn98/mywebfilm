import os
import subprocess
import sys
import threading


WINDOWS_CREATE_NO_WINDOW = (
    subprocess.CREATE_NO_WINDOW
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW")
    else 0
)


def ffmpeg_subprocess_kwargs(**kwargs):
    """Return kwargs for media subprocess calls, suppressing console popup windows on Windows."""
    extra = {}
    if WINDOWS_CREATE_NO_WINDOW:
        extra["creationflags"] = WINDOWS_CREATE_NO_WINDOW
    extra.update(kwargs)
    return extra


def _env_int(name, default, minimum, maximum):
    try:
        value = int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


FFMPEG_CONCURRENCY = _env_int("CINEMA_FFMPEG_CONCURRENCY", 2, 1, 4)
FFMPEG_SHORT_TIMEOUT = _env_int("CINEMA_FFMPEG_SHORT_TIMEOUT_SECONDS", 90, 10, 900)
FFPROBE_TIMEOUT = _env_int("CINEMA_FFPROBE_TIMEOUT_SECONDS", 30, 5, 300)
FFMPEG_LONG_TIMEOUT = _env_int("CINEMA_FFMPEG_LONG_TIMEOUT_SECONDS", 21600, 300, 86400)

# One process budget for every FFmpeg consumer in this application.
FFMPEG_SEMAPHORE = threading.BoundedSemaphore(FFMPEG_CONCURRENCY)
