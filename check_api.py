import requests
import json
try:
    r = requests.get('http://127.0.0.1:5000/api/videos', timeout=5)
    data = r.json()
    print(f"API status: Success")
    print(f"Total videos from API: {len(data)}")
    if data:
        folders = set(v.get('folder') for v in data if v)
        print(f"Folders in API: {folders}")
    else:
        print("API returned empty list!")
except Exception as e:
    print(f"API Error: {e}")
