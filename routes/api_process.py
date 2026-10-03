from flask import Blueprint, jsonify, request
import os

import config_manager as cfg
from queue_worker import media_queue
from utils import check_path_safe

process_bp = Blueprint("api_process", __name__)
ALLOWED_TASK_TYPES = {"highlight", "convert"}


def _catalog_media(path):
    return bool(
        path
        and check_path_safe(path)
        and cfg.get_catalog_item(path)
        and os.path.isfile(path)
    )


@process_bp.route("/api/process/queue", methods=["POST"])
def add_to_queue():
    data = request.get_json(silent=True) or {}
    paths = data.get("paths", [])
    task_type = data.get("type", "highlight")

    if task_type not in ALLOWED_TASK_TYPES:
        return jsonify({
            "status": "err",
            "msg": "Unsupported task type",
        }), 400
    if not paths:
        return "No paths provided", 400
    if any(not _catalog_media(path) for path in paths):
        return jsonify({
            "status": "err",
            "msg": "Access denied",
        }), 403

    media_queue.add_items(
        paths,
        task_type=task_type,
    )
    return jsonify({
        "status": "ok",
        "msg": f"Added {len(paths)} items to queue",
    })


@process_bp.route("/api/process/status", methods=["GET"])
def get_queue_status():
    return jsonify(media_queue.get_status())


@process_bp.route("/api/process/clear", methods=["POST"])
def clear_completed():
    media_queue.clear_completed()
    return jsonify({"status": "ok"})


@process_bp.route("/api/process/highlight", methods=["POST"])
def process_manual_highlight():
    data = request.get_json(silent=True) or {}
    path = data.get("path")
    if not path:
        return jsonify({
            "status": "err",
            "msg": "File not found",
        }), 404
    if not _catalog_media(path):
        return jsonify({
            "status": "err",
            "msg": "Access denied",
        }), 403

    media_queue.add_items([path], task_type="highlight")
    return jsonify({
        "status": "ok",
        "queued": True,
        "msg": "Highlight added to queue",
    }), 202
