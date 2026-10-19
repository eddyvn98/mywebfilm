from unittest.mock import patch

from test_helpers import authenticate_client
from webfilm import app


def test_legacy_highlight_endpoint_queues_job_without_running_ffmpeg():
    app.config["TESTING"] = True

    with app.test_client() as client:
        authenticate_client(client)
        with patch("routes.api_process._catalog_media", return_value=True), \
             patch("routes.api_process.media_queue.add_items") as add_items:
            response = client.post(
                "/api/process/highlight",
                json={"path": "D:/Movies/movie.mp4"},
            )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["queued"] is True
    add_items.assert_called_once_with(
        ["D:/Movies/movie.mp4"],
        task_type="highlight",
    )


def test_queue_worker_moves_sidecars_and_updates_catalog_on_highlight(tmp_path, monkeypatch):
    import queue_worker
    import config_manager as cfg

    movie = tmp_path / "movie.mp4"
    movie.write_bytes(b"dummy video")
    nfo = tmp_path / "movie.nfo"
    nfo.write_text("<movie><title>Test</title></movie>", encoding="utf-8")
    poster = tmp_path / "movie.jpg"
    poster.write_bytes(b"dummy poster")

    processed_dir = tmp_path / "Processed"
    processed_dir.mkdir()
    highlight_out = processed_dir / "movie_highlight.mp4"
    highlight_out.write_bytes(b"dummy highlight")

    monkeypatch.setattr(queue_worker.ff, "process_highlight_video", lambda p, d, delete_src=True: str(highlight_out))
    
    mock_catalog = [{"full_path": str(movie), "name": "movie", "ext": "MP4", "size": 100}]
    monkeypatch.setattr(cfg, "mutate_cache", lambda fn: fn(mock_catalog))
    monkeypatch.setattr(cfg, "load_config", lambda: {"video_dirs": [str(tmp_path)]})
    monkeypatch.setattr(cfg, "save_config", lambda c: None)

    q = queue_worker.MediaQueue()
    # Mock queue with one item and exit
    item = {
        "id": "test_id",
        "path": str(movie),
        "name": "movie.mp4",
        "type": "highlight",
        "status": "pending",
        "output": None,
        "error": None,
    }
    q.queue.put(item)
    q.is_running = True

    # Process one item manually to test the loop logic
    # Stop worker immediately after 1 get
    original_get = q.queue.get
    def get_once(*args, **kwargs):
        val = original_get(*args, **kwargs)
        q.is_running = False
        return val
    monkeypatch.setattr(q.queue, "get", get_once)

    q._worker_loop()

    assert (processed_dir / "movie_highlight.nfo").exists()
    assert (processed_dir / "movie_highlight.jpg").exists()
    assert not nfo.exists()
    assert not poster.exists()
    assert mock_catalog[0]["full_path"] == str(highlight_out)
    assert mock_catalog[0]["name"] == "movie_highlight"

