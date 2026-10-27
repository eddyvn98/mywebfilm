"""Regression tests for private actor photos and legacy migration."""
from io import BytesIO
from urllib.parse import quote

import pytest

import actor_image_store as photos
from test_helpers import authenticate_client
from webfilm import app


@pytest.fixture
def isolated_photos(tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(photos, "DATA_DIR", str(tmp_path / "private"))
    return tmp_path


def test_safe_actor_names_reject_traversal_and_windows_devices(isolated_photos):
    for name in ("../evil", r"..\evil", "CON", "nul.jpg", "", "  ", "/", "a/b"):
        with pytest.raises(ValueError):
            photos.actor_image_filename(name)
    assert photos.actor_image_filename("藤原 凛") == "藤原_凛.jpg"
    assert photos.actor_image_filename("A  B.JPG") == "A_B.jpg"


def test_legacy_photos_are_removed_from_public_static_before_requests(isolated_photos):
    old = isolated_photos / "static" / "img" / "actors"
    old.mkdir(parents=True)
    (old / "Alice.jpg").write_bytes(b"legacy-alice")
    (old / "Conflict.jpg").write_bytes(b"legacy-conflict")
    private = isolated_photos / "private" / "actors"
    private.mkdir(parents=True)
    (private / "Conflict.jpg").write_bytes(b"current-conflict")
    assert photos.migrate_legacy_actor_images() == 1
    assert not old.exists()
    assert (private / "Alice.jpg").read_bytes() == b"legacy-alice"
    assert (private / "Conflict.jpg").read_bytes() == b"current-conflict"
    quarantine = isolated_photos / ".cinema-legacy-actor-images"
    assert (quarantine / "Conflict.jpg").read_bytes() == b"legacy-conflict"
    assert photos.migrate_legacy_actor_images() == 0


def test_actor_photos_auth_upload_and_read(isolated_photos):
    app.config["TESTING"] = True
    filename = "藤原_凛.jpg"
    img_path = photos.actor_image_path(filename)
    with app.test_client() as client:
        assert client.get("/api/actor_image/" + quote(filename)).status_code == 401
        authenticate_client(client)
        resp = client.post(
            "/api/admin/upload_actor_image",
            data={"name": "藤原 凛",
                  "image": (BytesIO(b"\xff\xd8\xffpicture"), "photo.jpg")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        assert resp.get_json()["url"] == "/api/actor_image/" + quote(filename)
        assert __import__("os").path.isfile(img_path)
        image = client.get(resp.get_json()["url"])
        assert image.status_code == 200
        assert image.data == b"\xff\xd8\xffpicture"
        assert "no-store" in image.headers.get("Cache-Control", "")


def test_private_photo_endpoint_never_serves_sibling_directory(isolated_photos):
    private = isolated_photos / "private"
    outside = private / "actors-other"
    outside.mkdir(parents=True)
    (outside / "secret.jpg").write_bytes(b"secret")
    app.config["TESTING"] = True
    with app.test_client() as client:
        authenticate_client(client)
        for target in ("../actors-other/secret.jpg",
                       "folder/../../actors-other/secret.jpg",
                       "foo\\bar.jpg"):
            result = client.get("/api/actor_image/" + quote(target))
            assert result.status_code in (403, 404)
            assert result.data != b"secret"
