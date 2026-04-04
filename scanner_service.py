import os
import time
import re
import json
import sys
from datetime import datetime
import ffmpeg_service
from config_manager import save_cache, load_cache, load_config
from category_service import get_categories
from queue_worker import media_queue
from nfo_service import parse_nfo
from nfo_service import parse_nfo
# import ffmpeg_service (moved inside to be safer)

VIDEO_EXTS = ('.mp4', '.ts', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm')
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif')


def safe_print(message):
    """Print safely on Windows consoles that may not support Unicode."""
    try:
        print(message)
    except UnicodeEncodeError:
        try:
            encoded = str(message).encode(sys.stdout.encoding or "utf-8", errors="replace")
            print(encoded.decode(sys.stdout.encoding or "utf-8", errors="replace"))
        except Exception:
            # Last resort: avoid crashing scan due to logging.
            pass

def scan_videos(video_dirs):
    """Quét các thư mục để tìm file video và hình ảnh"""
    import ffmpeg_service
    old_cache = load_cache()
    # Map để lưu giữ views và date_added cũ
    meta_map = {v["full_path"]: {
        "views": v.get("views", 0), 
        "date_added": v.get("date_added", 0),
        "jav_metadata": v.get("jav_metadata"),
        "nfo_metadata": v.get("nfo_metadata"),
        "categories": v.get("categories", [])
    } for v in old_cache}
    
    # Backup map based on base name to handle extension changes (e.g. .ts -> .mp4)
    base_name_map = {}
    
    # Smart Scan: Map to detect moved files (Name + Size -> Path)
    # Only consider files that MIGHT be missing (we check existence later or assume if not found in scan)
    # Actually, efficient way: Build map of ALL old files (Name, Size) -> (OldPath, Data)
    move_candidates = {} 
    
    for v in old_cache:
        base = os.path.splitext(os.path.basename(v["full_path"]))[0]
        key = (base, v.get("folder"))
        if key not in base_name_map:
            base_name_map[key] = meta_map[v["full_path"]]
            
        # Add to move candidates: (Filename, Size)
        # Note: v['name'] might be Title, we need filename. os.path.basename(v['full_path'])
        fname = os.path.basename(v['full_path'])
        fsize = v.get('size', 0)
        move_candidates[(fname, fsize)] = (v['full_path'], meta_map[v["full_path"]])
    
    items = []
    current_time = time.time()
    
    # Determine reachable vs unreachable roots
    reachable_roots = []
    unreachable_roots = []
    for bdir in video_dirs:
        # We consider a root reachable if its folder exists
        if os.path.exists(bdir):
            reachable_roots.append(bdir)
        else:
            unreachable_roots.append(bdir)

    items = []
    current_time = time.time()
    
    # Auto-convert & Scraper config
    cfg = load_config()
    auto_convert = False #cfg.get("auto_convert_ts", True) # Disable auto-convert by default
    enable_scraping = cfg.get("enable_jav_scraping", False) # Mặc định tắt (User request)
    
    # Đếm tổng số file trước để hiện tiến độ
    safe_print(f"Bắt đầu quét. Thư mục Online: {len(reachable_roots)}, Offline: {len(unreachable_roots)}")
    all_files_to_process = []
    for bdir in reachable_roots:
        for root, dirs, files in os.walk(bdir):
            if '.mycinema' in root: continue
            for f in files:
                lower_f = f.lower()
                if lower_f.endswith(VIDEO_EXTS) or lower_f.endswith(IMAGE_EXTS):
                    all_files_to_process.append((root, f))
    
    total_files = len(all_files_to_process)
    safe_print(f"Bắt đầu xử lý {total_files} videos (Scraping: {enable_scraping})...")
    
    processed_count = 0
    processed_paths = set()
    for root, f in all_files_to_process:
        fp = os.path.join(root, f)
        if fp in processed_paths:
            continue
        processed_paths.add(fp)
        
        processed_count += 1
        lower_f = f.lower()
        is_video = lower_f.endswith(VIDEO_EXTS)
        try:
            st = os.stat(fp)
            
            # --- Logic trích xuất ngày từ tên tệp (Đa định dạng) ---
            file_date_ts = None
            # Pattern: YYYY-MM-DD, YYYY_MM_DD, YYYY MM DD, hoặc YYYYMMDD
            # Ưu tiên các định dạng có dấu phân cách để tránh nhầm lẫn với mã JAV
            date_match = re.search(r'(\d{4})[-_\s](\d{2})[-_\s](\d{2})', f)
            if not date_match:
                # Fallback: IMG_20180327
                date_match = re.search(r'(?:IMG|VID|MV)?_?(\d{4})(\d{2})(\d{2})', f, re.IGNORECASE)
            
            if date_match:
                try:
                    yyyy, mm, dd = date_match.groups()
                    yy_int, mm_int, dd_int = int(yyyy), int(mm), int(dd)
                    # Kiểm tra tính hợp lệ sơ bộ
                    if 1990 < yy_int < 2030 and 1 <= mm_int <= 12 and 1 <= dd_int <= 31:
                        dt_obj = datetime(yy_int, mm_int, dd_int)
                        file_date_ts = dt_obj.timestamp()
                        safe_print(f"  [Dòng thời gian] Nhận diện {f} -> {yyyy}-{mm}-{dd}")
                except Exception as e:
                    # print(f"  [DateError] {f}: {e}")
                    pass
            # -----------------------------------------------------------
            
            # Move Detection Logic
            # Detect if this file matches a lost file from old_cache
            # Criteria: Same Name + Same Size + Old Path Missing
            old_meta = meta_map.get(fp)
            
            if not old_meta:
                 # Check if this "new" file is actually a moved file
                 # We look for a file in old_cache with same name & size that NO LONGER EXISTS at old path
                 candidate_key = (f, st.st_size)
                 candidate = move_candidates.get(candidate_key)
                 
                 if candidate:
                     old_path, old_data = candidate
                     # Confirm old path is gone (Double check)
                     if not os.path.exists(old_path):
                         safe_print(f"  [SmartScan] Detected Move: {old_path} -> {fp}")
                         # Adopt old metadata
                         old_meta = old_data
                         # Sync Artifacts
                         try:
                             from utils import sync_artifacts
                             if sync_artifacts(old_path, fp):
                                 safe_print(f"  [SmartScan] Artifacts synced.")
                         except Exception as e:
                             safe_print(f"  [SmartScan] Sync failed: {e}")
                             
                         # Remove from candidates so we don't match again
                         del move_candidates[candidate_key]
            
            if not old_meta:
                # Try fuzzy match (base name + folder) - LEGACY LOGIC
                base = os.path.splitext(f)[0]
                folder = os.path.basename(root)
                old_meta = base_name_map.get((base, folder), {})
                if old_meta:
                    safe_print(f"  [Sync] Found metadata for extension-changed file: {f}")

            current_views = old_meta.get("views", 0)
            jav_meta = old_meta.get("jav_metadata")
            nfo_meta = old_meta.get("nfo_metadata")
            old_categories = old_meta.get("categories", [])

            # Special logic for converted files: If we found metadata from a previous version
            # and that version was likely the one we just converted...
            if jav_meta and lower_f.endswith('.mp4'):
                # Check if it was converted
                # For now, let's just make sure is_ai_verified is preserved or set
                if 'is_ai_verified' not in jav_meta:
                    jav_meta['is_ai_verified'] = True
            
            # --- Cáº£i thiá»‡n tá»‘c Ä‘á»™: Chỉ Ä‘á»c metadata tá»« file náº¿u trong Cache chÆ°a có ---
            if not jav_meta:
                import metadata_injector
                internal_blob = metadata_injector.read_metadata(fp)
                if internal_blob:
                    safe_print(f"  [SmartTag] Äá»c thông tin tá»« file: {f}")
                    jav_meta = {
                        'code': internal_blob.get('code'),
                        'title': internal_blob.get('title'),
                        'actors': internal_blob.get('actors', []),
                        'genres': internal_blob.get('genres', []),
                        'studio': internal_blob.get('studio'),
                        'source': 'internal_tag',
                        'timestamp': time.time()
                    }

            # Check for NFO file
            nfo_path = os.path.splitext(fp)[0] + '.nfo'
            if os.path.exists(nfo_path):
                nfo_meta = parse_nfo(nfo_path)

            # Ưu tiên: 1. Ngày từ tên file, 2. Ngày cũ trong cache, 3. Ngày mtime của file
            date_added = file_date_ts if file_date_ts else old_meta.get("date_added")
            if not date_added:
                 date_added = st.st_mtime
            
            # Categorize
            cats, jav_meta = get_categories(f, existing_metadata=jav_meta, nfo_metadata=nfo_meta, skip_scraping=not enable_scraping)
            
            if old_categories:
                cats = list(dict.fromkeys(cats + old_categories))
            
            duration = 0.0
            if is_video:
                duration = old_meta.get("duration", 0.0)
                if duration <= 0:
                    duration = ffmpeg_service.get_video_duration(fp)

            items.append({
                "name": nfo_meta.get('title') if nfo_meta and nfo_meta.get('title') else (jav_meta.get('title') if jav_meta and jav_meta.get('title') else os.path.splitext(f)[0]),
                "ext": os.path.splitext(f)[1][1:].upper(),
                "type": "video" if is_video else "image",
                "full_path": fp,
                "folder": os.path.basename(root),
                "size": st.st_size,
                "size_fmt": format_size(st.st_size),
                "mtime": st.st_mtime,
                "date_added": date_added,
                "views": current_views,
                "categories": cats,
                "duration": duration,
                
                "jav_metadata": jav_meta,
                "nfo_metadata": nfo_meta,
                "is_offline": False
            })

            # Auto-convert TS
            if auto_convert and lower_f.endswith('.ts'):
                media_queue.add_items([fp], task_type="convert")
                
            # Cập nhật tiến độ
            if processed_count % 50 == 0 or processed_count == total_files:
                safe_print(f"Tiến độ: {processed_count}/{total_files} videos...")
                
        except Exception as e:
            safe_print(f"Lỗi xử lý video {f}: {e}")
            continue

    # --- STICKY CACHE LOGIC ---
    # Merge existing items with old_cache entries that are currently offline
    for v in old_cache:
        path = v.get("full_path")
        if not path: continue
        
        # If this path was ALREADY processed in the current online scan, skip
        if path in processed_paths:
            continue
            
        # Check if the path belongs to an unreachable root
        is_sticky = False
        for root in unreachable_roots:
            if path.startswith(root):
                is_sticky = True
                break
        
        # If it's sticky, keep it in the cache and mark as offline
        if is_sticky:
            v["is_offline"] = True
            items.append(v)
            processed_paths.add(path) # Mark as kept
    
    save_cache(items)
    safe_print(f"Quét hoàn tất! Tổng cộng: {len(items)} items ({len(reachable_roots)} online, {len(unreachable_roots)} offline roots)")
    return items

def format_size(size_bytes):
    if size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024} KB"
    return f"{size_bytes // (1024 * 1024)} MB"
