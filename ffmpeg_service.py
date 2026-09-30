import subprocess
import os
import threading
from constants import FFMPEG_PATH, FFPROBE_PATH, THUMB_SEEK_TIME, THUMB_SIZE, PREVIEW_SEEK_TIME, PREVIEW_DURATION, PREVIEW_SIZE

# Giới hạn tối đa 2 tiến trình FFmpeg chạy cùng lúc để tránh quá tải RAM/CPU
ffmpeg_semaphore = threading.Semaphore(2)

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
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
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
            
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if res.returncode != 0:
                if is_image: return False
                
                # Giai đoạn 2: Slow-seek (Bền bỉ hơn, sau -i, seek tại 1s)
                # Giúp xử lý các video quá ngắn hoặc header 'Duration: N/A'
                cmd_fallback = [
                    FFMPEG_PATH, '-y',
                    '-analyzeduration', '10M', '-probesize', '10M',
                    '-i', media_path,
                    '-ss', '00:00:01', 
                    '-vframes', '1',
                    '-vf', f'scale={THUMB_SIZE}:force_original_aspect_ratio=increase,crop={THUMB_SIZE}',
                    '-q:v', '5',
                    output_path
                ]
                res2 = subprocess.run(cmd_fallback, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if res2.returncode == 0: return True
                
                # Giai đoạn 3: Cuối cùng - Không seek gì cả, lấy frame đầu tiên
                cmd_last = [
                    FFMPEG_PATH, '-y', 
                    '-i', media_path, 
                    '-vframes', '1', 
                    '-vf', f'scale={THUMB_SIZE}:force_original_aspect_ratio=increase,crop={THUMB_SIZE}', 
                    output_path
                ]
                res3 = subprocess.run(cmd_last, capture_output=True, text=True, encoding='utf-8', errors='replace')
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
                output_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
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
                    output_path
                ]
                res2 = subprocess.run(cmd_fallback, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if res2.returncode == 0: return True
                
                # Giai đoạn 3: No seek
                cmd_last = [c for c in cmd if c != '-ss' and c != PREVIEW_SEEK_TIME]
                res3 = subprocess.run(cmd_last, capture_output=True, text=True, encoding='utf-8', errors='replace')
                return res3.returncode == 0
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

def get_best_gpu_encoder(codec="h264"):
    """Detect available hardware encoders for the specified codec (h264 or hevc)"""
    try:
        res = subprocess.run([FFMPEG_PATH, "-encoders"], capture_output=True, text=True, encoding='utf-8', errors='replace')
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
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
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
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
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
    """
    Thực hiện Remux (copy stream) cực nhanh từ TS sang MP4.
    Thử nghiệm nhiều chiến thuật để đảm bảo tỷ lệ thành công cao nhất.
    """
    with ffmpeg_semaphore:
        # Chiến thuật 1: Remux tiêu chuẩn với AAC bitstream filter (Dành cho đại đa số file)
        try:
            cmd = [
                FFMPEG_PATH, "-y",
                "-fflags", "+genpts",
                "-err_detect", "ignore_err",
                "-i", input_path,
                "-map", "0:v:0?", "-map", "0:a:0?", # Lấy luồng video/audio đầu tiên nếu có
                "-c", "copy",
                "-bsf:a", "aac_adtstoasc",
                "-movflags", "+faststart",
                output_path
            ]
            print(f"Attempting Fast Remux (Standard): {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if res.returncode == 0: return True
            
            # Chiến thuật 2: Nếu fail, thử bỏ AAC bitstream filter (Có thể audio không phải AAC)
            print("Standard Remux failed, trying without AAC bitstream filter...")
            cmd_no_bsf = [c for c in cmd if c not in ["-bsf:a", "aac_adtstoasc"]]
            res = subprocess.run(cmd_no_bsf, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if res.returncode == 0: return True

            # Chiến thuật 3: Nếu vẫn fail, thử Encode riêng Audio (Video vẫn copy - Vẫn rất nhanh)
            print("Copy Remux failed, trying Video Copy + Audio Encode (AAC)...")
            cmd_hybrid = [
                FFMPEG_PATH, "-y",
                "-fflags", "+genpts",
                "-i", input_path,
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                output_path
            ]
            res = subprocess.run(cmd_hybrid, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if res.returncode == 0: return True

            print(f"All Fast Remux strategies failed for {input_path}. Error: {res.stderr}")
            return False
        except Exception as e:
            print(f"Remux Exception: {e}")
            return False

def convert_ts_to_mp4(input_path, delete_src=True):
    """
    Chuyển đổi file video sang .mp4 (H264/H265): 
    - Nếu là .ts: Thử Remux trước, nếu hỏng mới Encode.
    - Nếu là .mp4: Encode thẳng (để đổi Codec hoặc nén lại).
    """
    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    # Đường dẫn đích mặc định
    output_path = os.path.join(os.path.dirname(input_path), f"{name}.mp4")
    temp_output = False
    
    # Xử lý xung đột tên: Nếu file nguồn đã là .mp4, ta cần tên tạm để tránh ghi đè chính nó
    if ext == '.mp4':
        output_path = os.path.join(os.path.dirname(input_path), f"{name}.converting.mp4")
        temp_output = True

    # BƯỚC 1: Nếu là .ts, thử Remux (Cực nhanh, 5-20 giây)
    if ext == '.ts' or ext == '.m2ts':
        if remux_ts_to_mp4(input_path, output_path):
            if validate_media_output(output_path):
                if delete_src:
                    os.remove(input_path)
                    print("Auto-cleanup: Deleted original TS after validated REMUX")
                return output_path
            if os.path.exists(output_path):
                os.remove(output_path)
            print(f"Remux output validation failed for {input_path}; falling back to encode")

    # BƯỚC 2: Fallback Encode (Vài phút) - Dành cho .mp4 hoặc khi Remux .ts thất bại
    with ffmpeg_semaphore:
        try:
            from config_manager import load_config
            cfg = load_config()
            pref_codec = cfg.get("preferred_codec", "h264").lower()
            
            encoder = get_best_gpu_encoder(pref_codec)
            cmd = [
                FFMPEG_PATH, '-y',
                '-i', input_path,
                '-c:v', encoder,
            ]
            
            if "libx264" in encoder or "libx265" in encoder:
                # Dùng CRF 18 cho chất lượng gần như không suy giảm (Visually Lossless)
                cmd.extend(['-preset', 'veryfast', '-crf', '18'])
            else:
                # GPU: Giảm giá trị CQ để tăng chất lượng (CQ thấp = chất lượng cao)
                if 'nvenc' in encoder:
                    cmd.extend(['-rc', 'vbr', '-cq', '18', '-qmin', '15', '-qmax', '22'])
                elif 'qsv' in encoder:
                    cmd.extend(['-global_quality', '18'])
                else:
                    cmd.extend(['-b:v', '10M', '-maxrate', '15M', '-bufsize', '30M'])
                
                cmd.extend(['-preset', 'p4' if 'nvenc' in encoder else 'veryfast'])
                
            cmd.extend(['-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', output_path])
            
            print(f"Encoding Task (Target: {pref_codec}): {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if res.returncode != 0:
                print(f"Conversion Error: {res.stderr}")
                return None
            if not validate_media_output(output_path):
                print(f"Conversion validation failed for {input_path}")
                if os.path.exists(output_path) and output_path != input_path:
                    os.remove(output_path)
                return None
                
            final_path = output_path
            
            # BƯỚC 3: Tráo đổi nguyên tử nếu nguồn đã là .mp4.
            # os.replace chỉ thay original khi file mới đã sẵn sàng; không xóa source trước.
            if temp_output:
                original_final = os.path.join(os.path.dirname(input_path), f"{name}.mp4")
                if delete_src:
                    try:
                        os.replace(output_path, original_final)
                        final_path = original_final
                        print(f"Atomic Swap: Replaced original with NEW {pref_codec} file")
                    except Exception as e:
                        print(f"Atomic Swap Error: {e}")
                        try:
                            if os.path.exists(output_path):
                                os.remove(output_path)
                        except OSError:
                            pass
                        return None
                else:
                    # Nếu không xóa nguồn, giữ nguyên tên .converting.mp4 hoặc đổi sang tên khác
                    pass
                    
            elif delete_src and os.path.exists(output_path) and input_path != output_path:
                try:
                    os.remove(input_path)
                    print(f"Cleanup: Deleted source {ext} after encoding")
                except: pass
                    
            return final_path
        except Exception as e:
            print(f"Convert Exception: {e}")
            return None
