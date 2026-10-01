from flask import Blueprint, request, jsonify
from config_manager import get_catalog_item, load_favorites, mutate_favorites

api_favorites_bp = Blueprint('api_favorites', __name__)

@api_favorites_bp.route('/api/favorites/toggle', methods=['POST'])
def toggle_favorite():
    data = request.json
    video_path = data.get('full_path')
    video_name = data.get('name')
    video_type = data.get('type')
    
    if not video_path:
        return jsonify({"error": "Missing path"}), 400
    if not get_catalog_item(video_path):
        return jsonify({"error": "Unknown media"}), 403
        
    result = {"is_favorite": False}

    def update(favorites):
        exists = any(item.get('full_path') == video_path for item in favorites)
        if exists:
            result["is_favorite"] = False
            return [item for item in favorites if item.get('full_path') != video_path]

        result["is_favorite"] = True
        favorites.insert(0, {
            "full_path": video_path,
            "name": video_name,
            "type": video_type
        })
        return favorites

    mutate_favorites(update)
    return jsonify({"success": True, "is_favorite": result["is_favorite"]})

@api_favorites_bp.route('/api/favorites/list', methods=['GET'])
def get_favorites():
    return jsonify(load_favorites())
