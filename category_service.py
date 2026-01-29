import re
from jav_metadata_service import extract_code, fetch_jav_metadata

# Mapping specialized categories to keywords
CATEGORY_MAP = {
    'Học sinh / Teen': ['học sinh', 'hs', 'teen', 'rau non', 'sinh viên', 'sv', '2k', 'mới lớn', 'student', 'schoolgirl'],
    'Show hàng / Live': ['show hàng', 'livetream', 'livestream', 'cam', 'webcam', 'clip nóng', 'tập tành', 'onlyfans'],
    'Thủ dâm / Solo': ['thủ dâm', 'thu dam', 'masturbat', 'solo', 'tự sướng', 'sục', 'sướng', 'fingering', 'handjob'],
    'Gái múp / Vú to': ['vú', 'ngực', 'boob', 'tits', 'múp', 'to', 'bự', 'nuột', 'dáng', 'big assets', 'curvy'],
    'Gạ gẫm / Call sex': ['gạ', 'call sex', 'chat sex', 'phỏng vấn', 'thử thách', 'interview'],
    'Người quen / MILF': ['em dâu', 'chị dâu', 'mẹ kế', 'cô giáo', 'sugar baby', 'giã gạo', 'milf', 'teacher', 'stepmother'],
}

IGNORE_LIST = {
    'IMG', 'MP4', 'VIDEO', 'SCREEN', 'REC', 'DSC', 'VLOG', 'MOV', 'AVI', 'MKV', 
    'WEB-DL', 'BLURAY', '1080P', '4K', '720P', 'HDRIP', 'HIGHLIGHT'
}

def get_categories(filename, existing_metadata=None, nfo_metadata=None, skip_scraping=True):
    """
    Phân tích tên file và trả về (categories, metadata).
    Ưu tiên: 1. NFO -> 2. Scraper (nếu enabled) -> 3. Keywords
    """
    name_clean = re.sub(r'(\.mp4|\.mkv|\.avi|\.ts|_highlight|- highlight)$', '', filename, flags=re.IGNORECASE)
    name_lower = name_clean.lower()
    categories = []

    # 1. NFO Priority
    if nfo_metadata:
        if nfo_metadata.get('studio'):
            cat_studio = f"Studio: {nfo_metadata['studio'].upper()}"
            if cat_studio not in categories:
                categories.append(cat_studio)
        
        for actor in nfo_metadata.get('actors', []):
            cat_actor = f"Diễn viên: {actor}"
            if cat_actor not in categories:
                categories.append(cat_actor)
                
        for gen in nfo_metadata.get('genres', []):
            if gen not in categories:
                categories.append(gen)

    # 2. Scraper fallback (Chỉ chạy nếu không skip)
    code = extract_code(filename)
    jav = existing_metadata
    
    if not categories and code and not skip_scraping:
        if not jav or jav.get('not_found') or jav.get('error'):
            jav = fetch_jav_metadata(code)

    if jav and not jav.get('not_found') and not jav.get('error') and not categories:
        if jav.get('studio'):
             cat_studio = f"Studio: {jav['studio'].upper()}"
             if cat_studio not in categories:
                 categories.append(cat_studio)
        
        for actor in jav.get('actors', []):
             cat_actor = f"Diễn viên: {actor}"
             if cat_actor not in categories:
                 categories.append(cat_actor)
        
        for gen in jav.get('genres', []):
             if gen not in categories:
                 categories.append(gen)
    
    # 3. Keywords (Dùng keywords này làm fallback nhanh)
    for cat, keywords in CATEGORY_MAP.items():
        if cat in categories: continue
        for kw in keywords:
            pattern = r'(?:^|[\s\._\-\[\]\(\)])' + re.escape(kw) + r'(?:$|[\s\._\-\[\]\(\)])'
            if re.search(pattern, name_lower):
                if cat not in categories:
                    categories.append(cat)
                break 

    # 4. Studio Regex Fallback
    if not categories:
        code_pattern = r'([a-zA-Z]{2,10})[-_ ]?(\d{3,8})'
        matches = re.findall(code_pattern, name_clean)
        for studio, _ in matches:
            studio_upper = studio.upper()
            if studio_upper not in IGNORE_LIST:
                cat_name = f"Studio: {studio_upper}"
                if cat_name not in categories:
                    categories.append(cat_name)

    # 5. Actor Regex Fallback
    if not any(c.startswith('Diễn viên:') for c in categories):
        actor_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?)$'
        actor_match = re.search(actor_pattern, name_clean.strip())
        if actor_match:
            actor_name = actor_match.group(1)
            if actor_name.upper() not in IGNORE_LIST:
                cat_label = f"Diễn viên: {actor_name}"
                if cat_label not in categories:
                    categories.append(cat_label)

    return categories, jav
