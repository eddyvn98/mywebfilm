"""Background daemon service to periodically auto-sort Incoming folders once per day."""
from datetime import datetime, timedelta
import json
import logging
import os
import threading
import time

import config_manager as cfg
from constants import CONFIG_DIR
from sort_engine import INCOMING_DIRS, SortEngine, VIDEO_EXTS

logger = logging.getLogger(__name__)

SORT_SCHEDULE_MODE = os.environ.get("CINEMA_SORT_SCHEDULE_MODE", "daily").lower()
SORT_DAILY_HOUR = int(os.environ.get("CINEMA_SORT_DAILY_HOUR", "4"))
SORT_INTERVAL_SECONDS = int(os.environ.get("CINEMA_SORT_INTERVAL_SECONDS", "86400"))
FILE_STABILITY_SECONDS = int(os.environ.get("CINEMA_SORT_STABILITY_SECONDS", "20"))
STATE_FILE = os.path.join(CONFIG_DIR, "last_daily_sort.json")

_monitor_thread = None
_start_lock = threading.Lock()
_sort_execution_lock = threading.Lock()
_stop_event = threading.Event()


def get_last_daily_sort_date():
    """Return the YYYY-MM-DD string of the last successful daily sort run."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_date")
        except Exception:
            return None
    return None


def set_last_daily_sort_date(date_str):
    """Save the YYYY-MM-DD string of the last daily sort run."""
    try:
        from storage_utils import atomic_write_json
        atomic_write_json(STATE_FILE, {"last_date": date_str, "timestamp": time.time()})
    except Exception:
        pass


def seconds_until_daily_target(target_hour=4, target_minute=0, now_dt=None):
    """Compute number of seconds from now until the next occurrence of target_hour:target_minute."""
    now = now_dt or datetime.now()
    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def is_file_ready_for_sort(filepath, now=None):
    """Check if a file is completely downloaded, stable, and not locked."""
    now = now or time.time()
    try:
        stat = os.stat(filepath)
        if now - stat.st_mtime < FILE_STABILITY_SECONDS:
            return False
        with open(filepath, "rb") as test_f:
            test_f.read(1024)
        return True
    except (OSError, PermissionError):
        return False


def collect_ready_incoming_files():
    """Scan all configured INCOMING_DIRS and return files ready for sorting."""
    now = time.time()
    ready_files = []
    for directory in INCOMING_DIRS:
        if not os.path.isdir(directory):
            continue
        for root, dirs, files in os.walk(directory):
            dirs[:] = [
                d for d in dirs
                if d not in {"Sorted_Videos", "$RECYCLE.BIN", "System Volume Information", ".mycinema"}
            ]
            if ".mycinema" in root:
                continue
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext in VIDEO_EXTS:
                    full_path = os.path.join(root, fn)
                    if is_file_ready_for_sort(full_path, now):
                        ready_files.append(full_path)
    return ready_files


def run_auto_sort_cycle():
    """Execute a single auto-sort check and process ready incoming files."""
    if not _sort_execution_lock.acquire(blocking=False):
        logger.debug("Auto-sort cycle skipped: another sort process is currently active.")
        return 0

    try:
        ready = collect_ready_incoming_files()
        if not ready:
            today_str = datetime.now().strftime("%Y-%m-%d")
            set_last_daily_sort_date(today_str)
            return 0

        logger.info("Found %d ready files in incoming folders, starting auto-sort...", len(ready))
        engine = SortEngine(dry_run=False)
        result = engine.run()

        moved_count = len(result.get("moved", [])) + len(result.get("pending_review", []))
        errors = result.get("errors", [])
        if errors:
            logger.warning("Auto-sort completed with errors: %s", errors)

        if moved_count > 0:
            logger.info("Auto-sort moved %d files into Sorted_Videos.", moved_count)
            _refresh_catalog_after_sort()

        today_str = datetime.now().strftime("%Y-%m-%d")
        set_last_daily_sort_date(today_str)
        return moved_count
    except Exception:
        logger.exception("Error during auto-sort cycle")
        return 0
    finally:
        _sort_execution_lock.release()


def _refresh_catalog_after_sort():
    """Scan library directories so newly sorted files immediately enter catalog."""
    try:
        import scanner_service
        video_dirs = cfg.load_config().get("video_dirs", [])
        if video_dirs:
            logger.info("Refreshing library catalog for %d directories...", len(video_dirs))
            scanner_service.scan_videos(video_dirs)
    except Exception:
        logger.exception("Failed to refresh catalog after auto-sort")


def _monitor_loop():
    logger.info(
        "Cinema daily sort monitor started (mode=%s, target_hour=%02d:00, stability=%ds).",
        SORT_SCHEDULE_MODE, SORT_DAILY_HOUR, FILE_STABILITY_SECONDS
    )

    # Startup check: if today hasn't sorted yet and there are ready files
    if not _stop_event.wait(30):
        today_str = datetime.now().strftime("%Y-%m-%d")
        if get_last_daily_sort_date() != today_str:
            try:
                run_auto_sort_cycle()
            except Exception:
                logger.exception("Startup daily sort check failed")

    while not _stop_event.is_set():
        if SORT_SCHEDULE_MODE == "daily":
            wait_seconds = seconds_until_daily_target(SORT_DAILY_HOUR, 0)
            logger.info("Next daily auto-sort scheduled in %.1f hours (at %02d:00).",
                        wait_seconds / 3600.0, SORT_DAILY_HOUR)
        else:
            wait_seconds = SORT_INTERVAL_SECONDS
            logger.info("Next auto-sort interval check in %.1f hours.", wait_seconds / 3600.0)

        if _stop_event.wait(wait_seconds):
            break

        try:
            run_auto_sort_cycle()
        except Exception:
            logger.exception("Scheduled daily auto-sort failed")


def start_sort_service():
    """Start background sort monitor thread if not already running."""
    global _monitor_thread
    with _start_lock:
        _stop_event.clear()
        if _monitor_thread is None or not _monitor_thread.is_alive():
            _monitor_thread = threading.Thread(
                target=_monitor_loop,
                name="cinema-sort-worker",
                daemon=True,
            )
            _monitor_thread.start()
            logger.info("Started background daily sort service thread.")


def stop_sort_service():
    """Stop the background sort monitor thread."""
    _stop_event.set()
