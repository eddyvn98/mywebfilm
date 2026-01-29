import json
import os
from constants import CONFIG_FILE, CACHE_FILE

def load_config():
    default_config = {"video_dirs": [], "auto_convert_ts": True}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: 
                cfg = json.load(f)
                return {**default_config, **cfg}
        except Exception as e:
            print(f"Lỗi load config: {e}")
    return default_config

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f: 
                data = json.load(f)
                # Đảm bảo không có phần tử None trong danh sách (giúp tránh lỗi AttributeError sau này)
                if isinstance(data, list):
                    return [v for v in data if v is not None]
                return data
        except Exception as e:
            print(f"Lỗi load cache: {e}")
            return []
    return []

def save_cache(data):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
