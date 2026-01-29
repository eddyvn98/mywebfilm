
import os
import sys
import json
from scanner_service import scan_videos

# We want to check if D:\New folder (2)\test_tmm.mp4 gets the data from test_tmm.nfo
test_dir = r"D:\New folder (2)"
test_file = os.path.join(test_dir, "test_tmm.mp4")
test_nfo = os.path.join(test_dir, "test_tmm.nfo")

if not os.path.exists(test_file):
    print(f"FAILED: Test file {test_file} not found.")
    sys.exit(1)

print("--- Running Scan for TMM Verification ---")
# Only scan the specific directory
items = scan_videos([test_dir])

# Find our test item
test_item = next((i for i in items if i['full_path'] == test_file), None)

if test_item:
    print(f"Found item: {test_item['name']}")
    print(f"Categories: {test_item['categories']}")
    print(f"NFO Data present: {'nfo_metadata' in test_item and test_item['nfo_metadata'] is not None}")
    
    # Check prioritization
    has_tmm_studio = any("TMM Studio" in c for c in test_item['categories'])
    has_tmm_actor = any("Diễn viên Nhật" in c for c in test_item['categories'])
    
    if has_tmm_studio and has_tmm_actor:
        print("SUCCESS: NFO metadata correctly prioritized and applied.")
    else:
        print("FAILED: NFO metadata not found in categories.")
else:
    print("FAILED: Test item not found in scan results.")
