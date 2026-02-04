import json
import os
from constants import CONFIG_FILE, CACHE_FILE, HISTORY_FILE, FAVORITES_FILE
import time

_config_cache = None
_config_mtime = 0
_movies_cache = None
_movies_mtime = 0
_history_cache = None
_history_mtime = 0
_favorites_cache = None
_favorites_mtime = 0

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

    try:
        current_mtime = os.path.getmtime(CONFIG_FILE)
        if _config_cache is not None and current_mtime <= _config_mtime:
            return _config_cache

        with open(CONFIG_FILE, 'r', encoding='utf-8') as f: 
            cfg = json.load(f)
            _config_cache = {**default_config, **cfg}
            _config_mtime = current_mtime
            return _config_cache
    except Exception as e:
        print(f"Lỗi load config: {e}")
    return default_config

def save_config(config):
    global _config_cache
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    _config_cache = None

def load_cache():
    global _movies_cache, _movies_mtime
    
    if not os.path.exists(CACHE_FILE):
        return []

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
    global _movies_cache
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    _movies_cache = None

def load_history():
    global _history_cache, _history_mtime
    if not os.path.exists(HISTORY_FILE):
        return []
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
    global _history_cache
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    _history_cache = None

def load_favorites():
    global _favorites_cache, _favorites_mtime
    if not os.path.exists(FAVORITES_FILE):
        return []
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
    global _favorites_cache
    with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    _favorites_cache = None
