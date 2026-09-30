import json
import os

import runtime_db


def _path_key(path):
    return os.path.normcase(os.path.normpath(str(path or "")))


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
    runtime_db.ensure_schema()
    if not path or not os.path.exists(path):
        return 0

    with runtime_db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        count = conn.execute(
            "SELECT COUNT(*) FROM media_catalog"
        ).fetchone()[0]
        if count:
            return 0

        items = _legacy_items(path)
        _insert_rows(conn, items)
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
    return items


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
        return True


def get_item(path, legacy_json_path=None):
    runtime_db.ensure_schema()
    if legacy_json_path:
        migrate_legacy_catalog(legacy_json_path)

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
    return item if isinstance(item, dict) else None
