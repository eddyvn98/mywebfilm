"""
app.py - Flask Web Dashboard for Video Auto-Sort.
Run: python app.py
Open: http://localhost:5000
"""
import sys, os, threading, json
if sys.stdout.encoding != "utf-8":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

from flask import Flask, render_template, jsonify, request
from sort_engine import SortEngine

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'

# Global sort state shared between threads
_sort_state = {"status": "idle", "total": 0, "done": 0, "current_file": "",
               "moved": [], "pending_review": [], "errors": []}
_sort_lock = threading.Lock()
_sort_thread = None


def _on_progress(state):
    global _sort_state
    with _sort_lock:
        _sort_state = dict(state)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    with _sort_lock:
        s = dict(_sort_state)
    pct = 0
    if s.get("total", 0) > 0:
        pct = round(s["done"] / s["total"] * 100)
    s["pct"] = pct
    return jsonify(s)


@app.route("/api/sort", methods=["POST"])
def api_sort():
    global _sort_thread, _sort_state
    with _sort_lock:
        if _sort_state.get("status") in ("scanning", "sorting"):
            return jsonify({"error": "Sort already running"}), 409
        _sort_state = {"status": "starting", "total": 0, "done": 0,
                       "current_file": "", "moved": [], "pending_review": [], "errors": []}

    dry_run = request.json.get("dry_run", False) if request.json else False

    def run_sort():
        engine = SortEngine(on_progress=_on_progress, dry_run=dry_run)
        engine.run()

    _sort_thread = threading.Thread(target=run_sort, daemon=True)
    _sort_thread.start()
    return jsonify({"ok": True, "dry_run": dry_run})


@app.route("/api/library")
def api_library():
    engine = SortEngine()
    data = engine.get_library()
    return jsonify(data)


@app.route("/api/retry", methods=["POST"])
def api_retry():
    code = (request.json or {}).get("code", "")
    if not code:
        return jsonify({"error": "No code provided"}), 400
    engine = SortEngine()
    actresses = engine.retry_lookup(code)
    return jsonify({"code": code, "actresses": actresses})


@app.route("/api/incoming_count")
def api_incoming_count():
    """Return count of unsorted videos waiting in Incoming folders."""
    from sort_engine import INCOMING_DIRS, VIDEO_EXTS
    count = 0
    for d in INCOMING_DIRS:
        if not os.path.isdir(d): continue
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x not in {"$RECYCLE.BIN","System Volume Information"}]
            for fn in files:
                if os.path.splitext(fn)[1].lower() in VIDEO_EXTS:
                    count += 1
    return jsonify({"count": count, "incoming_dirs": INCOMING_DIRS})


if __name__ == "__main__":
    print("Starting LOCAL-ONLY Video Sort Dashboard at http://localhost:5500")
    app.run(debug=False, host="127.0.0.1", port=5500, threaded=True)
