import json
import logging
import os
import random
import re
import time
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)

# Persistent cache for metadata
CACHE_FILE = 'jav_metadata_cache.json'

def load_jav_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_jav_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

_cache = load_jav_cache()

IGNORE_PREFIXES = {
    'IMG', 'DSC', 'VID', 'REC', 'DSC', 'PIC', 'PHOTO', 'MOV', 'AVI', 'CLIP', 
    'SCREEN', 'SCREENSHOT', 'VLOG', 'MP4', 'VIDEO', '1080P', '720P', '4K',
    'CORDER', 'RECORDER', 'RECORD', 'MOBILE', 'PHONE', 'WHATSAPP'
}

def extract_code(filename):
    clean_name = re.sub(r'(_highlight|- highlight)$', '', os.path.splitext(filename)[0], flags=re.IGNORECASE)
    match = re.search(r'([a-zA-Z]{2,10})[-_ ]?(\d{3,8})', clean_name)
    if match:
        prefix = match.group(1).upper()
        if prefix in IGNORE_PREFIXES:
            return None
        if prefix == 'FC2' or prefix == 'PPV':
             full_match = re.search(r'(FC2[-_ ]+PPV[-_ ]+\d{3,8})', clean_name, re.IGNORECASE)
             if full_match:
                  return full_match.group(1).upper().replace(' ', '-')
        return f"{prefix}-{match.group(2)}"
    return None

def get_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    return s

def fetch_jav_metadata(code):
    if not code: return None
    code_upper = code.upper()
    if code_upper in _cache:
        cached = _cache[code_upper]
        if not cached.get('not_found') and not cached.get('error'):
            return cached
        if time.time() - cached.get('timestamp', 0) < 86400:
            return None

    logger.info("Looking up JAV metadata for code: %s", code_upper)
    metadata = fetch_from_javlibrary(code_upper)
    if not metadata:
        logger.info("JAVLibrary failed, trying JAVBus for %s", code_upper)
        metadata = fetch_from_javbus(code_upper)
        
    if metadata:
        _cache[code_upper] = metadata
        save_jav_cache(_cache)
        return metadata
    else:
        _cache[code_upper] = {'code': code_upper, 'not_found': True, 'timestamp': time.time()}
        save_jav_cache(_cache)
    return None

def fetch_from_javlibrary(code_upper):
    try:
        time.sleep(random.uniform(1.0, 2.5)) 
        search_url = f"https://www.javlibrary.com/en/vl_searchbyid.php?keyword={code_upper}"
        session = get_session()
        response = session.get(search_url, timeout=15)
        if response.status_code != 200: return None
        html = response.text
        
        if 'vl_searchbyid.php?keyword=' in html:
             id_match = re.search(r'vl_searchbyid\.php\?keyword=[^"]+">[^<]+</a></div><div class="id"><a href="\.\/\?v=([^"]+)"', html)
             if id_match:
                  movie_id = id_match.group(1)
                  time.sleep(1)
                  response = session.get(f"https://www.javlibrary.com/en/?v={movie_id}", timeout=15)
                  html = response.text

        soup = BeautifulSoup(html, 'html.parser')
        metadata = {
            'code': code_upper,
            'actors': [a.get_text() for a in soup.select('span.star a')],
            'genres': [g.get_text() for g in soup.select('span.genre a')],
            'studio': '',
            'source': 'javlibrary',
            'timestamp': time.time()
        }
        studio_el = soup.select_one('span.maker a')
        if studio_el: metadata['studio'] = studio_el.get_text()
        
        return metadata if metadata['actors'] or metadata['studio'] else None
    except Exception as e:
        logger.warning("JAVLibrary scrape error for %s: %s", code_upper, e)
    return None

def fetch_from_javbus(code_upper):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        session = get_session()
        res = session.get(f"https://www.javbus.com/en/{code_upper}", timeout=15)
        if res.status_code != 200: return None
        
        soup = BeautifulSoup(res.text, 'html.parser')
        metadata = {
            'code': code_upper,
            'actors': [],
            'genres': [],
            'studio': '',
            'source': 'javbus',
            'timestamp': time.time()
        }
        
        # Robust Studio & Actor parsing for JAVBus
        for p in soup.select('div.info p'):
            text = p.get_text()
            if 'Studio:' in text or 'Maker:' in text:
                a = p.find('a')
                if a: metadata['studio'] = a.get_text().strip()
                
        for g in soup.select('span.genre'):
            label = g.get_text().strip()
            if label and not g.find('a', href=re.compile('star')):
                metadata['genres'].append(label)
                
        for a in soup.select('div.star-name a, span.star a'):
            name = a.get_text().strip()
            if name and name not in metadata['actors']:
                metadata['actors'].append(name)
                
        return metadata if metadata['actors'] or metadata['studio'] else None
    except Exception as e:
        logger.warning("JAVBus scrape error for %s: %s", code_upper, e)
    return None

def fetch_and_cache_actor_avatar(actor_obj):
    # Dummy to keep compatibility, handles within main loop if needed
    return None
