import os
import time
from config_manager import save_cache, load_cache, load_config
from category_service import get_categories
from queue_worker import media_queue
from nfo_service import parse_nfo

VIDEO_EXTS = ('.mp4', '.ts', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm')
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif')

def scan_videos(video_dirs):
    """Quét các thư mục để tìm file video và hình ảnh"""
    old_cache = load_cache()
    # Map để lưu giữ views và date_added cũ
    meta_map = {v["full_path"]: {
        "views": v.get("views", 0), 
        "date_added": v.get("date_added", 0),
        "jav_metadata": v.get("jav_metadata"),
        "nfo_metadata": v.get("nfo_metadata")
    } for v in old_cache}
    
    items = []
    current_time = time.time()
    
    # Auto-convert & Scraper config
    cfg = load_config()
    auto_convert = False #cfg.get("auto_convert_ts", True) # Disable auto-convert by default
    enable_scraping = cfg.get("enable_jav_scraping", False) # Mặc định tắt (User request)
    
    # Đếm tổng số file trước để hiện tiến độ
    print("Đang chuẩn bị danh sách file...")
    all_files_to_process = []
    for bdir in video_dirs:
        if not os.path.exists(bdir): continue
        for root, dirs, files in os.walk(bdir):
            if '.mycinema' in root: continue
            for f in files:
                if f.lower().endswith(VIDEO_EXTS): # Chỉ lấy video
                    all_files_to_process.append((root, f))
    
    total_files = len(all_files_to_process)
    print(f"Bắt đầu xử lý {total_files} videos (Scraping: {enable_scraping})...")
    
    processed_count = 0
    for root, f in all_files_to_process:
        processed_count += 1
        lower_f = f.lower()
        # Vì all_files_to_process chỉ chứa video nên is_video luôn True
        is_video = True 
        
        fp = os.path.join(root, f)
        try:
            st = os.stat(fp)
            
            old_meta = meta_map.get(fp, {})
            current_views = old_meta.get("views", 0)
            jav_meta = old_meta.get("jav_metadata")
            nfo_meta = old_meta.get("nfo_metadata")
            
            # --- Ưu tiên 1: Đọc Tags từ chính file video (do AI chèn) ---
            import metadata_injector
            internal_blob = metadata_injector.read_metadata(fp)
            if internal_blob:
                print(f"  [SmartTag] Đọc thông tin từ file: {f}")
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

            date_added = old_meta.get("date_added")
            if not date_added:
                 date_added = current_time
            
            # Categorize
            # 1. Thử lấy từ NFO hoặc Scraper cũ
            cats, jav_meta = get_categories(f, existing_metadata=jav_meta, nfo_metadata=nfo_meta, skip_scraping=not enable_scraping)
            
            # 2. TỰ ĐỘNG: Nếu chưa có metadata xịn và bật LLM auto
            auto_llm = False #cfg.get("enable_llm_metadata", False) # Tắt theo yêu cầu user (Manual trigger only)
            if auto_llm and not nfo_meta and (not jav_meta or jav_meta.get('not_found')):
                # Lấy thẳng tên file đi tìm kiếm (Bỏ bước Regex theo yêu cầu người dùng)
                print(f"  [Auto-LLM] Tra cứu cho: {f}")
                from search_service import search_jav_context
                from llm_service import normalize_metadata_with_llm
                
                # Search web bằng tên file trực tiếp
                context = search_jav_context(f)
                # LLM tự đọc tên file và context để chuẩn hóa
                llm_result = normalize_metadata_with_llm(f, context)
                if llm_result:
                    jav_meta = {
                        'code': llm_result.get('code'),
                        'title': llm_result.get('title'),
                        'actors': llm_result.get('actors', []),
                        'genres': llm_result.get('genres', []),
                        'studio': llm_result.get('studio'),
                        'source': 'llm_local',
                        'timestamp': time.time()
                    }
                    new_cats = []
                    for g in llm_result.get('genres', []): new_cats.append(g)
                    if llm_result.get('studio'): new_cats.append(f"Studio: {llm_result['studio'].upper()}")
                    for a in llm_result.get('actors', []): new_cats.append(f"Diễn viên: {a}")
                    cats = list(dict.fromkeys(cats + new_cats))

            items.append({
                "name": nfo_meta.get('title') if nfo_meta and nfo_meta.get('title') else (jav_meta.get('title') if jav_meta and jav_meta.get('title') else os.path.splitext(f)[0]),
                "ext": os.path.splitext(f)[1][1:].upper(),
                "type": "video",
                "full_path": fp,
                "folder": os.path.basename(root),
                "size": st.st_size,
                "size_fmt": format_size(st.st_size),
                "mtime": st.st_mtime,
                "date_added": date_added,
                "views": current_views,
                "categories": cats,
                "jav_metadata": jav_meta,
                "nfo_metadata": nfo_meta
            })

            # Auto-convert TS
            if auto_convert and lower_f.endswith('.ts'):
                media_queue.add_items([fp], task_type="convert")
                
            # Cập nhật tiến độ
            if processed_count % 50 == 0 or processed_count == total_files:
                print(f"Tiến độ: {processed_count}/{total_files} videos...")
                # KHÔNG save_cache ở đây để tránh trigger Flask reload loop
                
        except Exception as e:
            print(f"Lỗi xử lý video {f}: {e}")
            continue
    
    save_cache(items)
    print("Quét hoàn tất!")
    return items

def format_size(size_bytes):
    if size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024} KB"
    return f"{size_bytes // (1024 * 1024)} MB"
