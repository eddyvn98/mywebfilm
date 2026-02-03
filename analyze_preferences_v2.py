import json
import os
import re
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

        # Regex to try and extract actor from name: e.g. "Title - Actor", "[Code] Title - Actor", "Actor - Title"
        # Patterns often used in filenames
        actor_patterns = [
            re.compile(r'-\s*([A-Za-z\s]+)$'), # e.g. "Title - Actor"
            re.compile(r'\]\s*(.*?)\s*-'),     # e.g. "[Code] Actor - Title"
            re.compile(r'^\s*([A-Za-z\s]+)\s*-'), # e.g. "Actor - Title"
        ]

        # Common known idols to help extraction
        known_idols = ["Ai Uehara", "Yua Mikami", "Eimi Fukada", "Arina Hashimoto", "Sola Aoi", "Ken Shimizu", "Tsubasa Amami"]

        for video in data:
            full_path = video.get("full_path", "")
            if full_path.lower().startswith("f:"):
                f_drive_count += 1
                name = video.get("name", "")
                jav_meta = video.get("jav_metadata")
                categories = video.get("categories", [])
                
                found_actors = []
                found_genres = list(categories) # Start with categories

                if jav_meta:
                    found_actors.extend(jav_meta.get("actors", []))
                    found_genres.extend(jav_meta.get("genres", []))
                
                # If no actors found yet, try extracting from name
                if not found_actors:
                    # Check for known idols in name first
                    for idol in known_idols:
                        if idol.lower() in name.lower():
                            found_actors.append(idol)
                    
                    # Try regex patterns
                    if not found_actors:
                        for pattern in actor_patterns:
                            match = pattern.search(name)
                            if match:
                                actor = match.group(1).strip()
                                if len(actor) > 3 and len(actor) < 30:
                                    found_actors.append(actor)
                                break
                
                actors_counter.update([a for a in found_actors if a])
                genres_counter.update([g for g in found_genres if g])

        print(f"Analysis complete for {f_drive_count} videos on drive F:")
        print("\nTop 15 Potential Actors/Names found:")
        for actor, count in actors_counter.most_common(15):
            print(f"- {actor}: {count}")

        print("\nTop 15 Potential Genres/Categories found:")
        for genre, count in genres_counter.most_common(15):
            print(f"- {genre}: {count}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    analyze_preferences()
