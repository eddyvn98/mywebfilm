import os
import re
import sys
import hashlib
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SORTED_ROOTS = ["G:\\Sorted_Videos", "H:\\Sorted_Videos", "E:\\Sorted_Videos"]
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".wmv", ".mov", ".flv", ".webm", ".ts", ".m2ts"}


def clean_filename(name):
    base, ext = os.path.splitext(name)
    cleaned = re.sub(r"([_\s\-\(\[]+)(\d+)([\]\)]*)$", "", base).strip()
    return cleaned.lower(), ext.lower()


def get_file_sample_hash(filepath, sz):
    try:
        h = hashlib.md5()
        with open(filepath, "rb") as f:
            h.update(f.read(65536))
        return h.hexdigest()
    except Exception:
        return None


def run_cleanup(dry_run=True):
    all_files = []
    for root_dir in SORTED_ROOTS:
        if not os.path.isdir(root_dir):
            continue
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in {"$RECYCLE.BIN", "System Volume Information", ".mycinema"}]
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext in VIDEO_EXTS:
                    fp = os.path.join(root, fn)
                    try:
                        sz = os.path.getsize(fp)
                        if sz > 0:
                            all_files.append((fp, fn, sz))
                    except OSError:
                        pass

    by_size = defaultdict(list)
    for fp, fn, sz in all_files:
        by_size[sz].append((fp, fn))

    groups_to_clean = []
    for sz, items in by_size.items():
        if len(items) < 2:
            continue
        by_clean_name = defaultdict(list)
        for fp, fn in items:
            cname, ext = clean_filename(fn)
            by_clean_name[(cname, ext)].append((fp, fn))

        for (cname, ext), group in by_clean_name.items():
            if len(group) < 2:
                continue

            by_hash = defaultdict(list)
            for fp, fn in group:
                h = get_file_sample_hash(fp, sz)
                if h:
                    by_hash[h].append((fp, fn))

            for h, matching in by_hash.items():
                if len(matching) > 1:
                    def score_file(item):
                        fp, fn = item
                        base, _ = os.path.splitext(fn)
                        has_suffix = bool(re.search(r"([_\s\-\(\[]+)(\d+)([\]\)]*)$", base))
                        return (
                            1 if has_suffix else 0,
                            len(fn),
                            0 if fp.startswith("H:") else 1,
                        )

                    sorted_matching = sorted(matching, key=score_file)
                    keep = sorted_matching[0]
                    to_delete = sorted_matching[1:]
                    groups_to_clean.append((sz, keep, to_delete))

    total_deleted = 0
    total_bytes_freed = 0
    errors = []

    print(f"Total duplicate groups to process: {len(groups_to_clean)}")
    for sz, keep, to_delete in groups_to_clean:
        keep_path, keep_name = keep
        # CRITICAL SAFETY CHECK: Ensure the file to keep actually exists!
        if not os.path.isfile(keep_path) or os.path.getsize(keep_path) != sz:
            errors.append(f"Safety check failed: keep file {keep_path} not valid")
            continue

        for del_path, del_name in to_delete:
            if not os.path.isfile(del_path):
                continue
            if os.path.abspath(del_path) == os.path.abspath(keep_path):
                continue

            if not dry_run:
                try:
                    os.remove(del_path)
                    total_deleted += 1
                    total_bytes_freed += sz

                    # Also delete orphan sidecars (.nfo, .jpg) if present
                    del_base, _ = os.path.splitext(del_path)
                    for ext in [".nfo", ".jpg", ".jpeg", ".png", ".nfo.bak"]:
                        sidecar = del_base + ext
                        if os.path.isfile(sidecar):
                            try:
                                os.remove(sidecar)
                            except OSError:
                                pass
                except Exception as exc:
                    errors.append(f"Failed to delete {del_path}: {exc}")
            else:
                total_deleted += 1
                total_bytes_freed += sz

    print(f"Dry run: {dry_run}")
    print(f"Total duplicate files deleted: {total_deleted}")
    print(f"Total space freed: {total_bytes_freed / (1024**3):.2f} GB")
    if errors:
        print(f"Errors encountered: {len(errors)}")
        for err in errors[:5]:
            print(f"  - {err}")

    return total_deleted, total_bytes_freed


if __name__ == "__main__":
    is_dry = "--execute" not in sys.argv
    deleted, freed = run_cleanup(dry_run=is_dry)
    if not is_dry and deleted > 0:
        print("Refreshing library catalog after duplicate cleanup...")
        try:
            import config_manager as cfg
            import scanner_service
            video_dirs = cfg.load_config().get("video_dirs", [])
            scanner_service.scan_videos(video_dirs)
            print("Library catalog refresh complete.")
        except Exception as e:
            print(f"Failed to refresh catalog: {e}")

