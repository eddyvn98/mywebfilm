import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2" # Model này nhẹ (2-3GB) sẽ chạy mượt trên GPU 4GB của anh

def call_local_llm(prompt):
    """Gửi prompt tới Ollama local"""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json().get('response')
        else:
            print(f"Error: Status {response.status_code}")
            return f"Error: Status {response.status_code}"
    except Exception as e:
        print(f"Error connecting to Ollama: {str(e)}")
        return f"Error connecting to Ollama: {str(e)}"

def create_analyzer_prompt(filename, context="", known_actors=None, known_studios=None):
    """Tạo prompt chuẩn để gửi cho LLM"""
    search_info = f'Context tìm kiếm: "{context}"' if context else "KHÔNG CÓ CONTEXT WEB. Hãy tự suy luận từ tên file."
    
    known_msg = ""
    if known_actors or known_studios:
        known_msg = "SỬ DỤNG LẠI DỮ LIỆU CŨ NẾU KHỚP:\n"
        if known_studios:
            known_msg += f"- Studios đã có: {', '.join(known_studios[:50])}...\n"
        if known_actors:
            # Chỉ lấy top 50 diễn viên để tránh quá dài
            known_msg += f"- Actors đã có: {', '.join(known_actors[:50])}...\n"

    return f"""
    Bạn là một trợ lý chuyên về metadata phim.
    Tên file: "{filename}"
    {search_info}

    {known_msg}
    
    Nhiệm vụ:
    - Trích xuất mã ID chuẩn (ví dụ: ABC-123).
    - Chuẩn hóa tên phim (Title): Nếu không có context, hãy đoán dựa trên mã/tên file (ví dụ "ABC-123" -> "Tác phẩm ABC 123").
    - Đoán Tên diễn viên (Actors) và Hãng phim (Studio). ƯU TIÊN dùng tên có trong danh sách "Studios đã có" hoặc "Actors đã có" nếu gần giống.
    - Đề xuất các thể loại (Genres) phù hợp.
    
    CHỈ trả về JSON duy nhất:
    {{
      "code": "MÃ_PHIM",
      "title": "Tên phim chuẩn hóa",
      "actors": ["Diễn viên"],
      "studio": "Hãng phim",
      "genres": ["Thể loại"]
    }}
    """

def parse_llm_json(raw_response):
    """Parse JSON từ phản hồi thô của LLM"""
    if not raw_response or raw_response.startswith("Error"):
        return None
    try:
        return json.loads(raw_response)
    except:
        # Fallback nếu JSON bị lỗi format (thường LLM hay viết thêm chữ bên ngoài)
        match = re.search(r'(\{.*\})', raw_response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
    return None

def normalize_metadata_with_llm(filename, context=""):
    """
    Dùng LLM để chuẩn hóa tên và phân loại dựa trên filename và context search được.
    """
    from tag_service import tag_manager
    tags = tag_manager.get_all()
    
    prompt = create_analyzer_prompt(
        filename, 
        context, 
        known_actors=tags.get('actors', []), 
        known_studios=tags.get('studios', [])
    )
    raw_response = call_local_llm(prompt)
    return parse_llm_json(raw_response)

if __name__ == "__main__":
    # Test
    test_file = "ADN-413.mp4"
    test_context = "Maker: Attack on Titan, Cast: Mikasa, Genre: Action"
    print(normalize_metadata_with_llm(test_file, test_context))
