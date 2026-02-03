from flask import Blueprint, jsonify, request
import os
import config_manager as cfg
import ffmpeg_service as ff
from queue_worker import media_queue

process_bp = Blueprint('api_process', __name__)

@process_bp.route('/api/process/queue', methods=['POST'])
def add_to_queue():
    paths = request.json.get('paths', [])
    task_type = request.json.get('type', 'highlight')
    if not paths: return "No paths provided", 400
    valid_paths = [p for p in paths if os.path.exists(p)]
    if not valid_paths: return "No valid files found", 404
    media_queue.add_items(valid_paths, task_type=task_type)
    return jsonify({"status": "ok", "msg": f"Added {len(valid_paths)} items to queue"})

@process_bp.route('/api/process/status', methods=['GET'])
def get_queue_status():
    return jsonify(media_queue.get_status())

@process_bp.route('/api/process/clear', methods=['POST'])
def clear_completed():
    media_queue.clear_completed()
    return jsonify({"status": "ok"})

@process_bp.route('/api/process/highlight', methods=['POST'])
def process_manual_highlight():
    p = request.json.get('path')
    if not p or not os.path.exists(p): 
        return jsonify({"status":"err", "msg": "File not found"}), 404
    video_dir = os.path.dirname(p)
    processed_dir = os.path.join(video_dir, 'Processed')
    try:
        out_path = ff.process_highlight_video(p, processed_dir)
        if out_path:
            c = cfg.load_config()
            if processed_dir not in c["video_dirs"]:
                c["video_dirs"].append(processed_dir)
                cfg.save_config(c)
            return jsonify({"status":"ok", "output": out_path})
        return jsonify({"status":"err", "msg": "FFmpeg failed"}), 500
    except Exception as e:
        return jsonify({"status":"err", "msg": str(e)}), 500
