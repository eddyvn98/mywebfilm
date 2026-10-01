import errno
from unittest.mock import patch

import pytest

import config_manager as cfg
import operation_journal
import runtime_db
from webfilm import app
from test_helpers import authenticate_client


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_db, "DB_PATH", str(tmp_path / "cinema_state.db"))
    monkeypatch.setattr(runtime_db, "_schema_path", None)
    monkeypatch.setattr(cfg, "CACHE_FILE", str(tmp_path / "movies_cache.json"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        authenticate_client(client)
        yield client


def test_locked_delete_keeps_file_and_records_failure(client, tmp_path):
    source = tmp_path / "locked.mp4"
    source.write_bytes(b"video")
    cfg.save_cache([{"full_path": str(source), "name": "locked"}])

    with patch("routes.api_fs.check_path_safe", return_value=True), \
         patch("routes.api_fs.os.remove", side_effect=PermissionError("file locked")):
        resp = client.post("/api/delete_file", json={"path": str(source)})

    assert resp.status_code == 500
    assert source.exists()
    assert resp.get_json()["filesystem_changed"] is False

    incomplete = operation_journal.list_incomplete_operations()
    assert len(incomplete) == 1
    assert incomplete[0]["op_type"] == "delete"
    assert incomplete[0]["status"] == "failed"
    assert "file locked" in incomplete[0]["detail"]


def test_locked_rename_keeps_source_and_records_failure(client, tmp_path):
    source = tmp_path / "locked.mp4"
    source.write_bytes(b"video")
    cfg.save_cache([{"full_path": str(source), "name": "locked"}])

    with patch("routes.api_fs.check_path_safe", return_value=True), \
         patch("routes.api_fs.os.rename", side_effect=PermissionError("rename locked")):
        resp = client.post(
            "/api/fs/rename",
            json={"old_path": str(source), "new_name": "renamed.mp4"},
        )

    assert resp.status_code == 500
    assert source.exists()
    assert not (tmp_path / "renamed.mp4").exists()
    assert resp.get_json()["filesystem_changed"] is False

    incomplete = operation_journal.list_incomplete_operations()
    assert len(incomplete) == 1
    assert incomplete[0]["op_type"] == "rename"
    assert "rename locked" in incomplete[0]["detail"]


def test_disk_full_after_move_records_recovery_evidence(client, tmp_path):
    source = tmp_path / "move.mp4"
    source.write_bytes(b"video")
    target = tmp_path / "target"
    target.mkdir()
    cfg.save_cache([{"full_path": str(source), "folder": tmp_path.name}])

    disk_full = OSError(errno.ENOSPC, "No space left on device")
    with patch("routes.api_fs.check_path_safe", return_value=True), \
         patch("routes.api_fs.move_in_catalog", side_effect=disk_full), \
         patch("routes.api_fs.sync_artifacts"):
        resp = client.post(
            "/api/fs/move",
            json={"paths": [str(source)], "target_dir": str(target)},
        )

    assert resp.status_code == 500
    assert not source.exists()
    assert (target / "move.mp4").exists()
    payload = resp.get_json()
    assert payload["filesystem_changed"] is True
    assert "catalog update failed" in payload["msg"]

    incomplete = operation_journal.list_incomplete_operations()
    assert len(incomplete) == 1
    assert incomplete[0]["status"] == "failed"
    assert "No space left on device" in incomplete[0]["detail"]
