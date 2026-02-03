import json
import os
import re

def analyze_body_traits():
    cache_file = "movies_cache.json"
    owned_file = "owned_data.json"
    
    if not os.path.exists(cache_file) or not os.path.exists(owned_file):
        print("Required files missing.")
        return

    with open(owned_file, "r", encoding="utf-8") as f:
        owned_codes = set(json.load(f).get("codes", []))

    with open(cache_file, "r", encoding="utf-8") as f:
        cache_data = json.load(f)

    stats = {
        "Breasts": 0,
        "Butt": 0,
        "Face/Pretty": 0,
        "Curvy/Múp": 0,
        "Legs/Thighs": 0,
        "Total_Sample": 0
    }

    # Keywords for mapping
    mapping = {
        "Breasts": ["Big Breasts", "Busty", "Vú to", "Ngực", "Oppai", "Big Tits", "Huge Breasts"],
        "Butt": ["Butt", "Ass", "Mông", "Hips", "Big Butt"],
        "Face/Pretty": ["Beautiful Face", "Gương mặt đẹp", "Idol Face", "Pretty", "Cute Face"],
        "Curvy/Múp": ["Múp", "Plump", "Curvy", "Full-figured", "Chubby", "Thick"],
        "Legs/Thighs": ["Legs", "Thighs", "Đùi", "Chân", "Beautiful Legs"]
    }

    analyzed_count = 0
    for video in cache_data:
        full_path = video.get("full_path", "")
        if full_path.lower().startswith("f:"):
            analyzed_count += 1
            tags = video.get("categories", [])
            jav_meta = video.get("jav_metadata")
            if jav_meta:
                tags.extend(jav_meta.get("genres", []))
            
            tag_text = " ".join(tags).lower()
            path_text = full_path.lower()
            
            combined_text = tag_text + " " + path_text
            
            hit = False
            for category, keywords in mapping.items():
                if any(k.lower() in combined_text for k in keywords):
                    stats[category] += 1
                    hit = True
            
            if hit:
                stats["Total_Sample"] += 1

    print(f"--- BODY TRAIT PROBABILITY (Based on {analyzed_count} videos) ---")
    if stats["Total_Sample"] > 0:
        # We use a total based on hits to get relative percentages
        for trait, count in stats.items():
            if trait != "Total_Sample":
                percentage = (count / analyzed_count) * 100
                print(f"{trait}: {percentage:.2f}% ({count} hits)")
    else:
        print("No specific body traits found in metadata spikes.")

if __name__ == "__main__":
    analyze_body_traits()
