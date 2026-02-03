import json
import os

def generate_massive_archive():
    owned_file = "owned_data.json"
    output_html = "Massive_Discovery_Archive.html"
    
    if not os.path.exists(owned_file):
        print(f"Error: {owned_file} not found. Hãy chạy extract_owned_data.py trước.")
        return

    with open(owned_file, "r", encoding="utf-8") as f:
        owned_data = json.load(f)
    
    owned_codes = set(owned_data.get("codes", []))

    # --- CONFIGURATION ---
    # Top Series prefixes matching user's taste (S1, IP, Moodyz, SOD, etc.)
    series_config = [
        {"prefix": "SSNI", "range": range(1, 1000), "cat": "S1 No.1 Style (Top Idols)"},
        {"prefix": "IPX", "range": range(1, 1000), "cat": "Idea Pocket (Premium/Múp)"},
        {"prefix": "STARS", "range": range(1, 1000), "cat": "SOD Create (Teen/High-end)"},
        {"prefix": "MIDE", "range": range(1, 1000), "cat": "Moodyz (Best of All)"},
        {"prefix": "SNIS", "range": range(1, 1000), "cat": "S1 Legacy (Classic)"},
        {"prefix": "FSFR", "range": range(1, 300), "cat": "Faleno (New Gen/Premium)"},
        {"prefix": "FSDSS", "range": range(1, 800), "cat": "Faleno (High Quality)"},
        {"prefix": "MEYD", "range": range(1, 800), "cat": "Moodyz Diva (Top Idols)"},
        {"prefix": "JUL", "range": range(1, 999), "cat": "Madonna (MILF/Mature)"},
        {"prefix": "JUX", "range": range(1, 999), "cat": "Madonna (Mature/Wife)"},
        {"prefix": "ADN", "range": range(1, 500), "cat": "Attackers (Dark/Story)"},
        {"prefix": "KAWD", "range": range(1, 800), "cat": "Kawaii* (Cute/Teen)"},
        {"prefix": "MIAD", "range": range(1, 999), "cat": "Moodyz (Amateur Style)"},
        {"prefix": "EBOD", "range": range(1, 999), "cat": "E-Body (Fit/Body)"},
        {"prefix": "IPZ", "range": range(1, 999), "cat": "Idea Pocket (Legacy)"},
        {"prefix": "PRED", "range": range(1, 400), "cat": "Premium (Beautiful Idols)"},
        {"prefix": "RBD", "range": range(1, 999), "cat": "Attacker (Real/Story)"},
        {"prefix": "SHKD", "range": range(1, 999), "cat": "Attackers (Story-driven)"},
        {"prefix": "ABP", "range": range(1, 999), "cat": "Prestige (Variety)"},
        {"prefix": "ABW", "range": range(1, 500), "cat": "Prestige (Top Idols)"},
        {"prefix": "DASD", "range": range(1, 999), "cat": "Das! (Real/Story)"},
        {"prefix": "DASS", "range": range(1, 999), "cat": "Das! (Amateur style)"},
    ]

    # Expanded Idols list (100+ high quality idols)
    idols = [
        "Yua Mikami", "Ai Uehara", "Eimi Fukada", "Arina Hashimoto", "Remu Suzumori",
        "Julia", "Akari Mitani", "Hina Maeda", "Mei Satsuki", "Nanami Kondou",
        "Minami Aizawa", "Yuna Ogura", "Shoko Takahashi", "Remu Suzumori", "Shiho Shinsaku",
        "Mao Kurata", "Kano Jura", "Rion", "Mana Sakura", "Miku Abeno",
        "Nozomi Ishihara", "Hibiki Otsuki", "Rin Jingu", "Reiko Sawamura", "Akiho Yoshizawa",
        "Tsubasa Amami", "Sola Aoi", "Ken Shimizu", "Mami Yamasaki", "Asuka Kirara",
        "Moe Amatsuka", "Kaoru Adachi", "Yua Kotone", "Nao Jinguuji", "Saori Hara",
        "Maria Ozawa", "Tina Yuzuki", "Anri Okita", "Hitomi Tanaka", "Meguri",
        "Miku Ishizuka", "Yui Hatano", "Erika Momotani", "Nene Yoshikawa", "Sakura Kizuna",
        "Karen Kaede", "Miru", "Urara Otani", "Hina Sakurada", "Miu Akari",
        "Ria Yamate", "Miyu Kano", "Ichika Matsumoto", "Riri Nanatsumi", "Mina Kanno",
        "Honoka", "Kurea Hasumi", "Sakuya Yua", "Uta Koharu", "Kurumi Miki",
        "Misaki Nanami", "Rio", "Rola Takizawa", "Asami Kondou", "Nana Ninomiya",
        "Reia Kuraki", "Suzu Hidaka", "Miku Ohashi", "Hikaru Koto", "Marina Shiraishi",
        "Kirari Koshikawa", "Natsuha Hirose", "Rika Hoshizaki", "Sakura Mana", "Tsubomi",
        "Aina Kiba", "Naho Ozawa", "Minami Kojima", "Miyuki Yokoyama", "An Nanba",
        "Misa Ononokomachi", "Riko Hinata", "Shiori Kamisaki", "Yuma Asami", "Aoi",
        "Miyabi Komori", "Rina Ishihara", "Shizuku Moria", "Ayumi Shinoda", "Kaho Kasumi",
        "Ria Sakurai", "Sora Shiina", "Airi Kijima", "Momoka Nishina", "Reon Kadena"
    ]

    html_content = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Massive Discovery Archive - 10,000+ Potential Codes</title>
    <style>
        body { font-family: 'Inter', sans-serif; background: #050505; color: #fff; margin: 0; padding: 0; }
        .header { background: linear-gradient(to bottom, #111, #000); padding: 50px 20px; text-align: center; border-bottom: 3px solid #ff9800; }
        .header h1 { color: #ff9800; font-size: 42px; margin: 0; text-transform: uppercase; }
        .container { max-width: 1400px; margin: 20px auto; padding: 20px; }
        .stats-bar { background: #111; padding: 15px; border-radius: 8px; margin-bottom: 30px; display: flex; justify-content: space-around; font-weight: bold; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 30px; }
        .section-card { background: #111; border: 1px solid #222; border-radius: 12px; overflow: hidden; }
        .section-header { background: #222; padding: 15px; border-bottom: 2px solid #ff9800; font-size: 18px; font-weight: bold; color: #ff9800; }
        .code-list { padding: 15px; height: 300px; overflow-y: auto; display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
        .code-item { border-bottom: 1px solid #222; padding: 5px; display: flex; justify-content: space-between; align-items: center; }
        .code-id { font-family: monospace; font-size: 13px; color: #4fc3f7; }
        .btn-s { background: #ff9800; color: #fff; text-decoration: none; padding: 3px 6px; border-radius: 3px; font-size: 10px; }
        .btn-s.njav { background: #f43f5e; }
        .idol-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; margin-bottom: 50px; }
        .idol-btn { background: #1a1a1a; border: 1px solid #333; padding: 15px; text-align: center; border-radius: 8px; transition: 0.2s; text-decoration: none; color: #fff; }
        .idol-btn:hover { border-color: #ff9800; background: #222; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #111; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #444; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Massive Discovery Archive</h1>
        <p>Kho lưu trữ hàng ngàn mã phim và Idol dựa trên sở thích cá nhân của bạn</p>
    </div>

    <div class="container">
        <div class="stats-bar">
            <span>Đã sở hữu: """ + str(len(owned_codes)) + """ mã</span>
            <span>Target: 10,000+ codes</span>
            <span>Update: 2026</span>
        </div>

        <h2>1. Danh sách Idol Gợi Ý (100+ Idols)</h2>
        <div class="idol-grid">
    """

    for idol in sorted(idols):
        search_url = f"https://missav.live/vi/search/[{idol.replace(' ', '%20')}]"
        html_content += f'<a href="{search_url}" target="_blank" class="idol-btn">{idol}</a>'

    html_content += """
        </div>

        <h2>2. Kho Series Phim Khổng Lồ (Deduplicated)</h2>
        <div class="grid">
    """

    total_codes_generated = 0
    for config in series_config:
        prefix = config["prefix"]
        cat = config["cat"]
        
        codes = []
        # Generate codes, but in reverse to get newest first
        for i in reversed(list(config["range"])):
            code = f"{prefix}-{i:03d}"
            if code.upper() not in owned_codes:
                codes.append(code)
            if len(codes) >= 200: # Limit per section for stability
                break
        
        total_codes_generated += len(codes)
        
        html_content += f"""
            <div class="section-card">
                <div class="section-header">{cat} ({prefix})</div>
                <div class="code-list">
        """
        
        for code in codes:
            missav_url = f"https://missav.live/vi/search/[{code}]"
            njav_url = f"https://njav.tv/en/search?keyword={code}"
            html_content += f"""
                    <div class="code-item">
                        <span class="code-id">{code}</span>
                        <div>
                            <a href="{missav_url}" target="_blank" class="btn-s">M</a>
                            <a href="{njav_url}" target="_blank" class="btn-s njav">N</a>
                        </div>
                    </div>
            """
            
        html_content += """
                </div>
            </div>
        """

    html_content += f"""
        </div>
        <div style="text-align: center; margin-top: 50px; color: #888;">
            <p>Tổng cộng đã tạo {total_codes_generated} mã mới chưa có trong kho của bạn.</p>
        </div>
    </div>
</body>
</html>
    """

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Báo cáo Massive Archive đã được tạo thành công: {total_codes_generated} mã mới.")

if __name__ == "__main__":
    generate_massive_archive()
