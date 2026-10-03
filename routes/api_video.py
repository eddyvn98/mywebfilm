from flask import Blueprint, jsonify, request, send_file
import mimetypes
import os
import subprocess

import config_manager as cfg
import ffmpeg_service as ff
from constants import MPC_PATH
from utils import (
    check_path_safe,
    ensure_metadata_dirs,
    get_metadata_paths,
)

video_bp = Blueprint("api_video", __name__)

EXT_MAP = {
    ".mkv": "video/x-matroska",
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
    ".webm": "video/webm",
    ".ts": "video/mp2t",
    ".m2ts": "video/mp2t",
}


def _catalog_item(path):
    if not path or not check_path_safe(path):
        return None
    return cfg.get_catalog_item(path)


def _compact_catalog_item(item):
    result = {
        key: item.get(key)
        for key in (
            "name",
            "ext",
            "type",
            "full_path",
            "folder",
            "size",
            "size_fmt",
            "mtime",
            "date_added",
            "views",
            "categories",
            "duration",
            "is_offline",
        )
    }
    meta = item.get("jav_metadata")
    if isinstance(meta, dict):
        result["jav_metadata"] = {
            key: meta.get(key)
            for key in (
                "title",
                "code",
                "studio",
                "actors",
                "genres",
            )
            if meta.get(key) not in (None, "", [], {})
        }
    else:
        result["jav_metadata"] = None
    return result


@video_bp.route("/api/videos")
def get_videos():
    items = cfg.load_cache_snapshot()
    compact = request.args.get("compact", "").lower() in {
        "1", "true", "yes", "on"
    }
    if compact:
        items = [_compact_catalog_item(item) for item in items]
    return jsonify(items)


@video_bp.route("/api/thumbnail")
def get_thumb():
    path = request.args.get("path")
    if not path:
        return "Path missing", 400

    item = _catalog_item(path)
    if not item:
        return "Access denied", 403
    if not os.path.isfile(path):
        return "File not found", 404

    paths = get_metadata_paths(path)
    out = paths["thumb_path"]

    if not os.path.exists(out):
        ensure_metadata_dirs(paths)
        if not ff.generate_thumbnail(
            path,
            out,
            is_image=(item.get("type") == "image"),
        ):
            return "FFmpeg error", 500

    if os.path.exists(out):
        return send_file(out)
    return "Failed", 500


@video_bp.route("/api/preview")
def get_prev():
    path = request.args.get("path")
    if not path:
        return "Path missing", 400

    if not _catalog_item(path):
        return "Access denied", 403
    if not os.path.isfile(path):
        return "File not found", 404

    paths = get_metadata_paths(path)
    out = paths["prev_path"]

    if not os.path.exists(out):
        ensure_metadata_dirs(paths)
        if not ff.generate_preview(path, out):
            return "FFmpeg error", 500

    if os.path.exists(out):
        return send_file(out)
    return "Failed", 500


@video_bp.route("/api/play", methods=["POST"])
def play():
    data = request.get_json(silent=True) or {}
    path = data.get("path")
    media_type = data.get("type", "video")

    if not path:
        return jsonify({
            "status": "err",
            "msg": "File not found",
        }), 404

    item = _catalog_item(path)
    if not item:
        return jsonify({
            "status": "err",
            "msg": "Access denied",
        }), 403
    if not os.path.isfile(path):
        return jsonify({
            "status": "err",
            "msg": "File not found",
        }), 404

    cfg.increment_views(path)

    if media_type == "image":
        os.startfile(path)
    elif os.path.exists(MPC_PATH):
        subprocess.Popen([MPC_PATH, path])
    else:
        os.startfile(path)

    return jsonify({"status": "ok"})


@video_bp.route("/api/stream")
def stream_video():
    path = request.args.get("path")
    if not path:
        return "File not found", 404

    if not _catalog_item(path):
        return "Access denied", 403
    if not os.path.isfile(path):
        return "File not found", 404

    ext = os.path.splitext(path)[1].lower()
    mime = (
        EXT_MAP.get(ext)
        or mimetypes.guess_type(path)[0]
        or "application/octet-stream"
    )

    return send_file(
        path,
        mimetype=mime,
        conditional=True,
        as_attachment=False,
    )
