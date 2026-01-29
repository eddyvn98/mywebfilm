
import requests
from bs4 import BeautifulSoup
import re

def get_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    })
    return s

code = "MEYD-855"
url = f"https://www.javbus.com/en/{code}"
print(f"Testing JAVBus for: {code}")

session = get_session()
res = session.get(url, timeout=15)
print(f"Status: {res.status_code}")

if res.status_code == 200:
    soup = BeautifulSoup(res.text, 'html.parser')
    container = soup.find('div', class_='container')
    print(f"Container found: {container is not None}")
    
    if container:
        info = container.find('div', class_='info')
        print(f"Info div found: {info is not None}")
        
        if info:
            # Studio
            p_tags = info.find_all('p')
            for p in p_tags:
                text = p.get_text()
                if 'Studio:' in text or 'Maker:' in text:
                    a = p.find('a')
                    if a: print(f"Studio: {a.get_text().strip()}")
            
            # Genres
            genres = container.find_all('span', class_='genre')
            genre_list = []
            for g in genres:
                label = g.get_text().strip()
                if label and not g.find('a', href=re.compile('star')):
                    genre_list.append(label)
            print(f"Genres: {genre_list}")
            
            # Actors
            star_divs = container.find_all('div', class_='star-name')
            actor_list = []
            for div in star_divs:
                a = div.find('a')
                if a: actor_list.append(a.get_text().strip())
            print(f"Actors: {actor_list}")
else:
    print(f"Error response: {res.text[:500]}")
