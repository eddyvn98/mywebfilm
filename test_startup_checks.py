from unittest.mock import patch

import pytest

from webfilm import app
import startup_checks


def test_startup_checks_ready_when_dependencies_available(tmp_path, monkeypatch):
    media = tmp_path / "media"
    media.mkdir()
    data_dir = tmp_path / "data"

    monkeypatch.setattr(
        startup_checks.shutil,
        "which",
        lambda command: f"/usr/bin/{command}",
    )
    monkeypatch.setattr(startup_checks.runtime_db, "ensure_schema", lambda: None)

    checks = startup_checks.run_startup_checks(
        config={"video_dirs": [str(media)]},
        data_dir=str(data_dir),
    )

    assert checks["ready"] is True
    assert checks["ffmpeg"] is True
    assert checks["ffprobe"] is True
    assert checks["data_dir_writable"] is True
    assert checks["sqlite"] is True
    assert checks["media_roots_available"] == 1
    assert checks["media_roots_missing"] == 0


def test_startup_checks_degraded_without_media_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(startup_checks.shutil, "which", lambda command: None)
    monkeypatch.setattr(startup_checks.runtime_db, "ensure_schema", lambda: None)

    checks = startup_checks.run_startup_checks(
        config={"video_dirs": []},
        data_dir=str(tmp_path / "data"),
    )

    assert checks["ready"] is False
    assert checks["ffmpeg"] is False
    assert checks["ffprobe"] is False


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["authenticated"] = True
        yield client


def test_health_reports_readiness_without_local_paths(client):
    fake_checks = {
        "ready": True,
        "ffmpeg": True,
        "ffprobe": True,
        "data_dir_writable": True,
        "sqlite": True,
        "media_roots_configured": 2,
        "media_roots_available": 1,
        "media_roots_missing": 1,
    }
    fake_config = {
        "video_dirs": ["D:/SecretMedia", "E:/AnotherSecret"],
        "gemini_api_key": "secret",
    }

    with patch("routes.api_config.cfg.load_config", return_value=fake_config), \
         patch("routes.api_config.run_startup_checks", return_value=fake_checks):
        resp = client.get("/api/health")

    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "ok"
    assert payload["readiness"] == fake_checks
    serialized = resp.get_data(as_text=True)
    assert "D:/SecretMedia" not in serialized
    assert "secret" not in serialized
