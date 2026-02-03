import json
import os
from collections import Counter

def verify_genres_deeply():
    cache_file = "movies_cache.json"
    owned_file = "owned_data.json"
    
    if not os.path.exists(cache_file) or not os.path.exists(owned_file):
        print("Required files missing.")
        return

    with open(owned_file, "r", encoding="utf-8") as f:
        owned_codes = set(json.load(f).get("codes", []))

    with open(cache_file, "r", encoding="utf-8") as f:
        cache_data = json.load(f)

    # Dictionary to hold the frequency of every single tag/genre found
    genre_inventory = Counter()

    for video in cache_data:
        full_path = video.get("full_path", "")
        # Focus on the F: drive collection as it represents the core taste
        if full_path.lower().startswith("f:"):
            # Extract from categories
            cats = video.get("categories", [])
            for c in cats:
                genre_inventory[c.strip()] += 1
            
            # Extract from jav_metadata
            jav_meta = video.get("jav_metadata")
            if jav_meta:
                genres = jav_meta.get("genres", [])
                for g in genres:
                    genre_inventory[g.strip()] += 1
                
                # Check for studio as a genre preference
                studio = jav_meta.get("studio")
                if studio:
                    genre_inventory[f"Studio: {studio}"] += 1

    # Sorting the results
    sorted_inventory = genre_inventory.most_common()

    # Output to a file for review
    with open("Final_Genre_Profile.txt", "w", encoding="utf-8") as f:
        f.write("=== FINAL GENRE PROFILE (DERIVED FROM 1238 VIDEOS) ===\n\n")
        for genre, count in sorted_inventory:
            f.write(f"{genre}: {count}\n")
    
    # Print the top 50 to console
    print("Top 50 Genres found in your collection:")
    for genre, count in sorted_inventory[:50]:
        print(f" - {genre}: {count}")

if __name__ == "__main__":
    verify_genres_deeply()
