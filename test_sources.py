import requests
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
print("Testing JavDb...")
try:
    r = requests.get("https://javdb.com/search?q=ADN-413&f=all", headers=headers, timeout=5)
    print(f"JavDb: {r.status_code}")
except Exception as e:
    print(f"JavDb Error: {e}")

print("Testing JAVBus...")
try:
    r = requests.get("https://www.javbus.com/en/search/ADN-413", headers=headers, timeout=5)
    print(f"JAVBus: {r.status_code}")
except Exception as e:
    print(f"JAVBus Error: {e}")
