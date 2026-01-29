
import os
import json
import time
from scanner_service import scan_videos

# Monkey patch print to see output
def debug_scan():
    with open('config.json', 'r') as f:
        cfg = json.load(f)
    
    print("Starting Detailed Debug Scan...")
    start_time = time.time()
    
    # We will run the real scan_videos but with some tracking
    # Actually, let's just run a modified version of it here to see where it fails
    video_dirs = cfg['video_dirs']
    VIDEO_EXTS = ('.mp4', '.ts', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm')
    
    found_count = 0
    error_count = 0
    
    for bdir in video_dirs:
        print(f"\nProcessing Dir: {bdir}")
        if not os.path.exists(bdir):
            print("  Path does not exist!")
            continue
            
        for root, dirs, files in os.walk(bdir):
            if '.mycinema' in root: continue
            for f in files:
                if f.lower().endswith(VIDEO_EXTS):
                    found_count += 1
                    fp = os.path.join(root, f)
                    try:
                        # Try to simulate the critical parts of scan_videos
                        from category_service import get_categories
                        # We won't block on network for this debug, but we'll check if it's called
                        # print(f"  Checking: {f}")
                        if found_count % 50 == 0:
                            print(f"  Processed {found_count} files...")
                    except Exception as e:
                        print(f"  Error on {f}: {e}")
                        error_count += 1

    print(f"\nScan finished in {time.time() - start_time:.2f}s")
    print(f"Total videos found: {found_count}")
    print(f"Total errors: {error_count}")

debug_scan()
