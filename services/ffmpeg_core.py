import os
import subprocess
import threading
from constants import FFMPEG_PATH, THUMB_SEEK_TIME, THUMB_SIZE, PREVIEW_SEEK_TIME, PREVIEW_DURATION, PREVIEW_SIZE

# Maintain the semaphore for FFmpeg process management
ffmpeg_semaphore = threading.Semaphore(2)

def check_ffmpeg_presence():
    try:
        subprocess.run([FFMPEG_PATH, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def generate_thumbnail(media_path, output_path, is_image=False):
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
            if res.returncode != 0 and not is_image:
                cmd_no_ss = [c for c in cmd if c != '-ss' and c != THUMB_SEEK_TIME]
                res2 = subprocess.run(cmd_no_ss, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if res2.returncode == 0: return True
                return False
            return res.returncode == 0
        except Exception as e:
            print(f"Thumb Exception: {e}")
            return False

def generate_preview(media_path, output_path):
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
                cmd_no_ss = [c for c in cmd if c != '-ss' and c != PREVIEW_SEEK_TIME]
                res2 = subprocess.run(cmd_no_ss, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if res2.returncode == 0: return True
                return False
            return True
        except Exception as e:
            print(f"Preview Exception: {e}")
            return False
