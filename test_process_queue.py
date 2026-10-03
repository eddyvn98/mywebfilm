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
