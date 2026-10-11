"""Single-session NVENC/CUDA HLS stream; GPU spatial scaling, not neural AI."""
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from functools import lru_cache
from pathlib import Path

from web_security import DATA_DIR

ROOT = Path(DATA_DIR) / "gpu_hls"
ROOT.mkdir(parents=True, exist_ok=True)
_LOCK = threading.RLock()
_SESSIONS = {}
TTL = 180
HEIGHTS = {540, 720, 1080}
NAME = re.compile(r"^(index\.m3u8|segment_[0-9]{5,8}\.ts)$")


class UpscaleUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def capabilities():
    ffmpeg = os.getenv("CINEMA_FFMPEG_PATH") or shutil.which("ffmpeg")
    if not ffmpeg:
        return {"available": False, "reason": "Không tìm thấy FFmpeg", "gpu": False}
    try:
        encoder = subprocess.run([ffmpeg, "-hide_banner", "-encoders"],
                                 capture_output=True, text=True, timeout=7)
        filters = subprocess.run([ffmpeg, "-hide_banner", "-filters"],
                                 capture_output=True, text=True, timeout=7)
        found = "h264_nvenc" in encoder.stdout and "scale_cuda" in filters.stdout
        if not found:
            return {"available": False, "reason": "FFmpeg thiếu h264_nvenc hoặc scale_cuda", "gpu": False}
        return {"available": True, "gpu": True, "max_height": 1080,
                "method": "CUDA Lanczos + NVENC (không phải AI neural)"}
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "reason": "Không đọc được cấu hình FFmpeg", "gpu": False}


def _terminate(record):
    proc = record["process"]
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
    record["log"].close()
    shutil.rmtree(record["directory"], ignore_errors=True)


def _cleanup():
    now = time.monotonic()
    for key, record in list(_SESSIONS.items()):
        if now - record["last"] > TTL:
            _SESSIONS.pop(key, None)
            _terminate(record)


def _janitor():
    while True:
        time.sleep(30)
        with _LOCK:
            _cleanup()


threading.Thread(target=_janitor, name="cinema-hls-cleanup", daemon=True).start()


def start(path, owner, height=720, interpolation="lanczos", start_at=0):
    if not capabilities()["available"]:
        raise UpscaleUnavailable(capabilities()["reason"])
    if type(height) is not int or height not in HEIGHTS:
        raise ValueError("Độ phân giải không hợp lệ")
    if interpolation not in {"bicubic", "lanczos"}:
        raise ValueError("Preset không hợp lệ")
    if type(start_at) not in (int, float) or not 0 <= start_at <= 86400:
        raise ValueError("Vị trí phát không hợp lệ")
    if not owner:
        raise ValueError("Thiếu phiên đăng nhập")
    ffmpeg = os.getenv("CINEMA_FFMPEG_PATH") or shutil.which("ffmpeg")
    with _LOCK:
        _cleanup()
        if _SESSIONS:
            # Switching movies in one authenticated session must replace the old GPU job.
            # A different login cannot evict another viewer's stream.
            if any(record["owner"] != owner for record in _SESSIONS.values()):
                raise UpscaleUnavailable("GTX 1050 Ti đang xử lý một phim khác")
            for old_id, old_record in list(_SESSIONS.items()):
                _SESSIONS.pop(old_id, None)
                _terminate(old_record)
        session_id = uuid.uuid4().hex
        directory = ROOT / session_id
        directory.mkdir(mode=0o700)
        log = (directory / "ffmpeg.log").open("wb")
        output = str(directory / "index.m3u8")
        command = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-nostdin",
                   "-stats_period", "2", "-progress", str(directory / "progress.txt"),
                   "-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        if start_at:
            command += ["-ss", str(round(start_at, 2))]
        command += ["-re", "-i", path, "-map", "0:v:0", "-map", "0:a:0?",
                    "-vf", f"scale_cuda=w=-2:h={height}:interp_algo={interpolation}",
                    "-c:v", "h264_nvenc", "-preset", "p4",
                    "-rc", "vbr", "-cq", "24", "-b:v", "2500k",
                    "-maxrate", "3500k", "-bufsize", "7000k",
                    "-g", "48", "-c:a", "aac", "-b:a", "128k",
                    "-ac", "2", "-sn", "-f", "hls", "-hls_time", "2",
                    "-hls_list_size", "0", "-hls_playlist_type", "event",
                    "-hls_flags", "independent_segments",
                    "-hls_segment_filename", str(directory / "segment_%05d.ts"), output]
        try:
            proc = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                                    stderr=log, stdin=subprocess.DEVNULL)
        except OSError as exc:
            log.close()
            shutil.rmtree(directory, ignore_errors=True)
            raise UpscaleUnavailable("Không thể khởi chạy FFmpeg") from exc
        record = {"id": session_id, "owner": owner, "directory": directory,
                  "process": proc, "log": log, "last": time.monotonic(),
                  "height": height, "start_at": start_at}
        _SESSIONS[session_id] = record

    # Ensure first segment is ready before browser starts requesting the playlist.
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            break
        manifest = directory / "index.m3u8"
        if manifest.exists() and list(directory.glob("segment_*.ts")):
            return record
        time.sleep(0.2)
    with _LOCK:
        _SESSIONS.pop(session_id, None)
        _terminate(record)
    raise UpscaleUnavailable("GPU/FFmpeg không tạo được video. Kiểm tra NVENC và CUDA.")


def get_owned(session_id, owner):
    with _LOCK:
        record = _SESSIONS.get(session_id)
        if not record or record["owner"] != owner:
            return None
        record["last"] = time.monotonic()
        return record


def asset(record, filename):
    if not NAME.fullmatch(filename):
        return None
    target = record["directory"] / filename
    return target if target.is_file() else None


def stop(session_id, owner):
    with _LOCK:
        record = _SESSIONS.get(session_id)
        if not record or record["owner"] != owner:
            return False
        _SESSIONS.pop(session_id, None)
        _terminate(record)
        return True

def telemetry(record):
    result = {"height": record["height"], "speed": None, "encoding_fps": None,
              "running": record["process"].poll() is None}
    progress = record["directory"] / "progress.txt"
    try:
        content = progress.read_text(encoding="utf-8", errors="replace")
        values = dict(line.split("=", 1) for line in content.splitlines() if "=" in line)
        speed = values.get("speed", "").strip().rstrip("x")
        fps = values.get("fps", "").strip()
        result["speed"] = float(speed) if speed and speed != "N/A" else None
        result["encoding_fps"] = float(fps) if fps else None
    except (OSError, ValueError):
        pass
    return result
