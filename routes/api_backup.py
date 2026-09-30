from flask import Blueprint, jsonify, request

import backup_service

backup_bp = Blueprint("api_backup", __name__)


@backup_bp.route("/api/backup", methods=["GET"])
def list_backup_sets():
    return jsonify({
        "status": "ok",
        "backups": backup_service.list_backups(),
    })


@backup_bp.route("/api/backup/create", methods=["POST"])
def create_backup():
    data = request.get_json(silent=True) or {}
    keep = data.get("keep")
    try:
        manifest = backup_service.create_backup(keep=keep)
    except Exception as exc:
        return jsonify({"status": "err", "msg": str(exc)}), 500

    return jsonify({
        "status": "ok",
        "backup": {
            "backup_id": manifest["backup_id"],
            "created_at": manifest["created_at"],
            "file_count": len(manifest["files"]),
        },
    })


@backup_bp.route("/api/backup/verify", methods=["POST"])
def verify_backup():
    data = request.get_json(silent=True) or {}
    backup_id = data.get("backup_id")
    try:
        manifest = backup_service.verify_backup(backup_id)
    except FileNotFoundError as exc:
        return jsonify({"status": "err", "msg": str(exc)}), 404
    except Exception as exc:
        return jsonify({"status": "err", "msg": str(exc)}), 400

    return jsonify({
        "status": "ok",
        "backup": {
            "backup_id": manifest["backup_id"],
            "created_at": manifest["created_at"],
            "file_count": len(manifest["files"]),
        },
    })


@backup_bp.route("/api/backup/restore", methods=["POST"])
def restore_backup():
    data = request.get_json(silent=True) or {}
    backup_id = data.get("backup_id")
    if data.get("confirm") != "RESTORE":
        return jsonify({
            "status": "err",
            "msg": "Explicit RESTORE confirmation required",
        }), 400

    try:
        result = backup_service.restore_backup(backup_id)
    except FileNotFoundError as exc:
        return jsonify({"status": "err", "msg": str(exc)}), 404
    except Exception as exc:
        return jsonify({"status": "err", "msg": str(exc)}), 500

    return jsonify({
        "status": "ok",
        **result,
    })
