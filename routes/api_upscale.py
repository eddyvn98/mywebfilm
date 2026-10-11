"""Authenticated GPU-transcoded HLS stream endpoints for remote browsers."""
from flask import Blueprint, jsonify, request, send_file
from routes.api_auth import get_session_state
import os

import config_manager as cfg
import server_upscale_service as streams
from utils import check_path_safe

upscale_bp = Blueprint("api_upscale", __name__)


def _owner():
    state = get_session_state()
    return state.get("session_id") if state and not state.get("locked") else None


@upscale_bp.route("/api/upscale/capabilities")
def capabilities():
    return jsonify(streams.capabilities())


@upscale_bp.route("/api/upscale/sessions", methods=["POST"])
def start_session():
    data = request.get_json(silent=True) or {}
    path = data.get("path")
    owner = _owner()
    if not owner:
        return jsonify({"error": "Không có phiên đăng nhập"}), 401
    if not isinstance(path, str) or not check_path_safe(path):
        return jsonify({"error": "Đường dẫn không hợp lệ"}), 403
    item = cfg.get_catalog_item(path)
    if not item or item.get("type") == "image":
        return jsonify({"error": "Video không nằm trong thư viện"}), 403
    if not os.path.isfile(path):
        return jsonify({"error": "Không tìm thấy phim"}), 404
    try:
        job = streams.start(path, owner, data.get("height", 720),
                            data.get("interpolation", "lanczos"),
                            data.get("start_at", 0))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except streams.UpscaleUnavailable as exc:
        return jsonify({"error": str(exc)}), 503
    cfg.increment_views(path)
    sid = job["id"]
    return jsonify({
        "session_id": sid,
        "url": f"/api/upscale/sessions/{sid}/index.m3u8",
        "height": job["height"],
        "mode": "server-gpu",
        "method": "CUDA spatial scaling + NVENC; not neural AI",
    })


@upscale_bp.route("/api/upscale/sessions/<sid>/<filename>")
def read_segment(sid, filename):
    record = streams.get_owned(sid, _owner())
    if not record:
        return jsonify({"error": "Luồng đã hết hạn hoặc không có quyền"}), 404
    path = streams.asset(record, filename)
    if not path:
        return "Segment unavailable", 404
    mime = ("application/vnd.apple.mpegurl" if filename == "index.m3u8"
            else "video/mp2t")
    return send_file(path, mimetype=mime, conditional=False,
                     max_age=0)


@upscale_bp.route("/api/upscale/sessions/<sid>", methods=["DELETE"])
def close_session(sid):
    if not streams.stop(sid, _owner()):
        return jsonify({"error": "Không tồn tại phiên của bạn"}), 404
    return jsonify({"ok": True})
