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
