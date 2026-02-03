from services.ffmpeg_core import check_ffmpeg_presence, generate_thumbnail, generate_preview, ffmpeg_semaphore
from services.ffmpeg_processor import process_highlight_video, convert_ts_to_mp4, get_best_gpu_encoder

# Compatibility wrapper for v2 refactoring
__all__ = [
    'check_ffmpeg_presence',
    'generate_thumbnail',
    'generate_preview',
    'process_highlight_video',
    'convert_ts_to_mp4',
    'get_best_gpu_encoder',
    'ffmpeg_semaphore'
]
