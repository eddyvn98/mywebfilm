
from jav_metadata_service import fetch_jav_metadata, _cache, save_jav_cache
import json
import time

# Clear cache for testing if needed
# _cache.clear()
# save_jav_cache(_cache)

test_codes = ["ADN-413", "MEYD-855"]

print("--- Testing JAV Scraper Improvements ---")

for code in test_codes:
    print(f"\n" + "="*30)
    print(f"Testing Code: {code}")
    start = time.time()
    metadata = fetch_jav_metadata(code)
    end = time.time()
    
    if metadata:
        print(f"RESULT: SUCCESS in {end-start:.2f}s")
        print(f"Source: {metadata.get('source', 'unknown')}")
        print(f"Studio: {metadata.get('studio')}")
        print(f"Actors: {metadata.get('actors')}")
        print(f"Genres: {metadata.get('genres')}")
    else:
        print(f"RESULT: FAILED")

print("\n--- Test Complete ---")
