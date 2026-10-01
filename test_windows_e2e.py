import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

import config_manager as cfg
import ffmpeg_service as ff
import runtime_db
from webfilm import app
from test_helpers import authenticate_client

pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows-only E2E suite",
)


@pytest.fixture
def windows_client(tmp_path, monkeypatch):
    media_root = tmp_path / "media"
    media_root.mkdir()
    monkeypatch.setattr(runtime_db, "DB_PATH", str(tmp_path / "cinema_state.db"))
    monkeypatch.setattr(runtime_db, "_schema_path", None)
    monkeypatch.setattr(cfg, "CACHE_FILE", str(tmp_path / "movies_cache.json"))
    monkeypatch.setattr(
        cfg,
        "load_config",
        lambda: {"video_dirs": [str(media_root)]},
    )
    app.config["TESTING"] = True
    with app.test_client() as client:
        authenticate_client(client)
        yield client, media_root


def test_windows_play_uses_startfile(windows_client):
    client, media_root = windows_client
    source = media_root / "photo.jpg"
    source.write_bytes(b"image")
    cfg.save_cache([{"full_path": str(source), "type": "image", "views": 0}])

    with patch("routes.api_video.os.startfile", create=True) as startfile:
        resp = client.post(
            "/api/play",
            json={"path": str(source), "type": "image"},
        )

    assert resp.status_code == 200
    startfile.assert_called_once_with(str(source))
    assert cfg.load_cache()[0]["views"] == 1


def test_windows_explorer_select_command(windows_client):
    client, media_root = windows_client
    source = media_root / "movie.mp4"
    source.write_bytes(b"video")

    with patch("routes.api_fs.subprocess.run") as run:
        resp = client.post("/api/explorer", json={"path": str(source)})

    assert resp.status_code == 200
    command = run.call_args.args[0]
    assert command[0].lower() == "explorer"
    assert "/select," in command


def test_windows_path_guard_rejects_sibling(tmp_path, monkeypatch):
    import utils

    allowed = tmp_path / "allowed"
    sibling = tmp_path / "allowed-escape"
    allowed.mkdir()
    sibling.mkdir()
    monkeypatch.setattr(
        cfg,
        "load_config",
        lambda: {"video_dirs": [str(allowed)]},
    )

    assert utils.check_path_safe(str(allowed / "movie.mp4")) is True
    assert utils.check_path_safe(str(sibling / "secret.mp4")) is False


def test_batch_launchers_are_repository_relative():
    root = Path(__file__).resolve().parent
    sorter = (root / "start_sorter.bat").read_text(encoding="utf-8")
    cinema = (root / "run_cinema.bat").read_text(encoding="utf-8")

    assert 'cd /d "%~dp0"' in sorter
    assert 'cd /d "%~dp0"' in cinema
    assert "D:\\CinemaProject" not in sorter
    assert "D:\\CinemaProject" not in cinema


@pytest.mark.skipif(
    os.environ.get("RUN_WINDOWS_FFMPEG_E2E") != "1",
    reason="Set RUN_WINDOWS_FFMPEG_E2E=1 for real FFmpeg validation",
)
def test_real_windows_ffmpeg_roundtrip(tmp_path):
    output = tmp_path / "probe.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc=size=160x90:rate=10",
            "-t", "1",
            "-pix_fmt", "yuv420p",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    assert ff.validate_media_output(str(output)) is True


@pytest.mark.skipif(
    not (
        os.environ.get("CINEMA_WINDOWS_TEST_ROOT_A")
        and os.environ.get("CINEMA_WINDOWS_TEST_ROOT_B")
    ),
    reason="Set disposable Windows test roots for real cross-drive move",
)
def test_real_cross_drive_move(monkeypatch):
    root_a = Path(os.environ["CINEMA_WINDOWS_TEST_ROOT_A"]).resolve()
    root_b = Path(os.environ["CINEMA_WINDOWS_TEST_ROOT_B"]).resolve()
    if root_a.drive.lower() == root_b.drive.lower():
        pytest.skip("Cross-drive roots must be on different drives")

    token = "mywebfilm-e2e-" + uuid.uuid4().hex[:8]
    source_dir = root_a / token
    target_dir = root_b / token
    source_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True)
    source = source_dir / "cross-drive.mp4"
    source.write_bytes(b"video")

    monkeypatch.setattr(
        cfg,
        "load_config",
        lambda: {"video_dirs": [str(source_dir), str(target_dir)]},
    )
    try:
        shutil.move(str(source), str(target_dir / source.name))
        assert not source.exists()
        assert (target_dir / source.name).exists()
    finally:
        shutil.rmtree(source_dir, ignore_errors=True)
        shutil.rmtree(target_dir, ignore_errors=True)
