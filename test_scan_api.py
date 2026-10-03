from unittest.mock import patch

from test_helpers import authenticate_client
from webfilm import app


def test_scan_api_starts_background_job():
    app.config["TESTING"] = True
    with app.test_client() as client:
        authenticate_client(client)
        with patch("routes.api_config.cfg.load_config", return_value={"video_dirs": ["A"]}), \
             patch("routes.api_config.scan_manager.start", return_value=(True, {
                 "status": "running",
                 "started_at": 1,
                 "finished_at": None,
                 "result_count": 0,
                 "error": "",
             })) as start:
            response = client.post("/api/scan")

    assert response.status_code == 202
    assert response.get_json()["started"] is True
    start.assert_called_once_with(["A"])


def test_scan_status_api_returns_manager_state():
    app.config["TESTING"] = True
    state = {
        "status": "done",
        "started_at": 1,
        "finished_at": 2,
        "result_count": 42,
        "error": "",
    }
    with app.test_client() as client:
        authenticate_client(client)
        with patch("routes.api_config.scan_manager.status", return_value=state):
            response = client.get("/api/scan/status")

    assert response.status_code == 200
    assert response.get_json()["result_count"] == 42
