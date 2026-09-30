import errno
import json
import os

import pytest

import backup_service
import runtime_db
from webfilm import app


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

    with pytest.raises(ValueError, match="checksum mismatch"):
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
        with client.session_transaction() as sess:
            sess["authenticated"] = True

        resp = client.post(
            "/api/backup/restore",
            json={"backup_id": manifest["backup_id"]},
        )

    assert resp.status_code == 400
    assert "RESTORE" in resp.get_json()["msg"]
