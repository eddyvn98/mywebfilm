import logging
import threading
import time

import scanner_service

logger = logging.getLogger(__name__)


class ScanManager:
    def __init__(self, scan_func=None):
        self._scan_func = scan_func or scanner_service.scan_videos
        self._lock = threading.RLock()
        self._thread = None
        self._state = {
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "result_count": 0,
            "error": "",
        }

    def start(self, video_dirs):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False, dict(self._state)

            self._state = {
                "status": "running",
                "started_at": time.time(),
                "finished_at": None,
                "result_count": 0,
                "error": "",
            }
            roots = tuple(video_dirs or ())
            self._thread = threading.Thread(
                target=self._run,
                args=(roots,),
                name="cinema-library-scan",
                daemon=True,
            )
            self._thread.start()
            return True, dict(self._state)

    def _run(self, video_dirs):
        try:
            items = self._scan_func(list(video_dirs))
            with self._lock:
                self._state.update(
                    status="done",
                    finished_at=time.time(),
                    result_count=len(items or []),
                    error="",
                )
        except Exception as exc:
            logger.exception("library_scan_failed")
            with self._lock:
                self._state.update(
                    status="failed",
                    finished_at=time.time(),
                    error=str(exc),
                )

    def status(self):
        with self._lock:
            return dict(self._state)


scan_manager = ScanManager()
