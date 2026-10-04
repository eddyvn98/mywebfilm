"""Free, source-backed JAV metadata lookup.

Primary path: Javinizer Go CLI JSON output (r18.dev by default).
Fallback path: the repository's existing JavLibrary/JavBus scraper.
No LLM is used to invent metadata.
"""
import json
import os
import re
import shutil
import subprocess
import time

from config_manager import load_config
from jav_metadata_service import fetch_jav_metadata


def _code_key(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _clean_list(values):
    cleaned = []
    for value in values or []:
        text = str(value or "").strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _actor_name(actor):
    if isinstance(actor, str):
        return actor.strip()
    if not isinstance(actor, dict):
        return ""
    first = str(actor.get("first_name") or "").strip()
    last = str(actor.get("last_name") or "").strip()
    full = " ".join(part for part in (first, last) if part).strip()
    return full or str(actor.get("japanese_name") or "").strip()


def _normalize_javinizer_result(code, payload):
    if not isinstance(payload, dict) or payload.get("error"):
        return None

    result_code = payload.get("id") or code
    if _code_key(result_code) != _code_key(code):
        return None

    actors = _clean_list(_actor_name(item) for item in payload.get("actresses", []))
    genres = _clean_list(payload.get("genres", []))
    source = str(payload.get("source") or "javinizer").strip()
    source_url = str(payload.get("source_url") or "").strip()

    metadata = {
        "code": str(result_code).upper(),
        "title": str(payload.get("title") or "").strip(),
        "original_title": str(payload.get("original_title") or "").strip(),
        "actors": actors,
        "genres": genres,
        "studio": str(payload.get("maker") or "").strip(),
        "label": str(payload.get("label") or "").strip(),
        "series": str(payload.get("series") or "").strip(),
        "release_date": payload.get("release_date"),
        "source_duration": int(payload.get("runtime") or 0),
        "poster_url": str(payload.get("poster_url") or "").strip(),
        "cover_url": str(payload.get("cover_url") or "").strip(),
        "source": f"javinizer:{source}",
        "source_url": source_url,
        "timestamp": time.time(),
        "verified": True,
    }
    if not any((
        metadata["title"],
        metadata["actors"],
        metadata["genres"],
        metadata["studio"],
    )):
        return None
    return metadata


def _javinizer_binary(config):
    configured = str(
        config.get("javinizer_path")
        or os.environ.get("JAVINIZER_PATH")
        or ""
    ).strip()
    if configured:
        return configured
    return shutil.which("javinizer") or shutil.which("javinizer.exe")


def _run_javinizer(code, scraper, config):
    binary = _javinizer_binary(config)
    if not binary:
        return None

    command = [binary]
    config_path = str(
        config.get("javinizer_config_path")
        or os.environ.get("JAVINIZER_CONFIG")
        or ""
    ).strip()
    if config_path:
        command.extend(["--config", config_path])

    command.extend([
        "scrape",
        code,
        "--scrapers",
        scraper,
        "--output",
        "json",
    ])

    timeout = max(
        5,
        int(config.get("metadata_lookup_timeout_seconds", 45) or 45),
    )
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    raw = (result.stdout or "").strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return _normalize_javinizer_result(code, payload)


def _configured_scrapers(config):
    value = config.get("javinizer_scrapers", ["r18dev"])
    if isinstance(value, str):
        value = [part.strip() for part in value.split(",")]
    return [str(item).strip() for item in (value or []) if str(item).strip()]


def _legacy_fallback(code):
    data = fetch_jav_metadata(code)
    if not isinstance(data, dict):
        return None
    if _code_key(data.get("code")) != _code_key(code):
        return None
    if data.get("not_found") or data.get("error"):
        return None

    metadata = dict(data)
    metadata["code"] = code.upper()
    metadata["actors"] = _clean_list(metadata.get("actors", []))
    metadata["genres"] = _clean_list(metadata.get("genres", []))
    metadata["source"] = f"fallback:{metadata.get('source') or 'web'}"
    metadata["source_url"] = str(metadata.get("source_url") or "")
    metadata["timestamp"] = time.time()
    metadata["verified"] = True
    return metadata


def lookup_metadata(code, config=None):
    """Return verified source-backed metadata for a normalized JAV code."""
    code = str(code or "").strip().upper()
    if not code:
        return None

    config = config or load_config()
    if config.get("enable_javinizer_metadata", True):
        for scraper in _configured_scrapers(config):
            metadata = _run_javinizer(code, scraper, config)
            if metadata:
                return metadata

    if config.get("enable_legacy_metadata_fallback", True):
        return _legacy_fallback(code)
    return None
