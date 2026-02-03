import json
import os
import re

def extract_owned_data():
    cache_file = "movies_cache.json"
    output_file = "owned_data.json"
    
    if not os.path.exists(cache_file):
        print(f"Error: {cache_file} not found.")
        return

    owned_codes = set()
    owned_idols = set()

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Regex for common JAV codes
        jav_regex = re.compile(r'([A-Z0-9]{2,10}-[0-9]{2,10}|n[0-9]{4})', re.IGNORECASE)

        for video in data:
            # 1. Extract from jav_metadata if available
            jav_meta = video.get("jav_metadata")
            if jav_meta:
                code = jav_meta.get("code")
                if code:
                    owned_codes.add(code.upper())
                
                actors = jav_meta.get("actors", [])
                if isinstance(actors, list):
                    for actor in actors:
                        owned_idols.add(actor.strip())

            # 2. Grep from filename/path just in case meta is missing
            name = video.get("name", "")
            matches = jav_regex.findall(name)
            for m in matches:
                owned_codes.add(m.upper())
                
        # Save to a small json for reference
        result = {
            "codes": sorted(list(owned_codes)),
            "idols": sorted(list(owned_idols))
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
            
        print(f"Successfully extracted {len(owned_codes)} unique codes and {len(owned_idols)} unique idols.")
        print(f"Data saved to {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    extract_owned_data()
