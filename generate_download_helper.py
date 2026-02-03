import re
import os

def generate_download_helper():
    input_file = "F_drive_recovered_list.txt"
    output_html = "Download_Helper.html"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    # Patterns for JAV codes: 
    # 1. Standard: XXX-000, XXX-000-A
    # 2. FC2: FC2-PPV-0000000
    # 3. Tokyo Hot/n-style: n0000, [n0000]
    # 4. Letters and Numbers: ID-014-9
    
    # regex for standard JAV codes: [A-Z0-9]{2,10}-[0-9]{2,10}
    # regex for nXXXX: n[0-9]{4}
    jav_regex = re.compile(r'([A-Z0-9]{2,10}-[0-9]{2,10}|n[0-9]{4})', re.IGNORECASE)

    codes_mapping = {} # code -> full line for context

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for line in lines:
        if "Path: F:" not in line:
            continue
            
        matches = jav_regex.findall(line)
        if matches:
            for code in matches:
                code_upper = code.upper()
                if code_upper not in codes_mapping:
                    codes_mapping[code_upper] = line.strip()

    html_content = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Download Helper</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #e0e0e0; padding: 20px; }
        h1 { color: #ff9800; border-bottom: 2px solid #ff9800; padding-bottom: 10px; }
        .stats { margin-bottom: 20px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; background: #2d2d2d; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #333; color: #ff9800; }
        tr:hover { background: #383838; }
        .code { font-weight: bold; color: #4fc3f7; }
        .links a { 
            display: inline-block; 
            margin-right: 10px; 
            padding: 6px 12px; 
            background: #ff9800; 
            color: white; 
            text-decoration: none; 
            border-radius: 4px; 
            font-size: 14px;
            transition: opacity 0.2s;
        }
        .links a.njav { background: #f43f5e; }
        .links a:hover { opacity: 0.8; }
        .done-checkbox { width: 20px; height: 20px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Video Download Helper (F: Drive Recovery)</h1>
    <div class="stats">Tổng cộng mã tìm thấy: """ + str(len(codes_mapping)) + """</div>
    <table>
        <thead>
            <tr>
                <th width="50">Xong</th>
                <th>Mã (Code)</th>
                <th>Thông tin gốc</th>
                <th>Tìm kiếm</th>
            </tr>
        </thead>
        <tbody>
    """

    for code, info in sorted(codes_mapping.items()):
        # Clean info line to remove the "Path: F:..." part for cleaner view
        display_info = re.sub(r'\(Path: F:.*\)', '', info).strip()
        
        missav_url = f"https://missav.live/vi/search/[{code}]"
        njav_url = f"https://njav.tv/en/search?keyword={code}"
        
        html_content += f"""
            <tr>
                <td><input type="checkbox" class="done-checkbox"></td>
                <td class="code">{code}</td>
                <td>{display_info}</td>
                <td class="links">
                    <a href="{missav_url}" target="_blank">MissAV</a>
                    <a href="{njav_url}" target="_blank" class="njav">Njav</a>
                </td>
            </tr>
        """

    html_content += """
        </tbody>
    </table>
</body>
</html>
    """

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Successfully generated {output_html} with {len(codes_mapping)} codes.")

if __name__ == "__main__":
    generate_download_helper()
