import hashlib
import os
from constants import METADATA_DIR_NAME

def get_hash(p):
    """Tạo MD5 hash cho đường dẫn file"""
    return hashlib.md5(p.encode()).hexdigest()

def get_metadata_paths(video_path):
    """
    Trả về đường dẫn thumbnail và preview dựa trên vị trí video.
    Cấu trúc: /path/to/video_dir/.mycinema/{hash}.jpg
    """
    video_dir = os.path.dirname(video_path)
    file_hash = get_hash(video_path)
    
    meta_root = os.path.join(video_dir, METADATA_DIR_NAME)
    
    # Không chia subfolder thumbnails/preview nữa để đơn giản, hoặc chia nếu thích
    # User yêu cầu "folder con", ta có thể làm .mycinema/thumbnails/ và .mycinema/previews/
    # Nhưng để gọn gàng trong folder con, ta để chung cũng được, đuôi file khác nhau.
    # Tuy nhiên để chuyên nghiệp ta chia ra.
    
    thumb_dir = os.path.join(meta_root, "thumbnails")
    prev_dir = os.path.join(meta_root, "previews")
    
    thumb_path = os.path.join(thumb_dir, f"{file_hash}.jpg")
    prev_path = os.path.join(prev_dir, f"{file_hash}.mp4")
    
    return {
        "root": meta_root,
        "thumb_dir": thumb_dir,
        "prev_dir": prev_dir,
        "thumb_path": thumb_path,
        "prev_path": prev_path
    }

def ensure_metadata_dirs(paths):
    """Đảm bảo các thư mục tồn tại"""
    if not os.path.exists(paths["thumb_dir"]): os.makedirs(paths["thumb_dir"])
    if not os.path.exists(paths["prev_dir"]): os.makedirs(paths["prev_dir"])

def sync_artifacts(old_path, new_path):
    """
    Di chuyển/Đổi tên thumbnails và previews khi file gốc thay đổi vị trí.
    Dùng hash của đường dẫn để xác định file artifact.
    """
    try:
        old_hash = get_hash(old_path)
        new_hash = get_hash(new_path)
        
        # Nếu hash không đổi (trường hợp lạ?), bỏ qua
        if old_hash == new_hash: return

        # Tìm vị trí metadata cũ
        old_dir = os.path.dirname(old_path)
        old_meta_root = os.path.join(old_dir, METADATA_DIR_NAME)
        
        # Tìm vị trí metadata mới
        new_dir = os.path.dirname(new_path)
        new_meta_root = os.path.join(new_dir, METADATA_DIR_NAME)
        
        # Đảm bảo thư mục đích tồn tại
        thumb_new_dir = os.path.join(new_meta_root, "thumbnails")
        prev_new_dir = os.path.join(new_meta_root, "previews")
        if not os.path.exists(thumb_new_dir): os.makedirs(thumb_new_dir)
        if not os.path.exists(prev_new_dir): os.makedirs(prev_new_dir)
        
        # 1. Sync Thumbnail
        thumb_old = os.path.join(old_meta_root, "thumbnails", f"{old_hash}.jpg")
        thumb_new = os.path.join(thumb_new_dir, f"{new_hash}.jpg")
        
        if os.path.exists(thumb_old):
            # Nếu đích đã có rồi thì thôi (tránh ghi đè nếu trùng)
            if not os.path.exists(thumb_new):
                os.rename(thumb_old, thumb_new)
        elif os.path.exists(os.path.join(old_dir, f"{old_hash}.jpg")): 
            # Legacy support: old structure at root
            if not os.path.exists(thumb_new):
                os.rename(os.path.join(old_dir, f"{old_hash}.jpg"), thumb_new)

        # 2. Sync Preview
        prev_old = os.path.join(old_meta_root, "previews", f"{old_hash}.mp4")
        prev_new = os.path.join(prev_new_dir, f"{new_hash}.mp4")
        
        if os.path.exists(prev_old):
            if not os.path.exists(prev_new):
                os.rename(prev_old, prev_new)
                
        return True
    except Exception as e:
        print(f"Sync Artifact Error ({old_path} -> {new_path}): {e}")
        return False
