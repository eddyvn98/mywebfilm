import time
from unittest.mock import patch

from flask import Response

import media_catalog
import runtime_db
import webfilm
from test_helpers import authenticate_client


def test_loaded_catalog_serves_membership_without_reopening_sqlite(tmp_path, monkeypatch):
    db_path = tmp_path / "cinema_state.db"
    monkeypatch.setattr(runtime_db, "DB_PATH", str(db_path))
    monkeypatch.setattr(runtime_db, "_schema_path", None)

    path = str(tmp_path / "movie.mp4")
    media_catalog.save_catalog([
        {
            "full_path": path,
            "name": "Movie",
            "type": "video",
            "views": 0,
        }
    ])

    with patch("media_catalog.runtime_db.db_session") as db_session:
        item = media_catalog.get_item(path)

    assert item["full_path"] == path
    db_session.assert_not_called()


def test_stream_activity_touch_is_throttled(monkeypatch):
    webfilm._stream_activity_last.clear()
    calls = []
    monkeypatch.setattr(
        webfilm.runtime_db,
        "touch_security_session",
        lambda session_id, when: calls.append((session_id, when)),
    )

    record = {"session_id": "session-1"}
    webfilm._touch_stream_activity(record)
    webfilm._touch_stream_activity(record)

    assert len(calls) == 1
    assert calls[0][0] == "session-1"


def test_thumbnail_response_can_use_private_browser_cache(monkeypatch):
    app = webfilm.app
    app.config["TESTING"] = True

    with app.test_client() as client:
        authenticate_client(client)

        monkeypatch.setattr(
            "routes.api_video._catalog_item",
            lambda _path: {"type": "video"},
        )
        monkeypatch.setattr(
            "routes.api_video.os.path.isfile",
            lambda _path: True,
        )
        monkeypatch.setattr(
            "routes.api_video.get_metadata_paths",
            lambda _path: {
                "thumb_dir": "thumbs",
                "prev_dir": "previews",
                "thumb_path": "thumb.jpg",
                "prev_path": "preview.mp4",
            },
        )
        monkeypatch.setattr(
            "routes.api_video.ensure_metadata_dirs",
            lambda _paths: None,
        )
        monkeypatch.setattr(
            "routes.api_video.os.path.exists",
            lambda _path: True,
        )
        monkeypatch.setattr(
            "routes.api_video.send_file",
            lambda _path: Response(b"thumb", mimetype="image/jpeg"),
        )

        response = client.get(
            "/api/thumbnail",
            query_string={"path": "movie.mp4"},
        )

    assert response.status_code == 200
    assert "private" in response.headers["Cache-Control"]
    assert "max-age=86400" in response.headers["Cache-Control"]
    assert "no-store" not in response.headers["Cache-Control"]


def test_repeated_legacy_migration_check_does_not_reopen_db(tmp_path, monkeypatch):
    db_path = tmp_path / "cinema_state.db"
    legacy_path = tmp_path / "legacy.json"
    monkeypatch.setattr(runtime_db, "DB_PATH", str(db_path))
    monkeypatch.setattr(runtime_db, "_schema_path", None)
    monkeypatch.setattr(media_catalog, "_migration_checked_db_path", None)

    media_catalog.save_catalog([
        {
            "full_path": str(tmp_path / "movie.mp4"),
            "name": "Movie",
            "type": "video",
        }
    ])
    media_catalog.migrate_legacy_catalog(str(legacy_path))

    with patch("media_catalog.runtime_db.db_session") as db_session:
        media_catalog.migrate_legacy_catalog(str(legacy_path))

    db_session.assert_not_called()


def test_compact_catalog_omits_heavy_unused_metadata(monkeypatch):
    app = webfilm.app
    app.config["TESTING"] = True

    item = {
        "name": "Movie",
        "ext": "MP4",
        "type": "video",
        "full_path": "D:/Movies/movie.mp4",
        "folder": "Movies",
        "size": 123,
        "size_fmt": "123 MB",
        "mtime": 10,
        "date_added": 9,
        "views": 3,
        "categories": ["Studio: Demo"],
        "duration": 120,
        "is_offline": False,
        "jav_metadata": {
            "title": "Movie",
            "code": "ABC-123",
            "studio": "Demo",
            "actors": ["A"],
            "genres": ["Drama"],
            "source": "unused",
            "timestamp": 123456,
        },
        "nfo_metadata": {
            "plot": "large unused text",
            "art": {"fanart": ["a", "b", "c"]},
        },
    }

    with app.test_client() as client:
        authenticate_client(client)
        monkeypatch.setattr(
            "routes.api_video.cfg.load_cache_snapshot",
            lambda: [item],
        )
        with patch(
            "routes.api_video.cfg.load_cache",
            side_effect=AssertionError("compact listing should use RAM snapshot"),
        ):
            response = client.get("/api/videos?compact=1")

    payload = response.get_json()[0]
    assert "nfo_metadata" not in payload
    assert "source" not in payload["jav_metadata"]
    assert "timestamp" not in payload["jav_metadata"]
    assert payload["jav_metadata"]["code"] == "ABC-123"


def test_existing_thumbnail_skips_directory_creation(monkeypatch):
    app = webfilm.app
    app.config["TESTING"] = True
    created = []

    with app.test_client() as client:
        authenticate_client(client)
        monkeypatch.setattr(
            "routes.api_video._catalog_item",
            lambda _path: {"type": "video"},
        )
        monkeypatch.setattr(
            "routes.api_video.os.path.isfile",
            lambda _path: True,
        )
        monkeypatch.setattr(
            "routes.api_video.get_metadata_paths",
            lambda _path: {
                "thumb_dir": "thumbs",
                "prev_dir": "previews",
                "thumb_path": "thumb.jpg",
                "prev_path": "preview.mp4",
            },
        )
        monkeypatch.setattr(
            "routes.api_video.ensure_metadata_dirs",
            lambda _paths: created.append(True),
        )
        monkeypatch.setattr(
            "routes.api_video.os.path.exists",
            lambda _path: True,
        )
        monkeypatch.setattr(
            "routes.api_video.send_file",
            lambda _path: Response(b"thumb", mimetype="image/jpeg"),
        )

        response = client.get(
            "/api/thumbnail",
            query_string={"path": "movie.mp4"},
        )

    assert response.status_code == 200
    assert created == []
