import json

import config_manager


def test_load_config_dedupes_video_dirs_and_persists_normalized_file(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "video_dirs": [
                    "E:\\",
                    "D:\\CinemaProject\\static",
                    "E:\\",
                    "D:\\CinemaProject\\templates",
                    "D:\\CinemaProject\\static",
                ],
                "auto_convert_ts": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config_manager, "CONFIG_FILE", str(cfg_path))
    monkeypatch.setattr(config_manager, "_config_cache", None)
    monkeypatch.setattr(config_manager, "_config_mtime", 0)

    config = config_manager.load_config()

    assert config["video_dirs"] == [
        "E:\\",
        "D:\\CinemaProject\\static",
        "D:\\CinemaProject\\templates",
    ]

    persisted = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert persisted["video_dirs"] == [
        "E:\\",
        "D:\\CinemaProject\\static",
        "D:\\CinemaProject\\templates",
    ]
