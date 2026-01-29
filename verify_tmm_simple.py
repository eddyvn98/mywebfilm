
import os
import sys
from nfo_service import parse_nfo
from category_service import get_categories

# Paths
test_nfo = r"D:\New folder (2)\test_tmm.nfo"
test_video = "test_tmm.mp4"

print("--- Testing NFO Parser ---")
nfo_data = parse_nfo(test_nfo)
if nfo_data:
    print(f"Parsed Title: {nfo_data['title']}")
    print(f"Parsed Studio: {nfo_data['studio']}")
    print(f"Parsed Actors: {nfo_data['actors']}")
    print(f"Parsed Genres: {nfo_data['genres']}")
    
    print("\n--- Testing Category Logic with NFO ---")
    cats, jav = get_categories(test_video, nfo_metadata=nfo_data)
    print(f"Generated Categories: {cats}")
    
    # Check prioritization
    has_studio = any("Studio: TMM STUDIO" in c for c in cats)
    has_actor = any("Diễn viên: Diễn viên Nhật" in c for c in cats)
    
    if has_studio and has_actor:
        print("\nSUCCESS: NFO metadata correctly integrated and prioritized.")
    else:
        print("\nFAILED: Integration check failed.")
else:
    print("FAILED: NFO parser returned None.")
