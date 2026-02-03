import json
try:
    with open('movies_cache.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"Total entries: {len(data)}")
        if len(data) > 0:
            folders = sorted(list(set(v.get('folder', 'NONE') for v in data if v)))
            print(f"Unique Folders ({len(folders)}):")
            for fld in folders[:50]: # Show first 50
                print(f" - {fld}")
        else:
            print("Cache is empty!")
except Exception as e:
    print(f"Error: {e}")
