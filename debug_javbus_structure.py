
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

if res.status_code == 200:
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Check for .movie info
    movie_info = soup.find('div', class_='movie')
    if movie_info:
        print("Found .movie div")
        info = movie_info.find('div', class_='info')
        if info:
            print("Found .info div inside .movie")
            for p in info.find_all('p'):
                print(f"P text: {p.get_text().strip()}")
                
    # Check for actors
    stars = soup.find_all('div', class_='star-name')
    print(f"Found {len(stars)} actors via .star-name")
    if not stars:
        # Try finding stars in the sidebar or info
        stars = soup.find_all('span', class_='star')
        print(f"Found {len(stars)} actors via span.star")

    # Search for Studio again
    studio_label = soup.find('span', string=re.compile("Studio:", re.I))
    if studio_label:
        print(f"Found Studio Label! Parent text: {studio_label.parent.get_text()}")
else:
    print(f"Status: {res.status_code}")
