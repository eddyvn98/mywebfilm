from flask import Blueprint, request, jsonify
from config_manager import load_favorites, save_favorites

api_favorites_bp = Blueprint('api_favorites', __name__)

@api_favorites_bp.route('/api/favorites/toggle', methods=['POST'])
def toggle_favorite():
    data = request.json
    video_path = data.get('full_path')
    video_name = data.get('name')
    video_type = data.get('type')
    
    if not video_path:
        return jsonify({"error": "Missing path"}), 400
        
    favorites = load_favorites()
    
    # Check if exists
    exists = any(item['full_path'] == video_path for item in favorites)
    
    if exists:
        # Remove
        favorites = [item for item in favorites if item['full_path'] != video_path]
        is_favorite = False
    else:
        # Add
        new_entry = {
            "full_path": video_path,
            "name": video_name,
            "type": video_type
        }
        favorites.insert(0, new_entry)
        is_favorite = True
    
    save_favorites(favorites)
    return jsonify({"success": True, "is_favorite": is_favorite})

@api_favorites_bp.route('/api/favorites/list', methods=['GET'])
def get_favorites():
    return jsonify(load_favorites())
