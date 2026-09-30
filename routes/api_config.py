from flask import Blueprint, jsonify, request
import os
import config_manager as cfg
import scanner_service as scanner
from tag_service import tag_manager

config_bp = Blueprint('api_config', __name__)
TUNNEL_URL = None

@config_bp.route('/api/tags')
def get_tags():
    return jsonify(tag_manager.get_all())

@config_bp.route('/api/config')
def get_config():
    config = cfg.load_config()
    safe_config = {
        key: value for key, value in config.items()
        if key not in {"gemini_api_key", "scrapper_cookies"}
    }
    safe_config["gemini_configured"] = bool(config.get("gemini_api_key"))
    safe_config["scrapper_cookies_configured"] = bool(config.get("scrapper_cookies"))
    return jsonify(safe_config)

@config_bp.route('/api/config/update', methods=['POST'])
def update_config():
    data = request.json
    c = cfg.load_config()
    changed = False
    if 'auto_convert_ts' in data:
        c['auto_convert_ts'] = bool(data['auto_convert_ts'])
        changed = True
    if 'scrapper_cookies' in data:
        c['scrapper_cookies'] = data['scrapper_cookies']
        changed = True
    if changed:
        cfg.save_config(c)
        return jsonify({"status": "ok", "config": c})
    return jsonify({"status": "no_change"})

@config_bp.route('/api/clear_cache', methods=['POST'])
def clear_cache():
    if os.path.exists(cfg.CACHE_FILE): os.remove(cfg.CACHE_FILE)
    return jsonify({"status": "ok"})

@config_bp.route('/api/scan', methods=['POST'])
def scan():
    config = cfg.load_config()
    items = scanner.scan_videos(config.get("video_dirs", []))
    return jsonify(items)

@config_bp.route('/api/add_folder', methods=['POST'])
def add_folder():
    p = request.json.get('path')
    if os.path.exists(p):
        c = cfg.load_config()
        if p not in c["video_dirs"]:
            c["video_dirs"].append(p)
            cfg.save_config(c)
        return jsonify({"status":"ok"})
    return jsonify({"status":"err"}), 400

@config_bp.route('/api/remove_folder', methods=['POST'])
def remove_folder():
    p = request.json.get('path')
    c = cfg.load_config()
    norm_p = os.path.normpath(p)
    c["video_dirs"] = [d for d in c["video_dirs"] if os.path.normpath(d) != norm_p]
    cfg.save_config(c)
    return jsonify({"status":"ok"})

@config_bp.route('/api/config/tunnel', methods=['GET', 'POST'])
def handle_tunnel():
    global TUNNEL_URL
    if request.method == 'POST':
        TUNNEL_URL = request.json.get('url')
        return jsonify({"status": "ok", "url": TUNNEL_URL})
    return jsonify({"url": TUNNEL_URL})
