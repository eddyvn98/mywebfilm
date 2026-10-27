"""Regression tests for AI metadata-driven rename security."""
from unittest.mock import patch

import pytest

from media_rename_security import plan_ai_media_rename
from test_helpers import authenticate_client
from webfilm import app


@pytest.mark.parametrize("code", [
    "../escape", r"..\escape", "A/B", r"A\B", "A:B",
    " ", "a" * 65,
])
def test_ai_media_rename_rejects_untrusted_codes(code, tmp_path):
    with pytest.raises(ValueError):
        plan_ai_media_rename(
            str(tmp_path / "movie.mp4"),
            {"code": code, "title": "Movie"},
        )


def test_ai_media_rename_stays_in_same_directory(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    filename, target = plan_ai_media_rename(
        str(root / "movie.mp4"),
        {"code": "ABP-123", "title": r"日本語 / test: title"},
    )
    assert filename == "[ABP-123] 日本語  test title.mp4"
    assert target == str(root / filename)


def test_ai_media_rename_rejects_invalid_title(tmp_path):
    for title in ("", "..", "/", None):
        with pytest.raises(ValueError):
            plan_ai_media_rename(
                str(tmp_path / "movie.mp4"), {"code": "ABP-123", "title": title}
            )


def test_ai_inject_unsafe_rename_has_no_side_effects(tmp_path, monkeypatch):
    import config_manager as cfg
    media = tmp_path / "media"
    media.mkdir()
    source = media / "movie.mp4"
    source.write_bytes(b"dummy")
    monkeypatch.setattr(cfg, "load_config", lambda: {"video_dirs": [str(media)]})
    app.config["TESTING"] = True

    with app.test_client() as client:
        authenticate_client(client)
        with patch("routes.api_ai.metadata_injector.save_metadata_fast") as save:
            response = client.post(
                "/api/ai/inject",
                json={
                    "filename": "movie.mp4",
                    "path": str(source),
                    "rename": True,
                    "metadata": {"code": "../escape", "title": "Movie"},
                },
            )
        assert response.status_code == 400
        save.assert_not_called()
    assert source.exists()
    assert not list(media.glob("*.nfo"))


def test_ai_inject_destination_must_be_authorized(tmp_path, monkeypatch):
    import config_manager as cfg
    media = tmp_path / "media"
    media.mkdir()
    source = media / "movie.mp4"
    source.write_bytes(b"dummy")
    monkeypatch.setattr(cfg, "load_config", lambda: {"video_dirs": [str(media)]})
    app.config["TESTING"] = True

    with app.test_client() as client:
        authenticate_client(client)
        with patch("routes.api_ai.check_path_safe", side_effect=[True, False]), \
             patch("routes.api_ai.metadata_injector.save_metadata_fast") as save:
            response = client.post(
                "/api/ai/inject",
                json={
                    "filename": "movie.mp4",
                    "path": str(source),
                    "rename": True,
                    "metadata": {"code": "ABP-123", "title": "Movie"},
                },
            )
        assert response.status_code == 403
        save.assert_not_called()


def test_ai_inject_refuses_to_overwrite_existing_file(tmp_path, monkeypatch):
    import config_manager as cfg
    media = tmp_path / "media"
    media.mkdir()
    source = media / "movie.mp4"
    source.write_bytes(b"source")
    existing = media / "[ABP-123] Movie.mp4"
    existing.write_bytes(b"existing")
    monkeypatch.setattr(cfg, "load_config", lambda: {"video_dirs": [str(media)]})
    app.config["TESTING"] = True

    with app.test_client() as client:
        authenticate_client(client)
        with patch("routes.api_ai.metadata_injector.save_metadata_fast") as save:
            response = client.post(
                "/api/ai/inject",
                json={
                    "filename": "movie.mp4",
                    "path": str(source),
                    "rename": True,
                    "metadata": {"code": "ABP-123", "title": "Movie"},
                },
            )
        assert response.status_code == 409
        save.assert_not_called()
    assert source.read_bytes() == b"source"
    assert existing.read_bytes() == b"existing"
