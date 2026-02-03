import json
import re
from llm_service import call_local_llm, parse_llm_json

def extract_search_intent(query):
    """
    Phân tích ý định tìm kiếm.
    Prompt được tối ưu để Llama 3.2 hiểu cấu trúc lệnh tốt hơn.
    """
    prompt = f"""
    ### SYSTEM
    You are a smart Search Query Analyzer. 
    Analyze the user's input: "{query}" and extract entities into JSON.

    ### INSTRUCTIONS
    - code: Look for patterns like ABC-123, SSIS-090.
    - actors: Look for names (Japanese or Vietnamese keywords referring to people).
    - genres: Look for categories (e.g., 'uncensored', 'drama', 'school').
    - target_site: If the query implies finding metadata, set to "javlibrary".
    - intent_summary: A short summary in Vietnamese.

    ### OUTPUT FORMAT (JSON ONLY)
    {{
      "actors": ["name1"],
      "genres": ["genre1"],
      "studio": "studio name",
      "code": "ABC-123",
      "keywords": ["keyword"],
      "intent_summary": "Tóm tắt ý định tìm kiếm",
      "target_site": "javlibrary" 
    }}
    """
    
    raw_response = call_local_llm(prompt)
    intent = parse_llm_json(raw_response)
    
    # Fallback nếu AI tịt ngòi
    if not intent:
        # Tự động nhận diện mã phim bằng regex nếu AI fail
        code_match = re.search(r'([a-zA-Z]{2,5}-\d{3,5})', query)
        code = code_match.group(1).upper() if code_match else ""
        return {
            "actors": [],
            "genres": [],
            "studio": "",
            "code": code,
            "keywords": [query],
            "intent_summary": f"Tìm kiếm: {query}",
            "target_site": "javlibrary"
        }
    
    return intent

def search_web(query, max_results=5):
    """
    General purpose web search using DuckDuckGo.
    Returns a combined text context from the search results.
    """
    try:
        from duckduckgo_search import DDGS
        import requests
        from bs4 import BeautifulSoup

        print(f"  [Search] Searching web for: {query}")
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"Title: {r['title']}\nSnippet: {r['body']}\nSource: {r['href']}")
        
        return "\n\n".join(results)
    except Exception as e:
        print(f"  [Search] DDGS Error: {e}")
        # Fallback to a very simple scraper if needed, or return empty
        return ""

def search_jav_context(query):
    """
    Specialized search for JAV metadata.
    Searches JavLibrary, JavBus, and other sources to get a rich context.
    """
    # Clean query to extract code if possible
    code_match = re.search(r'([a-zA-Z]{2,6}[-_]?\d{2,5})', query)
    code = code_match.group(1).upper().replace('_', '-') if code_match else query

    print(f"  [Search] Searching JAV context for: {code}")
    
    # Try multiple sources to build a solid context
    sources = [
        f"https://www.javlibrary.com/en/vl_searchbyid.php?keyword={code}",
        f"https://www.javbus.com/en/{code}"
    ]
    
    context_parts = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for url in sources:
        try:
            import requests
            from bs4 import BeautifulSoup
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Extract main content areas
                text = ""
                if 'javlibrary' in url:
                    video_info = soup.select_one('#video_info')
                    if video_info: text = video_info.get_text()
                else:
                    info = soup.select_one('.info')
                    if info: text = info.get_text()
                
                if text:
                    context_parts.append(f"Source: {url}\n{text.strip()}")
        except Exception as e:
            print(f"  [Search] Source error ({url}): {e}")

    # If specialized search fails, try general web search
    if not context_parts:
        return search_web(f"JAV {code} metadata cast studio genres")
        
    return "\n\n".join(context_parts)

def score_video(video, intent):
    """
    Hệ thống tính điểm (Ranking System) để tìm video khớp nhất.
    Không thay đổi nhiều vì logic cũ của bạn khá ổn, chỉ tinh chỉnh trọng số.
    """
    score = 0
    # Chuẩn hóa dữ liệu đầu vào để so sánh không phân biệt hoa thường
    name_lower = str(video.get('name', '')).lower()
    path_lower = str(video.get('path', '')).lower()
    cats = [str(c).lower() for c in video.get('categories', [])]
    
    # Metadata có sẵn trong file (nếu có)
    meta = video.get('jav_metadata', {})
    if not isinstance(meta, dict): meta = {}
    
    meta_actors = [str(a).lower() for a in meta.get('actors', [])]
    
    # 1. KHỚP MÃ PHIM (Trọng số TỐI THƯỢNG: 1000 điểm)
    # Mã phim là duy nhất, nếu khớp thì chắc chắn đúng 99%
    if intent.get('code'):
        code_clean = intent['code'].lower().replace('-', '')
        # Kiểm tra trong tên file và cả đường dẫn
        if code_clean in name_lower.replace('-', '') or code_clean in path_lower.replace('-', ''):
            score += 1000 
    
    # 2. Khớp diễn viên (Trọng số cao: 100 điểm)
    for actor in intent.get('actors', []):
        actor_l = actor.lower()
        # Tìm trong tên file hoặc metadata đã có
        if actor_l in name_lower or any(actor_l in a for a in meta_actors):
            score += 100
        # Tìm trong categories (nhiều khi tag chứa tên diễn viên)
        elif any(actor_l in c for c in cats):
            score += 50

    # 3. Khớp hãng phim (50 điểm)
    studio = intent.get('studio')
    if studio:
        studio_l = studio.lower()
        if studio_l in name_lower or (meta.get('studio') and studio_l in meta['studio'].lower()):
            score += 50
            
    # 4. Khớp thể loại (30 điểm)
    for genre in intent.get('genres', []):
        genre_l = genre.lower()
        if any(genre_l in c for c in cats):
            score += 30
            
    return score

def semantic_search(query, all_videos):
    """
    Hàm gọi chính: Từ query -> Intent -> Score -> Sort
    """
    # Bước 1: Hiểu ý người dùng
    intent = extract_search_intent(query)
    print(f"  [Search] Intent parsed: {intent.get('intent_summary')} | Code: {intent.get('code')}")
    
    scored_items = []
    for v in all_videos:
        final_score = score_video(v, intent)
        if final_score > 0:
            scored_items.append((v, final_score))
            
    # Bước 2: Sắp xếp điểm từ cao xuống thấp
    scored_items.sort(key=lambda x: x[1], reverse=True)
    
    # Chỉ lấy danh sách video, bỏ điểm số khi return
    results = [item[0] for item in scored_items]
    return results, intent

if __name__ == "__main__":
    # Test thử logic tìm kiếm
    mock_db = [
        {"name": "SSIS-987.mp4", "categories": ["uncensored"], "jav_metadata": {"actors": ["Eimi Fukada"]}},
        {"name": "ABP-123.mp4", "categories": ["drama"], "jav_metadata": {"actors": ["Yua Mikami"]}}
    ]
    query = "Tìm phim của Eimi Fukada mã SSIS-987"
    res, intent = semantic_search(query, mock_db)
    print("Found:", [r['name'] for r in res])