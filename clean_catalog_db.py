import json
import os
import sqlite3
import sys

from config_manager import load_config
from runtime_db import DB_PATH, database_maintenance
from scanner_service import _normalize_roots

sys.stdout.reconfigure(encoding="utf-8")


def get_allowed_roots():
    config = load_config()
    return _normalize_roots(config.get("video_dirs", []))


def is_under_root(path, root):
    try:
        norm_path = os.path.normcase(os.path.abspath(path))
        norm_root = os.path.normcase(os.path.abspath(root))
        return os.path.commonpath([norm_path, norm_root]) == norm_root
    except (OSError, ValueError):
        return False


def is_garbage(path, item):
    norm_path = os.path.normpath(path)

    # 1. Outside the same roots currently used by the scanner.
    allowed_roots = get_allowed_roots()
    if allowed_roots and not any(is_under_root(norm_path, root) for root in allowed_roots):
        return True, "Outside configured roots"

    lower_path = norm_path.lower()

    # 2. TypeScript files masquerading as MPEG-TS.
    if lower_path.endswith(".d.ts"):
        return True, "TypeScript .d.ts"
    if lower_path.endswith(".ts"):
        try:
            if os.path.getsize(path) < 500 * 1024:
                return True, "Invalid .ts size (<500KB)"
            with open(path, "rb") as stream:
                if stream.read(1) != b"\x47":
                    return True, "Invalid .ts sync byte"
        except OSError:
            return True, "Missing/unreadable .ts on disk"

    # 3. Corrupted empty video stubs.
    size = item.get("size", 0)
    if item.get("type") == "video" and size <= 1024:
        return True, f"Corrupted empty video stub ({size}b)"

    # 4. Tiny icon or 9-patch images.
    if item.get("type") == "image":
        if lower_path.endswith(".9.png") or size < 30 * 1024:
            return True, f"Tiny icon/9-patch image ({size}b)"

    return False, ""


def clean_database():
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return

    allowed_roots = get_allowed_roots()
    if not allowed_roots:
        print("No configured media roots; refusing destructive cleanup.")
        return

    print("Allowed media roots:")
    for root in allowed_roots:
        print(f"  - {root}")

    with database_maintenance():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        before_count = cur.execute(
            "SELECT count(*) FROM media_catalog"
        ).fetchone()[0]
        print(f"Total media_catalog records before: {before_count}")

        rows = cur.execute(
            "SELECT path_key, full_path, payload FROM media_catalog"
        ).fetchall()

        keys_to_delete = []
        reasons = {}

        for key, path, payload in rows:
            try:
                item = json.loads(payload)
            except Exception:
                item = {}

            flag, reason = is_garbage(path, item)
            if flag:
                keys_to_delete.append((key,))
                reasons[reason] = reasons.get(reason, 0) + 1

        print(f"Found {len(keys_to_delete)} records to delete:")
        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"  - {reason}: {count}")

        if keys_to_delete:
            cur.executemany(
                "DELETE FROM media_catalog WHERE path_key = ?",
                keys_to_delete,
            )
            conn.commit()
            print(
                f"Successfully deleted {len(keys_to_delete)} "
                "records from media_catalog."
            )

        after_count = cur.execute(
            "SELECT count(*) FROM media_catalog"
        ).fetchone()[0]
        print(f"Total media_catalog records after: {after_count}")

        jobs_before = cur.execute(
            "SELECT count(*) FROM metadata_jobs"
        ).fetchone()[0]
        cur.execute(
            """
            DELETE FROM metadata_jobs
            WHERE path NOT IN (SELECT full_path FROM media_catalog)
            """
        )
        conn.commit()
        jobs_after = cur.execute(
            "SELECT count(*) FROM metadata_jobs"
        ).fetchone()[0]
        print(
            f"Cleaned metadata_jobs: {jobs_before} -> {jobs_after} "
            f"(deleted {jobs_before - jobs_after} orphaned jobs)"
        )

        print("Vacuuming database...")
        cur.execute("VACUUM")
        conn.close()

    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"Database vacuum completed. Current size: {size_mb:.2f} MB")


if __name__ == "__main__":
    clean_database()
