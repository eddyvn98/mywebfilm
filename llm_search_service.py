import json
import re
from llm_service import call_local_llm, parse_llm_json

def extract_search_intent(query):
    """
    Dùng LLM để phân tích ý định tìm kiếm của người dùng.
    Trả về cấu trúc JSON gồm: actors, genres, studio, keywords, và original_query.
    """
    prompt = f"""
    Bạn là trợ lý tìm kiếm phim thông minh. 
    Người dùng gõ: "{query}"

    Nhiệm vụ: Trích xuất các thực thể tìm kiếm từ câu trên.
    - actors: Danh sách tên diễn viên (nếu có).
    - genres: Danh sách thể loại (nếu có).
    - studio: Hãng phim (nếu có).
    - code: Mã phim (ví dụ: ABC-123) (nếu có).
    - keywords: Các từ khóa mô tả nội dung khác (ví dụ: "y tá", "bác sĩ", "tàu điện").
    - intent_summary: Một câu ngắn gọn tóm tắt ý định tìm kiếm bằng tiếng Việt.

    CHỈ trả về JSON duy nhất:
    {{
      "actors": [],
      "genres": [],
      "studio": "",
      "code": "",
      "keywords": [],
      "intent_summary": ""
    }}
    """
    
    raw_response = call_local_llm(prompt)
    intent = parse_llm_json(raw_response)
    
    if not intent:
        # Fallback cơ bản nếu LLM lỗi
        return {
            "actors": [],
            "genres": [],
            "studio": "",
            "code": "",
            "keywords": [query],
            "intent_summary": f"Tìm kiếm từ khóa: {query}"
        }
    
    return intent

def score_video(video, intent):
    """
    Tính điểm độ khớp của một video với ý định tìm kiếm.
    """
    score = 0
    name_lower = video.get('name', '').lower()
    cats = [c.lower() for c in video.get('categories', [])]
    meta = video.get('jav_metadata', {})
    
    # 1. Khớp mã phim (Trọng số cao nhất)
    if intent.get('code'):
        code_clean = intent['code'].lower().replace('-', '')
        if code_clean in name_lower.replace('-', ''):
            score += 100
    
    # 2. Khớp diễn viên
    for actor in intent.get('actors', []):
        actor_l = actor.lower()
        if actor_l in name_lower or any(actor_l in c for c in cats):
            score += 50
        elif meta.get('actors') and any(actor_l in a.lower() for a in meta['actors']):
            score += 50

    # 3. Khớp thể loại
    for genre in intent.get('genres', []):
        genre_l = genre.lower()
        if any(genre_l in c for c in cats):
            score += 30
            
    # 4. Khớp hãng phim
    studio = intent.get('studio')
    if studio:
        studio_l = studio.lower()
        if studio_l in name_lower or any(studio_l in c for c in cats):
            score += 40
            
    # 5. Khớp từ khóa keywords
    for kw in intent.get('keywords', []):
        kw_l = kw.lower()
        if kw_l in name_lower:
            score += 20
        if any(kw_l in c for c in cats):
            score += 15
            
    return score

def semantic_search(query, all_videos):
    """
    Thực hiện tìm kiếm ngữ nghĩa:
    1. Extract intent.
    2. Score all videos.
    3. Filter and sort by score.
    """
    intent = extract_search_intent(query)
    
    scored_items = []
    for v in all_videos:
        score = score_video(v, intent)
        if score > 0:
            scored_items.append((v, score))
            
    # Sắp xếp theo điểm giảm dần
    scored_items.sort(key=lambda x: x[1], reverse=True)
    
    results = [item[0] for item in scored_items]
    return results, intent
