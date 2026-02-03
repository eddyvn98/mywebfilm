import json
try:
    with open('movies_cache.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"Total entries: {len(data)}")
        if len(data) > 0:
            print("First item keys: ", data[0].keys())
            folders = set(v.get('folder', 'NONE') for v in data)
            print(f"Folders found: {folders}")
        else:
            print("Cache is empty!")
except Exception as e:
    print(f"Error: {e}")
