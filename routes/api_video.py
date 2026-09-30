from flask import Blueprint, jsonify, request, send_file, Response
import os
import re
import mimetypes
import subprocess
import threading
import config_manager as cfg
import ffmpeg_service as ff
from constants import MPC_PATH
from utils import get_metadata_paths, ensure_metadata_dirs, check_path_safe

video_bp = Blueprint('api_video', __name__)

EXT_MAP = {
    '.mkv': 'video/x-matroska', '.mp4': 'video/mp4', '.avi': 'video/x-msvideo',
    '.mov': 'video/quicktime', '.wmv': 'video/x-ms-wmv', '.flv': 'video/x-flv',
    '.webm': 'video/webm', '.ts': 'video/mp2t', '.m2ts': 'video/mp2t'
}

@video_bp.route('/api/videos')
def get_videos():
    return jsonify(cfg.load_cache())

@video_bp.route('/api/thumbnail')
def get_thumb():
    p = request.args.get('path')
    t = request.args.get('type', 'video')
    if not p: return "Path missing", 400
    if not check_path_safe(p): return "Access denied", 403
    
    paths = get_metadata_paths(p)
    ensure_metadata_dirs(paths)
    out = paths['thumb_path']
    
    if not os.path.exists(out):
        if not ff.generate_thumbnail(p, out, is_image=(t == 'image')):
            return "FFmpeg error", 500
            
    if os.path.exists(out):
        return send_file(out)
    return "Failed", 500

@video_bp.route('/api/preview')
def get_prev():
    p = request.args.get('path')
    if not p: return "Path missing", 400
    if not check_path_safe(p): return "Access denied", 403
    
    paths = get_metadata_paths(p)
    ensure_metadata_dirs(paths)
    out = paths['prev_path']
    
    if not os.path.exists(out):
        if not ff.generate_preview(p, out):
            return "FFmpeg error", 500
            
    if os.path.exists(out):
        return send_file(out)
    return "Failed", 500

@video_bp.route('/api/play', methods=['POST'])
def play():
    p = request.json.get('path')
    t = request.json.get('type', 'video')
    
    if not p or not os.path.exists(p):
        return jsonify({"status":"err", "msg": "File not found"}), 404
    if not check_path_safe(p):
        return jsonify({"status":"err", "msg": "Access denied"}), 403

    # Increase view count in background to avoid blocking initial stream request
    def update_views(p_val):
        items = cfg.load_cache()
        for v in items:
            if v['full_path'] == p_val:
                v['views'] = v.get('views', 0) + 1
                break
        cfg.save_cache(items)
    
    threading.Thread(target=update_views, args=(p,), daemon=True).start()
    
    # Open file
    if t == 'image':
        os.startfile(p)
    else:
        if os.path.exists(MPC_PATH): 
            subprocess.Popen([MPC_PATH, p])
        else:
            os.startfile(p)
            
    return jsonify({"status":"ok"})

@video_bp.route('/api/stream')
def stream_video():
    path = request.args.get('path')
    if not path or not os.path.exists(path): return "File not found", 404
    if not check_path_safe(path): return "Access denied", 403
    
    # Determine Mime Type safely
    ext = os.path.splitext(path)[1].lower()
    mime = EXT_MAP.get(ext) or mimetypes.guess_type(path)[0] or 'video/mp4'
    
    # Native Flask streaming handles Range requests via conditional=True
    # It uses optimized buffers and handles the 206 status automatically.
    return send_file(
        path, 
        mimetype=mime, 
        conditional=True, 
        as_attachment=False
    )
