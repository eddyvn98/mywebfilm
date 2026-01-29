import os
import requests
import time

def download_avatar(actor_name, url):
    """
    Tải ảnh đại diện diễn viên về máy.
    Lưu tại: static/img/actors/{actor_name}.jpg
    """
    if not url:
        return False
        
    # Chuẩn hóa tên file
    safe_name = actor_name.replace(' ', '_')
    output_dir = os.path.join('static', 'img', 'actors')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    filepath = os.path.join(output_dir, f"{safe_name}.jpg")
    
    # Nếu đã có rồi thì thôi (trừ khi file quá nhỏ/lỗi)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        return True
        
    print(f"Đang tải avatar cho {actor_name} từ {url}...")
    try:
        # Xử lý URL protocol-relative
        if url.startswith('//'):
            url = 'https:' + url
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.javlibrary.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=20, stream=True)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            print(f"Lỗi tải ảnh {actor_name}: HTTP {response.status_code}")
    except Exception as e:
        print(f"Exception khi tải avatar {actor_name}: {e}")
        
    return False
