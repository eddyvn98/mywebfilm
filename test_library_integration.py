from unittest.mock import patch

import config_manager as cfg
import runtime_db
from webfilm import app
from test_helpers import authenticate_client


def test_library_filesystem_flow_survives_restart(tmp_path, monkeypatch):
    media_root = tmp_path / "media"
    target = media_root / "target"
    media_root.mkdir()
    target.mkdir()
    source = media_root / "movie.mp4"
    source.write_bytes(b"video")

    monkeypatch.setattr(runtime_db, "DB_PATH", str(tmp_path / "cinema_state.db"))
    monkeypatch.setattr(runtime_db, "_schema_path", None)
    monkeypatch.setattr(cfg, "CACHE_FILE", str(tmp_path / "movies_cache.json"))
    monkeypatch.setattr(
        cfg,
        "load_config",
        lambda: {"video_dirs": [str(media_root)]},
    )

    cfg.save_cache([{
        "full_path": str(source),
        "name": "movie",
        "folder": media_root.name,
        "views": 4,
        "type": "video",
        "ext": "MP4",
    }])

    app.config["TESTING"] = True
    with app.test_client() as client:
        authenticate_client(client)

        listed = client.get("/api/videos").get_json()
        assert listed[0]["full_path"] == str(source)

        with patch("routes.api_fs.sync_artifacts"):
            renamed = client.post(
                "/api/fs/rename",
                json={"old_path": str(source), "new_name": "renamed.mp4"},
            )
        assert renamed.status_code == 200
        renamed_path = media_root / "renamed.mp4"

        with patch("routes.api_video.os.startfile", create=True):
            played = client.post(
                "/api/play",
                json={"path": str(renamed_path), "type": "image"},
            )
        assert played.status_code == 200

        with patch("routes.api_fs.sync_artifacts"):
            moved = client.post(
                "/api/fs/move",
                json={"paths": [str(renamed_path)], "target_dir": str(target)},
            )
        assert moved.status_code == 200
        moved_path = target / "renamed.mp4"

        catalog = client.get("/api/videos").get_json()
        assert catalog[0]["full_path"] == str(moved_path)
        assert catalog[0]["views"] == 5

        diagnostics = client.get("/api/diagnostics/operations").get_json()
        assert diagnostics["operations"] == []

        deleted = client.post("/api/delete_file", json={"path": str(moved_path)})
        assert deleted.status_code == 200
        assert client.get("/api/videos").get_json() == []

    monkeypatch.setattr(runtime_db, "_schema_path", None)
    assert cfg.load_cache() == []
