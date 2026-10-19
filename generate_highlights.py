"""
generate_highlights.py
Processes newly updated long movies to generate condensed highlight videos.
Moves sidecars (.nfo, posters) into Processed/ and deletes source files to save disk space.
Finally, re-scans library catalog so all highlights appear live in CinemaWeb.
"""
import os
import sys
import time
import shutil
import logging
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import ffmpeg_service as ff
import config_manager as cfg
from scanner_service import scan_videos, format_size
from sort_engine import JAV_RE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("HighlightBatch")

ROOT_DIRS = [
    r"H:\Sorted_Videos\JAV",
    r"H:\Sorted_Videos\Uncategorized\2026-10",
]

MIN_MOVIE_SIZE_BYTES = 300 * 1024 * 1024  # 300 MB minimum for a feature movie
DEFAULT_SINCE_DATE = datetime(2026, 10, 16, 0, 0, 0).timestamp()


def find_target_movies(since_timestamp=None, specific_codes=None):
    """
    Find candidate long movies that need highlight generation:
    - Located in ROOT_DIRS
    - Not already inside a Processed folder
    - Does not contain '_highlight' in filename
    - Size >= MIN_MOVIE_SIZE_BYTES
    - Modified since since_timestamp (or matching specific_codes)
    - Does not already have an existing highlight in Processed/
    """
    if since_timestamp is None and not specific_codes:
        since_timestamp = DEFAULT_SINCE_DATE

    matched = []
    seen_paths = set()

    for root_dir in ROOT_DIRS:
        if not os.path.exists(root_dir):
            continue
        for root, dirs, files in os.walk(root_dir):
            if "processed" in root.lower():
                continue
            for f in files:
                if "_highlight" in f.lower():
                    continue
                if not f.lower().endswith((".mp4", ".mkv", ".ts", ".avi")):
                    continue

                file_path = os.path.join(root, f)
                if file_path in seen_paths:
                    continue

                try:
                    st = os.stat(file_path)
                except Exception:
                    continue

                if st.st_size < MIN_MOVIE_SIZE_BYTES:
                    continue

                video_dir = os.path.dirname(file_path)
                name, _ = os.path.splitext(f)
                proc_hl = os.path.join(video_dir, "Processed", f"{name}_highlight.mp4")
                if os.path.exists(proc_hl):
                    continue

                m = JAV_RE.search(f)
                code = f"{m.group(1).upper()}-{m.group(2)}" if m else name[:25]

                if specific_codes:
                    if not any(sc.lower() in f.lower() for sc in specific_codes):
                        continue
                elif since_timestamp and st.st_mtime < since_timestamp:
                    continue

                seen_paths.add(file_path)
                matched.append((code, file_path, st.st_mtime, st.st_size))

    # Sort by mtime ascending
    matched.sort(key=lambda x: x[2])
    return [(m[0], m[1]) for m in matched]


def process_movie(file_path, code, idx, total):
    """Process a single movie to create a highlight and free source disk space."""
    if not os.path.exists(file_path):
        logger.warning("[%d/%d] Skipping %s: file not found (%s)", idx, total, code, file_path)
        return 0, False

    try:
        s1 = os.path.getsize(file_path)
        time.sleep(0.5)
        s2 = os.path.getsize(file_path)
        if s1 != s2 or s1 == 0:
            logger.warning("[%d/%d] Skipping %s: file is still in-flight / being copied (%s)", idx, total, code, file_path)
            return 0, False
    except Exception:
        return 0, False

    orig_size = os.path.getsize(file_path)
    video_dir = os.path.dirname(file_path)
    processed_dir = os.path.join(video_dir, "Processed")
    os.makedirs(processed_dir, exist_ok=True)

    name, _ = os.path.splitext(os.path.basename(file_path))
    expected_output = os.path.join(processed_dir, f"{name}_highlight.mp4")
    same_dir_hl = os.path.join(video_dir, f"{name}_highlight.mp4")

    # Fast-path: if a highlight already exists in the same directory, move it to Processed/
    if os.path.exists(same_dir_hl):
        logger.info("[%d/%d] Found existing highlight in parent folder for %s. Moving to Processed...", idx, total, code)
        try:
            shutil.move(same_dir_hl, expected_output)
            highlight_size = os.path.getsize(expected_output)
            # Remove original source file
            if os.path.exists(file_path) and os.path.abspath(file_path) != os.path.abspath(expected_output):
                os.remove(file_path)
                logger.info("   Removed heavy source file %s", os.path.basename(file_path))
            freed = max(0, orig_size - highlight_size)

            # Move sidecars
            _move_sidecars(file_path, expected_output)
            _ensure_video_dir(processed_dir)
            _update_catalog_entry(file_path, expected_output)

            logger.info("[%d/%d] SUCCESS (relocated existing) %s: %s (%s). Freed %s.",
                        idx, total, code, os.path.basename(expected_output), format_size(highlight_size), format_size(freed))
            return freed, True
        except Exception as e:
            logger.exception("[%d/%d] Failed relocating existing highlight for %s: %s", idx, total, code, e)

    logger.info("[%d/%d] Processing %s (%s) -> %s", idx, total, code, format_size(orig_size), expected_output)
    t0 = time.time()

    try:
        res_path = ff.process_highlight_video(file_path, processed_dir, delete_src=True)
        elapsed = time.time() - t0

        if res_path and os.path.exists(res_path):
            highlight_size = os.path.getsize(res_path)
            freed = max(0, orig_size - highlight_size)
            logger.info(
                "[%d/%d] SUCCESS %s in %.1fs: Generated %s (%s). Freed %s.",
                idx, total, code, elapsed,
                os.path.basename(res_path), format_size(highlight_size), format_size(freed)
            )

            # Move sidecars (.nfo, posters, etc.)
            _move_sidecars(file_path, res_path)

            # Ensure Processed is in video_dirs
            _ensure_video_dir(processed_dir)

            # Mutate catalog cache entry
            _update_catalog_entry(file_path, res_path)

            return freed, True
        else:
            logger.error("[%d/%d] FAILED %s after %.1fs: FFmpeg failed validation.", idx, total, code, elapsed)
            return 0, False
    except Exception as e:
        logger.exception("[%d/%d] EXCEPTION %s: %s", idx, total, code, e)
        return 0, False


def _move_sidecars(src_file_path, dst_highlight_path):
    src_base, _ = os.path.splitext(src_file_path)
    res_base, _ = os.path.splitext(dst_highlight_path)
    for ext in (".nfo", ".jpg", ".jpeg", ".png", ".webp", ".bmp"):
        src_sidecar = src_base + ext
        if os.path.exists(src_sidecar):
            dst_sidecar = res_base + ext
            try:
                shutil.move(src_sidecar, dst_sidecar)
                logger.info("   Moved sidecar: %s -> %s", os.path.basename(src_sidecar), os.path.basename(dst_sidecar))
            except Exception as e:
                logger.warning("   Failed to move sidecar %s: %s", src_sidecar, e)


def _ensure_video_dir(directory):
    try:
        c = cfg.load_config()
        if directory not in c.get("video_dirs", []):
            c["video_dirs"].append(directory)
            cfg.save_config(c)
    except Exception as e:
        logger.warning("Failed updating config with directory %s: %s", directory, e)


def _update_catalog_entry(old_path, new_path):
    try:
        def update_catalog(items):
            for video in items:
                if video.get("full_path") != old_path:
                    continue
                video["full_path"] = new_path
                video["ext"] = "MP4"
                video["name"] = os.path.splitext(os.path.basename(new_path))[0]
                st = os.stat(new_path)
                video["size"] = st.st_size
                video["size_fmt"] = format_size(st.st_size)
                break
            return items
        cfg.mutate_cache(update_catalog)
    except Exception as e:
        logger.warning("Failed updating catalog entry for %s: %s", old_path, e)


def main():
    logger.info("Scanning for newly updated long movies without highlights...")
    matched = find_target_movies()
    logger.info("Discovered %d target movies to process.", len(matched))

    total_freed_bytes = 0
    success_count = 0
    fail_count = 0

    for idx, (code, file_path) in enumerate(matched, 1):
        freed, ok = process_movie(file_path, code, idx, len(matched))
        if ok:
            success_count += 1
            total_freed_bytes += freed
        else:
            fail_count += 1

    logger.info("=" * 60)
    logger.info("Batch highlight processing finished: %d succeeded, %d failed. Total net space freed: %s.",
                success_count, fail_count, format_size(total_freed_bytes))
    logger.info("=" * 60)

    logger.info("Executing full library catalog re-scan to refresh all video metadata and highlight paths...")
    video_dirs = cfg.load_config().get("video_dirs", [])
    scan_videos(video_dirs)
    logger.info("Catalog re-scan complete! All highlights are now live in CinemaWeb.")


if __name__ == "__main__":
    main()
