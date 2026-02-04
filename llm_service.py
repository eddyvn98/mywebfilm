import requests
import json
import re
import time
from config_manager import load_config

_config = load_config()
MODEL_NAME = _config.get("llm_model", "llama3.2")
# Tăng context window lên 4096 để đọc được nhiều nội dung web hơn
DEFAULT_OPTIONS = {
    "temperature": 0.1,  # CỰC KỲ QUAN TRỌNG: 0.1 giúp AI không "bịa" chuyện
    "top_p": 0.5,        # Giới hạn xác suất, giúp câu trả lời tập trung hơn
    "num_ctx": 4096,     # Bộ nhớ ngữ cảnh rộng hơn
    "repeat_penalty": 1.2 # Tránh lặp từ
}

OLLAMA_URL = "http://localhost:11434/api/generate"

def call_gemini_api(prompt, api_key):
    """Gửi prompt tới Google Gemini API với cơ chế Retry khi quá tải"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.8,
            "topK": 40
        }
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code in [503, 429]:
                # 503: Overloaded, 429: Too Many Requests
                print(f"  [Gemini] Model overloaded/busy (Attempt {attempt+1}/{max_retries}). Retrying in 2s...")
                time.sleep(2)
                continue
            else:
                print(f"  [Gemini] API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"  [Gemini] Connection error: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
    
    print("  [Gemini] Failed after all retries.")
    return None

def call_local_llm(prompt, json_format=True):
    """Hàm wrapper: Chỉ sử dụng Gemini API. Đã vô hiệu hóa Ollama local."""
    api_key = _config.get("gemini_api_key")
    if api_key and api_key.strip():
        # print("  [LLM] Using Gemini 3 Flash...")
        res = call_gemini_api(prompt, api_key)
        return res
    
    print("  [LLM] Error: Gemini API Key not found. Local LLM is disabled.")
    return None

# Mapping studio giữ nguyên vì nó hữu ích
STUDIO_MAP = {
    "SSPD": "Shichiseidou", "ATID": "Attackers", "ADN": "Attackers", "MIDE": "Moodyz",
    "IPX": "Idea Pocket", "PRED": "Premium", "SSIS": "S1 NO.1 STYLE", "STARS": "SOD Star",
    "TEK": "Teikiry", "DAS": "DAS!", "DV": "Alice Japan", "EBOD": "E-Body",
    "FSDSS": "Faleno Star", "HND": "H.M.P", "MDS": "MOODYZ", "SPRD": "Sparking",
    "WANZ": "Wanz Factory", "SNIS": "S1 NO.1 STYLE", "JUFE": "Fitch", "FC2": "FC2-PPV"
}

def get_studio_by_code(code):
    if not code: return "Unknown"
    # Lấy prefix chữ cái đầu (VD: ABC-123 -> ABC)
    match = re.match(r'^([A-Z]+)', code.upper())
    prefix = match.group(1) if match else ""
    return STUDIO_MAP.get(prefix, "Unknown")

def clean_context(text):
    """Làm sạch ngữ cảnh trước khi đưa vào AI để tránh nhiễu"""
    if not text: return ""
    # Xóa các khoảng trắng thừa và dòng trống liên tiếp
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    # Cắt bớt nếu quá dài (Llama 3.2 3B chịu được khoảng 2000-3000 từ tốt nhất)
    return text[:6000]

def sanitize_metadata(data):
    """Lớp bảo vệ cuối cùng: Lọc rác nếu AI vẫn sơ suất"""
    if not data: return data
    
    # 1. Xử lý Title
    if data.get('title'):
        title = data['title']
        title = re.sub(r'\(\d{2,4}[/-]\d{2}[/-]\d{2,4}\)', '', title) # Xóa ngày tháng
        title = re.sub(r'\[.*?\]', '', title) # Xóa text trong ngoặc vuông
        data['title'] = title.strip()
    
    # 2. Xử lý Diễn viên (Chặn tên Việt Nam triệt để)
    if data.get('actors'):
        vn_surnames = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Ngô", "Dương", "Lý"]
        # Chỉ giữ lại tên nếu KHÔNG chứa họ Việt Nam và độ dài > 2 ký tự
        clean_actors = []
        for actor in data['actors']:
            if not any(vn in actor for vn in vn_surnames) and len(actor) > 2:
                clean_actors.append(actor)
        data['actors'] = clean_actors

    # 3. Studio Override
    code = data.get('code')
    if code:
        guess = get_studio_by_code(code)
        # Nếu AI không tìm ra Studio hoặc Studio là Unknown, dùng Mapping
        if guess != "Unknown" and (not data.get('studio') or data.get('studio') == "Unknown"):
            data['studio'] = guess
    
    return data

def create_analyzer_prompt(filename, context=""):
    """
    Prompt được viết lại theo phong cách 'Agent' cứng rắn.
    Sử dụng tiếng Anh để Llama 3.2 hiểu lệnh tốt nhất.
    """
    code_match = re.search(r'([a-zA-Z]{2,6}[-_]?\d{2,5})', filename)
    target_code = code_match.group(1).upper().replace('_', '-') if code_match else "UNKNOWN"
    studio_guess = get_studio_by_code(target_code)
    clean_ctx = clean_context(context)

    return f"""
    ### SYSTEM ROLE
    You are an Expert Metadata Extractor for JAV content. You are strict, precise, and never hallucinate.

    ### TASK
    Extract metadata for the video code: "{target_code}" based ONLY on the provided context.

    ### CONTEXT
    "{clean_ctx}"

    ### STRICT RULES (Follow these or you will be penalized)
    1. CODE: Must match "{target_code}" exactly.
    2. TITLE: Translate to professional Vietnamese. Remove release dates or file extensions.
    3. ACTORS:
       - Extract strictly from the 'Cast' or 'Actress' section.
       - Names MUST be in Romanized/Latin format (e.g., "Yua Mikami", NOT "三上悠亜").
       - ABSOLUTELY NO Vietnamese names (like Nguyen, Tran). If unsure, leave empty.
    4. STUDIO: If not found in context, use "{studio_guess}".
    5. IF DATA MISSING: Return "N/A" or empty list. Do not invent data.

    ### OUTPUT FORMAT (JSON ONLY)
    {{
      "code": "{target_code}",
      "title": "Vietnamese title string",
      "actors": ["Actor 1", "Actor 2"],
      "studio": "Studio name",
      "genres": ["Genre 1", "Genre 2"]
    }}
    """

def parse_llm_json(raw_response):
    """Parse JSON an toàn hơn, xử lý trường hợp AI nói nhảm trước khi đưa JSON"""
    if not raw_response: return None
    
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        # Dùng Regex để bắt đoạn JSON nằm giữa chuỗi văn bản
        match = re.search(r'(\{.*\})', raw_response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                return None
    return None

def normalize_metadata_with_llm(filename, context=""):
    """Hàm chính để gọi từ bên ngoài"""
    prompt = create_analyzer_prompt(filename, context)
    raw_response = call_local_llm(prompt)
    
    if not raw_response:
        print(f"  [LLM] Failed to get response for {filename}")
        return None
        
    result = parse_llm_json(raw_response)
    return sanitize_metadata(result)

if __name__ == "__main__":
    # Test tại chỗ
    test_file = "SSIS-987.mp4"
    # Giả lập context lộn xộn từ web
    test_context = """
    JavLibrary - SSIS-987 - Super Idol Story
    Release Date: 2023-10-10. Length: 120min.
    Cast: Eimi Fukada (Fukada Eimi), Tanaka (Male).
    Maker: S1 NO.1 STYLE. Label: S1.
    Genre: Solowork, Beautiful Girl, 4K.
    User comments: Phim này hay lắm.
    """
    print(json.dumps(normalize_metadata_with_llm(test_file, test_context), indent=2, ensure_ascii=False))