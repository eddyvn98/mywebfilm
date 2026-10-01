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


def test_delete_operation_completes_journal(client, tmp_path):
    source = tmp_path / "delete.mp4"
    source.write_bytes(b"video")
    cfg.save_cache([{"full_path": str(source), "name": "delete"}])

    with patch("routes.api_fs.check_path_safe", return_value=True):
        resp = client.post("/api/delete_file", json={"path": str(source)})

    assert resp.status_code == 200
    assert not source.exists()
    assert cfg.load_cache() == []
    assert resp.get_json()["operation_id"]
    assert operation_journal.list_incomplete_operations() == []


def test_rename_reports_partial_when_artifact_sync_fails(client, tmp_path):
    source = tmp_path / "old.mp4"
    source.write_bytes(b"video")
    cfg.save_cache([{
        "full_path": str(source),
        "name": "old.mp4",
        "folder": tmp_path.name,
    }])

    with patch("routes.api_fs.check_path_safe", return_value=True),          patch("routes.api_fs.sync_artifacts", side_effect=RuntimeError("artifact boom")):
        resp = client.post(
            "/api/fs/rename",
            json={"old_path": str(source), "new_name": "new.mp4"},
        )

    assert resp.status_code == 207
    payload = resp.get_json()
    assert payload["status"] == "partial"
    assert not source.exists()
    assert (tmp_path / "new.mp4").exists()
    assert cfg.load_cache()[0]["full_path"] == str(tmp_path / "new.mp4")

    incomplete = operation_journal.list_incomplete_operations()
    assert len(incomplete) == 1
    assert incomplete[0]["status"] == "failed"
    assert "artifact boom" in incomplete[0]["detail"]


def test_move_records_failure_when_catalog_write_fails(client, tmp_path):
    source = tmp_path / "move.mp4"
    source.write_bytes(b"video")
    target = tmp_path / "target"
    target.mkdir()
    cfg.save_cache([{"full_path": str(source), "folder": tmp_path.name}])

    with patch("routes.api_fs.check_path_safe", return_value=True),          patch("routes.api_fs.move_in_catalog", side_effect=RuntimeError("catalog boom")),          patch("routes.api_fs.sync_artifacts"):
        resp = client.post(
            "/api/fs/move",
            json={"paths": [str(source)], "target_dir": str(target)},
        )

    assert resp.status_code == 500
    assert not source.exists()
    assert (target / "move.mp4").exists()
    assert resp.get_json()["filesystem_changed"] is True

    incomplete = operation_journal.list_incomplete_operations()
    assert len(incomplete) == 1
    assert incomplete[0]["status"] == "failed"
    assert "catalog update failed" in incomplete[0]["detail"]


def test_diagnostics_lists_incomplete_operations(client):
    op_id = operation_journal.begin_operation("move", "a.mp4", "b.mp4")
    operation_journal.update_operation(op_id, "filesystem_done")

    resp = client.get("/api/diagnostics/operations")

    assert resp.status_code == 200
    operations = resp.get_json()["operations"]
    assert operations[0]["id"] == op_id
    assert operations[0]["status"] == "filesystem_done"
