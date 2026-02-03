import json
import os

def generate_dark_hardcore_archive():
    owned_file = "owned_data.json"
    output_html = "Dark_Hardcore_Discovery.html"
    
    if not os.path.exists(owned_file):
        print(f"Error: {owned_file} not found.")
        return

    with open(owned_file, "r", encoding="utf-8") as f:
        owned_data = json.load(f)
    
    owned_codes = set(owned_data.get("codes", []))

    # --- DARK & HARDCORE SERIES CONFIGURATION ---
    dark_themes = {
        "FC2-PPV / Exclusive (Cực hiếm)": [
            {"prefix": "FC2-PPV", "range": range(3000000, 3010000), "fmt": "FC2-PPV-{}"}, # Modern FC2
            {"prefix": "FC2-PPV", "range": range(2000000, 2010000), "fmt": "FC2-PPV-{}"}, # Classic FC2
            {"prefix": "FC2-PPV", "range": range(1000000, 1010000), "fmt": "FC2-PPV-{}"}, # Legacy FC2
        ],
        "Hardcore / Attackers / Dark (ADN, GVH, etc.)": [
            {"prefix": "ADN", "range": range(1, 1000)}, # Attackers Night
            {"prefix": "GVH", "range": range(1, 1000)}, # Glory Visual
            {"prefix": "REB", "range": range(1, 600)}, # Real Action
            {"prefix": "DDT", "range": range(1, 1000)}, # Digital Channel
            {"prefix": "URKK", "range": range(1, 800)}, # Urara
            {"prefix": "VEMA", "range": range(1, 800)}, # Vema
            {"prefix": "TKT", "range": range(1, 600)}, # TKT
            {"prefix": "KIBD", "range": range(1, 600)}, # Kibou
        ],
        "Teacher / School / Discipline (MIDE, WANZ, IPX)": [
            {"prefix": "WANZ", "range": range(1, 1000)}, # Wanz (Discipline/Teacher)
            {"prefix": "MIDE", "range": range(1, 1000)}, # Moodyz (Teacher themes)
            {"prefix": "IPX", "range": range(1, 1000)}, # Idea Pocket (Teacher themes)
            {"prefix": "TEK", "range": range(1, 500)}, # Tek (School)
            {"prefix": "STARS", "range": range(1, 1000)}, # STARS (School/Uniforms)
        ],
        "Action / Heroine / Giga (Dark Hero)": [
            {"prefix": "GIGA", "range": range(1, 800)}, # GIGA (Dark Action)
            {"prefix": "GHV", "range": range(1, 500)}, # GIGA Heroine
            {"prefix": "ZEX", "range": range(1, 400)}, # Zex
        ]
    }

    html_content = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dark & Hardcore Discovery - Limited Edition</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&family=Outfit:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root { --dark-accent: #f44336; --dark-bg: #030303; --card-bg: #111; }
        body { font-family: 'Outfit', sans-serif; background: var(--dark-bg); color: #fff; margin: 0; }
        .hero { background: linear-gradient(to bottom, #2d0000, #000); padding: 80px 20px; text-align: center; border-bottom: 3px solid var(--dark-accent); }
        .hero h1 { font-family: 'Roboto Mono', monospace; font-size: 50px; color: var(--dark-accent); margin: 0; text-transform: uppercase; letter-spacing: 5px; }
        .container { max-width: 1400px; margin: 20px auto; padding: 20px; }
        
        .section-title { font-size: 28px; border-left: 5px solid var(--dark-accent); padding-left: 20px; margin-top: 50px; margin-bottom: 30px; color: var(--dark-accent); }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 25px; }
        .card { background: var(--card-bg); border-radius: 8px; border: 1px solid #300; overflow: hidden; }
        .card-header { background: #200; padding: 12px; font-weight: bold; border-bottom: 2px solid var(--dark-accent); }
        
        .code-grid { padding: 12px; height: 350px; overflow-y: auto; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .code-box { background: #1a1a1a; padding: 8px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #222; }
        .code-id { font-family: 'Roboto Mono', monospace; font-size: 13px; }
        .btn-link { background: var(--dark-accent); color: #fff; text-decoration: none; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold; }
        .btn-link.n { background: #2196f3; }

        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: #000; }
        ::-webkit-scrollbar-thumb { background: #444; }
    </style>
</head>
<body>
    <div class="hero">
        <h1>DARK & HARDCORE EDITION</h1>
        <p>Teacher, Rape-style, Hardcore & FC2-PPV - 100% Deduplicated</p>
    </div>

    <div class="container">
    """

    total_gen = 0
    for theme_name, series_list in dark_themes.items():
        html_content += f'<h2 class="section-title">{theme_name}</h2><div class="grid">'
        
        for s in series_list:
            prefix = s["prefix"]
            fmt_str = s.get("fmt", "{}-{}")
            
            codes = []
            # Reversed for newest first
            for i in reversed(list(s["range"])):
                if "fmt" in s:
                    id_str = s["fmt"].format(i)
                else:
                    id_str = f"{prefix}-{i:03d}"
                
                if id_str.upper() not in owned_codes:
                    codes.append(id_str)
                if len(codes) >= 400: # Depth per series
                    break
            
            total_gen += len(codes)
            html_content += f"""
                <div class="card">
                    <div class="card-header">{prefix} ({len(codes)} mới)</div>
                    <div class="code-grid">
            """
            for c in codes:
                m_url = f"https://missav.live/vi/search/[{c}]"
                n_url = f"https://njav.tv/en/search?keyword={c}"
                html_content += f"""
                        <div class="code-box">
                            <span class="code-id">{c}</span>
                            <div style="display:flex; gap:3px;">
                                <a href="{m_url}" target="_blank" class="btn-link">M</a>
                                <a href="{n_url}" target="_blank" class="btn-link n">N</a>
                            </div>
                        </div>
                """
            html_content += "</div></div>"
        
        html_content += "</div>"

    html_content += f"""
        <footer style="text-align: center; margin-top: 100px; padding: 50px; color: #555;">
            <p>Tổng cộng đã chuẩn bị {total_gen} mã phim Dark & Hardcore mới.</p>
            <p>© 2026 Dark Discovery Engine</p>
        </footer>
    </div>
</body>
</html>
    """

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Dark & Hardcore Archive created with {total_gen} codes!")

if __name__ == "__main__":
    generate_dark_hardcore_archive()
