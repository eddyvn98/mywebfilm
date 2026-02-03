import json
import os

def generate_smart_discovery():
    owned_file = "owned_data.json"
    output_html = "Smart_Discovery.html"
    
    if not os.path.exists(owned_file):
        print(f"Error: {owned_file} not found.")
        return

    with open(owned_file, "r", encoding="utf-8") as f:
        owned_data = json.load(f)
    
    owned_codes = set(owned_data.get("codes", []))
    owned_idols = set(owned_data.get("idols", []))

    # Curation of high-rated recommendations (Sample of what's popular and fits user preferences)
    # This is a curated list focusing on BIG BREASTS, MILF, TEEN and idols similar to Ai Uehara.
    recommendations = [
        # AI UEHARA SIMILAR / TOP PICK
        {"idol": "Mei Satsuki (五月芽衣)", "type": "Idol / Similar to Ai Uehara", "reason": "Gương mặt ngây thơ, thân hình múp nhẹ, cực giống phong cách thời kỳ đầu của Ai Uehara.", "codes": ["SSNI-928", "SSNI-865", "IPX-771"]},
        
        # BIG BREASTS / MÚP
        {"idol": "Julia (京香)", "type": "Big Breasts / MILF", "reason": "Nữ hoàng vòng 1, rất hợp với gu 'Gái múp / Vú to' của bạn.", "codes": ["JUL-822", "JUL-650", "JUL-233"]},
        {"idol": "Akari Mitani (三谷あかり)", "type": "Big Breasts / Idol", "reason": "Sở hữu vòng 1 khủng trên gương mặt búp bê.", "codes": ["SSNI-559", "SSNI-643", "IPX-214"]},
        {"idol": "Nanami Kondou (近藤七海)", "type": "Muchi Muchi / Plump", "reason": "Thân hình đầy đặn (Muchi Muchi) đúng chất 'múp' bạn đang tìm.", "codes": ["MIDE-837", "MIDE-763", "MIDE-613"]},
        
        # MILF / NGƯỜI QUEN
        {"idol": "Nozomi Ishihara (石原希望)", "type": "MILF / Versatile", "reason": "Diễn xuất biểu cảm cực tốt, thường đóng các vai chị dâu, hàng xóm.", "codes": ["SSNI-703", "SSNI-542", "IPX-572"]},
        {"idol": "Hibiki Otsuki (大槻ひびき)", "type": "Legend MILF", "reason": "Kỹ năng chuyên nghiệp, gương mặt mặn mà sang trọng.", "codes": ["MIDE-120", "MIDE-098", "MIDE-021"]},
        
        # TEEN / HỌC SINH
        {"idol": "Arina Hashimoto (橋本ありな)", "type": "Teen / Beauty", "reason": "Dù bạn đã có một số phim của Arina, đây là các mã cực mới/hot bạn có thể chưa có.", "codes": ["SSNI-911", "SSNI-880", "SSNI-776"]},
        {"idol": "Hina Maeda (前田ひな)", "type": "New Generation / Teen", "reason": "Tân binh đang cực hot với vẻ ngoài trẻ trung, năng động.", "codes": ["STARS-421", "STARS-365", "STARS-214"]},
        
        # OTHERS / TOP S1
        {"idol": "Eimi Fukada (深田えいみ)", "type": "Top Idol", "reason": "Gương mặt sắc sảo, đa dạng các thể loại.", "codes": ["SSNI-542", "SSNI-413", "IPX-213"]},
        {"idol": "Remu Suzumori (涼森れむ)", "type": "Premium Beauty", "reason": "Nét đẹp thanh tú, sang trọng.", "codes": ["IPX-497", "IPX-374", "IPX-202"]}
    ]

    html_content = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Discovery - Khám Phá Mới</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0a0a; color: #fff; padding: 30px; }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 { color: #ff9800; text-align: center; font-size: 32px; margin-bottom: 40px; text-transform: uppercase; letter-spacing: 2px; }
        .idol-card { background: #1a1a1a; margin-bottom: 30px; border-radius: 15px; border: 1px solid #333; overflow: hidden; display: flex; transition: transform 0.3s; }
        .idol-card:hover { border-color: #ff9800; transform: scale(1.02); }
        .idol-info { padding: 25px; flex: 1; }
        .idol-name { color: #ff9800; font-size: 24px; font-weight: bold; margin-bottom: 5px; }
        .idol-type { color: #4fc3f7; font-size: 14px; font-weight: bold; margin-bottom: 15px; text-transform: uppercase; }
        .idol-reason { color: #bbb; font-style: italic; margin-bottom: 20px; border-left: 3px solid #ff9800; padding-left: 10px; }
        .code-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
        .code-item { background: #262626; padding: 10px; text-align: center; border-radius: 8px; border: 1px solid #444; }
        .code-id { font-weight: bold; display: block; margin-bottom: 8px; font-family: 'Courier New', monospace; }
        .btn-link { background: #ff9800; color: #fff; text-decoration: none; font-size: 12px; padding: 5px 10px; border-radius: 4px; display: inline-block; }
        .btn-link:hover { opacity: 0.8; }
        .owned-tag { background: #4caf50; font-size: 10px; padding: 2px 5px; border-radius: 3px; position: absolute; top: 10px; right: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Smart Discovery & Personalized Recommendations</h1>
        <p style="text-align:center; color:#888;">Tất cả phim dưới đây đã được lọc bỏ những phim bạn đã có (Deduplicated)</p>
    """

    new_count = 0
    for rec in recommendations:
        # Filter codes
        filtered_codes = [c for c in rec["codes"] if c.upper() not in owned_codes]
        
        # If all codes filtered and idol already owned, skip or show as 'More from'
        if not filtered_codes:
            continue
            
        new_count += 1
        html_content += f"""
        <div class="idol-card">
            <div class="idol-info">
                <div class="idol-name">{rec['idol']}</div>
                <div class="idol-type">{rec['type']}</div>
                <div class="idol-reason">{rec['reason']}</div>
                <div class="code-grid">
        """
        
        for code in filtered_codes:
            missav_url = f"https://missav.live/vi/search/[{code}]"
            njav_url = f"https://njav.tv/en/search?keyword={code}"
            html_content += f"""
                    <div class="code-item">
                        <span class="code-id">{code}</span>
                        <a href="{missav_url}" target="_blank" class="btn-link">MissAV</a>
                        <a href="{njav_url}" target="_blank" class="btn-link" style="background:#f43f5e;">Njav</a>
                    </div>
            """
            
        html_content += """
                </div>
            </div>
        </div>
        """

    html_content += """
    </div>
</body>
</html>
    """

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Báo cáo Discovery đã được tạo với {new_count} idols mới. Đã lọc bỏ các trùng lặp.")

if __name__ == "__main__":
    generate_smart_discovery()
