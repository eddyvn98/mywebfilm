import os
import requests
from bs4 import BeautifulSoup
import re
import time
import random
import sys

# Biến toàn cục để lưu Class DDGS đã import thành công
GLOBAL_DDGS = None

def try_import():
    global GLOBAL_DDGS
    try:
        from duckduckgo_search import DDGS
        GLOBAL_DDGS = DDGS
        return True
    except ImportError:
        try:
            from ddgs import DDGS
            GLOBAL_DDGS = DDGS
            return True
        except ImportError:
            return False

# Debug và Tự động cài đặt nếu thiếu
print(f"--- DEBUG ENVIRONMENT ---")
print(f"Python Executable: {sys.executable}")

if not try_import():
    print("Dependency missing. Attempting self-installation...")
    try:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "duckduckgo-search"], check=True)
        if try_import():
            print("Self-installation: SUCCESS")
        else:
            print("Self-installation: FAILED")
    except Exception as e:
        print(f"Self-installation error: {e}")
else:
    print("Import DDGS: SUCCESS")
print(f"-------------------------")

def clean_filename_for_search(filename):
    """Xóa các phần rác phổ biến trong tên file để search chính xác hơn"""
    # Xóa extension
    name = os.path.splitext(filename)[0]
    
    # Xóa các domain và tag rác phổ biến
    junk_patterns = [
        r'MissAV(-| )?', r'Watch( )?HD( )?JAV( )?On(line)?', r'Uncensored', r'HD', r'4K', r'720p', r'1080p',
        r'Sub(title)?', r'Vietsub', r' thuyết minh', r' bản đẹp', r'Full( )?HD', r'Bluray', r'x264', r'x265',
        r'[-_]C(\.ts)?$', r'\.mp4$', r'\.mkv$', r'\.avi$', r' Nightmare-chan'
    ]
    for pattern in junk_patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    # Thay thế các ký tự đặc biệt bằng khoảng trắng để search linh hoạt
    name = re.sub(r'[-_.]', ' ', name)
    # Trim
    return ' '.join(name.split())

def extract_potential_code(filename):
    """Trích xuất mã phim tiềm năng (VD: HAKC-016)"""
    match = re.search(r'([a-zA-Z]{2,6}[-_]\d{3,5})', filename)
    return match.group(1) if match else None

def search_jav_context(filename):
    """
    Tìm kiếm context cho LLM với logic 'Search Agent':
    1. Trích xuất mã phim (VD: HAKC-016).
    2. Tìm kiếm JAVBus (Ưu tiên số 1).
    3. Nếu xịt, dùng DuckDuckGo với query đã lọc sạch.
    """
    code = extract_potential_code(filename)
    cleaned_name = clean_filename_for_search(filename)
    
    context_results = []

    # 1. Thử JAVBus (High Reliability)
    target_code = code if code else cleaned_name.split()[0] if cleaned_name else None
    if target_code:
        print(f"  [JAVBus] Đang quét: {target_code}...")
        try:
            # JAVBus thỉnh thoảng yêu cầu cookies hoặc redirect
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            # Thử search chung
            search_url = f"https://www.javbus.com/en/search/{target_code}"
            resp = requests.get(search_url, headers=headers, timeout=5, allow_redirects=True)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Trường hợp 1: Link trực tiếp (Đã redirect vào trang phim)
                if "movie-list" not in resp.text and "ID:" in resp.text:
                    title = soup.find('h3').get_text(strip=True) if soup.find('h3') else ""
                    # Lấy info trong thẻ .info
                    info = soup.find('div', class_='info')
                    info_text = info.get_text(" | ", strip=True) if info else ""
                    context_results.append(f"JAVBus (Direct): {title} | {info_text[:400]}")
                # Trường hợp 2: Danh sách kết quả
                else:
                    items = soup.find_all('a', class_='movie-box')
                    for item in items[:2]:
                        title = item.find('span').get_text(strip=True) if item.find('span') else ""
                        context_results.append(f"JAVBus (Search): {title}")
                
                if context_results: print("  [JAVBus] OK.")
        except Exception as e:
            print(f"  [JAVBus] Skip: {e}")

    # 2. Thử DuckDuckGo (Fallback rộng)
    if not context_results and GLOBAL_DDGS:
        # Search 2 lần: Một lần mã, một lần tên
        search_terms = []
        if code: search_terms.append(code)
        if cleaned_name and cleaned_name != code: search_terms.append(cleaned_name)
        
        for term in search_terms[:2]:
            try:
                with GLOBAL_DDGS() as ddgs:
                    print(f"  [DDG] Search: {term}")
                    results = ddgs.text(term, max_results=2)
                    if results:
                        for r in results:
                            context_results.append(f"Web: {r['title']} -> {r['body'][:300]}")
                        break # Nếu có kết quả rồi thì thôi
            except Exception as e:
                print(f"  [DDG] Error: {e}")

    if context_results:
        return "\n---\n".join(context_results)
    
    return f"Không tìm thấy thông tin trên mạng cho '{filename}'."

    if context_results:
        return "\n---\n".join(context_results)
    
    return f"No context found on web for '{filename}'. Local LLM will attempt to infer from name only."

if __name__ == "__main__":
    # Test
    print(search_jav_context("ADN-413"))
