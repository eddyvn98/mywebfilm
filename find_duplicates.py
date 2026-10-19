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
            if sz <= 2 * 1024 * 1024:
                h.update(f.read())
            else:
                h.update(f.read(1024 * 1024))
                f.seek(sz - 1024 * 1024)
                h.update(f.read(1024 * 1024))
        return h.hexdigest()
    except Exception:
        return None


def find_verified_duplicates():
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

    verified_duplicates = []
    total_bytes_to_delete = 0

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

                    verified_duplicates.append({
                        "size": sz,
                        "keep": keep,
                        "delete": to_delete
                    })
                    total_bytes_to_delete += sz * len(to_delete)

    return verified_duplicates, total_bytes_to_delete


if __name__ == "__main__":
    dups, wasted = find_verified_duplicates()
    total_delete_files = sum(len(d["delete"]) for d in dups)
    print(f"Verified duplicate groups: {len(dups)}")
    print(f"Total duplicate files to delete: {total_delete_files}")
    print(f"Total disk space to free: {wasted / (1024**3):.2f} GB")
    print("\nSample 10 duplicate plans:")
    for item in dups[:10]:
        sz_mb = item["size"] / (1024 * 1024)
        print(f"KEEP:   {item['keep'][0]} ({sz_mb:.1f} MB)")
        for d in item["delete"]:
            print(f"DELETE: {d[0]}")
        print()
