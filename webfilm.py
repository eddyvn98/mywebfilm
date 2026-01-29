from flask import Flask
import ffmpeg_service as ff
from routes.api import api_bp
from routes.views import views_bp

import os

# Ensure we're pointing to the correct folders relative to this script
app = Flask(__name__, template_folder='templates', static_folder='static')

# Register Blueprints
app.register_blueprint(api_bp)
app.register_blueprint(views_bp)

if __name__ == '__main__':
    if not ff.check_ffmpeg_presence():
        print("CẢNH BÁO: Không tìm thấy lệnh 'ffmpeg' trong PATH hệ thống.")
    
    print("\n" + "-"*30)
    print("MY CINEMA (Mobile Optimized)")
    print("-" * 30 + "\n")
    
    # Run with threaded=True for stream support
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)