import subprocess
import os
from functools import lru_cache
from constants import FFMPEG_PATH, FFPROBE_PATH, THUMB_SEEK_TIME, THUMB_SIZE, PREVIEW_SEEK_TIME, PREVIEW_DURATION, PREVIEW_SIZE
import ffmpeg_conversion
from ffmpeg_runtime import (
    FFMPEG_LONG_TIMEOUT,
    FFMPEG_SEMAPHORE,
    FFMPEG_SHORT_TIMEOUT,
    FFPROBE_TIMEOUT,
)

ffmpeg_semaphore = FFMPEG_SEMAPHORE

def validate_media_output(path):
    """Validate a generated media file before any destructive source cleanup."""
    if not os.path.exists(path) or os.path.getsize(path) <= 0:
        return False
    try:
        cmd = [
            FFPROBE_PATH, '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_type:format=duration',
            '-of', 'json', path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=FFPROBE_TIMEOUT)
        if res.returncode != 0:
            return False
        import json
        payload = json.loads(res.stdout or '{}')
        has_video = any(s.get('codec_type') == 'video' for s in payload.get('streams', []))
        duration = float((payload.get('format') or {}).get('duration') or 0)
        return has_video and duration > 0
    except Exception:
        return False

def generate_thumbnail(media_path, output_path, is_image=False):
    """Tạo ảnh thumbnail từ video hoặc resize ảnh gốc"""
    with ffmpeg_semaphore:
        try:
            if is_image:
                cmd = [
                    FFMPEG_PATH, '-y', 
                    '-i', media_path, 
                    '-vf', f'scale={THUMB_SIZE}:force_original_aspect_ratio=increase,crop={THUMB_SIZE}', 
                    output_path
                ]
            else:
                # Giai đoạn 1: Fast-seek (Cực nhanh, trước -i)
                cmd = [
                    FFMPEG_PATH, '-y', 
                    '-ss', THUMB_SEEK_TIME, 
                    '-i', media_path, 
                    '-vframes', '1', 
                    '-vf', f'scale={THUMB_SIZE}:force_original_aspect_ratio=increase,crop={THUMB_SIZE}', 
                    '-q:v', '5', 
                    output_path
                ]
            
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=FFMPEG_SHORT_TIMEOUT)
            if res.returncode != 0:
                if is_image: return False
                
                # Giai đoạn 2: Slow-seek (Bền bỉ hơn, sau -i, seek tại 1s)
                # Giúp xử lý các video quá ngắn hoặc header 'Duration: N/A'
                cmd_fallback = [
                    FFMPEG_PATH, '-loglevel', 'error', '-y',
                    '-analyzeduration', '10M', '-probesize', '10M',
                    '-i', media_path,
                    '-ss', '00:00:01', 
                    '-vframes', '1',
                    '-vf', f'scale={THUMB_SIZE}:force_original_aspect_ratio=increase,crop={THUMB_SIZE}',
                    '-q:v', '5',
                    output_path
                ]
                res2 = subprocess.run(cmd_fallback, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=FFMPEG_SHORT_TIMEOUT)
                if res2.returncode == 0: return True
                
                # Giai đoạn 3: Cuối cùng - Không seek gì cả, lấy frame đầu tiên
                cmd_last = [
                    FFMPEG_PATH, '-y', 
                    '-i', media_path, 
                    '-vframes', '1', 
                    '-vf', f'scale={THUMB_SIZE}:force_original_aspect_ratio=increase,crop={THUMB_SIZE}', 
                    output_path
                ]
                res3 = subprocess.run(cmd_last, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=FFMPEG_SHORT_TIMEOUT)
                if res3.returncode != 0:
                    print(f"FFmpeg Ultimate Error for {media_path}: {res3.stderr}")
                return res3.returncode == 0
                
            return True
        except Exception as e:
            print(f"FFmpeg Exception: {e}")
            return False

def generate_preview(media_path, output_path):
    """Tạo clip preview (mp4) từ video bằng codec x264"""
    with ffmpeg_semaphore:
        try:
            # Giai đoạn 1: Fast-seek
            cmd = [
                FFMPEG_PATH, '-y', 
                '-ss', PREVIEW_SEEK_TIME, 
                '-i', media_path, 
                '-t', PREVIEW_DURATION, 
                '-vf', f'scale={PREVIEW_SIZE}:force_original_aspect_ratio=increase,crop={PREVIEW_SIZE}', 
                '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                '-threads', '1', '-movflags', '+faststart',
                output_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=FFMPEG_SHORT_TIMEOUT)
            if res.returncode != 0:
                # Giai đoạn 2: Slow-seek tại 1s
                cmd_fallback = [
                    FFMPEG_PATH, '-y', 
                    '-analyzeduration', '10M', '-probesize', '10M',
                    '-i', media_path,
                    '-ss', '00:00:01',
                    '-t', PREVIEW_DURATION, 
                    '-vf', f'scale={PREVIEW_SIZE}:force_original_aspect_ratio=increase,crop={PREVIEW_SIZE}', 
                    '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                    '-threads', '1', '-movflags', '+faststart',
                    output_path
                ]
                res2 = subprocess.run(cmd_fallback, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=FFMPEG_SHORT_TIMEOUT)
                if res2.returncode == 0: return True
                
                # Giai đoạn 3: No seek
                cmd_last = [c for c in cmd if c != '-ss' and c != PREVIEW_SEEK_TIME]
                res3 = subprocess.run(cmd_last, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=FFMPEG_SHORT_TIMEOUT)
                return res3.returncode == 0
            return True
        except Exception as e:
            print(f"FFmpeg Preview Exception: {e}")
            return False

def check_ffmpeg_presence():
    """Kiểm tra FFmpeg có trong PATH không"""
    try:
        subprocess.run([FFMPEG_PATH, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=FFMPEG_SHORT_TIMEOUT)
        return True
    except (FileNotFoundError, subprocess.SubprocessError):
        return False

@lru_cache(maxsize=4)
def get_best_gpu_encoder(codec="h264"):
    """Detect available hardware encoders for the specified codec (h264 or hevc)"""
    try:
        res = subprocess.run([FFMPEG_PATH, "-encoders"], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=FFMPEG_SHORT_TIMEOUT)
        encoders = res.stdout.lower()
        if codec == "hevc":
            if "hevc_nvenc" in encoders: return "hevc_nvenc"
            if "hevc_qsv" in encoders: return "hevc_qsv"
            if "hevc_amf" in encoders: return "hevc_amf"
            return "libx265"
        else:
            if "h264_nvenc" in encoders: return "h264_nvenc"
            if "h264_qsv" in encoders: return "h264_qsv"
            if "h264_amf" in encoders: return "h264_amf"
            return "libx264"
    except: pass
    return "libx265" if codec == "hevc" else "libx264"

def get_video_duration(media_path):
    """L lấy độ dài video (giây) bằng ffprobe"""
    try:
        from constants import FFPROBE_PATH
        cmd = [
            FFPROBE_PATH, 
            '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            media_path
        ]
        # Không dùng semaphore cho probe vì nó nhanh và ít tốn resource
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=FFPROBE_TIMEOUT)
        if res.returncode == 0:
            return float(res.stdout.strip())
    except:
        pass
    return 0.0

def process_highlight_video(input_path, output_dir, delete_src=False):
    """Create a highlight; source deletion is intentional but happens only after validation."""
    with ffmpeg_semaphore:
        try:
            filename = os.path.basename(input_path)
            name, _ = os.path.splitext(filename)
            output_path = os.path.join(output_dir, f"{name}_highlight.mp4")
            temp_output = output_path + '.partial.mp4'

            os.makedirs(output_dir, exist_ok=True)
            if os.path.exists(temp_output):
                os.remove(temp_output)

            cmd = [
                FFMPEG_PATH, '-y',
                '-threads', '0',
                '-ss', '900',
                '-i', input_path,
                '-vf', "select='lt(mod(t,60),10)',setpts=N/FRAME_RATE/TB",
                '-af', "aselect='lt(mod(t,60),10)',asetpts=N/SR/TB",
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '18',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-movflags', '+faststart',
                temp_output
            ]

            print(f"Processing Highlight (Pure CPU): {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=FFMPEG_LONG_TIMEOUT)
            if res.returncode != 0 or not validate_media_output(temp_output):
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                print(f"Highlight validation failed for {input_path}")
                return None

            os.replace(temp_output, output_path)
            if delete_src:
                os.remove(input_path)
                print(f"Auto-cleanup: Deleted original {input_path}")
            return output_path
        except Exception as e:
            print(f"FFmpeg Highlight Exception: {e}")
            return None
def remux_ts_to_mp4(input_path, output_path):
    return ffmpeg_conversion.remux_ts_to_mp4(
        input_path,
        output_path,
        ffmpeg_semaphore,
    )


def convert_ts_to_mp4(input_path, delete_src=True):
    return ffmpeg_conversion.convert_ts_to_mp4(
        input_path,
        delete_src,
        semaphore=ffmpeg_semaphore,
        validate_output=validate_media_output,
        get_encoder=get_best_gpu_encoder,
        remux=remux_ts_to_mp4,
    )
