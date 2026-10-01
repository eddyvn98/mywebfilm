import subprocess
import os
import requests

def start_tunnel():
    print("-" * 40)
    print("CLOUD CINEMA - REMOTE ACCESS SETUP")
    print("-" * 40)
    
    # Check for local binary first, then system-wide
    cf_cmd = "cloudflared"
    if os.path.exists("cloudflared.exe"):
        cf_cmd = os.path.abspath("cloudflared.exe")
    
    # Check if cloudflared is installed or present locally
    try:
        subprocess.run([cf_cmd, "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("XIN LỖI: Bạn chưa cài đặt 'cloudflared'.")
        print("Vui lòng tải tại: https://github.com/cloudflare/cloudflared/releases")
        print("Hoặc đợi tôi tải giúp bạn vào thư mục dự án...")
        return

    print("Đang khởi tạo Tunnel miễn phí...")
    print("Lưu ý: Link này sẽ thay đổi mỗi khi bạn chạy lại script.")
    print("-" * 40)
    
    try:
        tunnel_args = [cf_cmd, "tunnel", "--protocol", "http2", "--url", "http://localhost:5000"]
        allowed_mail = os.environ.get("CINEMA_ALLOWED_EMAIL", "").strip()
        if allowed_mail:
            tunnel_args.extend(["--allowed-mail", allowed_mail])

        process = subprocess.Popen(
            tunnel_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        tunnel_url = None
        for line in process.stdout:
            print(line, end="")
            if "trycloudflare.com" in line:
                parts = line.split()
                for p in parts:
                    if "https://" in p and "trycloudflare.com" in p:
                        tunnel_url = p
                        print(f"\n🚀 LINK TRUY CẬP TỪ XA CỦA BẠN: {tunnel_url}\n")
                        print("Đang đồng bộ Public URL vào Cinema...")
                        try:
                            response = requests.post(
                                "http://localhost:5000/api/auth/tunnel/sync",
                                json={"url": tunnel_url},
                                timeout=2,
                            )
                            response.raise_for_status()
                            print("✅ Đã đồng bộ thành công!")
                        except Exception as exc:
                            print(f"❌ Không thể đồng bộ với Cinema: {exc}")
                        break
    except KeyboardInterrupt:
        print("\nĐã dừng Tunnel.")

if __name__ == "__main__":
    start_tunnel()
