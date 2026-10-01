"""
routes/api_sort.py - Auto-sort Incoming folders route.

Integrates sort_engine.SortEngine into the Cinema Manager web app.
Two endpoints:
  POST /api/sort/run    -> Start sort or rebalance in background
  GET  /api/sort/status -> Poll current sort progress
  POST /api/sort/retry  -> Force retry actress lookup for a specific code
"""

import threading
import sys
import os
from flask import Blueprint, jsonify, request

# Add project root to path so sort_engine is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sort_engine import SortEngine

sort_bp = Blueprint("api_sort", __name__)

# ── Shared state (thread-safe via lock) ────────────────────────────────────────
_lock   = threading.Lock()
_state  = {
    "status":        "idle",   # idle | scanning | sorting | done
    "total":         0,
    "done":          0,
    "current_file":  "",
    "moved":         [],
    "pending_review":[],
    "errors":        [],
    "pct":           0,
}
_thread = None


def _on_progress(s):
    with _lock:
        _state.update(s)
        if s.get("total", 0) > 0:
            _state["pct"] = round(s["done"] / s["total"] * 100)


def _run_sort(mode, dry_run):
    engine = SortEngine(on_progress=_on_progress, dry_run=dry_run)
    if mode == "rebalance":
        engine.rebalance()
    else:
        engine.run()


# ── Routes ────────────────────────────────────────────────────────────────────

@sort_bp.route("/api/sort/run", methods=["POST"])
def sort_run():
    """
    Start auto-sort of Incoming folders.
    Body: {"dry_run": false}  (optional, default false)
    Returns immediately; poll /api/sort/status for progress.
    """
    global _thread
    with _lock:
        current = _state.get("status")

    if current in ("scanning", "sorting"):
        return jsonify({"ok": False, "msg": "Sort already running", "status": current}), 409

    dry_run = False
    mode = "incoming"
    if request.json:
        dry_run = request.json.get("dry_run", False)
        mode = request.json.get("mode", "incoming")

    if not dry_run:
        from .api_auth import is_direct_local_request
        if not is_direct_local_request():
            return jsonify({
                "ok": False,
                "msg": "Bulk file sorting chỉ được chạy từ direct localhost"
            }), 403

    # Reset state
    with _lock:
        _state.update({
            "status": "starting", "total": 0, "done": 0,
            "current_file": "", "moved": [], "pending_review": [], "errors": [], "pct": 0,
        })

    _thread = threading.Thread(target=_run_sort, args=(mode, dry_run), daemon=True)
    _thread.start()
    return jsonify({"ok": True, "dry_run": dry_run})


@sort_bp.route("/api/sort/status", methods=["GET"])
def sort_status():
    """Return current sort progress as JSON."""
    with _lock:
        s = dict(_state)
    return jsonify(s)


@sort_bp.route("/api/sort/incoming_count", methods=["GET"])
def sort_incoming_count():
    """Count unsorted videos waiting in Incoming staging folders."""
    from sort_engine import INCOMING_DIRS, VIDEO_EXTS
    count = 0
    dirs_found = []
    for d in INCOMING_DIRS:
        if not os.path.isdir(d):
            continue
        dirs_found.append(d)
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x not in {"$RECYCLE.BIN", "System Volume Information"}]
            for fn in files:
                if os.path.splitext(fn)[1].lower() in VIDEO_EXTS:
                    count += 1
    return jsonify({"count": count, "dirs": dirs_found})


@sort_bp.route("/api/sort/retry", methods=["POST"])
def sort_retry():
    """Force re-fetch actress for a specific JAV code."""
    code = (request.json or {}).get("code", "").strip().upper()
    if not code:
        return jsonify({"ok": False, "msg": "code required"}), 400
    engine = SortEngine()
    actresses = engine.retry_lookup(code)
    return jsonify({"ok": True, "code": code, "actresses": actresses})
