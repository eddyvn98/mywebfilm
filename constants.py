import os

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.abspath(os.environ.get("CINEMA_CONFIG_DIR", BASE_DIR))
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CACHE_FILE = os.path.join(CONFIG_DIR, "movies_cache.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history_cache.json")
FAVORITES_FILE = os.path.join(CONFIG_DIR, "favorites_cache.json")

# Nơi lưu trữ metadata cục bộ trong mỗi thư mục chứa video
METADATA_DIR_NAME = ".mycinema" 

# --- EXECUTABLES ---
FFMPEG_PATH = "ffmpeg"
FFPROBE_PATH = "ffprobe"
MPC_PATH = r"C:\Program Files\MPC-HC\mpc-hc64.exe"

# --- FFMPEG SETTINGS ---
THUMB_SEEK_TIME = "00:00:05"
THUMB_SIZE = "300:450"
PREVIEW_SEEK_TIME = "00:00:10"
PREVIEW_DURATION = "3"
PREVIEW_SIZE = "240:360"
