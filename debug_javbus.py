
import requests

url = "https://www.javbus.com/en/ADN-413"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
}

try:
    print(f"Testing URL: {url}")
    res = requests.get(url, headers=headers, timeout=15)
    print(f"Status Code: {res.status_code}")
    print(f"Response Length: {len(res.text)}")
    if res.status_code == 200:
        print("First 200 chars:")
        print(res.text[:200])
except Exception as e:
    print(f"Error: {e}")
