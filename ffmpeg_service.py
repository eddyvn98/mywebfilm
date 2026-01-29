import subprocess
import os
import threading
from constants import FFMPEG_PATH, THUMB_SEEK_TIME, THUMB_SIZE, PREVIEW_SEEK_TIME, PREVIEW_DURATION, PREVIEW_SIZE

# Giới hạn tối đa 2 tiến trình FFmpeg chạy cùng lúc để tránh quá tải RAM/CPU
ffmpeg_semaphore = threading.Semaphore(2)

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
                # Dùng -ss sau -i để an toàn hơn với video cực ngắn (dù chậm hơn chút)
                cmd = [
                    FFMPEG_PATH, '-y', 
                    '-i', media_path, 
                    '-ss', THUMB_SEEK_TIME, 
                    '-vframes', '1', 
                    '-vf', f'scale={THUMB_SIZE}:force_original_aspect_ratio=increase,crop={THUMB_SIZE}', 
                    '-q:v', '5', 
                    output_path
                ]
            
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if res.returncode != 0:
                print(f"FFmpeg Thumb Error for {media_path}: {res.stderr}")
                # Thử lại nhưng không có seek nếu thất bại (có thể do video quá ngắn)
                if not is_image:
                    cmd_no_ss = [c for c in cmd if c != '-ss' and c != THUMB_SEEK_TIME]
                    res2 = subprocess.run(cmd_no_ss, capture_output=True, text=True, encoding='utf-8', errors='replace')
                    if res2.returncode == 0: return True
                return False
            return True
        except Exception as e:
            print(f"FFmpeg Exception: {e}")
            return False

def generate_preview(media_path, output_path):
    """Tạo clip preview (mp4) từ video bằng codec x264"""
    with ffmpeg_semaphore:
        try:
            cmd = [
                FFMPEG_PATH, '-y', 
                '-ss', PREVIEW_SEEK_TIME, 
                '-t', PREVIEW_DURATION, 
                '-i', media_path, 
                '-vf', f'scale={PREVIEW_SIZE}:force_original_aspect_ratio=increase,crop={PREVIEW_SIZE}', 
                '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                output_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if res.returncode != 0:
                print(f"FFmpeg Preview Error for {media_path}: {res.stderr}")
                # Thử lại không có seek
                cmd_no_ss = [c for c in cmd if c != '-ss' and c != PREVIEW_SEEK_TIME]
                res2 = subprocess.run(cmd_no_ss, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if res2.returncode == 0: return True
                return False
            return True
        except Exception as e:
            print(f"FFmpeg Preview Exception: {e}")
            return False

def check_ffmpeg_presence():
    """Kiểm tra FFmpeg có trong PATH không"""
    try:
        subprocess.run([FFMPEG_PATH, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def get_best_gpu_encoder():
    """Detect available hardware encoders"""
    try:
        res = subprocess.run([FFMPEG_PATH, "-encoders"], capture_output=True, text=True, encoding='utf-8', errors='replace')
        encoders = res.stdout.lower()
        if "h264_nvenc" in encoders: return "h264_nvenc"
        if "h264_qsv" in encoders: return "h264_qsv"
        if "h264_amf" in encoders: return "h264_amf"
    except: pass
    return "libx264"

def process_highlight_video(input_path, output_dir, delete_src=False):
    """
    Xử lý video highlight:
    1. Cắt bỏ 15 phút đầu.
    2. Mỗi 1 phút lấy 10 giây đầu.
    3. Xuất ra file mp4 trong thư mục output_dir.
    4. Xóa file gốc nếu thành công và delete_src=True.
    """
    with ffmpeg_semaphore:
        try:
            filename = os.path.basename(input_path)
            name, _ = os.path.splitext(filename)
            output_path = os.path.join(output_dir, f"{name}_highlight.mp4")
            
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            encoder = get_best_gpu_encoder()
            
            # Preset mapping
            preset = 'fast' if 'nvenc' in encoder else 'ultrafast'
            
            # Base command parts
            # REMOVED -hwaccel cuda because our filters (select) run on CPU.
            # Transferring frames between GPU and RAM for filters is slower 
            # than just decoding on CPU for this specific highlight logic.
            hwaccel_part = [] 
            encoder_extra = []
            
            if 'nvenc' in encoder:
                encoder_extra = ['-gpu', '0', '-rc:v', 'vbr', '-cq:v', '24']
            
            cmd_base = [
                FFMPEG_PATH, '-y',
                '-threads', '0', # Use all CPU cores for decoding/filtering
                '-ss', '900',
                '-i', input_path,
                '-vf', "select='lt(mod(t,60),10)',setpts=N/FRAME_RATE/TB",
                '-af', "aselect='lt(mod(t,60),10)',asetpts=N/SR/TB",
            ]

            def run_ffmpeg(target_encoder):
                # Build specific encoding part
                is_gpu = target_encoder != 'libx264'
                enc_part = ['-c:v', target_encoder]
                if is_gpu:
                    enc_part.extend(encoder_extra)
                
                # Preset and quality/bitrate
                if not is_gpu:
                    enc_part.extend(['-preset', 'ultrafast', '-crf', '26'])
                else:
                    enc_part.extend(['-preset', preset, '-b:v', '4M'])
                
                enc_part.extend(['-c:a', 'aac', output_path])
                
                full_cmd = cmd_base + enc_part
                print(f"Processing Highlight ({target_encoder}): {' '.join(full_cmd)}")
                return subprocess.run(full_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')

            res = run_ffmpeg(encoder)
            
            if res.returncode != 0:
                print(f"FFmpeg Process Error: {res.stderr}")
                return None
            
            if delete_src and os.path.exists(output_path):
                try:
                    os.remove(input_path)
                    print(f"Auto-cleanup: Deleted original {input_path}")
                except Exception as e:
                    print(f"Cleanup Error: {e}")
                
            return output_path
        except Exception as e:
            print(f"FFmpeg Process Exception: {e}")
            return None

def convert_ts_to_mp4(input_path, delete_src=True):
    """
    Chuyển đổi file .ts sang .mp4 dùng HEVC/H.264 (remux nếu có thể, không thì re-encode)
    Mặc định xóa file gốc nếu thành công.
    """
    with ffmpeg_semaphore:
        try:
            filename = os.path.basename(input_path)
            name, _ = os.path.splitext(filename)
            output_path = os.path.join(os.path.dirname(input_path), f"{name}.mp4")
            
            # Ưu tiên copy stream (không encode lại) nếu format hỗ trợ, cực nhanh
            # Tuy nhiên để đảm bảo tương thích trình duyệt tốt nhất (AAC audio), ta thường re-encode audio
            encoder = get_best_gpu_encoder()
            
            cmd = [
                FFMPEG_PATH, '-y',
                '-i', input_path,
                '-c:v', encoder if encoder != 'libx264' else 'libx264',
            ]
            
            if encoder == 'libx264':
                cmd.extend(['-preset', 'ultrafast', '-crf', '23'])
            else:
                preset = 'fast' if 'nvenc' in encoder else 'ultrafast'
                cmd.extend(['-preset', preset, '-b:v', '5M']) # 5Mbps quality
                
            cmd.extend(['-c:a', 'aac', '-b:a', '128k', output_path])
            
            print(f"Converting TS to MP4: {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if res.returncode != 0:
                print(f"Conversion Error: {res.stderr}")
                return None
                
            if delete_src and os.path.exists(output_path):
                try:
                    os.remove(input_path)
                    print(f"Auto-convert: Deleted original TS {input_path}")
                except Exception as e:
                    print(f"Cleanup Error: {e}")
                    
            return output_path
        except Exception as e:
            print(f"Convert Exception: {e}")
            return None
