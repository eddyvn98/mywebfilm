import json
import logging
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone

import config_manager as cfg
from jav_metadata_service import extract_code, fetch_jav_metadata
from metadata_job_store import (
    claim_next_metadata_job,
    complete_metadata_job,
    enqueue_metadata_job,
    mark_metadata_not_found,
    recover_metadata_jobs,
    retry_metadata_job,
)
from nfo_service import save_nfo

logger = logging.getLogger(__name__)

JAVINIZER_BIN = os.environ.get("CINEMA_JAVINIZER_BIN", "javinizer")
JAVINIZER_CONFIG = os.environ.get("CINEMA_JAVINIZER_CONFIG", "").strip()
JAVINIZER_TIMEOUT_SECONDS = int(os.environ.get("CINEMA_JAVINIZER_TIMEOUT_SECONDS", "60"))
MONITOR_INTERVAL_SECONDS = int(os.environ.get("CINEMA_METADATA_MONITOR_SECONDS", "60"))

_worker_thread = None
_monitor_thread = None
_start_lock = threading.Lock()
_stop_event = threading.Event()


def _iso_now():
    return datetime.now(timezone.utc).isoformat()


def _normalize_code(value):
    return str(value or "").upper().replace("_", "-").replace(" ", "-")


def _actress_name(item):
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return ""
    first = str(item.get("first_name") or "").strip()
    last = str(item.get("last_name") or "").strip()
    latin = " ".join(part for part in (first, last) if part).strip()
    return latin or str(item.get("japanese_name") or "").strip()


def normalize_javinizer_result(raw, expected_code):
    if not isinstance(raw, dict):
        return None
    result_code = _normalize_code(raw.get("id"))
    expected = _normalize_code(expected_code)
    if not result_code or result_code.replace("-", "") != expected.replace("-", ""):
        return None

    actors = []
    for item in raw.get("actresses") or []:
        name = _actress_name(item)
        if name and name not in actors:
            actors.append(name)

    genres = []
    for genre in raw.get("genres") or []:
        value = str(genre or "").strip()
        if value and value not in genres:
            genres.append(value)

    release_date = raw.get("release_date")
    if release_date:
        release_date = str(release_date)[:10]

    metadata = {
        "code": expected,
        "title": str(raw.get("title") or "").strip(),
        "actors": actors,
        "genres": genres,
        "studio": str(raw.get("maker") or "").strip(),
        "maker": str(raw.get("maker") or "").strip(),
        "label": str(raw.get("label") or "").strip(),
        "series": str(raw.get("series") or "").strip(),
        "release_date": release_date or "",
        "source_runtime": int(raw.get("runtime") or 0),
        "poster_url": str(raw.get("poster_url") or "").strip(),
        "cover_url": str(raw.get("cover_url") or "").strip(),
        "content_id": str(raw.get("content_id") or "").strip(),
        "source": str(raw.get("source") or "r18dev").strip(),
        "source_url": str(raw.get("source_url") or "").strip(),
        "metadata_status": "verified",
        "metadata_fetched_at": _iso_now(),
        "timestamp": time.time(),
    }
    if not any((metadata["title"], actors, genres, metadata["studio"])):
        return None
    return metadata


def _javinizer_command(code):
    command = [JAVINIZER_BIN]
    if JAVINIZER_CONFIG:
        command.extend(["--config", JAVINIZER_CONFIG])
    command.extend(["scrape", code, "--scrapers", "r18dev", "--output", "json"])
    return command


def fetch_from_javinizer(code):
    executable = JAVINIZER_BIN
    if not (os.path.isabs(executable) or os.path.dirname(executable)):
        executable = shutil.which(executable)
    elif not os.path.isfile(executable):
        executable = None
    if not executable:
        return None, "unavailable", "Javinizer executable not found"

    command = _javinizer_command(code)
    command[0] = executable
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=JAVINIZER_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, "unavailable", "Javinizer scrape timed out"
    except OSError as exc:
        return None, "unavailable", str(exc)

    payload_text = (proc.stdout or "").strip()
    if not payload_text:
        return None, "unavailable", (proc.stderr or "Javinizer returned no JSON").strip()

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return None, "unknown", "Javinizer returned invalid JSON"

    if proc.returncode == 0:
        metadata = normalize_javinizer_result(payload, code)
        if metadata:
            return metadata, None, ""
        return None, "unknown", "Javinizer result did not match requested code"

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return None, str(error.get("kind") or "unknown"), str(error.get("message") or "")
    return None, "unknown", "Javinizer scrape failed"


def _legacy_fallback(code):
    raw = fetch_jav_metadata(code)
    if not isinstance(raw, dict) or raw.get("not_found") or raw.get("error"):
        return None
    actors = [str(x).strip() for x in raw.get("actors") or [] if str(x).strip()]
    genres = [str(x).strip() for x in raw.get("genres") or [] if str(x).strip()]
    metadata = {
        "code": _normalize_code(code),
        "title": str(raw.get("title") or "").strip(),
        "actors": actors,
        "genres": genres,
        "studio": str(raw.get("studio") or "").strip(),
        "maker": str(raw.get("studio") or "").strip(),
        "label": "",
        "series": "",
        "release_date": "",
        "source_runtime": 0,
        "poster_url": "",
        "cover_url": "",
        "content_id": "",
        "source": str(raw.get("source") or "legacy_scraper"),
        "source_url": "",
        "metadata_status": "verified",
        "metadata_fetched_at": _iso_now(),
        "timestamp": time.time(),
    }
    return metadata if any((metadata["title"], actors, genres, metadata["studio"])) else None


def _metadata_categories(metadata):
    categories = []
    studio = metadata.get("studio")
    if studio:
        categories.append(f"Studio: {studio}")
    for actor in metadata.get("actors") or []:
        categories.append(f"Diễn viên: {actor}")
    for genre in metadata.get("genres") or []:
        if genre not in categories:
            categories.append(genre)
    return categories


def _apply_metadata(path, metadata):
    updated = {"matched": False}

    def mutate(items):
        for item in items:
            if item.get("full_path") != path:
                continue
            item["jav_metadata"] = dict(metadata)
            item["categories"] = _metadata_categories(metadata)
            if metadata.get("title"):
                item["name"] = metadata["title"]
            updated["matched"] = True
            break
        return items

    cfg.mutate_cache(mutate)
    if not updated["matched"]:
        return False

    try:
        save_nfo(path, metadata)
    except Exception:
        logger.exception("metadata_nfo_write_failed path=%r", path)
    return True


def enqueue_catalog_items(items=None):
    items = items if items is not None else cfg.load_cache_snapshot()
    queued = 0
    for item in items or []:
        if item.get("type") != "video" or item.get("is_offline"):
            continue
        path = item.get("full_path")
        if not path:
            continue
        code = extract_code(os.path.basename(path))
        if not code:
            continue
        existing = item.get("jav_metadata")
        if isinstance(existing, dict):
            existing_code = _normalize_code(existing.get("code"))
            if (
                existing.get("metadata_status") == "verified"
                and existing_code.replace("-", "") == _normalize_code(code).replace("-", "")
            ):
                continue
        if enqueue_metadata_job(path, _normalize_code(code)) is not None:
            queued += 1
    return queued


def process_metadata_job(job):
    path = job["path"]
    code = job["code"]
    if not os.path.isfile(path):
        mark_metadata_not_found(job["id"], "media file no longer exists")
        return

    metadata, error_kind, error_message = fetch_from_javinizer(code)
    if metadata is None:
        try:
            metadata = _legacy_fallback(code)
        except Exception as exc:
            logger.exception("metadata_fallback_failed code=%s", code)
            if error_kind == "not_found":
                error_message = str(exc)

    if metadata is not None:
        if _apply_metadata(path, metadata):
            complete_metadata_job(job["id"], metadata.get("source"))
        else:
            retry_metadata_job(job["id"], "catalog item not available yet", job["attempts"])
        return

    if error_kind == "not_found":
        mark_metadata_not_found(job["id"], error_message or "movie not found")
    else:
        retry_metadata_job(job["id"], error_message or error_kind or "metadata lookup failed", job["attempts"])


def _worker_loop():
    while not _stop_event.is_set():
        job = claim_next_metadata_job()
        if not job:
            _stop_event.wait(2)
            continue
        try:
            process_metadata_job(job)
        except Exception as exc:
            logger.exception("metadata_job_failed code=%s path=%r", job.get("code"), job.get("path"))
            retry_metadata_job(job["id"], str(exc), job.get("attempts", 1))


def _monitor_loop():
    enqueue_catalog_items()
    while not _stop_event.wait(MONITOR_INTERVAL_SECONDS):
        try:
            enqueue_catalog_items()
        except Exception:
            logger.exception("metadata_monitor_failed")


def start_metadata_service():
    global _worker_thread, _monitor_thread
    with _start_lock:
        recover_metadata_jobs()
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(
                target=_worker_loop,
                name="cinema-metadata-worker",
                daemon=True,
            )
            _worker_thread.start()
        if _monitor_thread is None or not _monitor_thread.is_alive():
            _monitor_thread = threading.Thread(
                target=_monitor_loop,
                name="cinema-metadata-monitor",
                daemon=True,
            )
            _monitor_thread.start()


def stop_metadata_service():
    _stop_event.set()
