import os

def generate_search_portal():
    output_html = "Ultimate_Search_Portal.html"

    # --- PORTAL DATA ---
    series_portals = {
        "Premium Idols (S1, IP, SOD)": ["SSNI", "SNIS", "IPX", "IPZ", "STARS", "ABW", "ABP", "MIDE", "MEYD", "TEK", "PPPD"],
        "High Quality / Bibian": ["BBAN", "BBI", "BBSS", "BBTU", "CHIA", "BBD", "FSDSS", "FSFR", "KAWD"],
        "Dark / Hardcore / Dark Hero": ["FC2-PPV", "ADN", "GVH", "REB", "DDT", "URKK", "VEMA", "TKT", "KIBD", "GIGA", "GHV", "ZEX"],
        "Amateur / Real Life": ["SIRO", "1Pondo", "Caribbeancom", "DASS", "DASD", "MIAD", "MIGD", "MKON", "SKE", "SCR"],
        "Mature / MILF / Story": ["JUL", "JUX", "RBD", "SHKD", "WANZ", "WZEN", "JUFE", "JUC", "WAN", "HODV"],
    }

    niche_portals = {
        "Teacher / School": ["Teacher", "Professor", "Uniform", "Sensei", "Discipline"],
        "Extreme Hardcore": ["Hardcore", "Rape", "Bondage", "Deep Throat", "Creampie", "Double Penetration"],
        "Physical Traits": ["Busty", "Big Breasts", "Múp", "Plump", "Slender", "Legs", "Tan Line"],
        "Scenario": ["Wife", "Adultery", "Neighbor", "Incest", "Office Lady", "Nurse"]
    }

    idols = [
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
    <title>Ultimate Search Portal - Verified Discovery</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&family=Bebas+Neue&display=swap" rel="stylesheet">
    <style>
        :root { --p: #ff5722; --bg: #050505; --c: #151515; }
        body { font-family: 'Outfit', sans-serif; background: var(--bg); color: #fff; margin:0; }
        .hero { background: linear-gradient(135deg, #111, #000); padding: 80px 20px; text-align: center; border-bottom: 4px solid var(--p); }
        .hero h1 { font-family: 'Bebas Neue'; font-size: 72px; margin:0; color: var(--p); letter-spacing: 5px; }
        .hero p { color: #888; font-size: 18px; margin-top: 10px; }
        .container { max-width: 1400px; margin: 40px auto; padding: 0 40px; }
        
        .section { margin-bottom: 60px; scroll-margin-top: 100px; }
        .s-title { font-size: 32px; color: var(--p); margin-bottom: 30px; border-left: 8px solid var(--p); padding-left: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
        .card { background: var(--c); border-radius: 10px; padding: 20px; border: 1px solid #222; transition: 0.3s; }
        .card:hover { border-color: var(--p); transform: translateY(-3px); }
        
        .idol-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }
        .idol-tile { background: #111; padding: 10px; border-radius: 8px; text-align: left; text-decoration: none; color: #fff; border: 1px solid #222; display: flex; align-items: center; gap: 10px; transition: 0.2s; }
        .idol-tile:hover { background: var(--p); border-color: var(--p); transform: translateY(-3px); }
        
        .avatar-box { width: 45px; height: 45px; border-radius: 50%; overflow: hidden; background: #222; border: 1px solid rgba(255,255,255,0.1); }
        .avatar { width: 100%; height: 100%; object-fit: cover; }
        
        .idol-tile span { font-weight: bold; font-size: 14px; }
        .tag-link { background: #222; color: #fff; text-decoration: none; padding: 5px 12px; border-radius: 3px; font-size: 13px; font-weight: bold; margin: 2px; display: inline-block; }
        .tag-link:hover { background: #333; color: var(--p); }
        
        .footer { text-align: center; padding: 100px; border-top: 1px solid #222; color: #444; }
    </style>
</head>
<body>
    <div class="hero">
        <h1>ULTIMATE SEARCH PORTAL</h1>
        <p>Hệ thống cổng tìm kiếm vạn năng - Tích hợp Ảnh đại diện Idol tự động</p>
    </div>

    <div class="container">
    <script>
        function handleImageError(img, name) {
            const sources = [
                `https://www.javdatabase.com/images/idols/${name.toLowerCase().replace(/ /g, '-')}.jpg`,
                `https://missav.com/images/actresses/${encodeURIComponent(name)}.jpg`,
                `https://www.asianpornstars.com/performer_images/${name.toLowerCase().replace(/ /g, '-')}.jpg`
            ];
            let currentSourceIdx = parseInt(img.getAttribute('data-src-idx') || '0');
            if (currentSourceIdx < sources.length) {
                img.setAttribute('data-src-idx', currentSourceIdx + 1);
                img.src = sources[currentSourceIdx];
            } else {
                img.src = "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y";
                img.style.opacity = "0.3";
            }
        }
    </script>
    <section id="series" class="section">
        <h2 class="s-title">Series Portals</h2>
        <div class="grid">
    """

    for cat, list_p in series_portals.items():
        html_content += f"""
                <div class="card">
                    <h3 style="color:#999; font-size:12px; text-transform:uppercase;">{cat}</h3>
                    <div style="margin-top:10px;">
        """
        for s in list_p:
            m_url = f"https://missav.live/vi/search/[{s}]"
            html_content += f'<a href="{m_url}" target="_blank" class="tag-link">{s}</a>'
        html_content += "</div></div>"

    html_content += """
        </div>
    </section>

    <section id="idols" class="section">
        <h2 class="s-title">My Idol Collection (70+ Idols)</h2>
        <div class="idol-grid">
    """

    for name in sorted(idols):
        m_url = f"https://missav.live/vi/search/[{name.replace(' ', '%20')}]"
        initial_src = f"https://www.javdatabase.com/images/idols/{name.lower().replace(' ', '-')}.jpg"
        html_content += f"""
            <a href="{m_url}" target="_blank" class="idol-tile">
                <div class="avatar-box">
                    <img class="avatar" src="{initial_src}" alt="{name}" data-src-idx="1"
                         onerror="handleImageError(this, '{name}')">
                </div>
                <span>{name}</span>
            </a>
        """

    html_content += """
        </div>
    </section>

    <footer class="footer">
        <p>© 2026 AI SUPREME SEARCH ENGINE</p>
    </footer>
    </div>
</body>
</html>
    """

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Ultimate Search Portal with Automated Avatars generated successfully!")

if __name__ == "__main__":
    generate_search_portal()
