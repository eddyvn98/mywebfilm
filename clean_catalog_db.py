import sqlite3
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("CINEMA_DB_PATH", os.path.join(BASE_DIR, "data", "cinema_state.db"))

ALLOWED_ROOTS = [
    r"E:\Sorted_Videos",
    r"E:\Processed",
    r"G:\Sorted_Videos",
    r"H:\Sorted_Videos",
]

def is_garbage(path, item):
    norm_path = os.path.normpath(path)
    
    # 1. Outside allowed roots
    is_in_allowed = any(
        norm_path.lower() == root.lower() or norm_path.lower().startswith(root.lower() + os.sep)
        for root in ALLOWED_ROOTS
    )
    if not is_in_allowed:
        return True, "Outside allowed roots"
        
    lower_path = norm_path.lower()
    
    # 2. TypeScript files
    if lower_path.endswith('.d.ts'):
        return True, "TypeScript .d.ts"
    if lower_path.endswith('.ts'):
        try:
            if os.path.getsize(path) < 500 * 1024:
                return True, "Invalid .ts size (<500KB)"
            with open(path, 'rb') as f:
                if f.read(1) != b'\x47':
                    return True, "Invalid .ts sync byte"
        except OSError:
            return True, "Missing/unreadable .ts on disk"

    # 3. Corrupted empty video stubs (48b, 261b)
    sz = item.get("size", 0)
    if item.get("type") == "video" and sz <= 1024:
        return True, f"Corrupted empty video stub ({sz}b)"
        
    # 4. Tiny icon or 9-patch images
    if item.get("type") == "image":
        if lower_path.endswith('.9.png') or sz < 30 * 1024:
            return True, f"Tiny icon/9-patch image ({sz}b)"
            
    return False, ""

def clean_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    before_count = cur.execute("SELECT count(*) FROM media_catalog").fetchone()[0]
    print(f"Total media_catalog records before: {before_count}")
    
    rows = cur.execute("SELECT path_key, full_path, payload FROM media_catalog").fetchall()
    
    keys_to_delete = []
    reasons = {}
    
    for key, path, pl in rows:
        try:
            item = json.loads(pl)
        except Exception:
            item = {}
        flag, reason = is_garbage(path, item)
        if flag:
            keys_to_delete.append((key,))
            reasons[reason] = reasons.get(reason, 0) + 1
            
    print(f"Found {len(keys_to_delete)} records to delete:")
    for r, count in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  - {r}: {count}")
        
    if keys_to_delete:
        cur.executemany("DELETE FROM media_catalog WHERE path_key = ?", keys_to_delete)
        conn.commit()
        print(f"Successfully deleted {len(keys_to_delete)} records from media_catalog.")
        
    after_count = cur.execute("SELECT count(*) FROM media_catalog").fetchone()[0]
    print(f"Total media_catalog records after: {after_count}")
    
    # Clean up metadata_jobs table
    jobs_before = cur.execute("SELECT count(*) FROM metadata_jobs").fetchone()[0]
    cur.execute("""
        DELETE FROM metadata_jobs
        WHERE path NOT IN (SELECT full_path FROM media_catalog)
    """)
    conn.commit()
    jobs_after = cur.execute("SELECT count(*) FROM metadata_jobs").fetchone()[0]
    print(f"Cleaned metadata_jobs: {jobs_before} -> {jobs_after} (deleted {jobs_before - jobs_after} orphaned jobs)")
    
    # Run VACUUM to reclaim space
    print("Vacuuming database...")
    cur.execute("VACUUM")
    conn.close()
    
    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"Database vacuum completed. Current size: {size_mb:.2f} MB")

if __name__ == "__main__":
    clean_database()
