import json
import threading

import config_manager as cfg
import media_catalog
import runtime_db


def use_temp_db(tmp_path, monkeypatch):
    db = tmp_path / "cinema_state.db"
    monkeypatch.setattr(runtime_db, "DB_PATH", str(db))
    monkeypatch.setattr(runtime_db, "_schema_path", None)
    return db


def test_media_catalog_migrates_legacy_json_once(tmp_path, monkeypatch):
    use_temp_db(tmp_path, monkeypatch)
    legacy = tmp_path / "movies_cache.json"
    legacy.write_text(json.dumps([
        {"full_path": "a.mp4", "views": 1},
        {"full_path": "b.mp4", "views": 2},
    ]), encoding="utf-8")

    first = media_catalog.load_catalog(str(legacy))
    legacy.write_text(json.dumps([{"full_path": "changed.mp4"}]), encoding="utf-8")
    second = media_catalog.load_catalog(str(legacy))

    assert [item["full_path"] for item in first] == ["a.mp4", "b.mp4"]
    assert second == first


def test_scan_replace_preserves_latest_view_count(tmp_path, monkeypatch):
    use_temp_db(tmp_path, monkeypatch)
    legacy = tmp_path / "movies_cache.json"
    monkeypatch.setattr(cfg, "CACHE_FILE", str(legacy))

    cfg.save_cache([{"full_path": "movie.mp4", "views": 10, "name": "old"}])
    assert cfg.increment_views("movie.mp4") is True

    cfg.save_scanned_cache([
        {"full_path": "movie.mp4", "views": 10, "name": "fresh scan"}
    ])

    item = cfg.load_cache()[0]
    assert item["views"] == 11
    assert item["name"] == "fresh scan"


def test_clear_catalog_does_not_reimport_legacy_cache(tmp_path, monkeypatch):
    use_temp_db(tmp_path, monkeypatch)
    legacy = tmp_path / "movies_cache.json"
    legacy.write_text(json.dumps([{"full_path": "old.mp4"}]), encoding="utf-8")
    monkeypatch.setattr(cfg, "CACHE_FILE", str(legacy))

    assert cfg.load_cache()
    cfg.clear_cache_data()

    assert cfg.load_cache() == []
    assert not legacy.exists()
