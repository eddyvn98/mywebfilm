import os
import subprocess
from constants import FFMPEG_PATH
from .ffmpeg_core import ffmpeg_semaphore

def get_best_gpu_encoder():
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
    Highlight Extraction: Forces Pure CPU (libx264 + ultrafast) 
    to maximize performance for complex filtering tasks.
    """
    with ffmpeg_semaphore:
        try:
            filename = os.path.basename(input_path)
            name, _ = os.path.splitext(filename)
            output_path = os.path.join(output_dir, f"{name}_highlight.mp4")
            if not os.path.exists(output_dir): os.makedirs(output_dir)

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
                output_path
            ]
            
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if res.returncode == 0:
                if delete_src and os.path.exists(output_path):
                    try: os.remove(input_path)
                    except: pass
                return output_path
            return None
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
                
            cmd.extend(['-c:a', 'aac', '-b:a', '128k', output_path])
            
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if res.returncode == 0:
                if delete_src and os.path.exists(output_path):
                    try: os.remove(input_path)
                    except: pass
                return output_path
            return None
        except Exception as e:
            print(f"Conversion Exception: {e}")
            return None
