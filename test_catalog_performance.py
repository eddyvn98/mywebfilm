import os
from unittest.mock import patch

import config_manager as cfg
import media_catalog
import runtime_db
import scanner_service


def test_catalog_snapshot_updates_views_without_db_reload_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_db, "DB_PATH", str(tmp_path / "cinema_state.db"))
    monkeypatch.setattr(runtime_db, "_schema_path", None)
    monkeypatch.setattr(cfg, "CACHE_FILE", str(tmp_path / "movies_cache.json"))

    source = str(tmp_path / "movie.mp4")
    cfg.save_cache([{
        "full_path": source,
        "name": "movie",
        "views": 2,
        "type": "video",
    }])

    first = cfg.load_cache_snapshot()
    assert first[0]["name"] == "movie"

    assert cfg.increment_views(source) is True
    second = cfg.load_cache_snapshot()
    assert second[0]["views"] == 3


def test_incremental_scan_reuses_unchanged_video_metadata(tmp_path, monkeypatch):
    media_root = tmp_path / "media"
    media_root.mkdir()
    source = media_root / "movie.mp4"
    source.write_bytes(b"unchanged-video")
    stat = source.stat()

    cached = {
        "full_path": str(source),
        "name": "Cached title",
        "folder": media_root.name,
        "views": 7,
        "date_added": stat.st_mtime - 100,
        "jav_metadata": {"title": "Cached title"},
        "nfo_metadata": None,
        "categories": ["cached"],
        "duration": 321.5,
        "size": stat.st_size,
        "size_fmt": scanner_service.format_size(stat.st_size),
        "mtime": stat.st_mtime,
        "nfo_mtime": None,
        "type": "video",
        "ext": "MP4",
        "is_offline": False,
    }

    monkeypatch.setattr(scanner_service, "SORTED_ROOTS", [])
    monkeypatch.setattr(scanner_service, "load_cache", lambda: [cached])
    monkeypatch.setattr(
        scanner_service,
        "load_config",
        lambda: {"enable_jav_scraping": False},
    )

    saved = []
    monkeypatch.setattr(
        scanner_service,
        "save_scanned_cache",
        lambda items: saved.extend(items),
    )

    with patch(
        "scanner_service.ffmpeg_service.get_video_duration",
        side_effect=AssertionError("ffprobe should not run for unchanged media"),
    ):
        result = scanner_service.scan_videos([str(media_root)])

    assert len(result) == 1
    assert result[0]["duration"] == 321.5
    assert result[0]["views"] == 7
    assert result[0]["categories"] == ["cached"]
    assert saved[0]["full_path"] == str(source)


def test_nfo_change_invalidates_incremental_reuse(tmp_path):
    source = tmp_path / "movie.mp4"
    source.write_bytes(b"video")
    stat = source.stat()
    nfo = tmp_path / "movie.nfo"
    nfo.write_text("<movie></movie>", encoding="utf-8")

    old_meta = {
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "nfo_metadata": {"title": "old"},
        "nfo_mtime": os.path.getmtime(nfo) - 10,
    }

    assert scanner_service._can_reuse_cached_item(
        old_meta,
        stat,
        str(nfo),
    ) is False


def test_media_iterator_streams_only_supported_files(monkeypatch):
    def fake_walk(_root):
        yield "root", [".mycinema", "child"], ["movie.mp4", "note.txt"]
        yield "root/child", [], ["image.jpg"]

    monkeypatch.setattr(scanner_service.os, "walk", fake_walk)

    found = list(scanner_service._iter_media_files(["root"]))

    assert found == [
        ("root", "movie.mp4"),
        ("root/child", "image.jpg"),
    ]
