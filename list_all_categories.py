import json
import os
from collections import Counter

def list_all_categories():
    cache_file = "movies_cache.json"
    
    if not os.path.exists(cache_file):
        print(f"Error: {cache_file} not found.")
        return

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        all_categories = Counter()
        f_drive_count = 0

        for video in data:
            full_path = video.get("full_path", "")
            if full_path.lower().startswith("f:"):
                f_drive_count += 1
                cat_list = video.get("categories", [])
                if isinstance(cat_list, list):
                    all_categories.update(cat_list)
                
                jav_meta = video.get("jav_metadata")
                if jav_meta:
                    genres = jav_meta.get("genres", [])
                    if isinstance(genres, list):
                        all_categories.update(genres)

        print(f"Total F: drive videos: {f_drive_count}")
        print("\nAll categories found (Sorted by frequency):")
        for cat, count in all_categories.most_common():
            print(f"['{cat}']: {count}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    list_all_categories()
