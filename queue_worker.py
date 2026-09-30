import threading
import queue
import os
import ffmpeg_service as ff
import config_manager as cfg
import logging
from runtime_db import (
    add_media_job,
    clear_finished_media_jobs,
    load_media_jobs,
    migrate_media_jobs_json,
    update_media_job,
)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CINEMA_DATA_DIR", os.path.join(BASE_DIR, "data"))
JOBS_FILE = os.path.join(DATA_DIR, "media_jobs.json")

class MediaQueue:
    def __init__(self):
        self.queue = queue.Queue()
        self.status_lock = threading.Lock()
        self.worker_lock = threading.Lock()
        migrate_media_jobs_json(JOBS_FILE)
        self.items = load_media_jobs()
        self.worker_thread = None
        self.is_running = False

    def add_items(self, paths, task_type="highlight"):
        with self.status_lock:
            for p in paths:
                item = add_media_job(p, os.path.basename(p), task_type)
                if item is None:
                    continue
                self.items.append(item)
                self.queue.put(item)

        self.ensure_worker_started()

    def ensure_worker_started(self):
        with self.worker_lock:
            if self.worker_thread is None or not self.worker_thread.is_alive():
                self.is_running = True
                self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
                self.worker_thread.start()

    def _worker_loop(self):
        while self.is_running:
            try:
                item = self.queue.get(timeout=5)
            except queue.Empty:
                continue

            with self.status_lock:
                item['status'] = "processing"
                update_media_job(item['id'], status="processing")
                logger.info("media_job_started type=%s path=%r", item['type'], item['path'])

            try:
                res_path = None
                if item['type'] == "highlight":
                    video_dir = os.path.dirname(item['path'])
                    processed_dir = os.path.join(video_dir, 'Processed')
                    res_path = ff.process_highlight_video(item['path'], processed_dir, delete_src=True)
                    
                    # Ensure Processed dir is in config
                    if res_path:
                        c = cfg.load_config()
                        if processed_dir not in c["video_dirs"]:
                            c["video_dirs"].append(processed_dir)
                            cfg.save_config(c)
                
                elif item['type'] == "convert":
                    res_path = ff.convert_ts_to_mp4(item['path'], delete_src=True)

                with self.status_lock:
                    if res_path:
                        item['status'] = "completed"
                        item['output'] = res_path
                        update_media_job(item['id'], status="completed", output=res_path, error="")
                        logger.info("media_job_completed type=%s source=%r output=%r", item['type'], item['path'], res_path)
                        
                        # Sync Cache
                        try:
                            items = cfg.load_cache()
                            updated = False
                            
                            if item['type'] == "convert":
                                # Replace the .ts entry with .mp4
                                for v in items:
                                    if v['full_path'] == item['path']:
                                        v['full_path'] = res_path
                                        v['ext'] = "MP4"
                                        v['name'] = os.path.splitext(os.path.basename(res_path))[0]
                                        # Update size if possible
                                        if os.path.exists(res_path):
                                            st = os.stat(res_path)
                                            v['size'] = st.st_size
                                            from scanner_service import format_size
                                            v['size_fmt'] = format_size(st.st_size)
                                        updated = True
                                        print(f"[Queue] Cache updated: {item['path']} -> {res_path}")
                                        break
                            
                            elif item['type'] == "highlight":
                                # Highlights are new files, but often in a 'Processed' folder
                                # We don't necessarily replace the old one, but we should add the new one
                                # if it's not already there.
                                if not any(v['full_path'] == res_path for v in items):
                                    # Create a basic entry or trigger a mini-scan
                                    # For simplicity, we trigger a save and the next user refresh/scan will pick it up
                                    # But let's try to add it minimally
                                    pass
                            
                            if updated:
                                cfg.save_cache(items)
                        except Exception as cache_err:
                            print(f"[Queue] Cache Sync Error: {cache_err}")
                    else:
                        item['status'] = "failed"
                        item['error'] = "FFmpeg task failed"
                        update_media_job(item['id'], status="failed", error=item['error'])
                        logger.error("media_job_failed type=%s path=%r reason=ffmpeg", item['type'], item['path'])
            except Exception as e:
                with self.status_lock:
                    item['status'] = "failed"
                    item['error'] = str(e)
                    update_media_job(item['id'], status="failed", error=item['error'])
                    logger.exception("media_job_failed type=%s path=%r", item['type'], item['path'])
            finally:
                self.queue.task_done()

    def get_status(self):
        with self.status_lock:
            return {
                "items": [dict(i) for i in self.items],
                "active_count": self.queue.qsize() + (1 if any(i['status'] == 'processing' for i in self.items) else 0)
            }

    def clear_completed(self):
        with self.status_lock:
            self.items = [i for i in self.items if i['status'] in ['pending', 'processing']]
            clear_finished_media_jobs()

# Global instance
media_queue = MediaQueue()
