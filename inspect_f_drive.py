import json
import os

def inspect_f_drive_videos():
    cache_file = "movies_cache.json"
    
    if not os.path.exists(cache_file):
        print(f"Error: {cache_file} not found.")
        return

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        count = 0
        for video in data:
            full_path = video.get("full_path", "")
            if full_path.lower().startswith("f:"):
                print(json.dumps(video, indent=4, ensure_ascii=False))
                count += 1
                if count >= 3:
                    break
        
        if count == 0:
            print("No videos found on drive F:")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    inspect_f_drive_videos()
