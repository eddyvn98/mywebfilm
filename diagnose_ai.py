import requests
import sys

def test_connectivity(url):
    print(f"Testing: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"  Status: {resp.status_code}")
        print(f"  Length: {len(resp.text)}")
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False

if __name__ == "__main__":
    test_connectivity("https://missav.ai/en/search/ADN-413")
    test_connectivity("https://javdb.com/search?q=ADN-413&f=all")
    test_connectivity("https://www.javbus.com/en/search/ADN-413")
    test_connectivity("http://localhost:11434/api/tags") # List models
    
    print("\nChecking for llama3.2 model...")
    try:
        resp = requests.get("http://localhost:11434/api/tags")
        if "llama3.2" in resp.text:
            print("  [SUCCESS] llama3.2 is installed.")
        else:
            print("  [WARNING] llama3.2 NOT FOUND. Please run 'ollama run llama3.2' manually.")
    except Exception as e:
        print(f"  [ERROR] Cannot connect to Ollama: {e}")
