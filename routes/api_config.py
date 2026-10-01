from flask import Blueprint, jsonify, request
import os
import config_manager as cfg
import scanner_service as scanner
from startup_checks import run_startup_checks
from tag_service import tag_manager

config_bp = Blueprint('api_config', __name__)
TUNNEL_URL = os.environ.get('CINEMA_PUBLIC_URL') or None


@config_bp.route('/api/health')
def health():
    config = cfg.load_config()
    checks = run_startup_checks(config=config)
    return jsonify({
        'status': 'ok' if checks['ready'] else 'degraded',
        'readiness': checks,
        'gemini_configured': bool(config.get('gemini_api_key')),
        'tunnel_configured': bool(TUNNEL_URL),
    })

@config_bp.route('/api/tags')
def get_tags():
    return jsonify(tag_manager.get_all())

def _public_config(config):
    public_keys = {
        "video_dirs",
        "auto_convert_ts",
        "preferred_codec",
        "llm_model",
        "enable_jav_scraping",
    }
    safe_config = {key: config[key] for key in public_keys if key in config}
    safe_config["gemini_configured"] = bool(config.get("gemini_api_key"))
    safe_config["scrapper_cookies_configured"] = bool(config.get("scrapper_cookies"))
    return safe_config

@config_bp.route('/api/config')
def get_config():
    return jsonify(_public_config(cfg.load_config()))

@config_bp.route('/api/config/update', methods=['POST'])
def update_config():
    data = request.get_json(silent=True) or {}
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
        return jsonify({"status": "ok", "config": _public_config(c)})
    return jsonify({"status": "no_change"})

@config_bp.route('/api/clear_cache', methods=['POST'])
def clear_cache():
    cfg.clear_cache_data()
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
        value = str((request.get_json(silent=True) or {}).get('url') or '').strip().rstrip('/')
        if value and not value.startswith('https://'):
            return jsonify({"status": "err", "msg": "Public URL phải dùng HTTPS"}), 400
        TUNNEL_URL = value or None
        return jsonify({"status": "ok", "url": TUNNEL_URL})
    return jsonify({"url": TUNNEL_URL})
