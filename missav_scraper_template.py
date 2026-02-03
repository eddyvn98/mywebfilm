import requests
from bs4 import BeautifulSoup
import time
import json

def local_scrape_missav(genre_slug):
    """
    User can run this script locally. 
    Note: MissAV has Cloudflare protection, so a simple 'requests' might fail 
    if not using appropriate headers or a library like 'Selenium'.
    This script is a template using standard headers.
    """
    url = f"https://missav.live/vi/genres/{genre_slug}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    print(f"Bắt đầu cào dữ liệu từ: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Lỗi: Không thể truy cập (Status code: {response.status_code}). Có thể do Cloudflare chặn.")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        videos = []
        
        # Cấu trúc MissAV thường dùng class 'thumbnail' hoặc tương tự cho video
        # Đây là cấu trúc giả định dựa trên mẫu chung của các trang này
        video_items = soup.find_all('div', class_='thumbnail') 
        
        for item in video_items:
            title_tag = item.find('a', class_='title')
            if title_tag:
                title = title_tag.text.strip()
                link = title_tag['href']
                videos.append({"title": title, "link": link})
        
        return videos

    except Exception as e:
        print(f"Đã xảy ra lỗi: {e}")
        return []

if __name__ == "__main__":
    # Ví dụ: cào thể loại vú to
    # Trong môi trường của USER, nếu requests bị chặn, tôi khuyên dùng Selenium.
    print("Script này là mẫu để bạn tham khảo. Hãy cài đặt 'requests' và 'beautifulsoup4' để chạy.")
    # results = local_scrape_missav("big-breasts")
    # print(results)
