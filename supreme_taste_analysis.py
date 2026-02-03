import json
import os
import re
from collections import Counter

def supreme_taste_analysis():
    cache_file = "movies_cache.json"
    owned_file = "owned_data.json"
    
    if not os.path.exists(cache_file) or not os.path.exists(owned_file):
        print("Required files missing.")
        return

    with open(owned_file, "r", encoding="utf-8") as f:
        owned_codes = set(json.load(f).get("codes", []))

    with open(cache_file, "r", encoding="utf-8") as f:
        cache_data = json.load(f)

    # 1. Series Frequency (Prefix Analysis)
    series_counter = Counter()
    for code in owned_codes:
        match = re.match(r'^([A-Z0-9]+)-', code.upper())
        if match:
            series_counter[match.group(1)] += 1
        elif code.lower().startswith('n') and code[1:].isdigit():
             series_counter['Tokyo Hot (n Series)'] += 1

    # 2. Granular Category Analysis
    all_tags = Counter()
    for video in cache_data:
        full_path = video.get("full_path", "")
        if full_path.lower().startswith("f:"):
            # Extract tags from 'categories' and 'jav_metadata'
            tags = video.get("categories", [])
            jav_meta = video.get("jav_metadata")
            if jav_meta:
                tags.extend(jav_meta.get("genres", []))
                # Add Studio if available
                studio = jav_meta.get("studio")
                if studio:
                    tags.append(f"Studio: {studio}")
            
            # Normalize and filter out junk
            for tag in tags:
                if tag and len(tag) > 1:
                    all_tags[tag.strip()] += 1

    # 3. Print a detailed "Fingerprint"
    print("--- SUPREME TASTE FINGERPRINT ---")
    print(f"\nTotal Owned Videos Analyzed: {len(owned_codes)}")
    
    print("\n[ Top 20 Discovery Series (Loyalty) ]")
    for series, count in series_counter.most_common(20):
        print(f" - {series}: {count} videos")

    print("\n[ Niche & Style Distribution (Granular) ]")
    # Grouping by themes to show depth
    major_themes = {
        "Technical / Style": ["Full HD", "4K", "POV", "VR", "Multi-angle", "No BGM", "Long-term profile"],
        "Scenario / Mood": ["Story-driven", "Drama", "School Life", "Nurse", "Office Lady", "Wife", "Adultery", "Neighbor", "Incest"],
        "Physical / Aesthetic": ["Big Breasts", "Múp", "Plump", "Slender", "Beautiful Face", "Legs", "Tan Line"],
        "Action / Variety": ["Creampie", "Handjob", "Blowjob", "Deep Throat", "Bondage", "Cosplay", "Teacher"]
    }

    for theme, keywords in major_themes.items():
        found = {k: all_tags[k] for k in keywords if all_tags[k] > 0}
        if found:
            print(f"\n >>> {theme}:")
            for k, v in sorted(found.items(), key=lambda x: x[1], reverse=True):
                print(f"   * {k}: {v}")

    print("\n[ Top 15 Studios Found ]")
    studios = {k.replace("Studio: ", ""): v for k, v in all_tags.items() if k.startswith("Studio: ")}
    for s, v in sorted(studios.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f" - {s}: {v}")

if __name__ == "__main__":
    supreme_taste_analysis()
