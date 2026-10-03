import json
import os
import threading
import copy

import runtime_db

_item_index_lock = threading.RLock()
_item_index = {}
_item_index_complete = False
_item_index_db_path = None
_catalog_snapshot = None
_catalog_snapshot_db_path = None
_migration_lock = threading.RLock()
_migration_checked_db_path = None


def _path_key(path):
    return os.path.normcase(os.path.normpath(str(path or "")))


def _reset_item_index(items=None, complete=False):
    global _item_index, _item_index_complete, _item_index_db_path
    global _catalog_snapshot, _catalog_snapshot_db_path
    with _item_index_lock:
        _item_index = {
            _path_key(item.get("full_path")): item
            for item in (items or [])
            if isinstance(item, dict) and item.get("full_path")
        }
        _item_index_complete = bool(complete)
        _item_index_db_path = runtime_db.DB_PATH
        _catalog_snapshot = tuple(items or ()) if complete else None
        _catalog_snapshot_db_path = runtime_db.DB_PATH if complete else None


def _cached_item(path):
    global _item_index, _item_index_complete, _item_index_db_path
    key = _path_key(path)
    with _item_index_lock:
        if _item_index_db_path != runtime_db.DB_PATH:
            _item_index = {}
            _item_index_complete = False
            _item_index_db_path = runtime_db.DB_PATH
        if key in _item_index:
            return _item_index[key]
        if _item_index_complete:
            return False
    return None


def _remember_item(item):
    global _item_index, _item_index_complete, _item_index_db_path
    if not isinstance(item, dict) or not item.get("full_path"):
        return
    with _item_index_lock:
        if _item_index_db_path != runtime_db.DB_PATH:
            _item_index = {}
            _item_index_complete = False
            _item_index_db_path = runtime_db.DB_PATH
        _item_index[_path_key(item["full_path"])] = item


def _clean_items(items):
    cleaned = []
    seen = set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        full_path = item.get("full_path")
        if not full_path:
            continue
        key = _path_key(full_path)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(dict(item))
    return cleaned


def _legacy_items(path):
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _clean_items(data if isinstance(data, list) else [])
    except Exception:
        return []


def _insert_rows(conn, items):
    now = runtime_db.utc_now()
    rows = [
        (
            _path_key(item["full_path"]),
            item["full_path"],
            index,
            json.dumps(item, ensure_ascii=False),
            now,
        )
        for index, item in enumerate(_clean_items(items))
    ]
    if rows:
        conn.executemany(
            """
            INSERT INTO media_catalog(
                path_key, full_path, position, payload, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )


def migrate_legacy_catalog(path):
    global _migration_checked_db_path
    runtime_db.ensure_schema()

    with _migration_lock:
        if _migration_checked_db_path == runtime_db.DB_PATH:
            return 0

        with runtime_db.db_session() as conn:
            conn.execute("BEGIN IMMEDIATE")
            marker = conn.execute(
                "SELECT value FROM runtime_meta WHERE key = 'media_catalog_migrated'"
            ).fetchone()
            if marker:
                _migration_checked_db_path = runtime_db.DB_PATH
                return 0

            count = conn.execute(
                "SELECT COUNT(*) FROM media_catalog"
            ).fetchone()[0]
            items = []
            if not count and path and os.path.exists(path):
                items = _legacy_items(path)
                _insert_rows(conn, items)

            conn.execute(
                """
                INSERT INTO runtime_meta(key, value, updated_at)
                VALUES ('media_catalog_migrated', '1', ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (runtime_db.utc_now(),),
            )

        _migration_checked_db_path = runtime_db.DB_PATH
        return len(items)


def load_catalog(legacy_json_path=None):
    runtime_db.ensure_schema()
    if legacy_json_path:
        migrate_legacy_catalog(legacy_json_path)

    with runtime_db.db_session() as conn:
        rows = conn.execute(
            """
            SELECT payload
            FROM media_catalog
            ORDER BY position, rowid
            """
        ).fetchall()

    items = []
    for row in rows:
        try:
            item = json.loads(row["payload"])
        except Exception:
            continue
        if isinstance(item, dict) and item.get("full_path"):
            items.append(item)
    _reset_item_index(items, complete=True)
    return items



def load_catalog_snapshot(legacy_json_path=None):
    """Return a RAM-backed catalog copy for read-only request paths."""
    global _catalog_snapshot, _catalog_snapshot_db_path
    runtime_db.ensure_schema()
    if legacy_json_path:
        migrate_legacy_catalog(legacy_json_path)

    with _item_index_lock:
        if (
            _catalog_snapshot is not None
            and _catalog_snapshot_db_path == runtime_db.DB_PATH
        ):
            return copy.deepcopy(list(_catalog_snapshot))

    # First read warms both the path index and ordered snapshot.
    return load_catalog(legacy_json_path)


def save_catalog(items, *, legacy_json_path=None, preserve_views=False):
    runtime_db.ensure_schema()
    if legacy_json_path:
        migrate_legacy_catalog(legacy_json_path)

    cleaned = _clean_items(items)
    with runtime_db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")

        if preserve_views:
            current_rows = conn.execute(
                "SELECT path_key, payload FROM media_catalog"
            ).fetchall()
            latest_views = {}
            for row in current_rows:
                try:
                    current = json.loads(row["payload"])
                except Exception:
                    continue
                latest_views[row["path_key"]] = current.get("views", 0)

            for item in cleaned:
                key = _path_key(item["full_path"])
                if key in latest_views:
                    item["views"] = latest_views[key]

        conn.execute("DELETE FROM media_catalog")
        _insert_rows(conn, cleaned)
    _reset_item_index(cleaned, complete=True)
    return cleaned


def mutate_catalog(mutator, legacy_json_path=None):
    runtime_db.ensure_schema()
    if legacy_json_path:
        migrate_legacy_catalog(legacy_json_path)

    with runtime_db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            """
            SELECT payload
            FROM media_catalog
            ORDER BY position, rowid
            """
        ).fetchall()

        items = []
        for row in rows:
            try:
                item = json.loads(row["payload"])
            except Exception:
                continue
            if isinstance(item, dict) and item.get("full_path"):
                items.append(item)

        updated = mutator(items)
        if not isinstance(updated, list):
            raise ValueError("catalog mutator must return a list")

        updated = _clean_items(updated)
        conn.execute("DELETE FROM media_catalog")
        _insert_rows(conn, updated)
    _reset_item_index(updated, complete=True)
    return updated


def increment_views(path, legacy_json_path=None):
    runtime_db.ensure_schema()
    if legacy_json_path:
        migrate_legacy_catalog(legacy_json_path)

    key = _path_key(path)
    with runtime_db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT payload FROM media_catalog WHERE path_key = ?",
            (key,),
        ).fetchone()
        if not row:
            return False

        item = json.loads(row["payload"])
        item["views"] = int(item.get("views", 0) or 0) + 1
        conn.execute(
            """
            UPDATE media_catalog
            SET payload = ?, updated_at = ?
            WHERE path_key = ?
            """,
            (
                json.dumps(item, ensure_ascii=False),
                runtime_db.utc_now(),
                key,
            ),
        )
    _remember_item(item)
    with _item_index_lock:
        if _catalog_snapshot is not None and _catalog_snapshot_db_path == runtime_db.DB_PATH:
            for index, cached_item in enumerate(_catalog_snapshot):
                if _path_key(cached_item.get("full_path")) == key:
                    updated = list(_catalog_snapshot)
                    updated[index] = item
                    _catalog_snapshot = tuple(updated)
                    break
    return True


def get_item(path, legacy_json_path=None):
    runtime_db.ensure_schema()
    if legacy_json_path:
        migrate_legacy_catalog(legacy_json_path)

    cached = _cached_item(path)
    if cached is False:
        return None
    if cached is not None:
        return cached

    with runtime_db.db_session() as conn:
        row = conn.execute(
            "SELECT payload FROM media_catalog WHERE path_key = ?",
            (_path_key(path),),
        ).fetchone()
    if not row:
        return None
    try:
        item = json.loads(row["payload"])
    except Exception:
        return None
    if isinstance(item, dict):
        _remember_item(item)
        return item
    return None


def clear_catalog(legacy_json_path=None):
    runtime_db.ensure_schema()
    with runtime_db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM media_catalog")
    _reset_item_index([], complete=True)
    if legacy_json_path and os.path.exists(legacy_json_path):
        os.remove(legacy_json_path)
