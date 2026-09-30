from flask import Blueprint, jsonify, request
import logging
import ntpath
import os
import shutil
import subprocess

import config_manager as cfg
from operation_journal import begin_operation, update_operation
from utils import check_path_safe, get_metadata_paths, sync_artifacts

fs_bp = Blueprint("api_fs", __name__)
logger = logging.getLogger(__name__)


def _basename(path):
    return ntpath.basename(path) if "\\" in path else os.path.basename(path)


def _dirname(path):
    return ntpath.dirname(path) if "\\" in path else os.path.dirname(path)


def _join(parent, name):
    return ntpath.join(parent, name) if "\\" in parent else os.path.join(parent, name)


def _operation_failure(op_id, exc, *, filesystem_changed=False):
    detail = str(exc)
    update_operation(op_id, "failed", detail)
    logger.exception("filesystem_operation_failed operation_id=%s", op_id)
    return jsonify({
        "status": "err",
        "msg": detail,
        "operation_id": op_id,
        "filesystem_changed": filesystem_changed,
    }), 500


@fs_bp.route("/api/delete_file", methods=["POST"])
def delete_file():
    data = request.get_json(silent=True) or {}
    path = data.get("path")
    if not path:
        return jsonify({"status": "err", "msg": "File not found"}), 404
    if not check_path_safe(path):
        return jsonify({"status": "err", "msg": "Access denied"}), 403
    if not os.path.exists(path):
        return jsonify({"status": "err", "msg": "File not found"}), 404

    op_id = begin_operation("delete", src_path=path)
    deleted = False
    try:
        os.remove(path)
        deleted = True
        update_operation(op_id, "filesystem_done")
        logger.info("file_delete operation_id=%s path=%r", op_id, path)

        metadata = get_metadata_paths(path)
        for key in ("thumb_path", "prev_path"):
            artifact = metadata[key]
            if os.path.exists(artifact):
                os.remove(artifact)

        cfg.mutate_cache(
            lambda items: [
                item for item in items
                if item.get("full_path") != path
            ]
        )
        update_operation(op_id, "completed")
        return jsonify({"status": "ok", "operation_id": op_id})
    except Exception as exc:
        return _operation_failure(op_id, exc, filesystem_changed=deleted)


@fs_bp.route("/api/explorer", methods=["POST"])
def open_explorer():
    data = request.get_json(silent=True) or {}
    path = data.get("path")
    if not path:
        return jsonify({"status": "err", "msg": "File not found"}), 404
    if not check_path_safe(path):
        return jsonify({"status": "err", "msg": "Access denied"}), 403
    if not os.path.exists(path):
        return jsonify({"status": "err", "msg": "File not found"}), 404
    try:
        subprocess.run(["explorer", "/select,", os.path.normpath(path)], check=False)
        return jsonify({"status": "ok"})
    except Exception as exc:
        return jsonify({"status": "err", "msg": str(exc)}), 500


@fs_bp.route("/api/fs/rename", methods=["POST"])
def fs_rename():
    data = request.get_json(silent=True) or {}
    old_path = data.get("old_path")
    new_name = data.get("new_name")
    if not old_path or not new_name:
        return "Params missing", 400

    new_name = _basename(new_name)
    if not new_name or new_name in {".", ".."}:
        return jsonify({"status": "err", "msg": "Invalid name"}), 400
    if not check_path_safe(old_path):
        return jsonify({"status": "err", "msg": "Access denied"}), 403
    if not os.path.exists(old_path):
        return jsonify({"status": "err", "msg": "File not found"}), 404

    new_path = _join(_dirname(old_path), new_name)
    if not check_path_safe(new_path):
        return jsonify({"status": "err", "msg": "Access denied"}), 403
    if os.path.exists(new_path):
        return jsonify({"status": "err", "msg": "Tên này đã tồn tại"}), 400

    op_id = begin_operation("rename", old_path, new_path)
    renamed = False
    warnings = []
    try:
        os.rename(old_path, new_path)
        renamed = True
        update_operation(op_id, "filesystem_done")
        logger.info(
            "file_rename operation_id=%s old=%r new=%r",
            op_id, old_path, new_path,
        )

        config = cfg.load_config()
        if old_path in config.get("video_dirs", []):
            config["video_dirs"] = [
                new_path if item == old_path else item
                for item in config["video_dirs"]
            ]
            cfg.save_config(config)

        snapshot = cfg.load_cache()
        old_folder = _basename(old_path)
        for item in snapshot:
            full_path = item.get("full_path", "")
            if full_path == old_path:
                try:
                    sync_artifacts(old_path, new_path)
                except Exception as exc:
                    warnings.append(f"artifact sync: {exc}")
            elif full_path.startswith(old_path + os.sep) or full_path.startswith(old_path + "\\"):
                new_full_path = full_path.replace(old_path, new_path, 1)
                try:
                    sync_artifacts(full_path, new_full_path)
                except Exception as exc:
                    warnings.append(f"artifact sync {full_path}: {exc}")

        def update_catalog(items):
            for item in items:
                full_path = item.get("full_path", "")
                if full_path == old_path:
                    item["full_path"] = new_path
                    item["name"] = new_name
                elif full_path.startswith(old_path + os.sep) or full_path.startswith(old_path + "\\"):
                    item["full_path"] = full_path.replace(old_path, new_path, 1)
                    if item.get("folder") == old_folder:
                        item["folder"] = new_name
            return items

        cfg.mutate_cache(update_catalog)
        if warnings:
            detail = "; ".join(warnings[:5])
            update_operation(op_id, "failed", detail)
            return jsonify({
                "status": "partial",
                "new_path": new_path,
                "operation_id": op_id,
                "warnings": warnings,
            }), 207

        update_operation(op_id, "completed")
        return jsonify({
            "status": "ok",
            "new_path": new_path,
            "operation_id": op_id,
        })
    except Exception as exc:
        return _operation_failure(op_id, exc, filesystem_changed=renamed)


@fs_bp.route("/api/fs/mkdir", methods=["POST"])
def fs_mkdir():
    data = request.get_json(silent=True) or {}
    parent = data.get("parent_path")
    name = data.get("name")
    if not parent or not name:
        return "Params missing", 400

    name = _basename(name)
    if not name or name in {".", ".."}:
        return jsonify({"status": "err", "msg": "Invalid folder name"}), 400
    if not check_path_safe(parent):
        return jsonify({"status": "err", "msg": "Access denied"}), 403

    try:
        new_path = _join(parent, name)
        if not check_path_safe(new_path):
            return jsonify({"status": "err", "msg": "Access denied"}), 403
        os.makedirs(new_path, exist_ok=True)
        return jsonify({"status": "ok", "path": new_path})
    except Exception as exc:
        return jsonify({"status": "err", "msg": str(exc)}), 500


@fs_bp.route("/api/fs/move", methods=["POST"])
def fs_move():
    data = request.get_json(silent=True) or {}
    paths = data.get("paths", [])
    target_dir = data.get("target_dir")
    if not paths or not target_dir:
        return "Params missing", 400
    if not check_path_safe(target_dir):
        return jsonify({"status": "err", "msg": "Access denied to target directory"}), 403

    results = []
    operations = []
    moved_paths = []

    for path in paths:
        if not check_path_safe(path):
            results.append({"path": path, "status": "access_denied"})
            continue
        if not os.path.exists(path):
            results.append({"path": path, "status": "missing"})
            continue

        new_path = _join(target_dir, _basename(path))
        if not check_path_safe(new_path):
            results.append({"path": path, "status": "access_denied"})
            continue
        if os.path.exists(new_path):
            results.append({"path": path, "status": "exists"})
            continue

        op_id = begin_operation("move", path, new_path)
        warnings = []
        try:
            shutil.move(path, new_path)
            update_operation(op_id, "filesystem_done")
            logger.info(
                "file_move operation_id=%s old=%r new=%r",
                op_id, path, new_path,
            )

            try:
                sync_artifacts(path, new_path)
            except Exception as exc:
                warnings.append(f"artifact sync: {exc}")

            moved_paths.append((path, new_path))
            operations.append((op_id, warnings))
            results.append({
                "path": path,
                "status": "partial" if warnings else "ok",
                "new_path": new_path,
                "operation_id": op_id,
                "warnings": warnings,
            })
        except Exception as exc:
            update_operation(op_id, "failed", str(exc))
            logger.exception("file_move_failed operation_id=%s path=%r", op_id, path)
            results.append({
                "path": path,
                "status": "error",
                "operation_id": op_id,
                "msg": str(exc),
            })

    try:
        if moved_paths:
            def update_catalog(items):
                for item in items:
                    full_path = item.get("full_path", "")
                    for old_path, new_path in moved_paths:
                        if full_path == old_path:
                            item["full_path"] = new_path
                            item["folder"] = _basename(target_dir)
                            full_path = new_path
                            break
                        if full_path.startswith(old_path + os.sep) or full_path.startswith(old_path + "\\"):
                            item["full_path"] = full_path.replace(old_path, new_path, 1)
                            break
                return items

            cfg.mutate_cache(update_catalog)
    except Exception as exc:
        detail = f"filesystem changed but catalog update failed: {exc}"
        for op_id, _ in operations:
            update_operation(op_id, "failed", detail)
        return jsonify({
            "status": "err",
            "msg": detail,
            "results": results,
            "filesystem_changed": True,
        }), 500

    has_partial = False
    for op_id, warnings in operations:
        if warnings:
            update_operation(op_id, "failed", "; ".join(warnings[:5]))
            has_partial = True
        else:
            update_operation(op_id, "completed")

    return jsonify({
        "status": "partial" if has_partial else "ok",
        "results": results,
    }), 207 if has_partial else 200
