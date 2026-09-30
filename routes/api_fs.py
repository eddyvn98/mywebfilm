from flask import Blueprint, jsonify, request
import os
import subprocess
import logging
import config_manager as cfg
from utils import get_metadata_paths, check_path_safe

fs_bp = Blueprint('api_fs', __name__)
logger = logging.getLogger(__name__)

@fs_bp.route('/api/delete_file', methods=['POST'])
def delete_file():
    p = request.json.get('path')
    if not p or not os.path.exists(p):
        return jsonify({"status":"err", "msg": "File not found"}), 404
    if not check_path_safe(p):
        return jsonify({"status":"err", "msg": "Access denied"}), 403
    try:
        os.remove(p)
        logger.info("file_delete path=%r", p)
        paths = get_metadata_paths(p)
        if os.path.exists(paths['thumb_path']): os.remove(paths['thumb_path'])
        if os.path.exists(paths['prev_path']): os.remove(paths['prev_path'])
        items = cfg.load_cache()
        items = [v for v in items if v['full_path'] != p]
        cfg.save_cache(items)
        return jsonify({"status":"ok"})
    except Exception as e:
        logger.exception("filesystem_operation_failed path=%r", locals().get('p'))
        return jsonify({"status":"err", "msg": str(e)}), 500

@fs_bp.route('/api/explorer', methods=['POST'])
def open_explorer():
    p = request.json.get('path')
    if not p or not os.path.exists(p):
        return jsonify({"status":"err", "msg": "File not found"}), 404
    if not check_path_safe(p):
        return jsonify({"status":"err", "msg": "Access denied"}), 403
    try:
        subprocess.run(['explorer', '/select,', os.path.normpath(p)])
        return jsonify({"status":"ok"})
    except Exception as e:
        return jsonify({"status":"err", "msg": str(e)}), 500

@fs_bp.route('/api/fs/rename', methods=['POST'])
def fs_rename():
    old_p = request.json.get('old_path')
    new_name = request.json.get('new_name')
    if not old_p or not new_name: return "Params missing", 400
    
    # Strip any directory separators from new_name to prevent path traversal
    new_name = os.path.basename(new_name)
    if not new_name or new_name in ['.', '..']:
        return jsonify({"status":"err", "msg": "Invalid name"}), 400
        
    if not check_path_safe(old_p):
        return jsonify({"status":"err", "msg": "Access denied"}), 403
        
    try:
        parent = os.path.dirname(old_p)
        new_p = os.path.join(parent, new_name)
        if not check_path_safe(new_p):
            return jsonify({"status":"err", "msg": "Access denied"}), 403
        if os.path.exists(new_p): return jsonify({"status":"err", "msg": "Tên này đã tồn tại"}), 400
        
        # 1. OS Rename
        os.rename(old_p, new_p)
        logger.info("file_rename old=%r new=%r", old_p, new_p)
        
        # 2. Config Update (If it's a source root)
        config = cfg.load_config()
        if old_p in config.get('video_dirs', []):
            config['video_dirs'] = [new_p if x == old_p else x for x in config['video_dirs']]
            cfg.save_config(config)
            
        # 3. Cache & Artifact Update
        items = cfg.load_cache()
        from utils import get_hash, METADATA_DIR_NAME
        
        for v in items:
            if v['full_path'] == old_p:
                # File rename case
                v['full_path'] = new_p
                v['name'] = new_name
                # (Artifacts rename for single file could be added here if needed, 
                # but usually single file rename doesn't change hash if hash is content based? 
                # Wait, our hash IS path based. So we need it here too.)
                try:
                    from utils import sync_artifacts
                    sync_artifacts(old_p, new_p)
                except: pass

            elif v['full_path'].startswith(old_p + os.sep):
                # Folder rename case
                old_full_path = v['full_path']
                new_full_path = old_full_path.replace(old_p, new_p, 1)
                
                # Artifact Rename Logic
                try:
                    # After OS rename, the .mycinema folder has moved to inside new_p
                    # so we just need to update the file hashes inside it.
                    from utils import sync_artifacts
                    sync_artifacts(old_full_path, new_full_path)
                except Exception as e:
                    print(f"Artifact sync failed for {old_full_path}: {e}")

                v['full_path'] = new_full_path
                # Update folder name in cache if it matches the renamed folder
                if v['folder'] == os.path.basename(old_p):
                    v['folder'] = new_name
                    
        cfg.save_cache(items)
        return jsonify({"status":"ok", "new_path": new_p})
    except Exception as e:
        return jsonify({"status":"err", "msg": str(e)}), 500

@fs_bp.route('/api/fs/mkdir', methods=['POST'])
def fs_mkdir():
    parent = request.json.get('parent_path')
    name = request.json.get('name')
    if not parent or not name: return "Params missing", 400
    
    name = os.path.basename(name)
    if not name or name in ['.', '..']:
        return jsonify({"status":"err", "msg": "Invalid folder name"}), 400
        
    if not check_path_safe(parent):
        return jsonify({"status":"err", "msg": "Access denied"}), 403
        
    try:
        new_p = os.path.join(parent, name)
        if not check_path_safe(new_p):
            return jsonify({"status":"err", "msg": "Access denied"}), 403
        if not os.path.exists(new_p): os.makedirs(new_p)
        return jsonify({"status":"ok", "path": new_p})
    except Exception as e:
        return jsonify({"status":"err", "msg": str(e)}), 500

@fs_bp.route('/api/fs/move', methods=['POST'])
def fs_move():
    paths = request.json.get('paths', [])
    target_dir = request.json.get('target_dir')
    if not paths or not target_dir: return "Params missing", 400
    
    if not check_path_safe(target_dir):
        return jsonify({"status":"err", "msg": "Access denied to target directory"}), 403
        
    try:
        results = []
        cache_updated = False
        items = cfg.load_cache()
        from utils import get_hash, METADATA_DIR_NAME

        for p in paths:
            if not os.path.exists(p): continue
            if not check_path_safe(p):
                results.append({"path": p, "status": "access_denied"})
                continue
            name = os.path.basename(p)
            new_p = os.path.join(target_dir, name)
            if os.path.exists(new_p):
                results.append({"path": p, "status": "exists"}); continue
            
            # 1. OS Move
            os.rename(p, new_p)
            logger.info("file_move old=%r new=%r", p, new_p)
            
            # 2. Artifact Sync (OldHash -> NewHash)
            try:
                from utils import sync_artifacts
                sync_artifacts(p, new_p)
            except Exception as e:
                print(f"Artifact move failed for {name}: {e}")

            results.append({"path": p, "status": "ok", "new_path": new_p})
            
            # 3. Cache Update
            for v in items:
                if v['full_path'] == p:
                    v['full_path'] = new_path = new_p
                    v['folder'] = os.path.basename(target_dir)
                    cache_updated = True
                elif v['full_path'].startswith(p + os.sep):
                    v['full_path'] = v['full_path'].replace(p, new_p, 1)
                    cache_updated = True
        if cache_updated: cfg.save_cache(items)
        return jsonify({"status":"ok", "results": results})
    except Exception as e:
        return jsonify({"status":"err", "msg": str(e)}), 500
