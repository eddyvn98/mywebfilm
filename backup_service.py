import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone

import runtime_db
from constants import CONFIG_FILE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CINEMA_DATA_DIR", os.path.join(BASE_DIR, "data"))
BACKUP_DIR = os.environ.get("CINEMA_BACKUP_DIR", os.path.join(DATA_DIR, "backups"))
TAGS_FILE = os.path.join(BASE_DIR, "tags.json")
CREDENTIALS_FILE = os.path.join(DATA_DIR, "credentials.json")
MANIFEST_FILE = "manifest.json"

BACKUP_ID_RE = re.compile(r"^\d{8}T\d{6}Z_[0-9a-f]{8}$")


def _backup_path(backup_id):
    if not BACKUP_ID_RE.fullmatch(str(backup_id or "")):
        raise ValueError("Invalid backup id")
    return os.path.join(BACKUP_DIR, backup_id)


def _utc_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_path(path):
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)


def _source_files():
    return {
        "credentials.json": CREDENTIALS_FILE,
        "config.json": _project_path(CONFIG_FILE),
        "tags.json": TAGS_FILE,
    }


def _backup_database(destination):
    runtime_db.ensure_schema()
    with runtime_db.database_maintenance():
        source = sqlite3.connect(runtime_db.DB_PATH, timeout=30)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()


def _validate_sqlite(path):
    conn = sqlite3.connect(path)
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        return bool(row and row[0] == "ok")
    finally:
        conn.close()


def _manifest_for(directory, backup_id):
    files = {}
    for name in os.listdir(directory):
        if name == MANIFEST_FILE:
            continue
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            files[name] = {
                "sha256": _sha256(path),
                "size": os.path.getsize(path),
            }
    return {
        "version": 1,
        "backup_id": backup_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }


def _write_manifest(directory, manifest):
    path = os.path.join(directory, MANIFEST_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())


def _cleanup_retention(keep):
    if keep <= 0 or not os.path.isdir(BACKUP_DIR):
        return
    backups = [
        name for name in os.listdir(BACKUP_DIR)
        if not name.startswith(".") and os.path.isdir(os.path.join(BACKUP_DIR, name))
    ]
    backups.sort(reverse=True)
    for name in backups[keep:]:
        shutil.rmtree(os.path.join(BACKUP_DIR, name), ignore_errors=True)


def create_backup(keep=None):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_id = f"{_utc_stamp()}_{uuid.uuid4().hex[:8]}"
    staging = tempfile.mkdtemp(prefix=".backup-", dir=BACKUP_DIR)
    final_dir = os.path.join(BACKUP_DIR, backup_id)

    try:
        db_copy = os.path.join(staging, "cinema_state.db")
        _backup_database(db_copy)
        if not _validate_sqlite(db_copy):
            raise RuntimeError("SQLite backup integrity check failed")

        for name, source in _source_files().items():
            if os.path.isfile(source):
                shutil.copy2(source, os.path.join(staging, name))

        manifest = _manifest_for(staging, backup_id)
        _write_manifest(staging, manifest)
        os.replace(staging, final_dir)

        if keep is None:
            keep = int(os.environ.get("CINEMA_BACKUP_KEEP", "10"))
        _cleanup_retention(max(1, min(int(keep), 100)))
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _load_manifest(backup_dir):
    path = os.path.join(backup_dir, MANIFEST_FILE)
    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    if manifest.get("version") != 1 or not isinstance(manifest.get("files"), dict):
        raise ValueError("Unsupported or invalid backup manifest")
    return manifest


def verify_backup(backup_id):
    backup_dir = _backup_path(backup_id)
    if not os.path.isdir(backup_dir):
        raise FileNotFoundError("Backup not found")

    manifest = _load_manifest(backup_dir)
    if manifest.get("backup_id") != backup_id:
        raise ValueError("Backup identity mismatch")

    for name, meta in manifest["files"].items():
        path = os.path.join(backup_dir, name)
        if not os.path.isfile(path):
            raise ValueError(f"Backup file missing: {name}")
        if os.path.getsize(path) != int(meta["size"]):
            raise ValueError(f"Backup size mismatch: {name}")
        if _sha256(path) != meta["sha256"]:
            raise ValueError(f"Backup checksum mismatch: {name}")

    db_path = os.path.join(backup_dir, "cinema_state.db")
    if not os.path.isfile(db_path) or not _validate_sqlite(db_path):
        raise ValueError("Backup SQLite database failed integrity check")
    return manifest


def list_backups():
    if not os.path.isdir(BACKUP_DIR):
        return []
    result = []
    for backup_id in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if backup_id.startswith("."):
            continue
        try:
            manifest = verify_backup(backup_id)
            result.append({
                "backup_id": backup_id,
                "created_at": manifest.get("created_at"),
                "file_count": len(manifest["files"]),
                "total_size": sum(int(v["size"]) for v in manifest["files"].values()),
                "valid": True,
            })
        except Exception as exc:
            result.append({
                "backup_id": backup_id,
                "valid": False,
                "error": str(exc),
            })
    return result


def _atomic_restore_file(source, destination):
    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        prefix=".restore-",
        dir=os.path.dirname(os.path.abspath(destination)),
    )
    os.close(fd)
    try:
        shutil.copy2(source, temp_path)
        os.replace(temp_path, destination)
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def _apply_backup_dir(backup_dir):
    db_source = os.path.join(backup_dir, "cinema_state.db")
    _atomic_restore_file(db_source, runtime_db.DB_PATH)
    for suffix in ("-wal", "-shm"):
        stale = runtime_db.DB_PATH + suffix
        if os.path.exists(stale):
            os.remove(stale)

    destinations = _source_files()
    for name in ("credentials.json", "config.json", "tags.json"):
        source = os.path.join(backup_dir, name)
        if os.path.isfile(source):
            _atomic_restore_file(source, destinations[name])

    runtime_db._schema_path = None


def restore_backup(backup_id):
    manifest = verify_backup(backup_id)
    backup_dir = _backup_path(backup_id)

    with runtime_db.database_maintenance():
        emergency = create_backup(keep=None)
        emergency_dir = _backup_path(emergency["backup_id"])
        try:
            _apply_backup_dir(backup_dir)
        except Exception:
            _apply_backup_dir(emergency_dir)
            raise

    return {
        "restored_backup_id": backup_id,
        "emergency_backup_id": emergency["backup_id"],
        "restart_required": True,
        "files": sorted(manifest["files"].keys()),
    }
