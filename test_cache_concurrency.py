import threading

import config_manager as cfg
import runtime_db


def test_cache_concurrency(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_db, "DB_PATH", str(tmp_path / "cinema_state.db"))
    monkeypatch.setattr(runtime_db, "_schema_path", None)
    monkeypatch.setattr(cfg, "CACHE_FILE", str(tmp_path / "movies_cache.json"))

    cfg.save_cache([
        {"full_path": "dummy1.mp4", "views": 10},
        {"full_path": "dummy2.mp4", "views": 5},
    ])

    errors = []

    def worker():
        try:
            for _ in range(30):
                assert cfg.increment_views("dummy1.mp4") is True
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    final_data = cfg.load_cache()
    assert final_data[0]["views"] == 310
