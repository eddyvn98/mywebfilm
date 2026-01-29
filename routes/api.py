from flask import Blueprint, jsonify, request, send_file, Response
import os
import re
import mimetypes
import subprocess

import config_manager as cfg
import ffmpeg_service as ff
from queue_worker import media_queue
import scanner_service as scanner
from constants import MPC_PATH
from utils import get_metadata_paths, ensure_metadata_dirs

import llm_service
import json
import time
from tag_service import tag_manager

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/tags')
def get_tags():
    return jsonify(tag_manager.get_all())

@api_bp.route('/api/admin/unverified')
def get_unverified():
    """Lấy danh sách các file chưa được AI chuẩn hóa"""
    items = cfg.load_cache()
    # Lọc những file chưa có flag is_ai_verified (Xử lý an toàn nếu v hoặc jav_metadata là None)
    unverified = [v for v in items if v and not (v.get('jav_metadata') or {}).get('is_ai_verified')]
    return jsonify(unverified)

@api_bp.route('/api/admin/upload_actor_image', methods=['POST'])
def upload_actor_image():
    """Lưu ảnh diễn viên vào thư mục static/img/actors"""
    name = request.form.get('name')
    file = request.files.get('image')
    if not name or not file: return "Missing data", 400
    
    # Chuẩn hóa tên file: "Maria Ozawa" -> "Maria_Ozawa.jpg"
    safe_name = name.strip().replace(' ', '_')
    save_dir = os.path.join('static', 'img', 'actors')
    if not os.path.exists(save_dir): os.makedirs(save_dir)
    
    save_path = os.path.join(save_dir, f"{safe_name}.jpg")
    file.save(save_path)
    
    return jsonify({"status": "ok", "url": f"/static/img/actors/{safe_name}.jpg"})

@api_bp.route('/api/ai/analyze', methods=['POST'])
def ai_analyze():
    filename = request.json.get('filename')
    if not filename: return "Filename missing", 400
    
    # BỎ QUA SEARCH WEB THEO YÊU CẦU NGƯỜI DÙNG
    context = "Đã tắt tìm kiếm Web. AI tự suy luận từ tên file."
    
    # Step 2: Use the formal prompt generation from llm_service
    prompt = llm_service.create_analyzer_prompt(filename, context)
    
    # Step 3: Call LLM with the REAL prompt
    raw_response = llm_service.call_local_llm(prompt)
    
    # Step 4: Parse
    result = llm_service.parse_llm_json(raw_response)
    
    return jsonify({
        "filename": filename,
        "context": context,
        "prompt": prompt,
        "raw_response": raw_response,
        "result": result
    })

@api_bp.route('/api/ai/inject', methods=['POST'])
def ai_inject():
    filename = request.json.get('filename')
    full_path = request.json.get('path')
    custom_metadata = request.json.get('metadata') # User có thể gửi metadata đã sửa tay
    should_rename = request.json.get('rename', False) # Có đổi tên file vật lý không

    if not filename or not full_path: return "Missing path", 400
    
    import llm_service
    import metadata_injector

    # 1. Lấy Metadata (Dùng gửi từ UI hoặc chạy AI nếu thiếu)
    final_meta = custom_metadata
    if not final_meta:
        final_meta = llm_service.normalize_metadata_with_llm(filename, "")
    
    if not final_meta:
        return jsonify({"status": "error", "msg": "AI không thể suy luận thông tin"}), 400
        
    # 2. Đánh dấu đã xác nhận
    final_meta['is_ai_verified'] = True
    final_meta['timestamp'] = time.time()

    # 3. Tiêm Metadata vào file vật lý
    ok, msg = metadata_injector.inject_metadata(full_path, final_meta)
    
    if ok:
        new_path = full_path
        new_filename = filename

        # 4. Đổi tên file vật lý nếu yêu cầu
        if should_rename:
            try:
                code = final_meta.get('code')
                title = final_meta.get('title')
                ext = os.path.splitext(full_path)[1]
                
                # Format: [CODE] Title.mp4
                clean_title = re.sub(r'[\\/:*?"<>|]', '', title) # Xóa ký tự cấm
                if code:
                    new_filename = f"[{code}] {clean_title}{ext}"
                else:
                    new_filename = f"{clean_title}{ext}"
                
                target_path = os.path.join(os.path.dirname(full_path), new_filename)
                
                if not os.path.exists(target_path):
                    os.rename(full_path, target_path)
                    new_path = target_path
                    print(f"Renamed {full_path} -> {new_path}")
                else:
                    print(f"Bỏ qua rename vì file đã tồn tại: {target_path}")
            except Exception as re:
                print(f"Rename error: {re}")

        # Harvest Tags
        if 'genres' in final_meta: tag_manager.add_tags('genres', final_meta['genres'])
        if 'actors' in final_meta: tag_manager.add_tags('actors', final_meta['actors'])
        if 'studio' in final_meta and final_meta['studio']: tag_manager.add_tags('studio', [final_meta['studio']])

        # 5. Cập nhật Cache ngay lập tức
        items = cfg.load_cache()
        updated = False
        for v in items:
            if v['full_path'] == full_path:
                v['full_path'] = new_path
                v['name'] = os.path.splitext(new_filename)[0]
                v['jav_metadata'] = final_meta
                # Cập nhật categories dựa trên metadata mới
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
            "msg": "Đã chèn metadata (và đổi tên) thành công!", 
            "metadata": final_meta,
            "new_path": new_path,
            "new_filename": new_filename
        })
    else:
        return jsonify({"status": "error", "msg": f"Lỗi chèn metadata: {msg}"}), 500

@api_bp.route('/api/config')
def get_config():
    return jsonify(cfg.load_config())

@api_bp.route('/api/config/update', methods=['POST'])
def update_config():
    data = request.json
    c = cfg.load_config()
    changed = False
    
    if 'auto_convert_ts' in data:
        c['auto_convert_ts'] = bool(data['auto_convert_ts'])
        changed = True
        
    if changed:
        cfg.save_config(c)
        return jsonify({"status": "ok", "config": c})
    return jsonify({"status": "no_change"})

@api_bp.route('/api/thumbnail')
def get_thumb():
    p = request.args.get('path')
    t = request.args.get('type', 'video') # 'video' or 'image'
    
    if not p: return "Path missing", 400
    
    paths = get_metadata_paths(p)
    ensure_metadata_dirs(paths)
    out = paths['thumb_path']
    
    if not os.path.exists(out):
        if not ff.generate_thumbnail(p, out, is_image=(t == 'image')):
            return "FFmpeg error", 500
            
    if os.path.exists(out):
        return send_file(out)
    return "Failed", 500

@api_bp.route('/api/preview')
def get_prev():
    p = request.args.get('path')
    if not p: return "Path missing", 400
    
    paths = get_metadata_paths(p)
    ensure_metadata_dirs(paths)
    out = paths['prev_path']
    
    if not os.path.exists(out):
        if not ff.generate_preview(p, out):
            return "FFmpeg error", 500
            
    if os.path.exists(out):
        return send_file(out)
    return "Failed", 500

@api_bp.route('/api/clear_cache', methods=['POST'])
def clear_cache():
    if os.path.exists(cfg.CACHE_FILE): 
        os.remove(cfg.CACHE_FILE)
    return jsonify({"status": "ok"})

@api_bp.route('/api/scan', methods=['POST'])
def scan():
    config = cfg.load_config()
    items = scanner.scan_videos(config.get("video_dirs", []))
    return jsonify(items)

@api_bp.route('/api/add_folder', methods=['POST'])
def add_f():
    p = request.json.get('path')
    if os.path.exists(p):
        c = cfg.load_config()
        if p not in c["video_dirs"]:
            c["video_dirs"].append(p)
            cfg.save_config(c)
        return jsonify({"status":"ok"})
    return jsonify({"status":"err"}), 400

@api_bp.route('/api/remove_folder', methods=['POST'])
def remove_f():
    p = request.json.get('path')
    c = cfg.load_config()
    norm_p = os.path.normpath(p)
    c["video_dirs"] = [d for d in c["video_dirs"] if os.path.normpath(d) != norm_p]
    cfg.save_config(c)
    return jsonify({"status":"ok"})

@api_bp.route('/api/videos')
def get_v():
    return jsonify(cfg.load_cache())

@api_bp.route('/api/play', methods=['POST'])
def play():
    p = request.json.get('path')
    t = request.json.get('type', 'video')
    
    if not p or not os.path.exists(p):
        return jsonify({"status":"err", "msg": "File not found"}), 404

    # Increase view count
    items = cfg.load_cache()
    for v in items:
        if v['full_path'] == p:
            v['views'] = v.get('views', 0) + 1
            break
    cfg.save_cache(items)
    
    # Open file
    if t == 'image':
        os.startfile(p)
    else:
        if os.path.exists(MPC_PATH): 
            subprocess.Popen([MPC_PATH, p])
        else:
            os.startfile(p)
            
    return jsonify({"status":"ok"})

@api_bp.route('/api/delete_file', methods=['POST'])
def delete_file():
    p = request.json.get('path')
    if not p or not os.path.exists(p):
        return jsonify({"status":"err", "msg": "File not found"}), 404
        
    try:
        # Delete file
        os.remove(p)
        
        # Delete metadata
        paths = get_metadata_paths(p)
        if os.path.exists(paths['thumb_path']): os.remove(paths['thumb_path'])
        if os.path.exists(paths['prev_path']): os.remove(paths['prev_path'])
        
        # Update cache
        items = cfg.load_cache()
        items = [v for v in items if v['full_path'] != p]
        cfg.save_cache(items)
        
        return jsonify({"status":"ok"})
    except Exception as e:
        return jsonify({"status":"err", "msg": str(e)}), 500

@api_bp.route('/api/explorer', methods=['POST'])
def open_explorer():
    p = request.json.get('path')
    if not p or not os.path.exists(p):
        return jsonify({"status":"err", "msg": "File not found"}), 404
        
    try:
        # Windows specific: Open explorer and select file
        subprocess.run(['explorer', '/select,', os.path.normpath(p)])
        return jsonify({"status":"ok"})
    except Exception as e:
        return jsonify({"status":"err", "msg": str(e)}), 500

@api_bp.route('/api/fs/rename', methods=['POST'])
def fs_rename():
    old_p = request.json.get('old_path')
    new_name = request.json.get('new_name')
    if not old_p or not new_name: return "Params missing", 400
    
    try:
        parent = os.path.dirname(old_p)
        new_p = os.path.join(parent, new_name)
        
        if os.path.exists(new_p):
            return jsonify({"status":"err", "msg": "Tên này đã tồn tại"}), 400
            
        os.rename(old_p, new_p)
        
        # Update cache if it was a video
        items = cfg.load_cache()
        for v in items:
            if v['full_path'] == old_p:
                v['full_path'] = new_p
                v['name'] = new_name
                break
            # If a folder was renamed, update all children
            elif v['full_path'].startswith(old_p + os.sep):
                v['full_path'] = v['full_path'].replace(old_p, new_p, 1)
        cfg.save_cache(items)
        
        return jsonify({"status":"ok", "new_path": new_p})
    except Exception as e:
        return jsonify({"status":"err", "msg": str(e)}), 500

@api_bp.route('/api/fs/mkdir', methods=['POST'])
def fs_mkdir():
    parent = request.json.get('parent_path')
    name = request.json.get('name')
    if not parent or not name: return "Params missing", 400
    
    try:
        new_p = os.path.join(parent, name)
        if not os.path.exists(new_p):
            os.makedirs(new_p)
        return jsonify({"status":"ok", "path": new_p})
    except Exception as e:
        return jsonify({"status":"err", "msg": str(e)}), 500

@api_bp.route('/api/fs/move', methods=['POST'])
def fs_move():
    paths = request.json.get('paths', []) # List of files/folders to move
    target_dir = request.json.get('target_dir')
    if not paths or not target_dir: return "Params missing", 400
    
    try:
        results = []
        cache_updated = False
        items = cfg.load_cache()
        
        for p in paths:
            if not os.path.exists(p): continue
            name = os.path.basename(p)
            new_p = os.path.join(target_dir, name)
            
            if os.path.exists(new_p):
                results.append({"path": p, "status": "exists"})
                continue
                
            os.rename(p, new_p)
            results.append({"path": p, "status": "ok", "new_path": new_p})
            
            # Update cache
            for v in items:
                if v['full_path'] == p:
                    v['full_path'] = new_p
                    v['folder'] = os.path.basename(target_dir)
                    cache_updated = True
                elif v['full_path'].startswith(p + os.sep):
                    v['full_path'] = v['full_path'].replace(p, new_p, 1)
                    cache_updated = True
        
        if cache_updated:
            cfg.save_cache(items)
            
        return jsonify({"status":"ok", "results": results})
    except Exception as e:
        return jsonify({"status":"err", "msg": str(e)}), 500

@api_bp.route('/api/process/queue', methods=['POST'])
def add_to_queue():
    paths = request.json.get('paths', [])
    task_type = request.json.get('type', 'highlight') # 'highlight' or 'convert'

    if not paths: return "No paths provided", 400
    
    # Filter valid existing paths
    valid_paths = [p for p in paths if os.path.exists(p)]
    if not valid_paths: return "No valid files found", 404
    
    media_queue.add_items(valid_paths, task_type=task_type)
    return jsonify({"status": "ok", "msg": f"Added {len(valid_paths)} items to queue for {task_type}"})

@api_bp.route('/api/process/status', methods=['GET'])
def get_queue_status():
    return jsonify(media_queue.get_status())

@api_bp.route('/api/process/clear', methods=['POST'])
def clear_completed():
    media_queue.clear_completed()
    return jsonify({"status": "ok"})

@api_bp.route('/api/process/highlight', methods=['POST'])
def process_highlight():
    p = request.json.get('path')
    if not p or not os.path.exists(p): 
        return jsonify({"status":"err", "msg": "File not found"}), 404
    
    # Create 'Processed' folder in the same directory as the video
    video_dir = os.path.dirname(p)
    processed_dir = os.path.join(video_dir, 'Processed')
    
    try:
        out_path = ff.process_highlight_video(p, processed_dir)
        if out_path:
            # Update cache to show new file immediately
            # The scanner usually handles this, but we can force add it for UX
            c = cfg.load_config()
            if processed_dir not in c["video_dirs"]:
                c["video_dirs"].append(processed_dir)
                cfg.save_config(c)
                
            return jsonify({"status":"ok", "output": out_path})
        else:
            return jsonify({"status":"err", "msg": "FFmpeg failed"}), 500
    except Exception as e:
        return jsonify({"status":"err", "msg": str(e)}), 500

@api_bp.route('/api/stream')
def stream_video():
    path = request.args.get('path')
    if not path or not os.path.exists(path): return "File not found", 404
    
    range_header = request.headers.get('Range', None)
    if not range_header:
        return send_file(path)
    
    size = os.path.getsize(path)
    byte1, byte2 = 0, None
    m = re.search(r'(\d+)-(\d*)', range_header)
    g = m.groups()
    
    if g[0]: byte1 = int(g[0])
    if g[1]: byte2 = int(g[1])
    
    length = size - byte1
    if byte2 is not None:
        length = byte2 + 1 - byte1
    
    def generate():
        try:
            with open(path, 'rb') as f:
                f.seek(byte1)
                remaining = length
                while remaining > 0:
                    chunk_size = min(remaining, 1024 * 512) # 512KB chunks
                    data = f.read(chunk_size)
                    if not data: break
                    remaining -= len(data)
                    yield data
        except Exception as e:
            print(f"Stream error: {e}")

    EXT_MAP = {
        '.mkv': 'video/x-matroska',
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.wmv': 'video/x-ms-wmv',
        '.flv': 'video/x-flv',
        '.webm': 'video/webm',
        '.ts': 'video/mp2t',
        '.m2ts': 'video/mp2t'
    }
    ext = os.path.splitext(path)[1].lower()
    mime = EXT_MAP.get(ext)
    
    if not mime:
        mime, _ = mimetypes.guess_type(path)
    if not mime:
        mime = 'video/mp4'
    
    rv = Response(generate(), 206, mimetype=mime, direct_passthrough=True)
    rv.headers.add('Content-Range', f'bytes {byte1}-{byte1+length-1}/{size}')
    rv.headers.add('Content-Length', str(length))
    rv.headers.add('Accept-Ranges', 'bytes')
    return rv
