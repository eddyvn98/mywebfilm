import json
import os

def generate_supreme_archive():
    owned_file = "owned_data.json"
    output_html = "Supreme_Discovery_Archive.html"
    
    if not os.path.exists(owned_file):
        print(f"Error: {owned_file} not found.")
        return

    with open(owned_file, "r", encoding="utf-8") as f:
        owned_data = json.load(f)
    
    owned_codes = set(owned_data.get("codes", []))

    # --- ULTIMATE SERIES CONFIGURATION (150+ Series) ---
    themes = {
        "Tokyo Hot / Legend (nXXXX, Maria Ozawa, etc.)": [
            {"prefix": "n", "range": range(1, 1500), "fmt": "n{:04d}"}, # Tokyo Hot nXXXX
            {"prefix": "k", "range": range(1, 1000), "fmt": "k{:04d}"}, # Tokyo Hot kXXXX
            {"prefix": "H0930", "range": range(1, 1500), "fmt": "H0930-ori{:03d}"}, # G-Area / High Quality
            {"prefix": "D-1", "range": range(1, 500), "fmt": "D-1-ori{:03d}"}, # Early legends
        ],
        "Bibian / High Quality (BBAN, BBI, etc.)": [
            {"prefix": "BBAN", "range": range(1, 1500)}, {"prefix": "BBI", "range": range(1, 800)},
            {"prefix": "BBSS", "range": range(1, 500)}, {"prefix": "BBTU", "range": range(1, 500)},
            {"prefix": "CHIA", "range": range(1, 500)}, {"prefix": "BBD", "range": range(1, 500)},
        ],
        "Premium / Idol (SSNI, IPX, STARS, ABW)": [
            {"prefix": "SSNI", "range": range(1, 1000)}, {"prefix": "SNIS", "range": range(1, 1000)},
            {"prefix": "IPX", "range": range(1, 1000)}, {"prefix": "IPZ", "range": range(1, 1000)},
            {"prefix": "STARS", "range": range(1, 1000)}, {"prefix": "ABW", "range": range(1, 800)},
            {"prefix": "MIDE", "range": range(1, 1000)}, {"prefix": "MEYD", "range": range(1, 1000)},
            {"prefix": "TEK", "range": range(1, 600)}, {"prefix": "PPPD", "range": range(1, 999)},
        ],
        "Amateur / Real / Amateur (SIRO, 1Pondo, Caribbean)": [
            {"prefix": "SIRO", "range": range(1, 5000)}, # SIRO-XXXX
            {"prefix": "1Pondo", "range": range(1, 3000), "fmt": "101516-{:03d}-1pon"}, # 1Pondo format varies
            {"prefix": "Caribbeancom", "range": range(1, 3000), "fmt": "101516-{:03d}-carib"}, # Caribbean format
            {"prefix": "DASS", "range": range(1, 1000)}, {"prefix": "DASD", "range": range(1, 1000)},
            {"prefix": "MIAD", "range": range(1, 1000)}, {"prefix": "GIGA", "range": range(1, 800)},
        ],
        "Mature / MILF / Story (JUL, RBD, WANZ)": [
            {"prefix": "JUL", "range": range(1, 1000)}, {"prefix": "JUX", "range": range(1, 1000)},
            {"prefix": "RBD", "range": range(1, 1000)}, {"prefix": "SHKD", "range": range(1, 1000)},
            {"prefix": "ADN", "range": range(1, 999)}, {"prefix": "WANZ", "range": range(1, 1000)},
            {"prefix": "WZEN", "range": range(1, 800)}, {"prefix": "JUFE", "range": range(1, 800)},
        ]
    }

    # User provided Idol List (Expanded to include all mentioned + legends)
    user_idols = [
        "Ai Wakana", "Aika", "Airi Honoka", "Akari Mitani", "Amakawa Sora", "Amiri Saito", "Aoi", "Asuka Kirara", 
        "Ayunohana Mori", "Azumi Kinoshita", "Emiri Okazaki", "Futaba Kurimiya", "Hibiki Ohtsuki", "Hikari Sena", 
        "Himari Asada", "Hinako Mori", "Honoka Mihara", "Julia", "Jun Suehiro", "Kana Momonogi", "Kana Morisawa", 
        "Kanna Misaki", "Karen Yuzuriha", "Kashiwagi Konatsu", "Kinoshita Azumi", "Konan Koyoi", "Koroharu Suzuki", 
        "Kotoneka", "Marin Hinata", "Mei Haruka", "Mei Itsukaichi", "Mei Satsuki", "Midori Arimura", "Minami Aizawa", 
        "Minami Kojima", "Mirai Asumi", "Mirei Uno", "Momo Sakurazora", "Nami Hoshino", "Nana Fukada", "Natsume Saiharu", 
        "Nishinomiya Yume", "Non Kohana", "Of Sato (Momo Kato)", "Ogawa Rio", "Rei Kamiki", "Ria Yamate", "Rin Hachimitsu", 
        "Rin Yamitsu", "Rina Ishihara", "Rino Kirishima", "Rino Yuki", "Rui Hizuki", "Sakura Miura", "Shiori Kamisaki", 
        "Sho Nishino", "Shouko Takahashi", "Sora Amakawa", "Suzu Mitake", "Suzuka Ishikawa", "Tachikawa Rie", "Uta Hayano", 
        "Yamaguchi Riko", "Yua Mikami", "Yuna Hasegawa", "Yuna Hayashi", "Yuna Mitake", "Lima Arai", "Shitara Yuuhi", 
        "Erika Isshin", "Akagi Midori", "Mitsuki Momota", "Maria Ozawa"
    ]

    html_content = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Supreme Discovery Archive - Tokyo Hot & Legends</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #ff5722; --bg: #050505; --card-bg: #111; --text: #eee; }
        body { font-family: 'Outfit', sans-serif; background: var(--bg); color: var(--text); margin: 0; }
        .hero { background: linear-gradient(135deg, #222 0%, #000 100%); padding: 100px 20px; text-align: center; border-bottom: 5px solid var(--primary); }
        .hero h1 { font-size: 64px; margin: 0; color: var(--primary); text-transform: uppercase; letter-spacing: 5px; }
        .hero p { font-size: 18px; color: #888; margin-top: 10px; }
        .container { max-width: 1600px; margin: 0 auto; padding: 40px; }
        
        .nav-links { display: flex; justify-content: center; gap: 15px; margin-bottom: 50px; flex-wrap: wrap; position: sticky; top: 0; background: var(--bg); padding: 20px; z-index: 100; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .nav-btn { background: #1a1a1a; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; border: 1px solid #333; transition: 0.3s; font-size: 14px; }
        .nav-btn:hover { background: var(--primary); border-color: var(--primary); }

        .theme-section { margin-bottom: 80px; }
        .theme-title { font-size: 36px; border-left: 8px solid var(--primary); padding-left: 20px; margin-bottom: 30px; color: #fff; display: flex; align-items: center; }
        
        .series-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 30px; }
        .series-card { background: var(--card-bg); border-radius: 12px; border: 1px solid #222; overflow: hidden; display: flex; flex-direction: column; }
        .series-head { background: #222; padding: 15px; font-weight: bold; color: var(--primary); border-bottom: 1px solid #333; display: flex; justify-content: space-between; }
        .code-container { padding: 15px; height: 400px; overflow-y: auto; display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .code-box { background: #151515; padding: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #222; }
        .code-id { font-family: 'Courier New', monospace; font-size: 14px; color: #eee; }
        
        .ln-btn { padding: 5px 10px; font-size: 11px; border-radius: 4px; text-decoration: none; color: #fff; font-weight: bold; background: var(--primary); }
        .ln-btn.njav { background: #00bcd4; }

        .idol-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; margin-bottom: 60px; }
        .idol-tile { background: #111; border: 1px solid #222; padding: 15px; text-align: center; border-radius: 8px; transition: 0.3s; text-decoration: none; color: #fff; display: block; font-weight: bold; }
        .idol-tile:hover { background: var(--primary); border-color: var(--primary); transform: translateY(-3px); }

        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #000; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--primary); }
    </style>
</head>
<body>
    <div class="hero">
        <h1>SUPREME DISCOVERY</h1>
        <p>Cá nhân hóa 100% dựa trên lịch sử download và sở thích Idols của bạn</p>
    </div>

    <div class="container">
        <div class="nav-links">
            <a href="#idols" class="nav-btn">Lịch sử Idols</a>
            <a href="#Tokyo" class="nav-btn">Tokyo Hot / Legends</a>
            <a href="#Bibian" class="nav-btn">Bibian / High Quality</a>
            <a href="#Premium" class="nav-btn">Idol / Premium</a>
            <a href="#Amateur" class="nav-btn">Amateur / SIRO</a>
            <a href="#Mature" class="nav-btn">Mature / MILF</a>
        </div>

        <h2 id="idols" class="theme-title">Gợi ý dựa trên danh sách Idols của bạn</h2>
        <div class="idol-grid">
    """

    for name in sorted(user_idols):
        url = f"https://missav.live/vi/search/[{name.replace(' ', '%20')}]"
        html_content += f'<a href="{url}" target="_blank" class="idol-tile">{name}</a>'

    html_content += """
        </div>
    """

    total_gen = 0
    for theme_name, series_list in themes.items():
        anchor = theme_name.split()[0]
        html_content += f'<section id="{anchor}" class="theme-section"><h2 class="theme-title">{theme_name}</h2><div class="series-grid">'
        
        for s in series_list:
            prefix = s["prefix"]
            fmt = s.get("fmt", "{}-{}") # Default format
            
            codes = []
            # Take newest 400 codes for supreme depth
            for i in reversed(list(s["range"])):
                if "fmt" in s:
                    id_str = s["fmt"].format(i)
                else:
                    id_str = f"{prefix}-{i:03d}"
                
                if id_str.upper() not in owned_codes:
                    codes.append(id_str)
                if len(codes) >= 400:
                    break
            
            total_gen += len(codes)
            html_content += f"""
                <div class="series-card">
                    <div class="series-head"><span>{prefix}</span> <span>{len(codes)} mới</span></div>
                    <div class="code-container">
            """
            for c in codes:
                m_url = f"https://missav.live/vi/search/[{c}]"
                n_url = f"https://njav.tv/en/search?keyword={c}"
                html_content += f"""
                        <div class="code-box">
                            <span class="code-id">{c}</span>
                            <div class="link-group">
                                <a href="{m_url}" target="_blank" class="ln-btn">M</a>
                                <a href="{n_url}" target="_blank" class="ln-btn njav">N</a>
                            </div>
                        </div>
                """
            html_content += "</div></div>"
        
        html_content += "</div></section>"

    html_content += f"""
        <footer style="text-align: center; margin-top: 100px; padding: 60px; border-top: 1px solid #222; color: #555;">
            <p>Đã tìm thấy {total_gen} mã phim mới dựa trên sở thích cá nhân của bạn.</p>
            <p>© 2026 Supreme Discovery Engine - Dedicated to Personalized Entertainment</p>
        </footer>
    </div>
</body>
</html>
    """

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Supreme Archive created with {total_gen} new personalized codes!")

if __name__ == "__main__":
    generate_supreme_archive()
