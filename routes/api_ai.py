from flask import Blueprint, jsonify, request
import os
import re
import time
from urllib.parse import quote
from media_rename_security import plan_ai_media_rename
import config_manager as cfg
import llm_service
import llm_search_service
import search_service
import metadata_injector
from tag_service import tag_manager

ai_bp = Blueprint('api_ai', __name__)

@ai_bp.route('/api/admin/unverified')
def get_unverified():
    """Lấy danh sách các file chưa được AI chuẩn hóa"""
    items = cfg.load_cache()
    unverified = [v for v in items if v and not (v.get('jav_metadata') or {}).get('is_ai_verified')]
    return jsonify(unverified)

@ai_bp.route('/api/admin/upload_actor_image', methods=['POST'])
def upload_actor_image():
    """Lưu ảnh diễn viên vào thư mục data/actors (bảo mật ngoài static)"""
    from actor_image_store import actor_image_path, actor_image_filename
    name = request.form.get('name')
    file = request.files.get('image')
    if not name or not file:
        return "Missing data", 400

    if file.mimetype not in {"image/jpeg", "image/jpg"}:
        return jsonify({
            "status": "error",
            "msg": "Chỉ chấp nhận ảnh JPEG"
        }), 415

    header = file.stream.read(3)
    file.stream.seek(0)
    if len(header) < 3 or header[:3] not in {
        b"\xff\xd8\xff",
    }:
        return jsonify({
            "status": "error",
            "msg": "Nội dung file không phải JPEG hợp lệ"
        }), 415

    try:
        filename = actor_image_filename(name.strip().replace(' ', '_'))
        save_path = actor_image_path(filename)
    except ValueError:
        return jsonify({"status": "error", "msg": "Invalid actor name"}), 400
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    file.save(save_path)
    return jsonify({
        "status": "ok",
        "url": f"/api/actor_image/{quote(filename, safe='')}"
    })


@ai_bp.route('/api/actor_image/<path:filename>')
def serve_actor_image(filename):
    """Serve exactly one private actor photo after session authorization."""
    from actor_image_store import actor_image_path
    from web_security import get_session_state
    from flask import send_file

    record = get_session_state()
    if not record or record.get("locked"):
        return jsonify({"status": "err", "msg": "Unauthorized"}), 401
    try:
        if filename != os.path.basename(filename):
            raise ValueError("Invalid actor filename")
        image_path = actor_image_path(filename)
        if not os.path.isfile(image_path):
            return jsonify({"status": "err", "msg": "File not found"}), 404
        return send_file(image_path, mimetype="image/jpeg", conditional=True, max_age=0)
    except (ValueError, OSError):
        return jsonify({"status": "err", "msg": "Access denied"}), 403

@ai_bp.route('/api/ai/analyze', methods=['POST'])
def ai_analyze():
    filename = request.json.get('filename')
    force_web = request.json.get('force_web', True) # Mặc định bật web search
    if not filename: return "Filename missing", 400
    
    context = ""
    if force_web:
        context = search_service.search_jav_context(filename)
    else:
        context = "Web search disabled. AI is inferring from filename only."
    
    prompt = llm_service.create_analyzer_prompt(filename, context)
    raw_response = llm_service.call_local_llm(prompt)
    result = llm_service.parse_llm_json(raw_response)
    
    print(f"  [AI] Result: {'Success' if result else 'Failed to parse'}")
    
    # Đảm bảo trả về cấu trúc tối thiểu để tránh lỗi frontend
    final_result = result if result else {
        "title": "", "code": "", "actors": [], "genres": [], "studio": "",
        "error": "AI không trích xuất được JSON. Xem raw_response để biết thêm chi tiết."
    }

    return jsonify({
        "status": "ok" if result else "warning",
        "filename": filename,
        "context": context,
        "prompt": prompt,
        "raw_response": raw_response,
        "result": final_result
    })

@ai_bp.route('/api/ai/inject', methods=['POST'])
def ai_inject():
    filename = request.json.get('filename')
    full_path = request.json.get('path')
    custom_metadata = request.json.get('metadata')
    should_rename = request.json.get('rename', False)

    if not filename or not full_path: return "Missing path", 400

    from utils import check_path_safe
    if not check_path_safe(full_path):
        return jsonify({"status": "error", "msg": "Access denied"}), 403
    if not os.path.exists(full_path):
        return jsonify({"status": "error", "msg": "File not found"}), 404
    
    final_meta = custom_metadata
    if not final_meta:
        final_meta = llm_service.normalize_metadata_with_llm(filename, "")
    
    if not final_meta:
        return jsonify({"status": "error", "msg": "AI không thể suy luận thông tin"}), 400
        
    final_meta['is_ai_verified'] = True
    final_meta['timestamp'] = time.time()

    # Check the destination BEFORE writing the NFO sidecar or moving media.
    new_path = full_path
    new_filename = os.path.basename(full_path)
    target_path = None
    if should_rename:
        try:
            new_filename, target_path = plan_ai_media_rename(full_path, final_meta)
        except ValueError:
            return jsonify({"status": "error", "msg": "Invalid target filename"}), 400
        if not check_path_safe(target_path):
            return jsonify({"status": "error", "msg": "Target outside allowed media roots"}), 403
        if os.path.normcase(os.path.realpath(target_path)) == os.path.normcase(os.path.realpath(full_path)):
            target_path = None
        elif os.path.lexists(target_path):
            return jsonify({"status": "error", "msg": "Target already exists"}), 409

    ok, msg = metadata_injector.save_metadata_fast(full_path, final_meta)

    if ok:
        if target_path:
            try:
                # Check once more immediately before the filesystem mutation.
                if not check_path_safe(target_path):
                    return jsonify({"status": "error", "msg": "Target outside allowed media roots"}), 403
                if os.path.lexists(target_path):
                    return jsonify({"status": "error", "msg": "Target already exists"}), 409
                os.rename(full_path, target_path)
                new_path = target_path
            except OSError:
                return jsonify({"status": "error", "msg": "Failed to rename media file"}), 500

        # Harvest Tags
        if 'genres' in final_meta: tag_manager.add_tags('genres', final_meta['genres'])
        if 'actors' in final_meta: tag_manager.add_tags('actors', final_meta['actors'])
        if 'studio' in final_meta and final_meta['studio']: tag_manager.add_tags('studio', [final_meta['studio']])

        # Update catalog inside one SQLite transaction.
        def update_catalog(items):
            for video in items:
                if video.get('full_path') != full_path:
                    continue
                video['full_path'] = new_path
                video['name'] = os.path.splitext(new_filename)[0]
                video['jav_metadata'] = final_meta
                cats = list(video.get('categories', []))
                cats.extend(final_meta.get('genres', []))
                if final_meta.get('studio'):
                    cats.append(f"Studio: {final_meta['studio'].upper()}")
                cats.extend(f"Diễn viên: {actor}" for actor in final_meta.get('actors', []))
                video['categories'] = list(dict.fromkeys(cats))
                break
            return items

        cfg.mutate_cache(update_catalog)

        return jsonify({
            "status": "ok", 
            "metadata": final_meta,
            "new_path": new_path,
            "new_filename": new_filename
        })
    else:
        return jsonify({"status": "error", "msg": f"Lỗi chèn metadata: {msg}"}), 500

@ai_bp.route('/api/ai/chat', methods=['POST'])
def ai_chat_endpoint():
    """Endpoint cho Clauwbot chat"""
    from llm_agent_service import agent
    user_msg = request.json.get('message')
    if not user_msg: return "Missing message", 400
    
    try:
        answer = agent.chat(user_msg)
        return jsonify({
            "status": "ok",
            "answer": answer
        })
    except Exception as e:
        print(f"  [Chat Error] {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

@ai_bp.route('/api/ai/search', methods=['POST'])
def ai_search():
    query = request.json.get('query')
    if not query: return "Query missing", 400
    
    all_videos = cfg.load_cache()
    results, intent = llm_search_service.semantic_search(query, all_videos)
    
    return jsonify({
        "status": "ok",
        "query": query,
        "intent": intent,
        "results": results
    })
