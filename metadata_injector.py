import subprocess
import os
import json
import shutil
from constants import FFPROBE_PATH, FFMPEG_PATH
from ffmpeg_runtime import ffmpeg_subprocess_kwargs

def get_ffmpeg_path():
    return FFMPEG_PATH

def inject_metadata_full(file_path, metadata):
    """
    Chèn metadata vào file video dùng FFmpeg (Rất nặng, remux lại file).
    metadata: dict {title, actors, studio, genres, code}
    """
    if not os.path.exists(file_path):
        return False, "File không tồn tại"

def save_metadata_fast(file_path, metadata):
    """
    Lưu metadata siêu nhanh dùng file .nfo sidecar.
    Không động vào file video, tránh lag máy.
    """
    try:
        from nfo_service import save_nfo
        if save_nfo(file_path, metadata):
            return True, "Thành công (NFO)"
        return False, "Lỗi lưu NFO"
    except Exception as e:
        return False, str(e)

def inject_metadata(file_path, metadata):
    """DEPRECATED: Use save_metadata_fast or inject_metadata_full"""
    return save_metadata_fast(file_path, metadata)

    ffmpeg = get_ffmpeg_path()
    temp_file = file_path + ".tmp.mp4"
    
    # Chuẩn bị blob JSON để lưu vào comment/description
    metadata_blob = json.dumps(metadata, ensure_ascii=False)
    
    # Tags cho Windows Explorer và các trình chơi video khác
    # - title: Tiêu đề
    # - artist/author: Diễn viên
    # - album/publisher: Studio
    # - genre: Thể loại
    # - description/synopsis: Chứa mã phim và tiêu đề
    # - comment: Chứa blob JSON để máy đọc lại
    
    actors_str = ", ".join(metadata.get('actors', []))
    genres_str = ", ".join(metadata.get('genres', []))
    studio = metadata.get('studio', '')
    title = metadata.get('title', '')
    code = metadata.get('code', '')
    
    full_desc = f"[{code}] {title}\nActors: {actors_str}\nStudio: {studio}\nGenres: {genres_str}"

    cmd = [
        ffmpeg, "-y", "-i", file_path,
        "-metadata", f"title={title}",
        "-metadata", f"artist={actors_str}",
        "-metadata", f"author={actors_str}",     # Windows Author
        "-metadata", f"album={studio}",
        "-metadata", f"publisher={studio}",    # Windows Publisher
        "-metadata", f"genre={genres_str}",
        "-metadata", f"description={full_desc}", # Windows Description
        "-metadata", f"synopsis={full_desc}",
        "-metadata", f"comment=AI_METADATA:{metadata_blob}",
        "-c", "copy",
        temp_file
    ]
    
    try:
        print(f"Injecting metadata into: {file_path}")
        subprocess.run(cmd, check=True, capture_output=True, **ffmpeg_subprocess_kwargs())
        
        # Kiểm tra file tạm có hợp lệ không trước khi ghi đè
        if os.path.getsize(temp_file) > 0:
            os.remove(file_path)
            os.rename(temp_file, file_path)
            return True, "Thành công"
        else:
            return False, "Lỗi: File tạo ra bị rỗng"
            
    except subprocess.CalledProcessError as e:
        if os.path.exists(temp_file): os.remove(temp_file)
        return False, f"FFmpeg Error: {e.stderr.decode('utf-8', errors='ignore')}"
    except Exception as e:
        if os.path.exists(temp_file): os.remove(temp_file)
        return False, str(e)

def read_metadata(file_path):
    """Đọc metadata từ file dùng ffprobe"""
    cmd = [
        FFPROBE_PATH, "-v", "quiet", "-print_format", "json", "-show_format", file_path
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            check=True,
            **ffmpeg_subprocess_kwargs(),
        )
        data = json.loads(result.stdout)
        tags = data.get('format', {}).get('tags', {})
        
        # Tìm blob AI_METADATA trong comment
        comment = tags.get('comment', '')
        if comment.startswith("AI_METADATA:"):
            return json.loads(comment.replace("AI_METADATA:", "", 1))
            
        return None
    except:
        return None

if __name__ == "__main__":
    # Test
    test_file = r"d:\trading\CinemaWeb\test_video.mp4" # Đảm bảo file tồn tại để test
    if os.path.exists(test_file):
        test_meta = {
            "title": "Phim Test AI",
            "actors": ["Actor A", "Actor B"],
            "studio": "AI Studio",
            "genres": ["Action", "Sci-Fi"],
            "code": "TEST-001"
        }
        ok, msg = inject_metadata(test_file, test_meta)
        print(f"Result: {ok}, {msg}")
        if ok:
            print("Read back:", read_metadata(test_file))
