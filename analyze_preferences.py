import json
import os
from collections import Counter

def analyze_preferences():
    cache_file = "movies_cache.json"
    
    if not os.path.exists(cache_file):
        print(f"Error: {cache_file} not found.")
        return

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        actors_counter = Counter()
        genres_counter = Counter()
        f_drive_count = 0

        for video in data:
            full_path = video.get("full_path", "")
            if full_path.lower().startswith("f:"):
                f_drive_count += 1
                jav_meta = video.get("jav_metadata")
                if jav_meta:
                    # Collect actors
                    actors = jav_meta.get("actors", [])
                    if isinstance(actors, list):
                        actors_counter.update(actors)
                    
                    # Collect genres
                    genres = jav_meta.get("genres", [])
                    if isinstance(genres, list):
                        genres_counter.update(genres)
                    elif isinstance(genres, str):
                        # Some might be comma separated strings if not normalized
                        genres_counter.update([g.strip() for g in genres.split(",")])

        print(f"Analysis complete for {f_drive_count} videos on drive F:")
        print("\nTop 15 Actors:")
        for actor, count in actors_counter.most_common(15):
            print(f"- {actor}: {count}")

        print("\nTop 15 Genres:")
        for genre, count in genres_counter.most_common(15):
            print(f"- {genre}: {count}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    analyze_preferences()
