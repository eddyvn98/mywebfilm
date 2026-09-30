import json
import os
from constants import CONFIG_FILE, CACHE_FILE, HISTORY_FILE, FAVORITES_FILE
import time
import threading
from storage_utils import atomic_write_json

# Thread locks to prevent concurrent write data corruption
_config_lock = threading.Lock()
_movies_lock = threading.Lock()
_history_lock = threading.Lock()
_favorites_lock = threading.Lock()

_config_cache = None
_config_mtime = 0
_movies_cache = None
_movies_mtime = 0
_history_cache = None
_history_mtime = 0
_favorites_cache = None
_favorites_mtime = 0


def normalize_video_dirs(video_dirs):
    seen = set()
    cleaned = []
    for path in video_dirs or []:
        if not path:
            continue
        norm = os.path.normpath(str(path))
        key = os.path.normcase(norm)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(norm)
    return cleaned


def normalize_config(config):
    cleaned = dict(config or {})
    cleaned["video_dirs"] = normalize_video_dirs(cleaned.get("video_dirs", []))
    return cleaned

def load_config():
    global _config_cache, _config_mtime
    
    default_config = {
        "video_dirs": [], 
        "auto_convert_ts": True,
        "scrapper_cookies": "",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "preferred_codec": "h264",
        "gemini_api_key": ""
    }

    if not os.path.exists(CONFIG_FILE):
        return default_config

    with _config_lock:
        try:
            current_mtime = os.path.getmtime(CONFIG_FILE)
            if _config_cache is not None and current_mtime <= _config_mtime:
                return _config_cache

            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: 
                cfg = json.load(f)
                raw_config = {**default_config, **cfg}
                _config_cache = normalize_config(raw_config)
                if _config_cache != raw_config:
                    atomic_write_json(CONFIG_FILE, _config_cache)
                _config_mtime = current_mtime
                return _config_cache
        except Exception as e:
            print(f"Lỗi load config: {e}")
        return default_config

def save_config(config):
    global _config_cache, _config_mtime
    config = normalize_config(config)
    with _config_lock:
        atomic_write_json(CONFIG_FILE, config)
        _config_cache = config
        try:
            _config_mtime = os.path.getmtime(CONFIG_FILE)
        except:
            _config_mtime = time.time()

def load_cache():
    global _movies_cache, _movies_mtime
    
    if not os.path.exists(CACHE_FILE):
        return []

    with _movies_lock:
        try:
            current_mtime = os.path.getmtime(CACHE_FILE)
            if _movies_cache is not None and current_mtime <= _movies_mtime:
                return _movies_cache

            with open(CACHE_FILE, 'r', encoding='utf-8') as f: 
                data = json.load(f)
                if isinstance(data, list):
                    _movies_cache = [v for v in data if v is not None]
                    _movies_mtime = current_mtime
                    return _movies_cache
                return data
        except Exception as e:
            print(f"Lỗi load cache: {e}")
            return []
        return []

def save_cache(data):
    global _movies_cache, _movies_mtime
    with _movies_lock:
        atomic_write_json(CACHE_FILE, data)
        _movies_cache = [v for v in data if v is not None]
        try:
            _movies_mtime = os.path.getmtime(CACHE_FILE)
        except:
            _movies_mtime = time.time()

def load_history():
    global _history_cache, _history_mtime
    if not os.path.exists(HISTORY_FILE):
        return []
    with _history_lock:
        try:
            current_mtime = os.path.getmtime(HISTORY_FILE)
            if _history_cache is not None and current_mtime <= _history_mtime:
                return _history_cache

            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                _history_cache = json.load(f)
                _history_mtime = current_mtime
                return _history_cache
        except Exception as e:
            print(f"Lỗi load history: {e}")
            return []

def save_history(data):
    global _history_cache, _history_mtime
    with _history_lock:
        atomic_write_json(HISTORY_FILE, data)
        _history_cache = data
        try:
            _history_mtime = os.path.getmtime(HISTORY_FILE)
        except:
            _history_mtime = time.time()

def load_favorites():
    global _favorites_cache, _favorites_mtime
    if not os.path.exists(FAVORITES_FILE):
        return []
    with _favorites_lock:
        try:
            current_mtime = os.path.getmtime(FAVORITES_FILE)
            if _favorites_cache is not None and current_mtime <= _favorites_mtime:
                return _favorites_cache

            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                _favorites_cache = json.load(f)
                _favorites_mtime = current_mtime
                return _favorites_cache
        except Exception as e:
            print(f"Lỗi load favorites: {e}")
            return []

def save_favorites(data):
    global _favorites_cache, _favorites_mtime
    with _favorites_lock:
        atomic_write_json(FAVORITES_FILE, data)
        _favorites_cache = data
        try:
            _favorites_mtime = os.path.getmtime(FAVORITES_FILE)
        except:
            _favorites_mtime = time.time()
