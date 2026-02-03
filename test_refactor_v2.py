import sys
import os

# Ensure the script can find the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("--- Testing FFmpeg Service V2 ---")
try:
    import ffmpeg_service_v2 as ff_v2
    functions = [
        'check_ffmpeg_presence', 
        'generate_thumbnail', 
        'generate_preview', 
        'process_highlight_video', 
        'convert_ts_to_mp4', 
        'get_best_gpu_encoder'
    ]
    for func in functions:
        if hasattr(ff_v2, func):
            print(f"[OK] Found function: {func}")
        else:
            print(f"[FAIL] Missing function: {func}")
except Exception as e:
    print(f"[ERROR] Failed to import ffmpeg_service_v2: {e}")

print("\n--- Testing API Route Modularization ---")
try:
    from flask import Flask
    from routes.api_v2 import ai_bp, video_bp, process_bp, fs_bp, config_bp
    
    app = Flask(__name__)
    app.register_blueprint(ai_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(process_bp)
    app.register_blueprint(fs_bp)
    app.register_blueprint(config_bp)
    
    print("[OK] Successfully registered all 5 sub-blueprints individually.")
    
    # Check if routes exist
    rules = [str(rule) for rule in app.url_map.iter_rules()]
    sample_routes = ['/api/tags', '/api/videos', '/api/scan', '/api/ai/analyze', '/api/process/status', '/api/delete_file']
    for route in sample_routes:
        if any(route in r for r in rules):
            print(f"[OK] Route found: {route}")
        else:
            print(f"[FAIL] Route missing: {route}")
            
except Exception as e:
    print(f"[ERROR] Failed to verify API blueprints: {e}")

print("\nVerification Complete.")
