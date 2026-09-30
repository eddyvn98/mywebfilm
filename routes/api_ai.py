from flask import Blueprint, jsonify, request
import os
import re
import time
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
    """Lưu ảnh diễn viên vào thư mục static/img/actors"""
    from werkzeug.utils import secure_filename
    name = request.form.get('name')
    file = request.files.get('image')
    if not name or not file: return "Missing data", 400
    
    # Sanitize name to prevent path traversal in filename
    safe_name = secure_filename(name.strip().replace(' ', '_'))
    if not safe_name: return "Invalid name", 400
    
    save_dir = os.path.join('static', 'img', 'actors')
    if not os.path.exists(save_dir): os.makedirs(save_dir)
    
    save_path = os.path.join(save_dir, f"{safe_name}.jpg")
    
    # Path safety verification
    from utils import check_path_safe
    if not check_path_safe(save_path):
        return jsonify({"status": "error", "msg": "Access denied"}), 403
        
    file.save(save_path)
    
    return jsonify({"status": "ok", "url": f"/static/img/actors/{safe_name}.jpg"})

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

    # Dùng phương thức lưu "siêu nhanh" (FAST) mặc định để tránh lag máy cho user
    ok, msg = metadata_injector.save_metadata_fast(full_path, final_meta)
    
    if ok:
        new_path = full_path
        new_filename = filename

        if should_rename:
            try:
                code = final_meta.get('code')
                title = final_meta.get('title')
                ext = os.path.splitext(full_path)[1]
                clean_title = re.sub(r'[\\/:*?"<>|]', '', title)
                new_filename = f"[{code}] {clean_title}{ext}" if code else f"{clean_title}{ext}"
                target_path = os.path.join(os.path.dirname(full_path), new_filename)
                
                if not os.path.exists(target_path):
                    os.rename(full_path, target_path)
                    new_path = target_path
            except Exception as re_err:
                print(f"Rename error: {re_err}")

        # Harvest Tags
        if 'genres' in final_meta: tag_manager.add_tags('genres', final_meta['genres'])
        if 'actors' in final_meta: tag_manager.add_tags('actors', final_meta['actors'])
        if 'studio' in final_meta and final_meta['studio']: tag_manager.add_tags('studio', [final_meta['studio']])

        # Update Cache
        items = cfg.load_cache()
        updated = False
        for v in items:
            if v['full_path'] == full_path:
                v['full_path'] = new_path
                v['name'] = os.path.splitext(new_filename)[0]
                v['jav_metadata'] = final_meta
                cats = list(v.get('categories', []))
                for g in final_meta.get('genres', []): cats.append(g)
                if final_meta.get('studio'): cats.append(f"Studio: {final_meta['studio'].upper()}")
                for a in final_meta.get('actors', []): cats.append(f"Diễn viên: {a}")
                v['categories'] = list(dict.fromkeys(cats))
                updated = True
                break
        
        if updated:
            cfg.save_cache(items)

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
