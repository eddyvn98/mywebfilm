
import os
import json

VIDEO_EXTS = ('.mp4', '.ts', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm')

def quick_scan(video_dirs):
    count = 0
    found_ts = 0
    for bdir in video_dirs:
        print(f"Scanning: {bdir}")
        if not os.path.exists(bdir):
            print(f"  Path does not exist!")
            continue
            
        for root, dirs, files in os.walk(bdir):
            if '.mycinema' in root: continue
            for f in files:
                lower_f = f.lower()
                if lower_f.endswith(VIDEO_EXTS):
                    count += 1
                    if lower_f.endswith('.ts'):
                        found_ts += 1
                        if found_ts < 10:
                            print(f"  Found TS: {f}")
    
    print(f"\nTotal videos found: {count}")
    print(f"Total .ts files found: {found_ts}")

with open('config.json', 'r') as f:
    cfg = json.load(f)

quick_scan(cfg['video_dirs'])
