import errno
import json
import os

import pytest

import backup_service
import runtime_db
from webfilm import app
from test_helpers import authenticate_client


@pytest.fixture
def backup_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    backup_dir = data_dir / "backups"
    config = tmp_path / "config.json"
    tags = tmp_path / "tags.json"
    credentials = data_dir / "credentials.json"

    monkeypatch.setattr(runtime_db, "DB_PATH", str(data_dir / "cinema_state.db"))
    monkeypatch.setattr(runtime_db, "_schema_path", None)
    monkeypatch.setattr(backup_service, "BACKUP_DIR", str(backup_dir))
    monkeypatch.setattr(backup_service, "CONFIG_FILE", str(config))
    monkeypatch.setattr(backup_service, "TAGS_FILE", str(tags))
    monkeypatch.setattr(backup_service, "CREDENTIALS_FILE", str(credentials))
    import actor_image_store
    monkeypatch.setattr(actor_image_store, "DATA_DIR", str(data_dir))

    config.write_text(json.dumps({"video_dirs": ["D:/Media"]}), encoding="utf-8")
    tags.write_text(json.dumps({"genres": ["Drama"]}), encoding="utf-8")
    credentials.write_text(json.dumps({"admin": []}), encoding="utf-8")
    runtime_db.save_list_state("history", [{"full_path": "before.mp4"}])

    return {
        "data_dir": data_dir,
        "backup_dir": backup_dir,
        "config": config,
        "tags": tags,
        "credentials": credentials,
    }


def test_backup_create_and_verify(backup_env):
    manifest = backup_service.create_backup()

    verified = backup_service.verify_backup(manifest["backup_id"])

    assert verified["backup_id"] == manifest["backup_id"]
    assert "cinema_state.db" in verified["files"]
    assert "config.json" in verified["files"]
    assert "credentials.json" in verified["files"]
    assert "tags.json" in verified["files"]


def test_corrupt_backup_is_rejected(backup_env):
    manifest = backup_service.create_backup()
    backup_path = backup_env["backup_dir"] / manifest["backup_id"]
    (backup_path / "config.json").write_text("tampered", encoding="utf-8")

    with pytest.raises(ValueError, match="mismatch"):
        backup_service.verify_backup(manifest["backup_id"])


def test_backup_failure_preserves_previous_valid_backup(backup_env, monkeypatch):
    good = backup_service.create_backup()

    monkeypatch.setattr(
        backup_service,
        "_backup_database",
        lambda _destination: (_ for _ in ()).throw(
            OSError(errno.ENOSPC, "No space left on device")
        ),
    )

    with pytest.raises(OSError):
        backup_service.create_backup()

    entries = [
        name for name in os.listdir(backup_env["backup_dir"])
        if not name.startswith(".")
    ]
    assert entries == [good["backup_id"]]
    assert not any(name.startswith(".backup-") for name in os.listdir(backup_env["backup_dir"]))


def test_restore_recovers_database_and_files(backup_env):
    target = backup_service.create_backup(cleanup=False)

    runtime_db.save_list_state("history", [{"full_path": "after.mp4"}])
    backup_env["config"].write_text(json.dumps({"video_dirs": ["E:/Changed"]}), encoding="utf-8")

    result = backup_service.restore_backup(target["backup_id"])

    assert result["restart_required"] is True
    assert runtime_db.load_list_state("history") == [{"full_path": "before.mp4"}]
    assert json.loads(backup_env["config"].read_text(encoding="utf-8")) == {
        "video_dirs": ["D:/Media"]
    }


def test_failed_restore_rolls_back_to_emergency_backup(backup_env, monkeypatch):
    target = backup_service.create_backup(cleanup=False)

    runtime_db.save_list_state("history", [{"full_path": "current.mp4"}])
    backup_env["config"].write_text(json.dumps({"video_dirs": ["E:/Current"]}), encoding="utf-8")

    original = backup_service._atomic_restore_file
    raised = {"done": False}

    def fail_once(source, destination):
        if destination == str(backup_env["config"]) and not raised["done"]:
            raised["done"] = True
            raise PermissionError("config locked")
        return original(source, destination)

    monkeypatch.setattr(backup_service, "_atomic_restore_file", fail_once)

    with pytest.raises(PermissionError, match="config locked"):
        backup_service.restore_backup(target["backup_id"])

    assert runtime_db.load_list_state("history") == [{"full_path": "current.mp4"}]
    assert json.loads(backup_env["config"].read_text(encoding="utf-8")) == {
        "video_dirs": ["E:/Current"]
    }


def test_backup_id_rejects_path_traversal(backup_env):
    with pytest.raises(ValueError, match="Invalid backup id"):
        backup_service.verify_backup("../../outside")


def test_restore_api_requires_explicit_confirmation(backup_env):
    manifest = backup_service.create_backup(cleanup=False)
    app.config["TESTING"] = True

    with app.test_client() as client:
        authenticate_client(client)

        resp = client.post(
            "/api/backup/restore",
            json={"backup_id": manifest["backup_id"]},
        )

    assert resp.status_code == 400
    assert "RESTORE" in resp.get_json()["msg"]


def test_restore_removes_files_absent_from_backup(backup_env):
    backup_env["credentials"].unlink()
    target = backup_service.create_backup(cleanup=False)

    backup_env["credentials"].write_text(
        json.dumps({"admin": [{"id": "new"}]}),
        encoding="utf-8",
    )
    assert backup_env["credentials"].exists()

    backup_service.restore_backup(target["backup_id"])

    assert not backup_env["credentials"].exists()


def test_private_actor_photos_are_part_of_backup_and_restore(backup_env):
    import actor_image_store
    from pathlib import Path

    actors = Path(actor_image_store.actor_image_dir())
    actors.mkdir(parents=True)
    (actors / "Alice.jpg").write_bytes(b"original-jpeg")
    target = backup_service.create_backup(cleanup=False)
    assert backup_service.ACTOR_ARCHIVE in target["files"]

    (actors / "Alice.jpg").write_bytes(b"mutated-jpeg")
    (actors / "New.jpg").write_bytes(b"not-in-backup")
    backup_service.restore_backup(target["backup_id"])

    assert (actors / "Alice.jpg").read_bytes() == b"original-jpeg"
    assert not (actors / "New.jpg").exists()


def test_legacy_backup_preserves_current_private_photos(backup_env):
    import actor_image_store
    from pathlib import Path

    actors = Path(actor_image_store.actor_image_dir())
    actors.mkdir(parents=True)
    (actors / "Alice.jpg").write_bytes(b"preserve-legacy")
    target = backup_service.create_backup(cleanup=False)
    folder = Path(backup_service._backup_path(target["backup_id"]))
    (folder / backup_service.ACTOR_ARCHIVE).unlink()
    backup_service._write_manifest(
        str(folder),
        backup_service._manifest_for(str(folder), target["backup_id"]),
    )

    backup_service.restore_backup(target["backup_id"])
    assert (actors / "Alice.jpg").read_bytes() == b"preserve-legacy"


def test_actor_archive_rejects_path_traversal_before_file_swap(backup_env):
    import io
    import tarfile
    from pathlib import Path
    import actor_image_store

    actors = Path(actor_image_store.actor_image_dir())
    actors.mkdir(parents=True)
    (actors / "Safe.jpg").write_bytes(b"safe")
    target = backup_service.create_backup(cleanup=False)
    folder = Path(backup_service._backup_path(target["backup_id"]))
    with tarfile.open(folder / backup_service.ACTOR_ARCHIVE, "w:gz") as archive:
        payload = b"malicious"
        info = tarfile.TarInfo("../escaped.jpg")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    backup_service._write_manifest(
        str(folder),
        backup_service._manifest_for(str(folder), target["backup_id"]),
    )

    with pytest.raises(ValueError, match="Invalid actor name|Unsafe actor name"):
        backup_service.restore_backup(target["backup_id"])
    assert (actors / "Safe.jpg").read_bytes() == b"safe"
    assert not (backup_env["data_dir"] / "escaped.jpg").exists()
