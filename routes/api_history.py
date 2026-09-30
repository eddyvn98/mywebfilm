from flask import Blueprint, request, jsonify
from config_manager import load_history, mutate_history
import time

api_history_bp = Blueprint('api_history', __name__)

@api_history_bp.route('/api/history/add', methods=['POST'])
def add_to_history():
    data = request.json
    video_path = data.get('full_path')
    video_name = data.get('name')
    video_type = data.get('type')
    
    if not video_path:
        return jsonify({"error": "Missing path"}), 400
        
    new_entry = {
        "full_path": video_path,
        "name": video_name,
        "type": video_type,
        "last_watched": time.time()
    }

    def update(history):
        history = [item for item in history if item.get('full_path') != video_path]
        history.insert(0, new_entry)
        return history[:20]

    mutate_history(update)
    return jsonify({"success": True})

@api_history_bp.route('/api/history/list', methods=['GET'])
def get_history():
    return jsonify(load_history())
