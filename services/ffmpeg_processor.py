import os
import json
import subprocess
from constants import FFMPEG_PATH, FFPROBE_PATH
from ffmpeg_runtime import ffmpeg_subprocess_kwargs
from .ffmpeg_core import ffmpeg_semaphore

def validate_media_output(path):
    if not os.path.exists(path) or os.path.getsize(path) <= 0:
        return False
    try:
        cmd = [
            FFPROBE_PATH, '-v', 'error',
            '-show_entries', 'stream=codec_type:format=duration',
            '-of', 'json', path
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30,
            **ffmpeg_subprocess_kwargs(),
        )
        if res.returncode != 0:
            return False
        payload = json.loads(res.stdout or '{}')
        has_video = any(s.get('codec_type') == 'video' for s in payload.get('streams', []))
        duration = float((payload.get('format') or {}).get('duration') or 0)
        return has_video and duration > 0
    except Exception:
        return False

def get_best_gpu_encoder():
    try:
        res = subprocess.run(
            [FFMPEG_PATH, "-encoders"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            **ffmpeg_subprocess_kwargs(),
        )
        encoders = res.stdout.lower()
        if "h264_nvenc" in encoders: return "h264_nvenc"
        if "h264_qsv" in encoders: return "h264_qsv"
        if "h264_amf" in encoders: return "h264_amf"
    except: pass
    return "libx264"

def process_highlight_video(input_path, output_dir, delete_src=False):
    """
    Highlight Extraction: Forces Pure CPU (libx264 + ultrafast) 
    to maximize performance for complex filtering tasks.
    """
    with ffmpeg_semaphore:
        try:
            filename = os.path.basename(input_path)
            name, _ = os.path.splitext(filename)
            output_path = os.path.join(output_dir, f"{name}_highlight.mp4")
            temp_output = output_path + '.partial.mp4'
            if not os.path.exists(output_dir): os.makedirs(output_dir)
            if os.path.exists(temp_output):
                os.remove(temp_output)

            # High-thread count CPU (i7-8750H) is faster here than GPU 1050Ti
            cmd = [
                FFMPEG_PATH, '-y',
                '-threads', '0',
                '-ss', '900',
                '-i', input_path,
                '-vf', "select='lt(mod(t,60),10)',setpts=N/FRAME_RATE/TB",
                '-af', "aselect='lt(mod(t,60),10)',asetpts=N/SR/TB",
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '26',
                '-c:a', 'aac',
                '-b:a', '128k',
                temp_output
            ]
            
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                **ffmpeg_subprocess_kwargs(),
            )
            if res.returncode != 0 or not validate_media_output(temp_output):
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                return None

            os.replace(temp_output, output_path)
            if delete_src:
                os.remove(input_path)
            return output_path
        except Exception as e:
            print(f"Highlight Exception: {e}")
            return None

def convert_ts_to_mp4(input_path, delete_src=True):
    """
    TS to MP4 Conversion: Prefers GPU (NVENC) for long-form sequential encoding.
    """
    with ffmpeg_semaphore:
        try:
            filename = os.path.basename(input_path)
            name, _ = os.path.splitext(filename)
            output_path = os.path.join(os.path.dirname(input_path), f"{name}.mp4")
            temp_output = output_path + '.partial.mp4'
            if os.path.exists(temp_output):
                os.remove(temp_output)
            encoder = get_best_gpu_encoder()
            
            cmd = [
                FFMPEG_PATH, '-y',
                '-i', input_path,
                '-c:v', encoder
            ]
            
            if encoder == 'libx264':
                cmd.extend(['-preset', 'ultrafast', '-crf', '23'])
            else:
                preset = 'fast' if 'nvenc' in encoder else 'ultrafast'
                cmd.extend(['-preset', preset, '-b:v', '5M'])
                
            cmd.extend(['-c:a', 'aac', '-b:a', '128k', temp_output])
            
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                **ffmpeg_subprocess_kwargs(),
            )
            if res.returncode != 0 or not validate_media_output(temp_output):
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                return None

            os.replace(temp_output, output_path)
            if delete_src:
                os.remove(input_path)
            return output_path
        except Exception as e:
            print(f"Conversion Exception: {e}")
            return None
